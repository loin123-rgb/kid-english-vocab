#!/usr/bin/env python3
"""
用 CEFR-J 字彙等級重新分配 vocab.json 的 grade 欄位:
  A1 → G6 (國小)
  A2 → G7 (國中一)
  B1 → G8 (國中二)
  B2 → G9 (國中三)

CEFR-J 沒收錄的字 → 用既有 level fallback (basic→G7, advanced→G9)。

讀:data/vocab.json
寫:data/vocab.json (in-place)
"""
import csv
import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent
DATA = ROOT.parent
VOCAB = DATA / "vocab.json"
CEFR = ROOT / "cefrj.csv"

CEFR_TO_GRADE = {"A1": 6, "A2": 7, "B1": 8, "B2": 9}


def normalize(word: str) -> str:
    cleaned = re.sub(r"\s*\([^)]*\)", "", word)
    cleaned = cleaned.split("/")[0]
    return cleaned.strip().lower()


def main():
    # 1. 讀 CEFR-J 建索引 (lowercase headword → CEFR level)
    cefr_idx = {}
    with open(CEFR, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            head = (row.get("headword") or "").strip()
            level = (row.get("CEFR") or "").strip()
            if not head or level not in CEFR_TO_GRADE:
                continue
            for variant in head.split("/"):
                v = variant.strip().lower()
                if not v:
                    continue
                # 同字若多個 CEFR 級,取最低(學最早的)
                if v not in cefr_idx or CEFR_TO_GRADE[level] < CEFR_TO_GRADE[cefr_idx[v]]:
                    cefr_idx[v] = level

    print(f"CEFR-J 索引: {len(cefr_idx)} 字")

    # 2. 套到 vocab.json
    data = json.loads(VOCAB.read_text(encoding="utf-8"))
    words = data["words"]

    matched = 0
    unmatched_basic = 0
    unmatched_advanced = 0
    grade_dist = Counter()

    for e in words:
        norm = normalize(e["word"])
        if norm in cefr_idx:
            cefr = cefr_idx[norm]
            e["grade"] = CEFR_TO_GRADE[cefr]
            e["cefr"] = cefr
            matched += 1
        else:
            # CEFR-J 沒這字 → 用 level 推估
            if e.get("level") == "basic":
                e["grade"] = 7
                unmatched_basic += 1
            else:
                e["grade"] = 9
                unmatched_advanced += 1
            e["cefr"] = ""
        grade_dist[e["grade"]] += 1

    VOCAB.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n總共: {len(words)} 字")
    print(f"  CEFR-J 命中: {matched}")
    print(f"  沒命中 basic → G7: {unmatched_basic}")
    print(f"  沒命中 advanced → G9: {unmatched_advanced}")
    print(f"\n年級分布:")
    for g in [6, 7, 8, 9]:
        print(f"  G{g}: {grade_dist.get(g, 0)}")


if __name__ == "__main__":
    main()
