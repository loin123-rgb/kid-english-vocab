#!/usr/bin/env python3
"""
用 LLM 替每個單字產生兒童英語插圖 prompt,寫進 image_prompts.csv。
取代 gen_image_prompts.py 的「分類 → template」拼字串作法,因為:
  - 動詞被誤分類塞名詞 template (bite/boil/burn 都炸)
  - a/an 文法錯
  - 多義字沒看中譯選義項 (bat = 蝙蝠 vs 球棒)
  - 風格詞蓋過主體

用法:
  1. 先去 https://console.groq.com 申請免費 API key
  2. 在專案根目錄 .env 加一行: GROQ_API_KEY=xxxxx
  3. pip install requests
  4. 跑:
       python gen_image_prompts_llm.py                   # P1+P2 全做
       python gen_image_prompts_llm.py --priority 1      # 只做 P1
       python gen_image_prompts_llm.py --priority 1,2,3  # 連抽象動詞也做
       python gen_image_prompts_llm.py --limit 30        # 試 30 字
       python gen_image_prompts_llm.py --rebuild         # 砍掉重來

  腳本會「續跑」:已存在於 csv 的字會保留,只補沒做的。中途中斷不會全沒。
"""
import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

# Windows cp950 console 印不出 unicode 箭頭/符號 -> 強制 utf-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).parent
REPO_ROOT = ROOT.parent.parent
VOCAB = ROOT.parent / "vocab.json"
OUT = ROOT / "image_prompts.csv"

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# 風格後綴 — 由腳本端統一加,LLM 不負責,確保風格一致
STYLE_SUFFIX = (
    ", flat clean illustration, soft pastel colors, "
    "plain white background, centered composition, no text, no letters"
)

# 沿用舊版的優先序分類
HIGH_PRI_CATS = {
    "Animals & insects", "Food & drinks", "Tableware",
    "Clothing & accessories", "Houses & apartments", "Transportation",
    "Sports, interests & hobbies", "Holidays & festivals", "Occupations",
    "Weather & nature", "Geographical terms",
}
MID_PRI_CATS = {
    "People", "Parts of body", "Health", "School", "Places & locations",
    "Colors", "Family",
}
ABSTRACT_CATS = {
    "Other nouns", "Time", "Money", "Sizes & measurements", "Numbers",
    "Languages", "Forms of address", "Personal characteristics",
    "Articles & determiners", "Prepositions", "Conjunctions",
    "Pronouns & reflexives", "Wh-words", "Be & auxiliaries",
    "Interjections", "Other verbs",
}

# 完全不畫:純語法詞,即使 LLM 想盡辦法也只會畫文字
SKIP_CATEGORIES = {
    "Articles & determiners", "Prepositions", "Conjunctions",
    "Pronouns & reflexives", "Wh-words", "Be & auxiliaries", "Interjections",
}
# 副詞也不畫(almost/again/also 之類概念視覺化會亂生)
SKIP_POS = {"prep", "conj", "det", "pron", "aux", "art", "interj", "adv"}
# 字典 pos 標錯,實際是副詞/語法詞,個別硬擋
SKIP_WORDS_HARD = {"almost", "ago", "abroad"}


