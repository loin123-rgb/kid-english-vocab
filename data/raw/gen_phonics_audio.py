#!/usr/bin/env python3
"""
用 edge-tts (Microsoft Edge Neural Voice) 一次性把全部 phonics 音檔生成 MP3,
分兩種:
  data/audio/phonics/sound_<key>.mp3   字母音(用標準 phonics 近似詞 ah/buh/kuh...)
  data/audio/phonics/word_<safe>.mp3   例字 (apple/ball/cat...)

為什麼 edge-tts 而不是 Azure/ElevenLabs:
  - 同源 Microsoft 神經音、品質一樣
  - 完全免費 + 不用註冊 + 不用 key
  - 一次生完就靜態化,後續完全不依賴外部服務(連大陸都通)

跑法:
  pip install edge-tts
  python gen_phonics_audio.py             # 只生缺的
  python gen_phonics_audio.py --force     # 全部重生
"""
import asyncio
import re
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).parent.parent.parent
OUT_DIR = ROOT / "data" / "audio" / "phonics"
VOICE = "en-US-AriaNeural"
RATE_WORD = "-15%"     # 例字慢一點
RATE_SOUND = "-25%"    # 字母音再慢一點,讓小朋友聽清楚
CONCURRENCY = 4

# ===== 字母音近似詞 — 標準 phonics 教法 =====
# (TTS 會自動加上 schwa 是業界已知問題,但小朋友聽得懂,Hooked on Phonics 也這樣)
LETTER_SOUNDS = {
    "a": "ah",     "b": "buh",    "c": "kah",    "d": "duh",
    "e": "eh",     "f": "fuh",    "g": "gah",    "h": "huh",
    "i": "in",     "j": "juh",    "k": "kit",    "l": "lll",
    "m": "muh",    "n": "nuh",    "o": "ah",     "p": "puh",
    "q": "kwuh",   "r": "ruh",    "s": "suh",    "t": "tuh",
    "u": "uh",     "v": "vuh",    "w": "woo",    "x": "ax",
    "y": "yee",    "z": "zuh",
}

# 雙字母發音
DIGRAPH_SOUNDS = {
    "sh": "shuh",
    "ch": "chuh",
    "th": "thuh",
    "wh": "wuh",
    "ph": "fuh",
    "ng": "ung",
    "ck": "koo",
    "qu": "kwuh",
}

# 母音團發音
VOWEL_TEAM_SOUNDS = {
    "ai": "ay",   "ay": "ay",
    "ee": "ee",   "ea": "ee",
    "ie": "eye",  "igh": "eye",
    "oa": "oh",   "ow": "oh",
    "oo": "ooh",  "ue": "ooh",
    "ar": "are",  "or": "or",
    "er": "er",   "ir": "er",  "ur": "er",
}

# Magic E 沒有獨立的「音」,跳過 (前端只播例字)
MAGIC_E_SOUNDS = {}

# Blends 也只播例字
BLEND_SOUNDS = {}

# ===== 例字 (跟 index.html 裡的 PHONICS_* 對齊) =====
LETTERS = [
    "apple", "ball", "cat", "dog", "egg", "fish", "goat", "hat",
    "ink", "jump", "key", "lion", "mouse", "nose", "orange", "pig",
    "queen", "rabbit", "sun", "tiger", "umbrella", "van", "water",
    "fox", "yellow", "zebra",
]
DIGRAPHS_WORDS = ["ship", "chair", "three", "whale", "phone", "ring", "duck", "queen"]
MAGIC_E_WORDS = ["cake", "bike", "rope", "cute", "these"]
VOWEL_TEAMS_WORDS = [
    "rain", "play", "bee", "tea", "pie", "light", "boat", "snow",
    "moon", "blue", "car", "horse", "her", "bird", "burn",
]
BLENDS_WORDS = [
    "blue", "brown", "clock", "crab", "drum", "flag", "frog", "glass",
    "grape", "plane", "prize", "scarf", "skate", "sleep", "smile", "snake",
    "spoon", "star", "swim", "tree", "twin", "spring", "string",
]


def safe_key(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", s.lower()).strip("_")


def word_filename(word: str) -> str:
    return f"word_{safe_key(word)}.mp3"


def sound_filename(key: str) -> str:
    return f"sound_{safe_key(key)}.mp3"


async def gen_one(sem, text, out_path, rate, force=False):
    if out_path.exists() and not force:
        return f"skip {out_path.name}"
    async with sem:
        try:
            communicate = edge_tts.Communicate(text, VOICE, rate=rate)
            await communicate.save(str(out_path))
            sz = out_path.stat().st_size
            return f"OK   {out_path.name:30} ('{text}', {sz//1024}KB)"
        except Exception as e:
            return f"FAIL {out_path.name:30} → {e}"


async def main():
    force = "--force" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 字母音 / 雙字母 / 母音團 → sound_*.mp3
    sound_tasks = []
    for d in (LETTER_SOUNDS, DIGRAPH_SOUNDS, VOWEL_TEAM_SOUNDS):
        for key, approximation in d.items():
            sound_tasks.append((approximation, OUT_DIR / sound_filename(key), RATE_SOUND))

    # 2. 例字 → word_*.mp3
    all_words = sorted(set(
        LETTERS + DIGRAPHS_WORDS + MAGIC_E_WORDS + VOWEL_TEAMS_WORDS + BLENDS_WORDS
    ))
    word_tasks = [(w, OUT_DIR / word_filename(w), RATE_WORD) for w in all_words]

    print(f"字母音 / 雙字母 / 母音團: {len(sound_tasks)} 個")
    print(f"例字: {len(word_tasks)} 個")
    print(f"輸出目錄: {OUT_DIR}")
    print(f"voice: {VOICE}, force={force}\n")

    sem = asyncio.Semaphore(CONCURRENCY)
    all_tasks = [gen_one(sem, t, p, r, force) for t, p, r in sound_tasks + word_tasks]
    results = await asyncio.gather(*all_tasks)
    for r in results:
        print(r)

    files = list(OUT_DIR.glob("*.mp3"))
    total = sum(p.stat().st_size for p in files)
    print(f"\n完成:{len(files)} 個檔, 共 {total//1024}KB")


if __name__ == "__main__":
    asyncio.run(main())
