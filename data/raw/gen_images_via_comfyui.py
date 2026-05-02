#!/usr/bin/env python3
"""
讀 image_prompts.csv,呼叫本機 ComfyUI HTTP API 自動生圖。
產出 data/images/vocab/word_<safe>.webp。

前置:
  1. ComfyUI 啟動中(預設 http://127.0.0.1:8188)
  2. 你準備好的 workflow.json (API format) 放在同目錄,檔名 comfyui_workflow.json
     - 在 ComfyUI 介面建好你滿意的 workflow
     - Settings → 開啟「Enable Dev mode Options」
     - 點 Save (API Format) 存成 comfyui_workflow.json
     - 如果有多個 CLIPTextEncode,把「正面 prompt」那個節點的標題改成 POSITIVE

跑法:
  pip install Pillow
  python gen_images_via_comfyui.py                # 跑全部 P1
  python gen_images_via_comfyui.py --priority 1,2 # 跑 P1 + P2
  python gen_images_via_comfyui.py --limit 10     # 試 10 張
  python gen_images_via_comfyui.py --force        # 已生過的也重做
"""
import argparse
import csv
import io
import json
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent
REPO_ROOT = ROOT.parent.parent
CSV_PATH = ROOT / "image_prompts.csv"
WORKFLOW_PATH = ROOT / "comfyui_workflow.json"
COMFYUI_URL = "http://127.0.0.1:8188"
WEBP_SIZE = 512
WEBP_QUALITY = 85
POLL_INTERVAL = 1.0
TIMEOUT_PER_IMAGE = 180

# 反向 prompt — 擋 3D 立體化、詭異變形、文字、複雜背景
# 強化:多手多腳、器具變形、四肢比例怪
NEGATIVE_PROMPT = (
    "3D, render, photorealistic, realistic, photo, "
    "scary, dark, creepy, monster, ugly, "
    "deformed, mutated, distorted, malformed, disfigured, "
    "extra arms, extra legs, extra hands, extra fingers, extra feet, "
    "too many fingers, too many limbs, missing fingers, fused fingers, "
    "duplicated limbs, mutated hands, deformed hands, deformed legs, "
    "warped object, melted object, broken object, malformed object, "
    "distorted tools, weird props, asymmetric, wrong proportions, "
    "low quality, blurry, lowres, jpeg artifacts, oversaturated, noisy, "
    "text, watermark, signature, logo, letters, words, captions, "
    "multiple characters, multiple subjects, busy background, cluttered, "
    "bad anatomy, oversized eyes"
)


# ---------- ComfyUI HTTP helpers ----------
def queue_prompt(workflow: dict, client_id: str) -> str:
    body = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["prompt_id"]


def get_history(prompt_id: str) -> dict:
    with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}", timeout=15) as r:
        return json.loads(r.read())


def fetch_image(filename: str, subfolder: str, type_: str) -> bytes:
    qs = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": type_})
    with urllib.request.urlopen(f"{COMFYUI_URL}/view?{qs}", timeout=30) as r:
        return r.read()


# ---------- workflow injection ----------
def find_positive_node(workflow: dict) -> str:
    """找正面 prompt 節點 id。優先找標題含 POSITIVE 的,fallback 第一個 CLIPTextEncode。"""
    # First: explicit title hint
    for nid, node in workflow.items():
        title = (node.get("_meta", {}) or {}).get("title", "").lower()
        if "positive" in title and node.get("class_type") == "CLIPTextEncode":
            return nid
    # Fallback: first CLIPTextEncode
    for nid, node in workflow.items():
        if node.get("class_type") == "CLIPTextEncode":
            return nid
    raise RuntimeError("找不到 CLIPTextEncode 節點 — workflow 是不是 API format?")


def find_negative_node(workflow: dict, positive_node_id: str) -> str | None:
    """找反向 prompt 節點 id。優先找標題含 negative 的,fallback 第二個 CLIPTextEncode。"""
    # First: explicit title hint
    for nid, node in workflow.items():
        title = (node.get("_meta", {}) or {}).get("title", "").lower()
        if "negative" in title and node.get("class_type") == "CLIPTextEncode":
            return nid
    # Fallback: 找另一個 CLIPTextEncode (不是 positive 那個)
    encodes = [nid for nid, node in workflow.items()
               if node.get("class_type") == "CLIPTextEncode"]
    for nid in encodes:
        if nid != positive_node_id:
            return nid
    return None  # workflow 沒有反向節點 (極少見)


