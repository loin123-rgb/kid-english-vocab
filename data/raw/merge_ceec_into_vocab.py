#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT.parent
MAIN_VOCAB = DATA / "vocab.json"
CEEC_VOCAB = ROOT / "vocab_ceec_7000.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def split_pos_chain(pos: str) -> list[str]:
    return [part.strip() for part in str(pos or "").split(";") if part.strip()]


def stage_from_grade(grade: int) -> str:
    if grade <= 6:
        return "elementary"
    if grade <= 9:
        return "junior"
    return "senior"


def prefer_pos(existing_pos: str, ceec_pos: str) -> str:
    ceec_parts = split_pos_chain(ceec_pos)
    if ceec_parts:
        return ceec_pos
    return existing_pos


def merge_existing_entry(existing: dict, ceec: dict) -> dict:
    merged = dict(existing)
    merged["pos"] = prefer_pos(existing.get("pos", ""), ceec.get("pos", ""))
    if ceec.get("definitions"):
        merged["definitions"] = ceec["definitions"]
    elif existing.get("definitions"):
        merged["definitions"] = existing["definitions"]
    if ceec.get("zh"):
        merged["zh"] = ceec["zh"]
    merged["grade"] = min(int(existing.get("grade", 99) or 99), int(ceec.get("grade", 99) or 99))
    merged["level_label"] = stage_from_grade(int(merged["grade"]))
    merged["stage"] = merged["level_label"]
    merged["ceec_level"] = ceec.get("level", "")
    return merged


def build_ceec_only_entry(ceec: dict) -> dict:
    grade = int(ceec.get("grade", 7) or 7)
    stage = stage_from_grade(grade)
    return {
        "word": ceec["word"],
        "level": ceec.get("stage", stage),
        "categories": [],
        "pos": ceec.get("pos", ""),
        "zh": ceec.get("zh", ""),
        "grade": grade,
        "level_label": stage,
        "cefr": "",
        "definitions": ceec.get("definitions", []),
        "stage": ceec.get("stage", stage),
        "ceec_level": ceec.get("level", ""),
    }


def main():
    main_data = load_json(MAIN_VOCAB)
    ceec_data = load_json(CEEC_VOCAB)

    main_words = main_data["words"]
    ceec_words = ceec_data["words"]
    ceec_by_word = {entry["word"].lower(): entry for entry in ceec_words}

    merged_words = []
    seen = set()
    overlap_count = 0

    for entry in main_words:
        key = entry["word"].lower()
        ceec = ceec_by_word.get(key)
        if ceec:
            merged_words.append(merge_existing_entry(entry, ceec))
            overlap_count += 1
        else:
            kept = dict(entry)
            kept["level_label"] = kept.get("level_label") or stage_from_grade(int(kept.get("grade", 6) or 6))
            kept["stage"] = stage_from_grade(int(kept.get("grade", 6) or 6))
            merged_words.append(kept)
        seen.add(key)

    appended_count = 0
    for ceec in ceec_words:
        key = ceec["word"].lower()
        if key in seen:
            continue
        merged_words.append(build_ceec_only_entry(ceec))
        appended_count += 1
        seen.add(key)

    merged_words.sort(key=lambda item: item["word"].lower())

    pos_breakdown = Counter()
    categories_used = set()
    count_with_pos = 0
    count_with_emoji = 0
    count_with_definitions = 0
    count_elementary = 0
    count_junior = 0
    count_senior = 0

    for entry in merged_words:
        grade = int(entry.get("grade", 0) or 0)
        if grade <= 6:
            count_elementary += 1
        elif grade <= 9:
            count_junior += 1
        else:
            count_senior += 1

        if entry.get("pos"):
            count_with_pos += 1
            for pos in split_pos_chain(entry.get("pos", "")):
                pos_breakdown[pos] += 1
        if entry.get("emoji"):
            count_with_emoji += 1
        if entry.get("definitions"):
            count_with_definitions += 1
        categories_used.update(entry.get("categories", []))

    main_data["source"] = "教育部 2000 字表 + CEEC 7000 字表整合"
    main_data["source_url"] = "https://cirn.moe.edu.tw/Upload/file/26192/74206.pdf"
    main_data["source_urls"] = [
        "https://cirn.moe.edu.tw/Upload/file/26192/74206.pdf",
        "https://www.ceec.edu.tw/",
    ]
    main_data["appendix"] = "教育部 2000 字 + CEEC 7000 字整合主詞庫"
    main_data["version"] = "108課綱 + CEEC merged"
    main_data["scope"] = "Taiwan elementary + junior high + senior high English vocabulary"
    main_data["count"] = len(merged_words)
    main_data["count_basic"] = count_elementary
    main_data["count_advanced"] = count_junior + count_senior
    main_data["count_elementary"] = count_elementary
    main_data["count_junior"] = count_junior
    main_data["count_senior"] = count_senior
    main_data["count_with_pos"] = count_with_pos
    main_data["count_with_emoji"] = count_with_emoji
    main_data["count_with_definitions"] = count_with_definitions
    main_data["count_ceec_overlap"] = overlap_count
    main_data["count_ceec_added"] = appended_count
    main_data["categories_used"] = sorted(categories_used)
    main_data["pos_breakdown"] = dict(sorted(pos_breakdown.items()))
    main_data["words"] = merged_words

    dump_json(MAIN_VOCAB, main_data)
    print(f"wrote {MAIN_VOCAB}")
    print(f"merged_words={len(merged_words)}")
    print(f"overlap={overlap_count}")
    print(f"ceec_added={appended_count}")


if __name__ == "__main__":
    main()
