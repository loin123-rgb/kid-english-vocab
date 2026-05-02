#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
FILES = [
    ROOT / "vocab_ceec_7000.json",
    ROOT.parent / "vocab.json",
]

POS_ALIASES = {
    "noun": "n",
    "vi": "v",
    "vt": "v",
    "art": "det",
}

PHRASE_REPLACEMENTS = {
    "帐号": "帳號",
    "账户": "帳戶",
    "注册": "註冊",
    "协会": "協會",
    "林荫道": "林蔭道",
    "严打": "鎮壓",
    "乡郊": "鄉村",
    "戚谊": "關係",
}

ENTRY_OVERRIDES = {
    "aboriginal": {"zh": "原住民", "defs": {"adj": "原住民的", "n": "原住民"}},
    "abrupt": {"zh": "突然的", "defs": {"adj": "突然的;唐突的"}},
    "accidental": {"zh": "意外的", "defs": {"adj": "意外的;偶然的"}},
    "alligator": {"zh": "短吻鱷", "defs": {"n": "短吻鱷"}},
    "am": {"zh": "上午", "defs": {"adv": "上午", "n": "上午"}},
    "ankle": {"zh": "腳踝", "defs": {"n": "腳踝"}},
    "act": {"zh": "做;扮演", "defs": {"n": "行為;動作", "v": "做;扮演"}},
    "actress": {"zh": "女演員", "defs": {"n": "女演員"}},
    "advantage": {"zh": "優勢", "defs": {"n": "優勢;有利條件"}},
    "affair": {"zh": "事務", "defs": {"n": "事務;事情"}},
    "affection": {"zh": "感情", "defs": {"n": "感情;喜愛"}},
    "after": {"zh": "之後", "defs": {"prep": "在…之後", "conj": "在…之後", "adv": "之後;隨後"}},
    "ago": {"zh": "以前", "defs": {"adv": "以前"}},
    "alive": {"zh": "活著的", "defs": {"adj": "活著的"}},
    "association": {"zh": "協會", "defs": {"n": "協會"}},
    "avenue": {"zh": "林蔭道", "defs": {"n": "林蔭道"}},
    "bandage": {"zh": "繃帶", "defs": {"n": "繃帶", "v": "包紮"}},
    "bell": {"zh": "鈴;鐘", "defs": {"n": "鈴;鐘"}},
    "bid": {"zh": "投標;競標", "defs": {"n": "投標;出價", "v": "投標;出價"}},
    "blunt": {"zh": "鈍", "defs": {"adj": "鈍;直率的", "v": "使變鈍"}},
    "boast": {"zh": "吹牛", "defs": {"n": "吹牛;自誇", "v": "吹牛;自誇"}},
    "bore": {"zh": "鑽孔", "defs": {"v": "鑽孔", "n": "鑽孔;孔"}},
    "brink": {"zh": "邊緣", "defs": {"n": "邊緣"}},
    "bunch": {"zh": "一串;一束", "defs": {"n": "一串;一束"}},
    "bundle": {"zh": "一捆;一包", "defs": {"n": "一捆;一包;一束"}},
    "boundary": {"zh": "邊界", "defs": {"n": "邊界;界線"}},
    "bug": {"zh": "蟲", "defs": {"n": "蟲;軟體錯誤", "v": "使煩擾;裝竊聽器"}},
    "burglar": {"zh": "小偷;竊賊", "defs": {"n": "小偷;竊賊"}},
    "carbon": {"zh": "碳", "defs": {"n": "碳"}},
    "caterpillar": {"zh": "毛毛蟲", "defs": {"n": "毛毛蟲"}},
    "chopstick": {"zh": "筷子", "defs": {"n": "筷子"}},
    "cherish": {"zh": "珍惜", "defs": {"v": "珍惜;愛護"}},
    "chirp": {"zh": "嘰嘰喳喳", "defs": {"n": "鳥叫聲;蟲鳴聲", "v": "嘰嘰喳喳叫"}},
    "consistent": {"zh": "一致的", "defs": {"adj": "一致的;前後一致的"}},
    "conceive": {"zh": "構想;想像", "defs": {"v": "構想;想像;懷孕"}},
    "confederation": {"zh": "聯邦;聯盟", "defs": {"n": "聯邦;聯盟"}},
    "confine": {"zh": "管制", "defs": {"v": "管制;侷限"}},
    "consist": {"zh": "由…組成", "defs": {"v": "由…組成"}},
    "cord": {"zh": "繩子", "defs": {"n": "繩子;繩索"}},
    "cousin": {"zh": "表;堂兄弟姊妹", "defs": {"n": "表;堂兄弟姊妹"}},
    "copy": {"zh": "複製"},
    "crackdown": {"zh": "鎮壓", "defs": {"n": "鎮壓"}},
    "crowded": {"pos": "adj", "zh": "擁擠的", "defs": {"adj": "擁擠的"}},
    "county": {"zh": "郡;縣", "defs": {"n": "郡;縣"}},
    "dam": {"zh": "水壩", "defs": {"n": "水壩", "v": "築壩攔阻"}},
    "dazzle": {"zh": "使目眩", "defs": {"v": "使目眩;使眼花", "n": "耀眼"}},
    "deceive": {"zh": "欺騙", "defs": {"v": "欺騙"}},
    "descend": {"zh": "下降", "defs": {"v": "下降;下來"}},
    "diagram": {"zh": "圖表", "defs": {"n": "圖表;圖解", "v": "用圖表示"}},
    "district": {"zh": "地區", "defs": {"n": "地區;區域"}},
    "doughnut": {"zh": "甜甜圈", "defs": {"n": "甜甜圈"}},
    "draw": {"zh": "畫", "defs": {"v": "畫;繪製", "n": "平手;平局"}},
    "enroll": {"zh": "註冊", "defs": {"v": "註冊;登記", "n": "註冊;入學"}},
    "freshman": {"zh": "新生", "defs": {"n": "新生;一年級生"}},
    "hawk": {"zh": "老鷹", "defs": {"n": "老鷹"}},
    "heap": {"zh": "一堆", "defs": {"n": "一堆", "v": "堆起"}},
    "hedge": {"zh": "樹籬", "defs": {"n": "樹籬", "v": "避免正面回答;對沖"}},
    "heel": {"zh": "腳跟", "defs": {"n": "腳跟", "v": "緊跟"}},
    "horn": {"zh": "角;喇叭", "defs": {"n": "角;喇叭"}},
    "hormone": {"zh": "賀爾蒙", "defs": {"n": "賀爾蒙"}},
    "hush": {"zh": "安靜", "defs": {"n": "安靜", "v": "使安靜"}},
    "jade": {"zh": "玉", "defs": {"n": "玉"}},
    "inquiry": {"zh": "詢問;諮詢", "defs": {"n": "詢問;諮詢"}},
    "inning": {"zh": "局;回合", "defs": {"n": "局;回合"}},
    "jar": {"zh": "罐子", "defs": {"n": "罐子;瓶子"}},
    "jet": {"zh": "噴射機", "defs": {"n": "噴射機", "v": "噴射"}},
    "lap": {"zh": "膝上", "defs": {"n": "膝上"}},
    "lean": {"zh": "倚靠", "defs": {"v": "倚靠;傾斜", "adj": "瘦的"}},
    "limb": {"zh": "四肢", "defs": {"n": "四肢"}},
    "linen": {"zh": "亞麻布", "defs": {"n": "亞麻布;亞麻製品"}},
    "longitude": {"zh": "經度", "defs": {"n": "經度"}},
    "luck": {"zh": "運氣", "defs": {"n": "運氣;好運"}},
    "mud": {"zh": "泥巴", "defs": {"n": "泥巴;泥"}},
    "preliminary": {"zh": "初步的", "defs": {"adj": "初步的;預備的", "n": "初步;預備工作"}},
    "prey": {"zh": "獵物", "defs": {"n": "獵物", "v": "捕食"}},
    "raid": {"zh": "突襲", "defs": {"n": "突襲", "v": "突襲;搜捕"}},
    "rat": {"zh": "老鼠", "defs": {"n": "老鼠;叛徒"}},
    "relation": {"zh": "關係", "defs": {"n": "關係;關聯"}},
    "rural": {"zh": "鄉村的", "defs": {"adj": "鄉村的"}},
    "sand": {"zh": "沙子", "defs": {"n": "沙子;沙灘", "v": "磨光;以沙堵塞"}},
    "shore": {"zh": "海岸", "defs": {"n": "海岸;岸邊"}},
    "spin": {"zh": "旋轉", "defs": {"n": "旋轉", "v": "旋轉;自旋"}},
    "steer": {"zh": "操縱", "defs": {"v": "操縱;引導", "n": "公牛"}},
    "stir": {"zh": "攪拌", "defs": {"v": "攪拌", "n": "攪動"}},
    "sweep": {"zh": "打掃", "defs": {"v": "打掃;掃過;掃視"}},
    "ticket": {"zh": "車票;票", "defs": {"n": "車票;票;罰單"}},
    "tide": {"zh": "潮汐", "defs": {"n": "潮汐"}},
    "toast": {"zh": "吐司", "defs": {"n": "吐司;烤麵包片", "v": "敬酒;烘烤"}},
    "track": {"zh": "跑道;軌道", "defs": {"n": "跑道;軌道;足跡", "v": "跟蹤;追蹤"}},
    "twig": {"zh": "細枝", "defs": {"n": "細枝;樹枝"}},
    "tube": {"zh": "管子", "defs": {"n": "管子"}},
    "trail": {"zh": "小徑", "defs": {"n": "小徑;步道", "v": "拖著走;尾隨"}},
    "urge": {"zh": "催促", "defs": {"n": "衝動;強烈慾望", "v": "催促;力勸"}},
    "wrist": {"zh": "手腕", "defs": {"n": "手腕"}},
    "zero": {"zh": "零;零分", "defs": {"n": "零;零分;零度", "num": "零"}},
    "assassinate": {"zh": "刺殺", "defs": {"v": "刺殺"}},
    "enlighten": {"zh": "啟發", "defs": {"v": "啟發", "n": "啟發"}},
    "fraction": {"zh": "分數;部分", "defs": {"n": "分數;部分"}},
    "frontier": {"zh": "邊疆", "defs": {"n": "邊疆;邊界"}},
    "gallop": {"zh": "飛奔", "defs": {"n": "飛奔", "v": "飛奔;疾馳"}},
    "intimidate": {"zh": "恐嚇", "defs": {"v": "恐嚇"}},
    "isle": {"zh": "小島", "defs": {"n": "小島"}},
    "kettle": {"zh": "水壺", "defs": {"n": "水壺"}},
    "mattress": {"zh": "床墊", "defs": {"n": "床墊"}},
    "mingle": {"zh": "混合", "defs": {"v": "混合;交際"}},
    "oppress": {"zh": "壓迫", "defs": {"v": "壓迫"}},
    "ornament": {"zh": "裝飾品", "defs": {"n": "裝飾品", "v": "裝飾"}},
    "pinch": {"zh": "捏", "defs": {"n": "捏一下", "v": "捏;掐"}},
    "province": {"zh": "省;省份", "defs": {"n": "省;省份"}},
    "quiver": {"zh": "顫抖", "defs": {"n": "箭袋", "v": "顫抖"}},
    "restrain": {"zh": "抑制", "defs": {"v": "抑制;克制"}},
    "revive": {"zh": "甦醒;恢復", "defs": {"v": "甦醒;恢復"}},
    "ridge": {"zh": "山脊", "defs": {"n": "山脊", "v": "形成脊狀"}},
    "robe": {"zh": "長袍", "defs": {"n": "長袍"}},
    "rust": {"zh": "鐵鏽", "defs": {"n": "鐵鏽", "v": "生鏽"}},
    "scold": {"zh": "責罵", "defs": {"v": "責罵", "n": "責罵"}},
    "shovel": {"zh": "鏟子", "defs": {"n": "鏟子", "v": "鏟"}},
    "silk": {"zh": "絲絹", "defs": {"n": "絲絹"}},
    "situation": {"zh": "情況", "defs": {"n": "情況;局面"}},
    "skim": {"zh": "略讀", "defs": {"v": "略讀;擇去", "n": "擇去"}},
    "spade": {"zh": "鏟子", "defs": {"n": "鏟子"}},
    "spear": {"zh": "長矛", "defs": {"n": "長矛", "v": "刺穿"}},
    "squad": {"zh": "小隊", "defs": {"n": "小隊"}},
    "stumble": {"zh": "絆倒", "defs": {"v": "絆倒;踉蹌", "n": "絆倒"}},
    "surpass": {"zh": "超越", "defs": {"v": "超越"}},
    "syllable": {"zh": "音節", "defs": {"n": "音節"}},
    "thigh": {"zh": "大腿", "defs": {"n": "大腿"}},
    "thirst": {"zh": "口渴", "defs": {"n": "口渴"}},
}