SYSTEM_PROMPT = """你是兒童英語單字插圖的 prompt 設計師,替 Stable Diffusion 寫一句視覺描述。
對象: 台灣國中小學生 (8~15 歲)。

最高原則: **圖一打開,孩子就能直覺把字記起來**。
視覺辨識度 > 字典義項對齊。簡單、清楚、印象鮮明。

規則:
1. 一句英文 prompt,純視覺、無文字。
2. 多義字: 選「最容易畫清楚、最具標誌性、國中小最熟悉」的義項。
   **詞性對齊 — 以「中譯詞語本身」判斷,不要看 pos 欄位** (字典 pos 常標錯):
   - 中譯是事物名 (公園/植物/海浪/日期/罐頭/火柴/月份/銀行) → 畫該事物
   - 中譯是動作 (跑步/跌倒/烤/玩/解釋/飛) → 畫人或動物做這動作
   - 中譯是形容詞/狀態 (害怕/開心/累) → 畫表情或情境
   - 若 pos="v" 但中譯是事物名 (例: park 中譯「公園」、plant 中譯「植物」、
     wave 中譯「海浪」、date 中譯「日期」),**一律畫事物,不要畫動作**
   - 中譯既能是物又能是動作時 (如 fly = 飛 / 蒼蠅),選國中小最常見義項
   視覺優先用在「同詞性下的義項選擇」,不能因此切換詞性。例:
   - bank (銀行,名詞) → "a bank building with columns and a clock"
   - light (光,名詞) → "a glowing yellow light bulb"
   - spring (春天,名詞) → "blooming pink cherry blossoms in spring"
   - match (火柴,名詞) → "a single matchstick with a burning flame"
   - park (公園,名詞) → "a green park with trees and a bench" (絕不畫「停車」)
   - plant (植物,名詞) → "a single potted green plant" (絕不畫「種樹」動作)
   - wave (海浪,名詞) → "a big blue ocean wave" (絕不畫「揮手」)
   - May (五月,名詞) → "a calendar page showing May with flowers"
   - can (罐頭,名詞義) → "a metal soda can" (中譯雖是「能」,選具象同形名詞)
   - run (跑,動詞) → "a cartoon child running fast"
   - fly (飛,動詞) → "a colorful bird flying in the sky"
   - bake (烤,動詞) → "a cartoon child taking a cake out of an oven"
3. 動詞: 「a cartoon child + 動作」,動作要明顯誇張、容易看出。
   例: run → "a cartoon child running fast with motion lines"
       jump → "a cartoon child jumping high in the air"
4. 抽象名詞: 挑最具標誌性的具象畫面。
   例: time → "a large round wall clock"
       air → "a blue sky with white clouds and floating leaves"
5. 形容詞: 用人物表情/姿勢誇張呈現。
   例: angry → "an angry cartoon child with red face stomping"
       happy → "a cartoon child laughing with both arms raised"
6. 具象名詞: **主體獨佔、特徵清楚、最少背景**。
   不好: "an apple on a wooden table" (桌子稀釋主體)
   好:   "a single shiny red apple, vivid color, simple shape"
   不好: "a wooden board on a table"
   好:   "a green school chalkboard with a wooden frame"
   不好: "a brown shoe on a wooden floor"
   好:   "a single brown leather shoe, side view"
7. 文法: a/an 不可錯 (an apple / an envelope / an old clock)。
8. **絕不寫風格詞** (watercolor / cartoon style / pastel / illustration / colorful)。
9. **絕不寫負面詞** (no text / no shadow / no background)。
10. 8~18 字, 名詞短語為主, "a ..." 開頭。

只輸出 JSON: {"results": [{"word": "...", "prompt": "..."}, ...]}
不要解釋、不要 markdown、不要程式碼框。
"""


def lookup_key(word: str) -> str:
    """去括號、去斜線後的乾淨字,給 LLM 用、也用來比對回應。
    例: 'math (mathematics)' -> 'math'; 'shoe (s)' -> 'shoe'"""
    cleaned = re.sub(r"\s*\(.*?\)", "", word)
    cleaned = cleaned.split("/")[0]
    return cleaned.strip().lower()


def safe_filename(word: str) -> str:
    cleaned = re.sub(r"\s*\([^)]*\)", "", word)
    cleaned = cleaned.split("/")[0]
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", cleaned.lower()).strip("_")
    return f"data/images/vocab/word_{safe}.webp"


def assign_priority(cats):
    if any(c in HIGH_PRI_CATS for c in cats):
        return 1
    if any(c in MID_PRI_CATS for c in cats):
        return 2
    if any(c in ABSTRACT_CATS for c in cats):
        return 3
    return 2


def is_skippable(entry):
    w = entry["word"]
    if entry.get("emoji"):
        return True
    if "/" in w or w.endswith("."):
        return True
    if len(w.split()) > 2:
        return True
    if entry.get("pos", "") in SKIP_POS:
        return True
    if w.lower() in SKIP_WORDS_HARD:
        return True
    cats = entry.get("categories", [])
    if cats and all(c in SKIP_CATEGORIES for c in cats):
        return True
    return False


def load_env(env_path: Path):
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def build_user_message(batch):
    lines = []
    for e in batch:
        cats = ",".join(e.get("categories", [])) or "(none)"
        # 餵 LLM 的 word 用清版本(去括號),回應好比對
        lines.append(
            f'- word="{lookup_key(e["word"])}", zh="{e.get("zh","")}", '
            f'pos="{e.get("pos","")}", categories="{cats}"'
        )
    return (
        "替下列單字各產生一句 prompt。"
        "務必依中譯選對義項、文法正確、a/an 不可錯。\n\n"
        + "\n".join(lines)
    )


def call_groq(api_key, system, user, retries=4):
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=90)
            if r.status_code == 429:
                # rate limit,等久一點
                wait = 30 + attempt * 15
                print(f"     -> 429 rate limit,{wait}s 後重試")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            last_err = e
            wait = 2 ** attempt
            print(f"     -> Groq 失敗 ({e}),{wait}s 後重試")
            time.sleep(wait)
    raise RuntimeError(f"Groq 連續失敗: {last_err}")


