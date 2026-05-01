#!/usr/bin/env python3
"""
用 Google 免費非官方翻譯端點翻 vocab_moe.json。

跟 translate_with_deepl.py 一樣會 in-place 更新 zh 欄位,但:
  - 不用 API key、不用註冊
  - 走 translate.google.com/translate_a/single — 非官方端點
  - 一次只能翻一個字串,不能 batch → 加 0.5s 延遲避免被擋
  - 大陸地區用不了(被牆)
  - Google 改規則時可能失效

用法:
  python translate_with_google.py            # 跑全部還沒翻的
  python translate_with_google.py --limit 30 # 只跑 30 個試品質
  python translate_with_google.py --force    # 連已經有中譯的也重翻
  python translate_with_google.py --delay 0.3  # 調延遲 (預設 0.5s)

對 2004 字 + 0.5s 延遲約 17 分鐘可以跑完。
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
VOCAB = ROOT / "vocab_moe.json"

ENDPOINT = "https://translate.google.com/translate_a/single"
USER_AGENT = "Mozilla/5.0 (compatible; kid-english-vocab/0.1)"
MAX_RETRIES = 3
BASE_DELAY = 0.5


def normalize_for_translation(word: str) -> str:
    """跟 DeepL 版一樣:去掉括號變化型 / 取斜線前的形式"""
    cleaned = re.sub(r"\s*\([^)]*\)", "", word)
    cleaned = cleaned.split("/")[0]
    return cleaned.strip()


def google_translate_one(text: str, target: str = "zh-TW", source: str = "en") -> str:
    """打 Google 免費端點翻單字。回傳合併後的中譯字串。"""
    params = {
        "client": "gtx",
        "sl": source,
        "tl": target,
        "dt": "t",
        "q": text,
    }
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            # 結構:[[[zh, en, null, null, 1], ...], null, "en", ...]
            if not data or not data[0]:
                return ""
            return "".join(
                seg[0] for seg in data[0] if isinstance(seg, list) and seg and seg[0]
            )
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code in (429, 503):
                wait = BASE_DELAY * 4 * attempt
                print(f"  ⚠ {last_err},等 {wait:.0f}s 重試 ({attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = str(e)
            wait = BASE_DELAY * 4 * attempt
            print(f"  ⚠ 錯誤 {e},等 {wait:.0f}s 重試 ({attempt}/{MAX_RETRIES})")
            time.sleep(wait)
    raise RuntimeError(f"Google 翻譯重試 {MAX_RETRIES} 次仍失敗:{last_err}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--delay", type=float, default=BASE_DELAY)
    args = ap.parse_args()

    data = json.loads(VOCAB.read_text(encoding="utf-8"))
    words = data["words"]

    todo_idxs = [
        i for i, e in enumerate(words)
        if args.force or not e.get("zh")
    ]
    if args.limit > 0:
        todo_idxs = todo_idxs[: args.limit]

    print(f"需要翻譯:{len(todo_idxs)} / {len(words)} 字,延遲 {args.delay}s/字")
    if not todo_idxs:
        print("沒東西要翻,結束。")
        return

    start = time.time()
    save_every = 25  # 每 25 字存一次

    for n, i in enumerate(todo_idxs, 1):
        word = words[i]["word"]
        send = normalize_for_translation(word)
        try:
            zh = google_translate_one(send)
        except Exception as e:
            print(f"  ✗ 第 {n} 字 '{word}' 失敗:{e}")
            zh = ""

        words[i]["zh"] = zh.strip()

        if n % save_every == 0 or n == len(todo_idxs):
            VOCAB.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            elapsed = time.time() - start
            eta = (elapsed / n) * (len(todo_idxs) - n)
            print(f"  [{n}/{len(todo_idxs)}] 已存檔 — 剩約 {eta:.0f}s")

        time.sleep(args.delay)

    print(f"\n完成。總耗時 {time.time() - start:.0f}s")
    print("提醒:這是 Google 初稿,記得人工校過再上線。")


if __name__ == "__main__":
    main()
