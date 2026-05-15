"""產 phonics 隔離音 MP3 — 用 ElevenLabs 自然語音

ElevenLabs 免費方案不開放 SSML <phoneme> IPA 標記(需付費 + pronunciation dictionary),
所以餵「phonics 老師唸法」(ahh, buh, shhh ...) 給它念,音質遠勝 edge-tts。

輸出: data/audio/phonics/sound_<key>.mp3
存在就 skip,不會重複扣 credit。
"""
import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")
API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not API_KEY:
    sys.exit("Missing ELEVENLABS_API_KEY in .env")

# Bella - 年輕女聲,清楚溫暖,適合教學
VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
MODEL = "eleven_multilingual_v2"
OUT_DIR = Path(__file__).parent.parent / "audio" / "phonics"

# 每個音標 key -> 餵給 TTS 的完整句子
# 走「字母 + 念音 + 例字」格式,ElevenLabs 念整句比念單音自然太多
SOUNDS = {
    # ===== 26 字母音 =====
    "a": "A. A says aa, like apple. aa, aa, apple.",
    "b": "B. B says buh, like ball. buh, buh, ball.",
    "c": "C. C says kuh, like cat. kuh, kuh, cat.",
    "d": "D. D says duh, like dog. duh, duh, dog.",
    "e": "E. E says eh, like egg. eh, eh, egg.",
    "f": "F. F says ffff, like fish. ffff, fish.",
    "g": "G. G says guh, like goat. guh, guh, goat.",
    "h": "H. H says huh, like hat. huh, huh, hat.",
    "i": "I. I says ih, like ink. ih, ih, ink.",
    "j": "J. J says juh, like jump. juh, juh, jump.",
    "k": "K. K says kuh, like key. kuh, kuh, key.",
    "l": "L. L says lll, like lion. lll, lion.",
    "m": "M. M says mmm, like mouse. mmm, mouse.",
    "n": "N. N says nnn, like nose. nnn, nose.",
    "o": "O. O says ah, like orange. ah, ah, orange.",
    "p": "P. P says puh, like pig. puh, puh, pig.",
    "q": "Q. Q says kwuh, like queen. kwuh, queen.",
    "r": "R. R says rrr, like rabbit. rrr, rabbit.",
    "s": "S. S says sss, like sun. sss, sun.",
    "t": "T. T says tuh, like tiger. tuh, tuh, tiger.",
    "u": "U. U says uh, like umbrella. uh, uh, umbrella.",
    "v": "V. V says vvv, like van. vvv, van.",
    "w": "W. W says wuh, like water. wuh, wuh, water.",
    "x": "X. X says kss, like fox. kss, fox.",
    "y": "Y. Y says yuh, like yellow. yuh, yuh, yellow.",
    "z": "Z. Z says zzz, like zebra. zzz, zebra.",

    # ===== 8 雙字母 digraphs =====
    "sh": "S H together says shh, like ship. shh, ship.",
    "ch": "C H together says chuh, like chair. chuh, chair.",
    "th": "T H together says thh, like three. thh, three.",
    "wh": "W H together says wuh, like whale. wuh, whale.",
    "ph": "P H together says ffff, like phone. ffff, phone.",
    "ng": "N G together says ng, like ring. ng, ring.",
    "ck": "C K together says kuh, like duck. kuh, duck.",
    "qu": "Q U together says kwuh, like queen. kwuh, queen.",

    # ===== 5 magic-e patterns =====
    "a_e": "Magic E. Like cake. The silent E makes A say its name.",
    "i_e": "Magic E. Like bike. The silent E makes I say its name.",
    "o_e": "Magic E. Like rope. The silent E makes O say its name.",
    "u_e": "Magic E. Like cute. The silent E makes U say its name.",
    "e_e": "Magic E. Like these. The last E is silent.",

    # ===== 15 母音團 vowel teams =====
    "ai": "A I together. Like rain. Long A sound.",
    "ay": "A Y together. Like play. Long A sound.",
    "ee": "Double E. Like bee. Long E sound.",
    "ea": "E A together. Like tea. Long E sound.",
    "ie": "I E together. Like pie. Long I sound.",
    "igh": "I G H together. Like light. Long I sound.",
    "oa": "O A together. Like boat. Long O sound.",
    "ow": "O W together. Like snow. Long O sound.",
    "oo": "Double O. Like moon. The oo sound.",
    "ue": "U E together. Like blue. Long U sound.",
    "ar": "A R together. Like car.",
    "or": "O R together. Like horse.",
    "er": "E R together. Like her.",
    "ir": "I R together. Like bird.",
    "ur": "U R together. Like burn.",
}


def synthesize(text: str, out_path: Path) -> int:
    """打 ElevenLabs API,回傳 bytes 數。失敗 raise。"""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    body = {
        "text": text,
        "model_id": MODEL,
        "voice_settings": {
            "stability": 0.6,        # 高一點,發音穩定
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }
    r = requests.post(url, headers=headers, json=body, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    out_path.write_bytes(r.content)
    return len(r.content)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = len(SOUNDS)
    done = skipped = failed = 0
    for i, (key, spoken) in enumerate(SOUNDS.items(), 1):
        out = OUT_DIR / f"sound_{key}.mp3"
        if out.exists() and out.stat().st_size > 1000:
            print(f"[{i}/{total}] skip {out.name}")
            skipped += 1
            continue
        try:
            n = synthesize(spoken, out)
            print(f"[{i}/{total}] OK   {out.name}  ({n//1024}KB)  text='{spoken}'")
            done += 1
            time.sleep(0.3)  # 禮貌 rate limit
        except Exception as e:
            print(f"[{i}/{total}] FAIL {key}: {e}")
            failed += 1

    print(f"\n=== 完成 ===  新產 {done}  跳過 {skipped}  失敗 {failed}")


if __name__ == "__main__":
    main()
