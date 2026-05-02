#!/usr/bin/env python3
import json
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from opencc import OpenCC

ROOT = Path(__file__).parent
PROJECT_ROOT = ROOT.parent.parent
CEEC_PATH = ROOT / "vocab_ceec_7000.json"
BACKUP_PATH = PROJECT_ROOT / "data" / "vocab_apppeterpan_backup.json"
ENV_PATH = PROJECT_ROOT / ".env"

BATCH_SIZE = 50
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
POS_MAP = {
    "vi": "v",
    "vt": "v",
    "art": "det",
}
MANUAL_DEFINITION_OVERRIDES = {
    "act": {
        "n": "行為;舉動",
        "v": "做;扮演",
    },
    "after": {
        "prep": "在…之後",
        "conj": "在…之後",
        "adv": "之後;後來",
    },
    "another": {
        "adj": "另一個;再一個",
        "pron": "另一個人(或事物)",
    },
    "any": {
        "pron": "任何一個;任何人",
        "adj": "任何的",
        "adv": "稍微;一點",
    },
    "back": {
        "adv": "向後;回原處",
        "n": "背;後面",
        "v": "支持;倒退",
        "adj": "後面的",
    },
    "both": {
        "pron": "兩者;雙方",
        "adv": "兩者都",
        "adj": "兩者的",
    },
    "belt": {
        "n": "皮帶;腰帶",
        "v": "用帶子繫住",
    },
    "bear": {
        "v": "承受;忍受",
    },
    "boss": {
        "n": "老闆;上司",
        "v": "指揮;差使",
    },
    "book": {
        "n": "書;書本",
        "v": "預訂",
    },
    "bottle": {
        "n": "瓶子",
        "v": "裝瓶",
    },
    "bug": {
        "n": "蟲;小蟲;臭蟲",
    },
    "chair": {
        "n": "椅子",
        "v": "主持",
    },
    "change": {
        "n": "改變;變化",
        "v": "改變",
    },
    "cheap": {
        "adj": "便宜的",
        "adv": "便宜地",
    },
    "choice": {
        "n": "選擇",
        "adj": "上等的;精選的",
    },
    "circle": {
        "n": "圓圈",
        "v": "圈出;環繞",
    },
    "cook": {
        "v": "烹調;煮",
    },
    "couch": {
        "n": "長沙發",
        "v": "表達",
    },
    "exercise": {
        "n": "運動;練習",
        "v": "運動;鍛鍊",
    },
    "cross": {
        "n": "十字形;十字架",
        "v": "穿越;橫過",
    },
    "alive": {
        "adj": "活著的",
    },
    "enroll": {
        "v": "註冊;登記",
        "n": "註冊;入學",
    },
    "inflict": {
        "v": "施加;使遭受",
    },
    "left": {
        "adj": "左邊的",
        "n": "左邊",
        "adv": "向左;在左邊",
    },
    "light": {
        "n": "光;燈",
        "adj": "輕的;淡的",
        "v": "點燃;照亮",
        "adv": "輕地",
    },
    "net": {
        "n": "網子",
        "v": "用網捕捉;淨得",
    },
    "play": {
        "v": "玩;玩耍;演奏",
        "n": "遊戲;戲劇",
    },
    "present": {
        "adj": "現在的;出席的",
        "n": "禮物",
        "v": "贈送;介紹",
    },
    "preliminary": {
        "adj": "初步的;預備的",
        "n": "初步;預備工作",
    },
    "relation": {
        "n": "關係;關聯",
    },
    "rainy": {
        "adj": "下雨的;多雨的",
    },
    "right": {
        "adv": "向右;正好",
        "adj": "對的;右邊的",
        "n": "權利;右邊",
    },
    "rural": {
        "adj": "鄉村的",
    },
    "watch": {
        "v": "看;觀看;注視",
        "n": "手錶",
    },
    "attack": {
        "n": "攻擊;襲擊",
        "v": "攻擊;襲擊",
    },
    "association": {
        "n": "協會",
    },
    "avenue": {
        "n": "林蔭道",
    },
    "eccentric": {
        "adj": "古怪的;怪裡怪氣的",
        "n": "怪人",
    },
    "agree": {
        "v": "同意",
        "n": "協議;約定",
    },
}
MANUAL_DEFINITION_OVERRIDES.update({
    "abrupt": {"adj": "突然的;唐突的"},
    "about": {"prep": "關於", "adv": "大約;在附近"},
    "above": {"prep": "在…上方", "adv": "在上面", "adj": "上面的"},
    "across": {"prep": "穿過;橫過", "adv": "橫過;在對面"},
    "accidental": {"adj": "意外的;偶然的"},
    "advantage": {"n": "優勢;有利條件"},
    "affair": {"n": "事務;事情"},
    "all": {"adj": "所有的;全部的", "adv": "完全地", "pron": "全部", "n": "全部;一切"},
    "along": {"prep": "沿著", "adv": "向前;一起"},
    "around": {"prep": "在…周圍;大約", "adv": "到處;四周"},
    "as": {"conj": "當…時;因為", "adv": "一樣地;如同", "prep": "作為"},
    "bank": {"n": "銀行", "v": "把(錢)存入銀行"},
    "bandage": {"n": "繃帶", "v": "包紮"},
    "before": {"prep": "在…之前", "conj": "在…以前", "adv": "以前;先前"},
    "best": {"adj": "最好的", "adv": "最好地", "v": "勝過", "n": "最好的人(或事物)"},
    "bid": {"n": "投標;出價", "v": "投標;出價"},
    "between": {"prep": "在…之間", "adv": "在中間"},
    "bite": {"n": "咬;一口", "v": "咬"},
    "black": {"adj": "黑色的", "n": "黑色"},
    "block": {"n": "街區;大塊", "v": "阻擋;堵住"},
    "blue": {"adj": "藍色的", "n": "藍色"},
    "break": {"n": "休息;中斷", "v": "打破;中斷"},
    "bright": {"adj": "明亮的;聰明的", "adv": "明亮地"},
    "class": {"n": "班級;課", "v": "把…分類"},
    "clean": {"adj": "乾淨的", "v": "打掃;清理", "adv": "完全地", "n": "打掃"},
    "clear": {"adj": "清楚的;晴朗的", "v": "清除;清理", "adv": "清楚地"},
    "close": {"adj": "接近的;親近的", "adv": "接近地", "v": "關上", "n": "結束"},
    "cool": {"adj": "涼爽的;很棒的", "v": "使冷卻", "n": "涼爽"},
    "copy": {"n": "副本", "v": "抄寫;複製"},
    "count": {"v": "數;計算", "n": "計數"},
    "course": {"n": "課程;科目", "v": "流動;奔流"},
    "even": {"adv": "甚至;連…都", "adj": "平坦的;平均的", "v": "使平坦"},
    "experience": {"n": "經驗;經歷", "v": "經歷;體驗"},
    "fall": {"n": "秋天", "v": "落下;跌倒"},
    "fast": {"adv": "快地", "adj": "快的"},
    "feel": {"v": "感覺;覺得", "n": "感覺"},
    "free": {"adj": "自由的;免費的", "v": "釋放", "adv": "免費地"},
})
MANUAL_DEFINITION_OVERRIDES.update({
    "backward": {"adj": "向後的;落後的"},
    "bottom": {"n": "底部;最下面", "adj": "最下面的;最低的", "v": "到底;降到最低"},
    "but": {"conj": "但是", "prep": "除了…以外", "adv": "只;僅僅"},
    "can": {"aux": "能;可以", "n": "罐頭", "v": "裝罐"},
    "care": {"n": "照顧;小心", "v": "關心;照顧"},
    "catch": {"v": "接住;抓到", "n": "接球;捕捉"},
    "climb": {"v": "爬;攀登", "n": "攀爬;攀登"},
    "dark": {"adj": "黑暗的", "n": "黑暗"},
    "deal": {"n": "交易", "v": "處理;對付"},
    "deep": {"adj": "深的", "adv": "深深地"},
    "enough": {"adv": "夠;足夠地", "adj": "足夠的", "n": "足夠;夠用"},
    "fight": {"v": "打架;戰鬥", "n": "打架;戰鬥"},
    "great": {"adj": "很棒的;偉大的", "n": "偉人"},
    "half": {"n": "一半", "adv": "一半地;部分地", "adj": "一半的"},
    "help": {"v": "幫助", "n": "幫助"},
    "hold": {"v": "拿著;握住", "n": "抓住;控制"},
    "home": {"n": "家", "adv": "在家;回家", "v": "回家", "adj": "家裡的;家庭的"},
    "hope": {"v": "希望", "n": "希望"},
    "inside": {"prep": "在…裡面", "adv": "在裡面", "n": "內部", "adj": "裡面的"},
    "key": {"adj": "重要的;關鍵的", "n": "鑰匙", "v": "鍵入"},
    "late": {"adj": "晚的;遲的", "adv": "晚;遲"},
    "love": {"n": "愛", "v": "愛;喜愛"},
    "matter": {"n": "事情;問題", "v": "要緊;有關係"},
    "mean": {"v": "意思是;表示", "adj": "小氣的;刻薄的"},
    "mind": {"n": "頭腦;心智", "v": "介意;注意"},
    "miss": {"v": "錯過;想念", "n": "小姐"},
    "pass": {"v": "經過;傳遞;及格", "n": "通行證;及格"},
    "point": {"n": "點;重點", "v": "指向;指出"},
    "rest": {"n": "休息;其餘", "v": "休息"},
    "round": {"adj": "圓形的", "n": "一輪;圓形物", "adv": "環繞地", "prep": "圍繞;繞著", "v": "使成圓形;繞行"},
    "study": {"n": "學習;研究", "v": "學習;讀書"},
    "train": {"n": "火車", "v": "訓練"},
    "turn": {"v": "轉動;轉彎", "n": "輪流;順序"},
    "type": {"n": "類型;種類", "v": "打字"},
    "use": {"v": "使用", "n": "用途"},
    "work": {"n": "工作", "v": "工作;運作"},
})
MAIN_ZH_OVERRIDES = {
    "act": "做;扮演",
    "after": "之後",
    "another": "另一個",
    "any": "任何",
    "attack": "攻擊",
    "association": "協會",
    "avenue": "林蔭道",
    "back": "後面",
    "belt": "腰帶",
    "both": "兩者都",
    "boss": "老闆",
    "book": "書",
    "chair": "椅子",
    "change": "改變",
    "cheap": "便宜的",
    "choice": "選擇",
    "cross": "穿越",
    "draw": "畫",
    "eccentric": "古怪的",
    "exercise": "運動",
    "alive": "活著的",
    "enroll": "註冊",
    "inflict": "施加",
    "agree": "同意",
    "left": "左邊",
    "light": "燈;光",
    "play": "玩",
    "present": "禮物",
    "preliminary": "初步的",
    "relation": "關係",
    "right": "對的;右邊的",
    "rural": "鄉村的",
    "watch": "看;手錶",
}
MAIN_ZH_OVERRIDES.update({
    "abrupt": "突然的",
    "about": "關於",
    "above": "上面;上方",
    "across": "穿過",
    "accidental": "意外的",
    "advantage": "優勢",
    "affair": "事務",
    "all": "全部",
    "along": "沿著",
    "around": "周圍;大約",
    "as": "作為",
    "bank": "銀行",
    "bandage": "繃帶",
    "before": "之前",
    "best": "最好的",
    "bid": "投標;競標",
    "between": "之間",
    "bite": "咬",
    "black": "黑色的",
    "block": "阻擋",
    "blue": "藍色的",
    "break": "休息;打破",
    "bright": "明亮的",
    "class": "班級",
    "clean": "乾淨的",
    "clear": "清楚的",
    "close": "關上;接近的",
    "cool": "涼爽的",
    "copy": "複製",
    "count": "數",
    "course": "課程",
    "even": "甚至",
    "experience": "經驗",
    "fall": "秋天;落下",
    "fast": "快的;快速地",
    "feel": "感覺",
    "free": "自由的;免費的",
})
MAIN_ZH_OVERRIDES.update({
    "backward": "向後的;落後的",
    "bottom": "底部",
    "but": "但是",
    "can": "能;可以",
    "care": "照顧;關心",
    "catch": "接住;抓到",
    "climb": "爬",
    "dark": "黑暗的",
    "deal": "處理",
    "deep": "深的",
    "enough": "足夠的",
    "fight": "打架;戰鬥",
    "great": "很棒的",
    "half": "一半",
    "help": "幫助",
    "hold": "拿著",
    "home": "家",
    "hope": "希望",
    "inside": "裡面",
    "key": "鑰匙",
    "late": "晚的;遲的",
    "love": "愛",
    "matter": "事情",
    "mean": "意思是",
    "mind": "頭腦",
    "miss": "錯過;想念",
    "pass": "經過",
    "point": "點;重點",
    "rest": "休息",
    "round": "圓形的",
    "study": "學習",
    "train": "火車",
    "turn": "轉動",
    "type": "類型",
    "use": "使用",
    "work": "工作",
})


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_traditional(text: str) -> str:
    if not isinstance(text, str):
        return text
    normalized = CC.convert(text)
    for src, dst in PREFERRED_TRADITIONAL_REPLACEMENTS.items():
        normalized = normalized.replace(src, dst)
    for src, dst in PREFERRED_TRADITIONAL_PHRASES.items():
        normalized = normalized.replace(src, dst)
    return normalized