def parse_response(text):
    """LLM 設了 JSON mode,理論上回 {"results": [...]}。仍做幾道 fallback。"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return {}
        try:
            data = json.loads(m.group())
        except json.JSONDecodeError:
            return {}

    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # 抓第一個 list 值
        for v in data.values():
            if isinstance(v, list):
                items = v
                break

    out = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        w = item.get("word", "").strip()
        p = item.get("prompt", "").strip()
        if w and p:
            out[w.lower()] = p
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--priority", default="1,2",
                    help="逗號分隔優先序,預設 '1,2'。'1,2,3' 連抽象詞也做")
    ap.add_argument("--limit", type=int, default=0,
                    help="只處理前 N 個 (測試用)")
    ap.add_argument("--batch", type=int, default=15,
                    help="一次餵 LLM 多少字 (default 15)")
    ap.add_argument("--rebuild", action="store_true",
                    help="忽略既有 csv,全部重做")
    args = ap.parse_args()

    load_env(REPO_ROOT / ".env")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        sys.exit(
            "缺 GROQ_API_KEY。\n"
            "1. 去 https://console.groq.com 註冊 (免費)\n"
            "2. 建一支 API key\n"
            f"3. 在 {REPO_ROOT / '.env'} 加一行: GROQ_API_KEY=xxxxx"
        )

    data = json.loads(VOCAB.read_text(encoding="utf-8"))
    wanted_pri = set(args.priority.split(","))

    existing = {}
    if OUT.exists() and not args.rebuild:
        with open(OUT, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                existing[r["word"]] = r

    todo = []
    keep = []
    for e in data["words"]:
        if is_skippable(e):
            continue
        cats = e.get("categories", [])
        pri = assign_priority(cats)
        if str(pri) not in wanted_pri:
            continue
        if e["word"] in existing and not args.rebuild:
            keep.append(existing[e["word"]])
            continue
        todo.append({**e, "_priority": pri})

    if args.limit > 0:
        todo = todo[: args.limit]

    print(f"已存在保留 {len(keep)} 字,本次新產 {len(todo)} 字 "
          f"(priority={args.priority}, batch={args.batch})")
    if not todo:
        return

    rows = list(keep)
    failed = []
    start = time.time()

    for i in range(0, len(todo), args.batch):
        batch = todo[i : i + args.batch]
        user_msg = build_user_message(batch)
        try:
            text = call_groq(api_key, SYSTEM_PROMPT, user_msg)
        except Exception as e:
            print(f"[{i+1}-{i+len(batch)}] BATCH FAIL: {e}")
            failed.extend(batch)
            continue

        parsed = parse_response(text)

        for e in batch:
            key = lookup_key(e["word"])
            llm_prompt = (parsed.get(key)
                          or parsed.get(e["word"].strip().lower())
                          or parsed.get(e["word"].strip()))
            if not llm_prompt:
                failed.append(e)
                continue
            full_prompt = llm_prompt.rstrip(".").rstrip(",") + STYLE_SUFFIX
            rows.append({
                "priority": str(e["_priority"]),
                "word": e["word"],
                "zh": e.get("zh", ""),
                "category": (e.get("categories") or [""])[0],
                "filename": safe_filename(e["word"]),
                "prompt": full_prompt,
            })

        # 每批存盤一次,中斷不會全沒
        rows_sorted = sorted(rows, key=lambda r: (int(r["priority"]), r["word"].lower()))
        with open(OUT, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["priority", "word", "zh", "category", "filename", "prompt"],
            )
            writer.writeheader()
            writer.writerows(rows_sorted)

        done = i + len(batch)
        elapsed = time.time() - start
        eta = elapsed / done * (len(todo) - done) if done else 0
        ok_in_batch = sum(1 for e in batch if (parsed.get(e["word"].lower()) or parsed.get(e["word"])))
        print(f"[{done}/{len(todo)}] +{ok_in_batch}/{len(batch)} ok (ETA {eta:.0f}s)")

    print(f"\n完成: 寫入 {len(rows)} 字到 {OUT.name}, "
          f"失敗 {len(failed)} 字, 共 {time.time()-start:.0f}s")
    if failed:
        names = ", ".join(e["word"] for e in failed[:30])
        print(f"失敗字 (前 30): {names}")
        print("→ 直接再跑一次,腳本會續跑這些。")


if __name__ == "__main__":
    main()
