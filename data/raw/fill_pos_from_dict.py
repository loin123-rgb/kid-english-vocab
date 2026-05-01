#!/usr/bin/env python3
"""
把 vocab_moe.json 裡 pos 還空著的字 (~397) 用 dictionaryapi.dev 補上。

dictionaryapi.dev:
  GET https://api.dictionaryapi.dev/api/v2/entries/en/<word>
  → array of entries, each有 meanings[].partOfSpeech

只跑單字 (含空格的片語直接略過)。每字延遲 0.3s。
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

API = "https://api.dictionaryapi.dev/api/v2/entries/en/"
DELAY = 0.3
MAX_RETRIES = 2

POS_MAP = {
    "noun": "n",
    "proper noun": "n",
    "verb": "v",
    "adjective": "adj",
    "adverb": "adv",
    "preposition": "prep",
    "conjunction": "conj",
    "pronoun": "pron",
    "interjection": "int",
    "exclamation": "int",
    "determiner": "det",
    "article": "det",
    "numeral": "num",
    "number": "num",
    "auxiliary": "v",
    "modal": "v",
}


def normalize_for_lookup(word: str) -> str:
    cleaned = re.sub(r"\s*\([^)]*\)", "", word)
    cleaned = cleaned.split("/")[0]
    return cleaned.strip()


def lookup_pos(word: str) -> str:
    """打 dictionaryapi.dev 抓第一個 meaning 的 pos,失敗回空字串"""
    url = API + urllib.parse.quote(word)
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "kid-english-vocab/0.1 pos-fill"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if not isinstance(data, list) or not data:
                return ""
            for entry in data:
                for m in entry.get("meanings", []):
                    raw_pos = (m.get("partOfSpeech") or "").lower()
                    if raw_pos in POS_MAP:
                        return POS_MAP[raw_pos]
            return ""
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ""  # 字典裡沒這個字,正常
            last_err = f"HTTP {e.code}"
            time.sleep(DELAY * 2 * attempt)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = str(e)
            time.sleep(DELAY * 2 * attempt)
    print(f"  ✗ {word}: {last_err}", file=sys.stderr)
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true",
                    help="連已經有 pos 的也重跑(用來覆蓋分類推估的不準結果)")
    args = ap.parse_args()

    data = json.loads(VOCAB.read_text(encoding="utf-8"))
    words = data["words"]

    todo = []
    for i, e in enumerate(words):
        if args.force or not e.get("pos"):
            # 片語跳過(dictionaryapi.dev 只認單字)
            if " " in e["word"]:
                continue
            todo.append(i)
    if args.limit > 0:
        todo = todo[: args.limit]

    print(f"要補 pos 的單字: {len(todo)}")
    if not todo:
        return

    start = time.time()
    save_every = 50
    hit = miss = 0

    for n, i in enumerate(todo, 1):
        word = words[i]["word"]
        send = normalize_for_lookup(word)
        pos = lookup_pos(send)
        if pos:
            words[i]["pos"] = pos
            hit += 1
        else:
            miss += 1

        if n % save_every == 0 or n == len(todo):
            VOCAB.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            elapsed = time.time() - start
            eta = (elapsed / n) * (len(todo) - n)
            print(f"  [{n}/{len(todo)}] hit={hit} miss={miss} 已存檔 — 剩約 {eta:.0f}s")

        time.sleep(DELAY)

    print(f"\n完成:hit={hit} miss={miss},總耗時 {time.time()-start:.0f}s")


if __name__ == "__main__":
    main()
