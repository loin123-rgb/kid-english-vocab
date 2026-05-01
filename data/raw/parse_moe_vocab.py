#!/usr/bin/env python3
"""
從官方教育部 PDF (12年國教英語領綱 附錄五) 抽出字彙表 → JSON

來源:十二年國民基本教育課程綱要 國民中小學暨普通型高級中等學校 語文領域-英語文
PDF: moe_official_k12ea.pdf (附錄五:參考字彙表 2,000 字)

輸出:vocab_moe.json,結構:
  {
    "source": "...",
    "version": "...",
    "count": ...,
    "words": [
      {"word": "...", "level": "basic|advanced", "categories": [...], "zh": ""}
    ]
  }
"""
import pdfplumber
import json
import re
from pathlib import Path

PDF = Path(__file__).parent / "moe_official_k12ea.pdf"
OUT = Path(__file__).parent / "vocab_moe.json"

# 字母行的正則:像 "A- a/an, a few, ..." 開頭
LETTER_LINE = re.compile(r"^[A-Z]-\s*(.*)$")

# 主題分類的標題:像 "1. People" "27. Articles & determiners"
CATEGORY_HEADER = re.compile(r"^(\d+)\.\s+(.+)$")


def extract_appendix_text(pdf_path: Path, start_page: int = 56, end_page: int = 68) -> str:
    """抽出附錄頁的純英文內容(過濾掉中文亂碼行)"""
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(start_page - 1, min(end_page, len(pdf.pages))):
            page = pdf.pages[i]
            text = page.extract_text() or ""
            for raw in text.split("\n"):
                if not raw.strip():
                    continue
                # 純頁碼跳過
                if raw.strip().isdigit():
                    continue
                # 60% 以上 ASCII 才算英文行,避免中文亂碼污染
                ascii_chars = sum(1 for c in raw if ord(c) < 128)
                if ascii_chars / len(raw) > 0.6:
                    lines.append(raw)
    return "\n".join(lines)


def split_words(s: str) -> list[str]:
    """把一行 'a/an, a few, a lot, ...' 切成 ['a/an', 'a few', ...]"""
    # 先處理括號內的逗號(如 'be (am, is, are)')— 這種逗號不能切
    parts = []
    buf = ""
    paren = 0
    for ch in s:
        if ch == "(":
            paren += 1
            buf += ch
        elif ch == ")":
            paren -= 1
            buf += ch
        elif ch == "," and paren == 0:
            if buf.strip():
                parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())
    return parts


def parse_alphabet_section(text: str) -> list[str]:
    """解析「依字母排列」段:把 A- ..., B- ..., ... 全部 join 起來再切"""
    words = []
    current_letter_buf = []

    def flush():
        nonlocal current_letter_buf
        if current_letter_buf:
            joined = " ".join(current_letter_buf)
            for w in split_words(joined):
                w = w.strip()
                # 砍句尾單一句點(像捕獲到 "...lemonade." 這種誤抓),
                # 但保留縮寫內的點(a.m. / Mr. / R.O.C.):有內部點就不砍尾點
                if w.endswith(".") and "." not in w[:-1]:
                    w = w[:-1]
                if w:
                    words.append(w)
            current_letter_buf = []

    for line in text.split("\n"):
        m = LETTER_LINE.match(line.strip())
        if m:
            # 新字母段開始,先把上一段 flush
            flush()
            tail = m.group(1).strip()
            if tail:
                current_letter_buf.append(tail)
        else:
            # 接續行(屬於上一字母段)
            current_letter_buf.append(line.strip())
    flush()
    return words


