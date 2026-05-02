#!/usr/bin/env python3
import json
from pathlib import Path
from opencc import OpenCC

CC = OpenCC("s2t")
PREFERRED_TRADITIONAL_REPLACEMENTS = {
    "牀": "床",
    "喫": "吃",
    "祕": "秘",
    "臺": "台",
    "峯": "峰",
    "脣": "唇",
    "羣": "群",
    "麪": "麵",
    "僱": "雇",
}
PREFERRED_TRADITIONAL_PHRASES = {
    "煙鬥": "煙斗",
    "瞭解": "了解",
}

ROOT = Path(__file__).parent
FILES = [
    ROOT / "vocab_ceec_7000.json",
    ROOT.parent / "vocab.json",
]


def sanitize_traditional(text: str) -> str:
    if not isinstance(text, str):
        return text
    normalized = CC.convert(text)
    for src, dst in PREFERRED_TRADITIONAL_REPLACEMENTS.items():
        normalized = normalized.replace(src, dst)
    for src, dst in PREFERRED_TRADITIONAL_PHRASES.items():
        normalized = normalized.replace(src, dst)
    return normalized


def normalize_file(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    words = data["words"] if isinstance(data, dict) else data
    changed = 0

    for entry in words:
        zh = entry.get("zh")
        if isinstance(zh, str):
            normalized = sanitize_traditional(zh)
            if normalized != zh:
                entry["zh"] = normalized
                changed += 1
        for definition in entry.get("definitions", []) or []:
            val = definition.get("zh")
            if isinstance(val, str):
                normalized = sanitize_traditional(val)
                if normalized != val:
                    definition["zh"] = normalized
                    changed += 1

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{path} changed={changed}")


def main():
    for path in FILES:
        normalize_file(path)


if __name__ == "__main__":
    main()
