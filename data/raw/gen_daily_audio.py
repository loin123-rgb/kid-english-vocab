#!/usr/bin/env python3
"""
用 edge-tts 把 articles.json 每篇文章預生成神經音 MP3。
存進 data/audio/daily/article_<id>.mp3,前端靜態載入。

跑法:
  pip install edge-tts
  python gen_daily_audio.py             # 只生缺的
  python gen_daily_audio.py --force     # 全部重生
"""
import asyncio
import json
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).parent.parent.parent
ARTICLES = ROOT / "data" / "articles.json"
OUT_DIR = ROOT / "data" / "audio" / "daily"
VOICE = "en-US-AriaNeural"
RATE = "-5%"   # 文章稍慢一點,小朋友比較跟得上;前端 slider 還可以再調
CONCURRENCY = 3
MAX_ARTICLES = 45   # 上限 45 篇,超過的文章前端會自動 fallback 瀏覽器 TTS,避免 repo 越塞越大


async def gen_one(sem, article, force, total, n):
    out = OUT_DIR / f"article_{article['id']}.mp3"
    if out.exists() and not force:
        return f"[{n}/{total}] skip {out.name}"
    async with sem:
        try:
            communicate = edge_tts.Communicate(article["text"], VOICE, rate=RATE)
            await communicate.save(str(out))
            sz = out.stat().st_size
            return f"[{n}/{total}] OK   {out.name} ({sz//1024}KB)"
        except Exception as e:
            return f"[{n}/{total}] FAIL {out.name}: {e}"


async def main():
    force = "--force" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    data = json.loads(ARTICLES.read_text(encoding="utf-8"))
    all_articles = data["articles"]
    # 只生前 MAX_ARTICLES 篇,超過的前端會自動 fallback 瀏覽器 TTS
    articles = all_articles[:MAX_ARTICLES]
    skipped_count = max(0, len(all_articles) - MAX_ARTICLES)
    print(f"目標: {len(articles)} 篇文章 (上限 {MAX_ARTICLES},超過 {skipped_count} 篇走 TTS fallback)")
    print(f"輸出: {OUT_DIR}")
    print(f"voice: {VOICE}, rate: {RATE}, force={force}\n")

    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [gen_one(sem, a, force, len(articles), i+1) for i, a in enumerate(articles)]
    for fut in asyncio.as_completed(tasks):
        print(await fut)

    files = list(OUT_DIR.glob("article_*.mp3"))
    total = sum(p.stat().st_size for p in files)
    print(f"\n完成: {len(files)} 個檔, 共 {total//1024}KB")


if __name__ == "__main__":
    asyncio.run(main())