BAD_MAIN_ZH = {
    "",
    "偶",
    "前",
    "後",
    "利",
    "事",
    "愛",
    "硬",
    "界",
    "一局",
    "研訊",
    "新丁",
    "嚴打",
    "侵入家宅者",
    "土著人",
}

BAD_SUBSTRINGS = (
    "家宅者",
    "土著",
    "嚴打",
    "新丁",
    "研訊",
)

SEPARATOR_RE = re.compile(r"\s*(?:/|,|，|；|;)\s*")


def normalize_pos(pos: str) -> str:
    key = str(pos or "").strip().lower()
    return POS_ALIASES.get(key, key)


def looks_mojibake(text: str) -> bool:
    if not isinstance(text, str) or not text:
        return False
    try:
        fixed = text.encode("latin1").decode("utf-8")
    except Exception:
        return False
    return fixed != text and any(ord(ch) > 127 for ch in text)


def maybe_fix_mojibake(text: str) -> str:
    if looks_mojibake(text):
        return text.encode("latin1").decode("utf-8")
    return text


def replace_phrases(text: str) -> str:
    out = text
    for src, dst in PHRASE_REPLACEMENTS.items():
        out = out.replace(src, dst)
    return out


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return out


def clean_fragment(text: str, pos: str) -> str:
    s = replace_phrases(maybe_fix_mojibake(str(text or "").strip()))
    s = s.replace("...", "")
    s = re.sub(r"\s+", "", s)
    s = s.strip(" ;；,/，")
    if pos == "adj":
        s = re.sub(r"^(很|非常)", "", s)
        if s and not s.endswith("的") and len(s) <= 4:
            s += "的"
    return s