def load_key() -> str:
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == "DEEPL_API_KEY":
            key = v.strip().strip('"').strip("'")
            if key:
                return key
    raise RuntimeError("DEEPL_API_KEY not found in .env")


def deepl_endpoint(key: str) -> str:
    return "https://api-free.deepl.com/v2/translate" if key.endswith(":fx") else "https://api.deepl.com/v2/translate"


def translate_batch(key: str, texts: list[str]) -> list[str]:
    if not texts:
        return []
    pairs = [("target_lang", "ZH-HANT"), ("source_lang", "EN")]
    for text in texts:
        pairs.append(("text", text))
    body = urllib.parse.urlencode(pairs).encode("utf-8")
    req = urllib.request.Request(
        deepl_endpoint(key),
        data=body,
        headers={
            "Authorization": f"DeepL-Auth-Key {key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "kid-english-vocab/0.1 ceec-definitions",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return [item.get("text", "").strip() for item in payload.get("translations", [])]


def normalize_pos(pos: str) -> str:
    p = (pos or "").strip().lower().rstrip(".")
    return POS_MAP.get(p, p)


def split_pos_chain(pos_chain: str) -> list[str]:
    return [normalize_pos(p) for p in str(pos_chain or "").split(";") if p.strip()]


def unique_keep_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        val = (item or "").strip()
        if not val or val in seen:
            continue
        seen.add(val)
        out.append(val)
    return out


def article_for(word: str) -> str:
    return "an" if word[:1].lower() in {"a", "e", "i", "o", "u"} else "a"


def variant_for_pos(word: str, raw: str, pos: str) -> str:
    raw = (raw or "").strip()
    pos = normalize_pos(pos)
    if not raw:
        return word
    if "(" in raw and ")" in raw and "/" not in raw:
        if pos == "n":
            return raw.replace("(", "").replace(")", "").strip()
        return re.sub(r"\([^)]*\)", "", raw).strip() or word
    if "/" in raw:
        return raw.split("/")[0].strip() or word
    return raw


def prompt_for(word: str, raw: str, pos: str) -> str:
    pos = normalize_pos(pos)
    base = variant_for_pos(word, raw, pos)
    if pos == "n":
        return f"{article_for(base)} {base}"
    if pos == "v":
        return f"to {base}"
    if pos == "adj":
        return f"very {base}"
    if pos == "adv":
        return base
    if pos == "prep":
        return base
    if pos == "conj":
        return base
    if pos == "pron":
        return f"{base} people"
    if pos == "aux":
        return base
    if pos == "det":
        return f"{base} book"
    if pos == "int":
        return base
    return base


def backup_grouped_definitions(entry: dict) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for definition in entry.get("definitions") or []:
        pos = normalize_pos(definition.get("pos", ""))
        zh = (definition.get("zh") or "").strip()
        if pos and zh:
            grouped[pos].append(zh)
    return {pos: unique_keep_order(values) for pos, values in grouped.items()}


def main():
    key = load_key()
    ceec = load_json(CEEC_PATH)
    backup = {item["word"]: item for item in load_json(BACKUP_PATH)["words"]}
    words = ceec["words"]

    prompt_cache: dict[str, str] = {}
    pending_prompts: list[str] = []
    pending_keys: list[str] = []
    built_entries: list[tuple[int, list[dict], list[str]]] = []

    for idx, entry in enumerate(words):
        pos_list = split_pos_chain(entry.get("pos", ""))
        if not pos_list:
            pos_list = [normalize_pos(entry.get("pos", "")) or ""]

        grouped = {}
        src = backup.get(entry["word"])
        if src and src.get("definitions"):
            grouped = backup_grouped_definitions(src)

        definitions = []
        missing = []
        for pos in pos_list:
            options = unique_keep_order(grouped.get(pos, []))
            if options:
                definitions.append({"pos": pos, "zh": " / ".join(options)})
            else:
                missing.append(pos)
        built_entries.append((idx, definitions, missing))

        for pos in missing:
            if pos in {"prep", "conj", "adv", "aux", "int"}:
                continue
            cache_key = f"{entry['word']}::{pos}"
            if cache_key not in prompt_cache:
                pending_keys.append(cache_key)
                pending_prompts.append(prompt_for(entry["word"], entry.get("raw", ""), pos))

    for batch_start in range(0, len(pending_prompts), BATCH_SIZE):
        batch_prompts = pending_prompts[batch_start:batch_start + BATCH_SIZE]
        batch_keys = pending_keys[batch_start:batch_start + BATCH_SIZE]
        batch_translations = translate_batch(key, batch_prompts)
        for cache_key, zh in zip(batch_keys, batch_translations):
            prompt_cache[cache_key] = zh
        done = batch_start + len(batch_prompts)
        print(f"translated fallback prompts {done}/{len(pending_prompts)}")

    fallback_only = 0
    backup_hit = 0
    for idx, definitions, missing in built_entries:
        entry = words[idx]
        entry_pos = split_pos_chain(entry.get("pos", ""))
        final_defs = []
        existing_by_pos = {normalize_pos(d["pos"]): d["zh"] for d in definitions}
        for pos in entry_pos:
            manual = MANUAL_DEFINITION_OVERRIDES.get(entry["word"], {}).get(pos)
            if manual:
                final_defs.append({"pos": pos, "zh": sanitize_traditional(manual)})
                continue
            zh = existing_by_pos.get(pos)
            if zh:
                backup_hit += 1
                final_defs.append({"pos": pos, "zh": sanitize_traditional(zh)})
                continue
            cache_key = f"{entry['word']}::{pos}"
            zh = (prompt_cache.get(cache_key) or "").strip() or (entry.get("zh") or "").strip()
            final_defs.append({"pos": pos, "zh": sanitize_traditional(zh)})
            fallback_only += 1

        if not final_defs:
            final_defs = [{"pos": normalize_pos(entry.get("pos", "")), "zh": sanitize_traditional((entry.get("zh") or "").strip())}]
        entry["definitions"] = final_defs
        if entry["word"] in MAIN_ZH_OVERRIDES:
            entry["zh"] = sanitize_traditional(MAIN_ZH_OVERRIDES[entry["word"]])
        else:
            entry["zh"] = sanitize_traditional((entry.get("zh") or "").strip())

    CEEC_PATH.write_text(json.dumps(ceec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {CEEC_PATH}")
    print(f"backup_definition_rows={backup_hit}")
    print(f"fallback_definition_rows={fallback_only}")


if __name__ == "__main__":
    main()
