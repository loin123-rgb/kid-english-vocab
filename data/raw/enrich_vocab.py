#!/usr/bin/env python3
"""
把 vocab_moe.json 補齊「跟舊版 vocab.json schema 對齊」的欄位:

  pos    — 詞性,從 35 個主題分類反推 + 片語偵測
  grade  — 年級,basic→6, advanced→8 (粗略,後續可細修)
  emoji  — 用 index.html 已存在的 EMOJI_MAP (165 條英文-emoji 對照)

寫回 vocab_moe.json,最終結構就跟舊版 vocab.json 完全相容,可以直接複製成
data/vocab.json 取代舊檔。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
VOCAB = ROOT / "vocab_moe.json"
EMOJI_MAP_FILE = ROOT / "emoji_map.json"

# 分類 → pos 映射 (依教育部附錄五的 35 類)
# 強訊號:這幾個分類本身就是某種詞性
CAT_TO_POS = {
    "Other verbs": "v",
    "Be & auxiliaries": "v",
    "Personal characteristics": "adj",
    "Prepositions": "prep",
    "Conjunctions": "conj",
    "Pronouns & reflexives": "pron",
    "Wh-words": "pron",            # what/who/which 之類
    "Articles & determiners": "det",
    "Interjections": "int",
    "Numbers": "num",
}

# 弱訊號:這些是主題分類,落在這裡的字「多半是名詞」(沒被強訊號分類覆蓋的話)
NOUN_THEME_CATS = {
    "People", "Parts of body", "Health", "Forms of address", "Family",
    "Time", "Money", "Food & drinks", "Tableware", "Clothing & accessories",
    "Colors", "Sports, interests & hobbies", "Houses & apartments", "School",
    "Places & locations", "Transportation", "Sizes & measurements",
    "Countries and areas", "Languages", "Holidays & festivals", "Occupations",
    "Weather & nature", "Geographical terms", "Animals & insects",
    "Other nouns",
}


def infer_pos(word: str, categories: list[str]) -> str:
    # 強訊號優先 — 分類本身就是某個詞性
    # (a few/a little/a lot 在 Numbers 分類 → num,不是 n)
    for c in categories:
        if c in CAT_TO_POS:
            return CAT_TO_POS[c]

    # 片語(含空格):分類沒給強訊號才走這邊
    if " " in word:
        n_tokens = len(word.split())
        if n_tokens >= 3:
            return "片"
        if re.search(r"\b(in|of|at|on|to|by|with|from)\b", word.lower()):
            return "片"
        # 兩個字、看起來像複合名詞 (ice cream / post office) → n
        return "n"

    # 弱訊號(主題類)→ n
    for c in categories:
        if c in NOUN_THEME_CATS:
            return "n"
    # 沒分類資訊 → 留空待人工/查字典補
    return ""


def infer_grade(level: str) -> int:
    if level == "basic":
        return 6  # 對齊舊版 G6 elementary 概念
    elif level == "advanced":
        return 8  # 對齊 JH 中段
    return 7


def infer_level_label(level: str) -> str:
    return "elementary" if level == "basic" else "junior"


def lookup_emoji(word: str, emoji_map: dict) -> str:
    """字串完整匹配,大小寫不敏感。也試剝括號 (apple (apple) → apple) 和取斜線前的形式。"""
    candidates = [
        word,
        word.lower(),
        re.sub(r"\s*\([^)]*\)", "", word).strip().lower(),
        word.split("/")[0].strip().lower(),
        # 也試移除空格(複合名詞 "ice cream" → "icecream"? 通常不會中)
    ]
    for c in candidates:
        if c in emoji_map:
            return emoji_map[c]
    return ""


def main():
    data = json.loads(VOCAB.read_text(encoding="utf-8"))
    emoji_map = json.loads(EMOJI_MAP_FILE.read_text(encoding="utf-8"))
    # lower-case keys 統一
    emoji_map = {k.lower(): v for k, v in emoji_map.items()}

    pos_filled = pos_empty = 0
    emoji_hit = 0
    pos_breakdown = {}

    for e in data["words"]:
        # pos:已有就保留(避免覆蓋 dictionary 補的或人工校正的),空才推估
        if not e.get("pos"):
            e["pos"] = infer_pos(e["word"], e.get("categories", []))
        e["grade"] = infer_grade(e["level"])
        e["level_label"] = infer_level_label(e["level"])  # elementary/junior
        # emoji 同樣只填空的(避免覆蓋手動加的)
        if not e.get("emoji"):
            em = lookup_emoji(e["word"], emoji_map)
            if em:
                e["emoji"] = em
        if e.get("emoji"):
            emoji_hit += 1
        if e["pos"]:
            pos_filled += 1
            pos_breakdown[e["pos"]] = pos_breakdown.get(e["pos"], 0) + 1
        else:
            pos_empty += 1

    # meta 欄位也更新一下
    data["count_with_pos"] = pos_filled
    data["count_with_emoji"] = emoji_hit
    data["pos_breakdown"] = pos_breakdown

    VOCAB.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"已 enrich {VOCAB.name}")
    print(f"  pos 已填: {pos_filled} / {pos_filled+pos_empty}")
    print(f"  pos 留空: {pos_empty} 個 (沒落在任何分類的)")
    print(f"  emoji 命中: {emoji_hit} / {len(data['words'])}")
    print(f"\n  pos 分布:")
    for p, n in sorted(pos_breakdown.items(), key=lambda x: -x[1]):
        print(f"    {p:6} {n}")


if __name__ == "__main__":
    main()