def clean_definition_text(text: str, pos: str) -> str:
    parts = [clean_fragment(part, pos) for part in SEPARATOR_RE.split(str(text or ""))]
    parts = [part for part in parts if part]
    parts = dedupe_keep_order(parts)
    return ";".join(parts[:4])


def first_piece(text: str) -> str:
    cleaned = clean_definition_text(text, "")
    if not cleaned:
        return ""
    return cleaned.split(";")[0].strip()


def should_replace_main_zh(text: str) -> bool:
    s = clean_fragment(text, "")
    if s in BAD_MAIN_ZH:
        return True
    if len(s) <= 1:
        return True
    if any(part in s for part in BAD_SUBSTRINGS):
        return True
    return False


def choose_main_zh(entry: dict, defs: list[dict]) -> str:
    current = clean_fragment(entry.get("zh", ""), "")
    pos_chain = [normalize_pos(p) for p in str(entry.get("pos", "")).split(";") if p.strip()]
    main_pos = pos_chain[0] if pos_chain else ""

    preferred = ""
    for definition in defs:
        if normalize_pos(definition.get("pos")) == main_pos and definition.get("zh"):
            preferred = first_piece(definition.get("zh", ""))
            break
    if not preferred:
        for definition in defs:
            if definition.get("zh"):
                preferred = first_piece(definition.get("zh", ""))
                break

    if should_replace_main_zh(current) and preferred:
        return preferred
    return current or preferred


