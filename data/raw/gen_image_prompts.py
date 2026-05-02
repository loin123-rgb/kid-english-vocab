#!/usr/bin/env python3
"""
產出「該生圖的單字清單」CSV 給 ComfyUI 批次餵。

優先序:
  1. 具象主題分類(Animals/Food/Clothing/Transport/Houses 等)的名詞
  2. 其他名詞
  3. 排除已有 emoji 的字、片語(>2 字)、超抽象的字

CSV 欄位:
  priority  整數,1=最高優先,3=最低
  word      英文字
  zh        中譯
  category  主分類(若有)
  filename  目標檔案路徑(對齊前端命名規則)
  prompt    給 ComfyUI 的建議 prompt
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
VOCAB = ROOT.parent / "vocab.json"
OUT = ROOT / "image_prompts.csv"

# 高優先(具象、好畫)
HIGH_PRI_CATS = {
    "Animals & insects", "Food & drinks", "Tableware",
    "Clothing & accessories", "Houses & apartments", "Transportation",
    "Sports, interests & hobbies", "Holidays & festivals", "Occupations",
    "Weather & nature", "Geographical terms",
}
# 中優先(部分具象)
MID_PRI_CATS = {
    "People", "Parts of body", "Health", "School", "Places & locations",
    "Colors", "Family",
}
# 低優先(抽象,生圖意義不大)— 會給優先 3
ABSTRACT_CATS = {
    "Other nouns", "Time", "Money", "Sizes & measurements", "Numbers",
    "Languages", "Forms of address", "Personal characteristics",
    "Articles & determiners", "Prepositions", "Conjunctions",
    "Pronouns & reflexives", "Wh-words", "Be & auxiliaries",
    "Interjections", "Other verbs",
}

# 風格後綴 — 強化 children's book 而不是 anime
# 反向 prompt 在 gen_images_via_comfyui.py 處理(no text 之類負面詞別寫進正向)
STYLE_SUFFIX = ", children's storybook illustration, watercolor, soft pastel colors, white background"


def safe_filename(word: str) -> str:
    cleaned = re.sub(r"\s*\([^)]*\)", "", word)
    cleaned = cleaned.split("/")[0]
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", cleaned.lower()).strip("_")
    return f"data/images/vocab/word_{safe}.webp"


# Occupations 抽象,給每個職業具體描述
OCCUPATION_VISUAL = {
    "actor": "happy actor performing on a stage with a microphone",
    "actress": "happy actress performing on a stage with a flower bouquet",
    "artist": "smiling artist painting on a canvas with a palette",
    "assistant": "smiling office assistant holding folders",
    "baby sitter": "smiling baby sitter holding a baby",
    "barber": "barber cutting hair with scissors",
    "boss": "businessman in a suit at a desk",
    "businessman": "businessman in a suit holding a briefcase",
    "clerk": "shop clerk standing behind a counter",
    "cook": "smiling cook with a chef hat holding a spoon",
    "cowboy": "cowboy with hat and boots",
    "dentist": "dentist with a face mask holding dental tools",
    "diplomat": "diplomat in a formal suit shaking hands",
    "doctor": "smiling doctor with a stethoscope and white coat",
    "driver": "driver behind a steering wheel",
    "engineer": "engineer with a hard hat holding blueprints",
    "farmer": "farmer with a straw hat and overalls",
    "fisherman": "fisherman holding a fishing rod",
    "guide": "tour guide with a flag and map",
    "hair dresser": "hair dresser holding scissors and comb",
    "housewife": "housewife with an apron in a kitchen",
    "hunter": "hunter with binoculars in a forest",
    "journalist": "journalist with a notebook and pen",
    "judge": "judge in a robe holding a gavel",
    "lawyer": "lawyer in a suit holding a briefcase",
    "magician": "magician with a top hat holding a wand",
    "mailman": "mailman with a mail bag",
    "manager": "manager in business clothes at a meeting",
    "mechanic": "mechanic with overalls holding a wrench",
    "musician": "musician playing a guitar",
    "nurse": "smiling nurse in white uniform holding a clipboard",
    "owner": "store owner standing in front of a shop",
    "painter": "painter holding a paintbrush in front of a canvas",
    "police": "police officer in uniform with a hat",
    "officer": "police officer in uniform with a badge",
    "president": "president at a podium",
    "priest": "priest in robes holding a book",
    "reporter": "reporter holding a microphone",
    "sailor": "sailor with a sailor hat on a boat",
    "salesman": "salesman holding a product",
    "scientist": "scientist in a lab coat with test tubes",
    "secretary": "secretary at a desk with a phone",
    "servant": "servant in formal attire holding a tray",
    "shopkeeper": "shopkeeper behind a store counter",
    "singer": "singer holding a microphone on a stage",
    "soldier": "soldier in green uniform standing at attention",
    "teacher": "smiling teacher pointing at a chalkboard",
    "vendor": "street vendor at a small stall",
    "waiter": "waiter holding a tray with food",
    "waitress": "waitress holding a tray with food",
    "worker": "construction worker with a hard hat and tools",
    "writer": "writer at a desk with a notebook",
}


def make_prompt(w: str, zh: str, cats: list[str]) -> str:
    cleaned_w = re.sub(r"\s*\([^)]*\)", "", w).split("/")[0].strip()
    cats_str = " ".join(cats)

    # 動物 → 具體動作避免飄
    if "Animals" in cats_str:
        subject = f"a {cleaned_w} sitting"
    # 食物 → 在盤子或桌上,自然
    elif "Food" in cats_str:
        subject = f"a {cleaned_w} on a plate"
    # 衣服配件 → 平攤好看
    elif "Clothing" in cats_str:
        subject = f"a {cleaned_w} laid flat"
    # 交通工具 → 完整車身
    elif "Transport" in cats_str:
        subject = f"a {cleaned_w} side view"
    # 職業 → 用具體查表(沒查到就用通用)
    elif "Occupations" in cats_str:
        subject = OCCUPATION_VISUAL.get(cleaned_w.lower(),
                  f"a friendly {cleaned_w} standing")
    # 餐具 → 在桌上
    elif "Tableware" in cats_str:
        subject = f"a {cleaned_w} on a wooden table"
    # 房屋部件 → 實物
    elif "Houses" in cats_str:
        subject = f"a {cleaned_w}"
    # 人 / 家庭 / 身體 → 友善人物
    elif any(c in cats_str for c in ["People", "Family", "Parts of body"]):
        subject = f"a smiling {cleaned_w}"
    # 顏色 → 純色塊
    elif "Colors" in cats_str:
        subject = f"a {cleaned_w} colored circle"
    # 天氣自然 → 場景
    elif "Weather" in cats_str:
        subject = f"a {cleaned_w} weather scene"
    elif "Geographical" in cats_str:
        subject = f"a {cleaned_w} landscape"
    # 學校 → 物品或場景
    elif "School" in cats_str:
        subject = f"a {cleaned_w}"
    # 場所地點 → 建築
    elif "Places" in cats_str:
        subject = f"a {cleaned_w} building"
    # 假日節慶 → 場景
    elif "Holidays" in cats_str:
        subject = f"a {cleaned_w} celebration scene"
    # Sports → 物件
    elif "Sports" in cats_str:
        subject = f"a {cleaned_w}"
    else:
        subject = f"a {cleaned_w}"

    return subject + STYLE_SUFFIX


def assign_priority(cats: list[str]) -> int:
    if any(c in HIGH_PRI_CATS for c in cats):
        return 1
    if any(c in MID_PRI_CATS for c in cats):
        return 2
    if any(c in ABSTRACT_CATS for c in cats):
        return 3
    # 沒分類資訊 → 預設中
    return 2


def is_too_abstract(word: str, pos: str) -> bool:
    # 不是名詞直接跳過
    if pos != "n":
        return True
    # 片語太長(>2 個 token)
    if len(word.split()) > 2:
        return True
    # 含 / 的(像 a/an)
    if "/" in word:
        return True
    # 結尾是 . 的(縮寫像 a.m./p.m./Mr.)
    if word.endswith("."):
        return True
    return False


def main():
    data = json.loads(VOCAB.read_text(encoding="utf-8"))
    rows = []
    for e in data["words"]:
        w = e["word"]
        if e.get("emoji"):  # 已有 emoji 跳過
            continue
        if is_too_abstract(w, e.get("pos", "")):
            continue
        cats = e.get("categories", [])
        rows.append({
            "priority": assign_priority(cats),
            "word": w,
            "zh": e.get("zh", ""),
            "category": cats[0] if cats else "",
            "filename": safe_filename(w),
            "prompt": make_prompt(w, e.get("zh", ""), cats),
        })

    # 排序:priority asc → word asc
    rows.sort(key=lambda r: (r["priority"], r["word"].lower()))

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["priority", "word", "zh", "category", "filename", "prompt"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"輸出 {OUT}: {len(rows)} 字")
    print()
    pri_count = {1: 0, 2: 0, 3: 0}
    for r in rows:
        pri_count[r["priority"]] += 1
    print(f"  P1 (具象,優先生): {pri_count[1]}")
    print(f"  P2 (中等):       {pri_count[2]}")
    print(f"  P3 (抽象,可不生): {pri_count[3]}")


if __name__ == "__main__":
    main()
