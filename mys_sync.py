"""将米游社绝区零详情转换为现有面板缓存。"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from .utils.mys_panel_sync import (
    PanelSyncResult,
    get_binding,
    save_cache,
    select_role,
    sync_panel,
)

PLAYER_INFO_DIR = Path(__file__).parent / "user_data" / "player_info"
RESOURCE_DIR = Path(__file__).parent / "res" / "json_data"


def _load(name):
    return json.loads((RESOURCE_DIR / f"{name}.json").read_text(encoding="utf-8"))


AVATARS = _load("avatars")
PROPERTIES = _load("property")
LOCS = _load("locs")["zh-cn"]
EQUIPMENT = _load("equipments")
WEAPONS = _load("weapons")
SKILL_INDEX = {0: 0, 2: 1, 6: 2, 1: 3, 3: 4, 5: 5}
PROP_NAMES = {
    1: "生命值",
    2: "攻击力",
    3: "防御力",
    4: "冲击力",
    5: "暴击率",
    6: "暴击伤害",
    7: "异常掌控",
    8: "异常精通",
    9: "穿透率",
    11: "能量自动回复",
    232: "穿透值",
    19: "贯穿力",
    25: "锐能自动累积",
    28: "锐暴伤害",
}
RATIOS = {"暴击率", "暴击伤害", "穿透率", "伤害加成", "锐暴伤害"}
MULTIPLIERS = {"冲击力", "异常掌控", "能量自动回复", "锐能自动累积"}


def _number(value, percent_scale=100):
    text = str(value or "0").replace(",", "").strip()
    number = float(text.rstrip("%"))
    return number * percent_scale if text.endswith("%") else number


def _property(data):
    prop_id = str(data["property_id"])
    name = LOCS.get(PROPERTIES.get(prop_id, {}).get("Name", ""))
    if not name:
        raise ValueError("不支持的装备属性")
    return {"属性名": name, "属性值": _number(data.get("base"))}


def _convert_properties(items):
    result = {f"基础{name}": 0 for name in PROP_NAMES.values()}
    for item in items:
        prop_id = int(item["property_id"])
        name = PROP_NAMES.get(prop_id)
        if name is None and "伤害加成" in str(item.get("property_name", "")):
            name = "伤害加成"
        if name is None:
            continue
        scale = 100 if name in RATIOS else 1
        base = _number(item.get("base"), scale)
        final = _number(item.get("final"), scale)
        if name in {"能量自动回复", "锐能自动累积"}:
            base *= 100
            final *= 100
        # 非重点属性常只返回 final，不能用空 base 参与乘法而显示成 0。
        if name in MULTIPLIERS and not base:
            base = final
        result[f"基础{name}"] = base
        result[f"额外{name}"] = (
            ((final / base - 1) * 10000 if base else 0)
            if name in MULTIPLIERS
            else final - base
        )
    return result


def convert_character(data):
    role_id = str(data["id"])
    path = RESOURCE_DIR / "Avatars" / f"{role_id}.json"
    if role_id not in AVATARS or not path.exists():
        return None
    metadata = json.loads(path.read_text(encoding="utf-8"))
    avatar = AVATARS[role_id]
    # 克拉蕾的米游社面板没有攻击力，不能按普通角色判作详情缺失。
    required_properties = {1, 3} if role_id == "1611" else {1, 2, 3}
    if not required_properties.issubset(
        {int(p["property_id"]) for p in data.get("properties", [])}
    ):
        raise ValueError("角色基础属性详情不完整")
    skills = [0] * 6
    seen = set()
    for skill in data.get("skills", []):
        skill_type = int(skill["skill_type"])
        if skill_type in SKILL_INDEX:
            skills[SKILL_INDEX[skill_type]] = int(skill["level"])
            seen.add(skill_type)
    if seen != set(SKILL_INDEX):
        raise ValueError("角色技能详情不完整")
    # 米游社直接返回面板技能等级；不能再次追加影画的技能加成。
    role = {
        "名称": metadata["Name"],
        "等级": int(data["level"]),
        "元素": metadata["ElementTypes"][0],
        "特性": metadata["Specialty"]["Name"],
        "技能": skills,
        "影画": int(data.get("rank", 0)),
        "立绘": avatar["Image"],
        "头像": avatar["CircleIcon"],
        "属性": _convert_properties(data["properties"]),
        "武器": {},
        "驱动盘": [{} for _ in range(6)],
        "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    for disc in data.get("equip", []):
        pos = int(disc["equipment_type"])
        if not 1 <= pos <= 6:
            raise ValueError("驱动盘位置无效")
        info = EQUIPMENT["Items"].get(str(disc["id"]))
        if not info:
            raise ValueError("驱动盘资源暂未收录")
        suit_id = info["SuitId"]
        suit = EQUIPMENT["Suits"][str(suit_id)]
        subs = []
        for prop in disc.get("properties", []):
            converted = _property(prop)
            # level 是词条总档数，初始词条为 1；add 为接口展示标记。
            if prop.get("level") is not None:
                converted["提升次数"] = max(0, int(prop["level"]) - 1)
            subs.append(converted)
        role["驱动盘"][pos - 1] = {
            "名称": disc["name"],
            "图标": suit["Icon"],
            "头像": role["头像"],
            "部位": pos,
            "所属套装": suit_id,
            "等级": int(disc["level"]),
            "星级": info["Rarity"],
            "主属性": _property(disc["main_properties"][0]),
            "词条": subs,
        }
    weapon = data.get("weapon")
    if weapon:
        weapon_id = str(weapon["id"])
        wmeta = WEAPONS.get(weapon_id)
        if wmeta is None:
            raise ValueError("音擎资源暂未收录")
        detail = RESOURCE_DIR / "Weapons" / f"{weapon_id}.json"
        wdetail = (
            json.loads(detail.read_text(encoding="utf-8")) if detail.exists() else {}
        )
        role["武器"] = {
            "名称": weapon["name"],
            "图标": Path(wmeta["ImagePath"]).stem,
            "类型": wdetail.get("Profession", {}).get("Name", role["特性"]),
            "等级": int(weapon["level"]),
            "星级": wmeta["Rarity"],
            "精炼等级": int(weapon["star"]),
            "基础攻击": _number(weapon["main_properties"][0]["base"]),
            "副属性": _property(weapon["properties"][0])
            if weapon.get("properties")
            else {"属性名": "无属性", "属性值": 0},
        }
    return role


def select_zzz_role(user, existing_uid=None):
    return select_role(user, "zzz", existing_uid)


def get_uid_binding(qq_id):
    return get_binding(PLAYER_INFO_DIR, qq_id)


def _save(uid, account, details):
    return save_cache(
        PLAYER_INFO_DIR, uid, account, details, convert_character, "驱动盘"
    )


def save_character_cache(uid, account, details):
    return len(_save(uid, account, details))


async def sync_single_zzz_uid(
    qq_id, user, api, captcha_notifier=None
) -> PanelSyncResult:
    return await sync_panel(
        qq_id, user, api, PLAYER_INFO_DIR, "zzz", _save, captcha_notifier
    )