def normalize_entry(entry: dict) -> int:
    changed = 0
    word = entry.get("word", "")
    override = ENTRY_OVERRIDES.get(word, {})

    if override.get("pos") and entry.get("pos") != override["pos"]:
        entry["pos"] = override["pos"]
        changed += 1

    defs = entry.get("definitions") or []
    for definition in defs:
        pos = normalize_pos(definition.get("pos"))
        if definition.get("pos") != pos:
            definition["pos"] = pos
            changed += 1

        desired = override.get("defs", {}).get(pos)
        if not desired:
            desired = clean_definition_text(definition.get("zh", ""), pos)
        if desired and definition.get("zh") != desired:
            definition["zh"] = desired
            changed += 1

    if override.get("zh"):
        main_zh = override["zh"]
    else:
        main_zh = choose_main_zh(entry, defs)
        main_zh = clean_fragment(main_zh, "")

    if main_zh and entry.get("zh") != main_zh:
        entry["zh"] = main_zh
        changed += 1

    return changed


def cleanup_file(path: Path) -> tuple[int, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    words = data["words"] if isinstance(data, dict) else data

    changed = 0
    for entry in words:
        changed += normalize_entry(entry)

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(words), changed


def main() -> None:
    for path in FILES:
        total, changed = cleanup_file(path)
        print(f"{path.name}: words={total} changed={changed}")


if __name__ == "__main__":
    main()
