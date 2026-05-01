#!/usr/bin/env python3
"""
把 vocab_moe.json 的英文字批次丟去 DeepL 拿中譯初稿。

讀:vocab_moe.json
寫:vocab_moe.json (in-place 更新 zh 欄位)

用法:
  python translate_with_deepl.py            # 跑全部還沒翻的
  python translate_with_deepl.py --limit 20 # 只跑 20 個試試
  python translate_with_deepl.py --force    # 連已經有中譯的也重翻

API key 從 ../../.env 讀(專案根目錄的那份),欄位名 DEEPL_API_KEY。
Free key 結尾 :fx → 走 api-free.deepl.com,沒結尾 → 走 api.deepl.com (Pro)。

注意:這只是「初稿」,小朋友看的最終中譯一定要人工校過再用。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
PROJECT_ROOT = ROOT.parent.parent
VOCAB = ROOT / "vocab_moe.json"
ENV_FILE = PROJECT_ROOT / ".env"

BATCH_SIZE = 50  # DeepL 單次 request 最多 50 個 text
RETRY_DELAY = 3  # 失敗重試前等幾秒
MAX_RETRIES = 3


def load_env_key() -> str:
    """從 .env 讀 DEEPL_API_KEY"""
    if not ENV_FILE.exists():
        sys.exit(
            f"找不到 {ENV_FILE},請先 cp .env.example .env 並填入 DEEPL_API_KEY"
        )
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == "DEEPL_API_KEY":
            v = v.strip().strip('"').strip("'")
            if v:
                return v
    sys.exit(f"{ENV_FILE} 裡沒有 DEEPL_API_KEY=... 那行,或是值是空的")


def deepl_endpoint(key: str) -> str:
    return (
        "https://api-free.deepl.com/v2/translate"
        if key.endswith(":fx")
        else "https://api.deepl.com/v2/translate"
    )


def normalize_for_translation(word: str) -> str:
    """
    把 'be (am, is, are, was, were, been)' 這種變化型清掉,只翻 base form。
    把 'airplane (plane)' 的別稱也清掉。
    """
    # 去掉括號內的所有東西
    cleaned = re.sub(r"\s*\([^)]*\)", "", word)
    # 去掉斜線後的別稱('a/an' → 'a')— 取第一個
    cleaned = cleaned.split("/")[0]
    return cleaned.strip()


def deepl_translate_batch(key: str, words: list[str]) -> list[str]:
    """送一批字到 DeepL,回傳對應順序的中譯 list"""
    if not words:
        return []

    data_pairs = [("target_lang", "ZH-HANT"), ("source_lang", "EN")]
    for w in words:
        data_pairs.append(("text", w))
    body = urllib.parse.urlencode(data_pairs).encode("utf-8")

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                deepl_endpoint(key),
                data=body,
                headers={
                    "Authorization": f"DeepL-Auth-Key {key}",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "kid-english-vocab/0.1 batch-translate",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return [t.get("text", "") for t in payload.get("translations", [])]
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
            last_err = f"HTTP {e.code}: {err_body}"
            if e.code in (429, 456, 503):
                # rate limit / quota / temporary → retry
                wait = RETRY_DELAY * attempt
                print(f"  ⚠ DeepL {e.code},等 {wait}s 重試 ({attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            # 401/403/400 → key 壞了/參數錯,重試也沒用
            sys.exit(f"DeepL 拒絕請求:{last_err}")
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = str(e)
            wait = RETRY_DELAY * attempt
            print(f"  ⚠ 網路錯誤 {e},等 {wait}s 重試 ({attempt}/{MAX_RETRIES})")
            time.sleep(wait)
    sys.exit(f"DeepL 重試 {MAX_RETRIES} 次仍失敗:{last_err}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="只跑前 N 個還沒翻的字(0 = 跑全部)")
    ap.add_argument("--force", action="store_true",
                    help="連已經有中譯的也重翻")
    ap.add_argument("--dry-run", action="store_true",
                    help="只顯示會送什麼,不真的打 API")
    args = ap.parse_args()

    key = load_env_key()
    print(f"使用 endpoint: {deepl_endpoint(key)}")
    print(f"Key 結尾: ...{key[-6:]}")

    data = json.loads(VOCAB.read_text(encoding="utf-8"))
    words = data["words"]

    # 找需要翻的
    todo_idxs = []
    for i, e in enumerate(words):
        if args.force or not e.get("zh"):
            todo_idxs.append(i)
    if args.limit > 0:
        todo_idxs = todo_idxs[: args.limit]

    print(f"需要翻譯:{len(todo_idxs)} / {len(words)} 字")
    if not todo_idxs:
        print("沒東西要翻,結束。")
        return

    if args.dry_run:
        print("\n=== Dry run 範例(前 5 個) ===")
        for i in todo_idxs[:5]:
            w = words[i]["word"]
            print(f"  '{w}' → 會送 '{normalize_for_translation(w)}'")
        return

    # 分批跑
    start = time.time()
    for batch_start in range(0, len(todo_idxs), BATCH_SIZE):
        batch_idxs = todo_idxs[batch_start : batch_start + BATCH_SIZE]
        batch_originals = [words[i]["word"] for i in batch_idxs]
        batch_to_send = [normalize_for_translation(w) for w in batch_originals]

        translations = deepl_translate_batch(key, batch_to_send)

        if len(translations) != len(batch_idxs):
            print(f"  ⚠ DeepL 回傳數量不對:{len(translations)} vs {len(batch_idxs)},跳過這批")
            continue

        for i, zh in zip(batch_idxs, translations):
            words[i]["zh"] = zh.strip()

        # 每批存一次,中途死不會白跑
        VOCAB.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        done = batch_start + len(batch_idxs)
        total = len(todo_idxs)
        elapsed = time.time() - start
        eta = (elapsed / done) * (total - done) if done else 0
        print(f"  [{done}/{total}] 已存檔 — 剩約 {eta:.0f}s")

    print(f"\n完成。總耗時 {time.time() - start:.0f}s")
    print("提醒:這是 DeepL 初稿,記得人工校過再上線。")


if __name__ == "__main__":
    main()
