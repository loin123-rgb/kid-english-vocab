"""產 A-Z 字母歌朗讀 MP3。TTS 不會唱歌,但可以照節奏唸"""
import asyncio
import edge_tts
from pathlib import Path

OUT = Path(__file__).parent.parent / "audio" / "phonics" / "abc_song.mp3"
VOICE = "en-US-AriaNeural"

# 仿 phonics 字母歌節奏:每個字母讀字母名 + 例字
LETTERS = [
    ("A","apple"),("B","ball"),("C","cat"),("D","dog"),
    ("E","egg"),("F","fish"),("G","goat"),("H","hat"),
    ("I","ink"),("J","jump"),("K","key"),("L","lion"),
    ("M","mouse"),("N","nose"),("O","orange"),("P","pig"),
    ("Q","queen"),("R","rabbit"),("S","sun"),("T","tiger"),
    ("U","umbrella"),("V","van"),("W","water"),("X","fox"),
    ("Y","yellow"),("Z","zebra"),
]

# 用 SSML 加長 pause,聽起來像有節奏
parts = ["Let's sing the alphabet."]
for letter, word in LETTERS:
    parts.append(f"{letter} is for {word}.")
parts.append("Now I know my A B C. Next time won't you sing with me?")

text = "  ".join(parts)

async def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = edge_tts.Communicate(text, VOICE, rate="-5%")
    await c.save(str(OUT))
    sz = OUT.stat().st_size
    print(f"OK: {OUT}  ({sz//1024}KB)")

asyncio.run(main())