def inject_prompt(workflow: dict, positive_node_id: str, negative_node_id: str | None,
                  prompt: str, neg_prompt: str, seed: int):
    workflow[positive_node_id]["inputs"]["text"] = prompt
    if negative_node_id:
        workflow[negative_node_id]["inputs"]["text"] = neg_prompt
    # 換 KSampler 的 seed (找第一個有 seed 欄位的節點)
    for node in workflow.values():
        if node.get("class_type") in ("KSampler", "KSamplerAdvanced"):
            if "seed" in node.get("inputs", {}):
                node["inputs"]["seed"] = seed
                break
            if "noise_seed" in node.get("inputs", {}):
                node["inputs"]["noise_seed"] = seed
                break


# ---------- per-image flow ----------
def png_to_webp(png_bytes: bytes, out_path: Path):
    img = Image.open(io.BytesIO(png_bytes))
    if img.mode in ("RGBA", "LA"):
        # 強制白底,小朋友看比較乾淨
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    if img.size != (WEBP_SIZE, WEBP_SIZE):
        img = img.resize((WEBP_SIZE, WEBP_SIZE), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=WEBP_QUALITY)


def generate_one(workflow_template: dict, positive_node_id: str, negative_node_id: str | None,
                 prompt: str, target: Path, seed: int) -> bool:
    workflow = json.loads(json.dumps(workflow_template))  # deep copy
    inject_prompt(workflow, positive_node_id, negative_node_id, prompt, NEGATIVE_PROMPT, seed)

    client_id = str(uuid.uuid4())
    prompt_id = queue_prompt(workflow, client_id)

    deadline = time.time() + TIMEOUT_PER_IMAGE
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        try:
            hist = get_history(prompt_id)
        except Exception:
            continue
        if prompt_id not in hist:
            continue
        record = hist[prompt_id]
        # 看有沒有 error
        status = record.get("status", {})
        if status.get("status_str") == "error":
            msgs = status.get("messages", [])
            err = next((m for m in msgs if m and m[0] == "execution_error"), None)
            if err:
                print(f"   ↳ ComfyUI error: {err[1].get('exception_message', err)[:200]}")
            return False
        outputs = record.get("outputs", {})
        for node_out in outputs.values():
            for img_info in node_out.get("images", []):
                png = fetch_image(
                    img_info["filename"],
                    img_info.get("subfolder", ""),
                    img_info.get("type", "output"),
                )
                png_to_webp(png, target)
                return True
        # 沒抓到 images — 把整個 outputs 印出來方便 debug
        print(f"   ↳ 沒在 outputs 找到 images。outputs 內容: {json.dumps(outputs)[:300]}")
        return False
    return False  # timeout


# ---------- main loop ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--priority", default="1",
                    help="逗號分隔的優先序,預設 '1'。例 '1,2' / '1,2,3'")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true",
                    help="已生過的也重做")
    args = ap.parse_args()

    if not WORKFLOW_PATH.exists():
        sys.exit(
            f"找不到 {WORKFLOW_PATH}\n"
            "請先在 ComfyUI 介面儲存 API format workflow,放這個位置。"
        )

    workflow_template = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    positive_node_id = find_positive_node(workflow_template)
    negative_node_id = find_negative_node(workflow_template, positive_node_id)
    print(f"使用 positive prompt 節點: {positive_node_id}")
    print(f"使用 negative prompt 節點: {negative_node_id or '(workflow 沒反向節點,跳過)'}")

    wanted = set(args.priority.split(","))
    rows = []
    with open(CSV_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["priority"] not in wanted:
                continue
            rows.append(r)
    if args.limit > 0:
        rows = rows[: args.limit]

    print(f"目標: {len(rows)} 張 (priority={args.priority}, force={args.force})")
    if not rows:
        return

    start = time.time()
    ok = fail = skip = 0
    for i, row in enumerate(rows, 1):
        target = REPO_ROOT / row["filename"]
        if target.exists() and not args.force:
            skip += 1
            print(f"[{i}/{len(rows)}] skip {target.name}")
            continue
        seed = abs(hash(row["word"])) % (2**31)
        try:
            success = generate_one(workflow_template, positive_node_id, negative_node_id,
                                   row["prompt"], target, seed)
            if success:
                ok += 1
                elapsed = time.time() - start
                eta = (elapsed / (ok + fail)) * (len(rows) - i) if (ok + fail) else 0
                print(f"[{i}/{len(rows)}] OK   {target.name} (ETA {eta:.0f}s)")
            else:
                fail += 1
                print(f"[{i}/{len(rows)}] FAIL {target.name} (timeout / no output)")
        except Exception as e:
            fail += 1
            print(f"[{i}/{len(rows)}] ERR  {target.name}: {e}")

    print(f"\n完成: ok={ok} fail={fail} skip={skip}, 共 {time.time()-start:.0f}s")


if __name__ == "__main__":
    main()