def parse_categories(text: str) -> dict[str, list[str]]:
    """解析「主題分類」段:返回 {category_name: [words...]}"""
    categories: dict[str, list[str]] = {}
    current = None
    buf = []

    def flush():
        nonlocal buf, current
        if current and buf:
            joined = " ".join(buf).replace("---", " ")
            for w in split_words(joined):
                w = w.strip()
                # 砍句尾單一句點(像捕獲到 "...lemonade." 這種誤抓),
                # 但保留縮寫內的點(a.m. / Mr. / R.O.C.):有內部點就不砍尾點
                if w.endswith(".") and "." not in w[:-1]:
                    w = w[:-1]
                if w and w not in categories[current]:
                    categories[current].append(w)
            buf = []

    for line in text.split("\n"):
        s = line.strip()
        m = CATEGORY_HEADER.match(s)
        if m:
            flush()
            current = m.group(2).strip()
            categories.setdefault(current, [])
        else:
            buf.append(s)
    flush()
    return categories


def main():
    full = extract_appendix_text(PDF)

    # 切三段:
    #   1. 第一部分 1200 字 = 從第一個 'A-' 到 第二個 'A-' 之前
    #   2. 第二部分 800 字  = 從第二個 'A-' 到 '1. People' 之前
    #   3. 主題分類          = 從 '1. People' 到結尾
    #
    # 找第二個 A- 的位置(它的特徵是 'A- absent' 開頭,absent 是進階字)
    lines = full.split("\n")
    a_indices = [i for i, ln in enumerate(lines) if re.match(r"^A-\s", ln.strip())]
    cat_index = next(
        (i for i, ln in enumerate(lines) if re.match(r"^1\.\s+People", ln.strip())),
        None,
    )

    if len(a_indices) < 2 or cat_index is None:
        raise SystemExit(
            f"PDF 結構解析失敗:A-section={len(a_indices)}, category={cat_index}"
        )

    basic_text = "\n".join(lines[a_indices[0]:a_indices[1]])
    advanced_text = "\n".join(lines[a_indices[1]:cat_index])
    category_text = "\n".join(lines[cat_index:])

    basic_words = parse_alphabet_section(basic_text)
    advanced_words = parse_alphabet_section(advanced_text)
    categories = parse_categories(category_text)

    # 為每個字反查它出現在哪些 category
    word_to_cats: dict[str, list[str]] = {}
    for cat_name, words in categories.items():
        for w in words:
            word_to_cats.setdefault(w, []).append(cat_name)

    # 輸出 — 維持跟現有 vocab.json 類似的 schema
    entries = []
    seen = set()

    def emit(word: str, level: str):
        # 同一個字若同時出現在 basic / advanced(理論上不會,但保險),只取第一次
        if word.lower() in seen:
            return
        seen.add(word.lower())
        entries.append({
            "word": word,
            "level": level,
            "categories": word_to_cats.get(word, []),
            "pos": "",   # 教育部 PDF 沒給 POS,之後人工或自動補
            "zh": "",    # 教育部 PDF 沒給中譯,自己校正後填入
        })

    for w in basic_words:
        emit(w, "basic")
    for w in advanced_words:
        emit(w, "advanced")

    out = {
        "source": "教育部:十二年國民基本教育課程綱要 國民中小學暨普通型高級中等學校 語文領域-英語文",
        "source_url": "https://cirn.moe.edu.tw/Upload/file/26192/74206.pdf",
        "appendix": "附錄五:參考字彙表(2,000 字)",
        "version": "108課綱 (民國107年4月公告)",
        "scope": "Taiwan elementary + junior high English vocabulary (basic 1200 + advanced 800)",
        "license_note": "教育部公開資料 — 字表本身是政府公開字彙(可商用)。中譯需要自己補(本檔留空)。",
        "count": len(entries),
        "count_basic": sum(1 for e in entries if e["level"] == "basic"),
        "count_advanced": sum(1 for e in entries if e["level"] == "advanced"),
        "categories_used": sorted(set(c for e in entries for c in e["categories"])),
        "words": entries,
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ 輸出 {OUT.name}:{out['count']} 字 "
          f"(basic={out['count_basic']}, advanced={out['count_advanced']})")
    print(f"  分類數:{len(out['categories_used'])}")


if __name__ == "__main__":
    main()
