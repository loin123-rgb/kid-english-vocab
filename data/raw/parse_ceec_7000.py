#!/usr/bin/env python3
"""
從大考中心《高中英文參考詞彙表 7000 字》PDF 抽出字彙清單。
只抓英文字 + pos + 級別,中文留空(由使用者自己校正)。

級別對應:
  第一級, 第二級, 第三級 → 國中(可能跟既有 vocab 重複)
  第四級, 第五級, 第六級 → 高中

輸出 vocab_ceec_7000.json,結構與既有 vocab.json 對齊,等你校好中譯就能 merge。

⚠️ 大考中心著作權:此資料原本「僅供非營利目的使用」。
   你說會自己挑字 + 寫中譯後,作品轉化程度足夠時可降低風險,但商用前自評。
"""
import json
import re
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).parent
PDF = ROOT / "ceec_7000.pdf"
OUT = ROOT / "vocab_ceec_7000.json"

# 級別 → 起始頁(從之前 dump 出來的)
LEVEL_PAGES = {
    "第一級": (13, 20),  # p13-p20
    "第二級": (21, 28),
    "第三級": (29, 37),
    "第四級": (38, 45),
    "第五級": (46, 54),
    "第六級": (55, 63),
}

LEVEL_TO_GRADE = {
    "第一級": 7,   # 已 mapped 到我們既有國中
    "第二級": 8,
    "第三級": 9,
    "第四級": 10,  # 高中一
    "第五級": 11,
    "第六級": 12,
}

# 詞性詞綴(完整列表)
POS_TOKENS = {
    "n.", "v.", "vt.", "vi.", "adj.", "adv.", "prep.", "conj.",
    "pron.", "int.", "art.", "aux.", "abbr.", "num.",
}

# 一個 entry 大致形態:word + pos
# 範例:
#   "vision n."
#   "access n./v."
#   "appoint(ment) v./(n.)"
#   "cola/Coke n."
#   "art" (沒 pos,少數案例)
ENTRY_RE = re.compile(
    r"([A-Za-z][A-Za-z\-/().]*?)\s+"             # word
    r"((?:[a-z]+\.)+(?:/[a-z()]+\.?)*)",         # pos chain
    re.MULTILINE,
)


def normalize_pos(pos: str) -> str:
    # "n./v." → ["n", "v"] → "n;v"
    # "v./(n.)" → ["v", "n"]
    pos = pos.replace("(", "").replace(")", "").replace(".", "")
    parts = [p.strip() for p in pos.split("/") if p.strip()]
    return ";".join(parts)


def normalize_word(word: str) -> tuple[str, str]:
    """
    回傳 (canonical_word, raw_with_variants)。
    'cola/Coke' → ('cola', 'cola/Coke')
    'appoint(ment)' → ('appoint', 'appoint(ment)')
    """
    raw = word
    # 取斜線前
    main = word.split("/")[0]
    # 去括號(只留主形)
    main = re.sub(r"\([^)]*\)", "", main).strip()
    return main, raw


def parse_pages(pdf, start: int, end: int) -> list[str]:
    """把指定頁範圍的內容串成大字串"""
    chunks = []
    for i in range(start - 1, min(end, len(pdf.pages))):
        text = pdf.pages[i].extract_text() or ""
        # 過濾頁眉/頁尾
        for line in text.split("\n"):
            ls = line.strip()
            if not ls:
                continue
            if "依級別排序" in ls or "高中英文參考詞彙表" in ls:
                continue
            if ls.startswith("第") and "級" in ls and len(ls) <= 5:
                continue
            chunks.append(ls)
    return "\n".join(chunks)


def parse_level(pdf, level_name: str, page_range: tuple[int, int]) -> list[dict]:
    text = parse_pages(pdf, *page_range)
    grade = LEVEL_TO_GRADE[level_name]
    results = []
    seen = set()

    for m in ENTRY_RE.finditer(text):
        raw_word = m.group(1)
        raw_pos = m.group(2)

        canon, raw = normalize_word(raw_word)
        if not canon or len(canon) < 2:
            continue
        # 簡單去重(同字保留第一次)
        key = canon.lower()
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "word": canon,
            "raw": raw if raw != canon else "",  # 多形態才存
            "pos": normalize_pos(raw_pos),
            "level": level_name,
            "grade": grade,
            "stage": "junior" if grade <= 9 else "senior",
            "zh": "",  # 留空待校正
        })
    return results


def main():
    all_words = []
    with pdfplumber.open(PDF) as pdf:
        for level_name, page_range in LEVEL_PAGES.items():
            words = parse_level(pdf, level_name, page_range)
            print(f"{level_name} (p{page_range[0]}-{page_range[1]}): {len(words)} 字")
            all_words.extend(words)

    # 統計
    print(f"\n總計: {len(all_words)} 字")
    from collections import Counter
    by_level = Counter(w["level"] for w in all_words)
    for lvl, n in sorted(by_level.items()):
        print(f"  {lvl}: {n}")

    output = {
        "source": "大學入學考試中心《高中英文參考詞彙表 - 111 學年度起適用》(108年版)",
        "source_url": "https://www.ceec.edu.tw/files/file_pool/1/...",
        "license_note": "原 PDF 著作權屬大考中心;此 JSON 僅抽取英文字 + 級別資訊,中譯由本專案自行撰寫。商用前自評風險。",
        "count": len(all_words),
        "by_level": dict(by_level),
        "words": all_words,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n輸出 → {OUT}")


if __name__ == "__main__":
    main()
