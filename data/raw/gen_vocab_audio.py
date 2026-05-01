#!/usr/bin/env python3
"""
用 edge-tts 把 vocab.json 全部 2004 字生成神經音 MP3。
存進 data/audio/vocab/word_<safe>.mp3,前端載靜態檔(0 API 呼叫)。

跑法:
  pip install edge-tts
  python gen_vocab_audio.py             # 只生缺的
  python gen_vocab_audio.py --force     # 全部重生
"""
import asyncio
import json
import re
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).parent.parent.parent
VOCAB = ROOT / "data" / "vocab.json"
OUT_DIR = ROOT / "data" / "audio" / "vocab"
VOICE = "en-US-AriaNeural"
RATE = "-10%"           # vocab 不用太慢
CONCURRENCY = 4


def safe_filename(word: str) -> str:
    # 去掉括號內變化 ("be (am, is, are)" → "be") 和斜線後別稱
    cleaned = re.sub(r"\s*\([^)]*\)", "", word)
    cleaned = cleaned.split("/")[0].strip()
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", cleaned.lower()).strip("_")
    return f"word_{safe}.mp3"


def text_to_speak(word: str) -> str:
    # 送 TTS 的乾淨文字 (去括號 / 取斜線前)
    cleaned = re.sub(r"\s*\([^)]*\)", "", word)
    return cleaned.split("/")[0].strip()


async def gen_one(sem, word, force, total, n):
    out = OUT_DIR / safe_filename(word)
    if out.exists() and not force:
        return None  # silent skip
    text = text_to_speak(word)
    if not text:
        return f"SKIP {word!r} (empty after normalize)"
    async with sem:
        try:
            communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
            await communicate.save(str(out))
            sz = out.stat().st_size
            return f"[{n}/{total}] OK   {out.name} ({sz//1024}KB)"
        except Exception as e:
            return f"[{n}/{total}] FAIL {word!r} → {e}"


async def main():
    force = "--force" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    data = json.loads(VOCAB.read_text(encoding="utf-8"))
    words = [e["word"] for e in data["words"]]
    print(f"目標字數: {len(words)}")
    print(f"輸出目錄: {OUT_DIR}")
    print(f"voice: {VOICE}, rate: {RATE}, force={force}\n")

    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [gen_one(sem, w, force, len(words), i + 1) for i, w in enumerate(words)]

    skipped = 0
    for fut in asyncio.as_completed(tasks):
        msg = await fut
        if msg is None:
            skipped += 1
        else:
            print(msg)

    files = list(OUT_DIR.glob("word_*.mp3"))
    total = sum(p.stat().st_size for p in files)
    print(f"\n完成。共 {len(files)} 個檔, {total//1024}KB ({total//1024//1024}MB),"
          f" 此次跳過 {skipped} 個既存檔。")


if __name__ == "__main__":
    asyncio.run(main())
