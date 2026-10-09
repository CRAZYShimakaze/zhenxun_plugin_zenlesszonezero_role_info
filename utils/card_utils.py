import datetime
import os

from PIL import ImageFont

from ..utils.json_utils import load_json, save_json

GENSHIN_CARD_PATH = os.path.join(os.path.dirname(__file__), "..")

GENSHIN_DATA_PATH = GENSHIN_CARD_PATH + "/user_data"
player_info_path = GENSHIN_DATA_PATH + "/player_info"
group_info_path = GENSHIN_DATA_PATH + "/group_info"
card_res_path = GENSHIN_CARD_PATH + "/res/"
data_res_path = GENSHIN_DATA_PATH + "/res/"
qq_logo_path = GENSHIN_DATA_PATH + "/qq_logo/"
json_path = card_res_path + "json_data"
bg_path = card_res_path + "background"
path_path = data_res_path + "path"
char_pic_path = data_res_path + "character"
avatar_path = data_res_path + "avatar"
other_path = card_res_path + "other"
type_path = card_res_path + "type"
outline_path = card_res_path + "outline"
skill_path = data_res_path + "skill"
talent_path = data_res_path + "talent"
weapon_path = data_res_path + "weapon"
reli_path = data_res_path + "reli"
font_path = card_res_path + "fonts"

avatar_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/avatars.json"
equipments_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/equipments.json"
locs_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/locs.json"
medals_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/medals.json"
namecards_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/namecards.json"
pfps_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/pfps.json"
property_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/property.json"
titles_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/titles.json"
weapons_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/weapons.json"
equipmentleveltemplatetb_url = "https://git.mero.moe/dimbreath/ZenlessData/raw/branch/master/FileCfg/equipmentleveltemplatetb.json"
weaponleveltemplatetb_url = "https://git.mero.moe/dimbreath/ZenlessData/raw/branch/master/FileCfg/weaponLeveltemplatetb.json"
weaponstartemplatetb_url = "https://git.mero.moe/dimbreath/ZenlessData/raw/branch/master/FileCfg/weaponstartemplatetb.json"

score_json = load_json(path=f"{json_path}/score.json")
avatars_json = load_json(path=f"{json_path}/avatars.json")
locs = load_json(path=f"{json_path}/locs.json")
locs = locs["zh-cn"]
property_json = load_json(path=f"{json_path}/property.json")
equipments_json = load_json(path=f"{json_path}/equipments.json")
equipmentleveltemplatetb_json = load_json(path=f"{json_path}/equipmentleveltemplatetb.json")
weaponleveltemplatetb_json = load_json(path=f"{json_path}/weaponLeveltemplatetb.json")
weaponstartemplatetb_json = load_json(path=f"{json_path}/weaponstartemplatetb.json")
prop_list = {
    "生命值": "11101",
    "攻击力": "12101",
    "防御力": "13101",
    "冲击力": "12201",
    "暴击率": "20101",
    "暴击伤害": "21101",
    "异常掌控": "31401",
    "异常精通": "31201",
    "能量自动回复": "30501",
    "穿透率": "",
    "穿透值": "",
    "贯穿力": "",
    "伤害加成": "",
}


def get_artifact_suit(artifacts: list):
    """
    获取遗器套装
    :param artifacts: 遗器列表
    :return: 套装列表
    """

    artifacts_type = set(artifacts)
    suit_2 = []
    suit_4 = []
    for item in artifacts_type:
        if item == "":
            continue
        if artifacts.count(item) == 6:
            suit_4.append(item)
            suit_2.append(item)
        elif artifacts.count(item) >= 4:
            suit_4.append(item)
        elif artifacts.count(item) >= 2:
            suit_2.append(item)
    return suit_4, suit_2


def _artifact_identity(artifact):
    """Match equipment type and stats independently of source metadata."""
    required_fields = ("所属套装", "部位", "等级", "星级", "主属性", "词条")
    if not isinstance(artifact, dict) or any(
        artifact.get(key) is None for key in required_fields
    ):
        return None

    main_property = artifact["主属性"]
    sub_properties = artifact["词条"]
    if not isinstance(main_property, dict) or not isinstance(sub_properties, list):
        return None
    if any(main_property.get(key) is None for key in ("属性名", "属性值")):
        return None

    normalized_sub_properties = []
    for item in sub_properties:
        if not isinstance(item, dict) or any(
            item.get(key) is None for key in ("属性名", "属性值")
        ):
            return None
        normalized_sub_properties.append((item["属性名"], item["属性值"]))

    return (
        artifact["所属套装"],
        artifact["部位"],
        artifact["等级"],
        artifact["星级"],
        main_property["属性名"],
        main_property["属性值"],
        tuple(sorted(normalized_sub_properties)),
    )


def _merge_artifact_metadata(old_artifact, new_artifact):
    merged = dict(old_artifact)
    merged.update(new_artifact)
    for key in ("角色", "头像"):
        if not new_artifact.get(key) and old_artifact.get(key):
            merged[key] = old_artifact[key]

    old_sub_properties = {}
    for item in old_artifact.get("词条", []):
        key = (item.get("属性名"), item.get("属性值"))
        old_sub_properties.setdefault(key, []).append(item)

    merged_sub_properties = []
    for item in new_artifact.get("词条", []):
        sub_property = dict(item)
        key = (item.get("属性名"), item.get("属性值"))
        old_items = old_sub_properties.get(key, [])
        if sub_property.get("提升次数") is None and old_items:
            previous = old_items.pop(0)
            if previous.get("提升次数") is not None:
                sub_property["提升次数"] = previous["提升次数"]
        elif old_items:
            old_items.pop(0)
        merged_sub_properties.append(sub_property)
    merged["词条"] = merged_sub_properties
    return merged


def _normalize_artifact_cache(artifact_cache, roles=None):
    if not isinstance(artifact_cache, list):
        return artifact_cache

    roles = roles if isinstance(roles, dict) else {}
    equipped_by_identity = {}
    for role_name, role_data in roles.items():
        if not isinstance(role_data, dict):
            continue
        avatar = role_data.get("头像")
        for artifact in role_data.get("驱动盘", []) or []:
            identity = _artifact_identity(artifact)
            if identity is not None:
                equipped_by_identity[identity] = (
                    role_name,
                    avatar or artifact.get("头像"),
                )

    normalized_cache = []
    for position_cache in artifact_cache:
        if not isinstance(position_cache, list):
            normalized_cache.append(position_cache)
            continue

        normalized_position = []
        identity_indexes = {}
        for artifact in position_cache:
            identity = _artifact_identity(artifact)
            if identity is None:
                normalized_position.append(artifact)
                continue
            if identity in identity_indexes:
                index = identity_indexes[identity]
                normalized_position[index] = _merge_artifact_metadata(
                    normalized_position[index], artifact
                )
            else:
                identity_indexes[identity] = len(normalized_position)
                normalized_position.append(artifact)

        for artifact in normalized_position:
            identity = _artifact_identity(artifact)
            if identity is None:
                continue
            if identity in equipped_by_identity:
                owner, avatar = equipped_by_identity[identity]
                artifact["角色"] = owner
                if avatar:
                    artifact["头像"] = avatar
            elif artifact.get("角色") in roles:
                artifact["角色"] = ""
        normalized_cache.append(normalized_position)
    return normalized_cache


class PlayerInfo:
    def __init__(self, uid: [int, str]):
        self.path = f"{player_info_path}/{uid}.json"
        self.data = load_json(path=self.path)
        self.player_info = self.data["玩家信息"] if "玩家信息" in self.data else {}
        self.roles = self.data["角色"] if "角色" in self.data else {}
        if "驱动盘榜单" not in self.data:
            self.data["驱动盘榜单"] = []
        if "小毕业驱动盘" not in self.data:
            self.data["小毕业驱动盘"] = 0
        if "大毕业驱动盘" not in self.data:
            self.data["大毕业驱动盘"] = 0
        if "驱动盘列表" not in self.data:
            self.data["驱动盘列表"] = [[], [], [], [], [], []]
        self.data["驱动盘列表"] = _normalize_artifact_cache(self.data["驱动盘列表"], self.roles)

    def set_player(self, data: dict):
        player_info = data["SocialDetail"]["ProfileDetail"]
        self.player_info["昵称"] = player_info.get("Nickname", "unknown")
        self.player_info["等级"] = player_info.get("Level", "unknown")
        # self.player_info["世界等级"] = data.get("worldLevel", "unknown")
        # self.player_info["签名"] = data.get("signature", "unknown")
        # self.player_info["成就"] = data.get("finishAchievementNum", "unknown")
        self.player_info["角色列表"] = dictlist_to_list(data["ShowcaseDetail"].get("AvatarList", []))
        # self.player_info["名片列表"] = data.get("showNameCardIdList", "unknown")
        # self.player_info["头像"] = data["profilePicture"].get("avatarId", "unknown")
        self.player_info["更新时间"] = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")

    def set_role(self, data: dict):
        role_info = {}
        role_name, role_json = get_name_by_id(str(data["Id"]))
        if role_name is not None:
            role_info["名称"] = role_name
            role_info["等级"] = data["Level"]
            role_info["元素"] = role_json["ElementTypes"][0]
            role_info["特性"] = role_json["Specialty"]["Name"]
            role_info["技能"] = [0] * 6
            role_info["立绘"] = avatars_json[str(data["Id"])]["Image"]
            role_info["头像"] = avatars_json[str(data["Id"])]["CircleIcon"]
            index_conver = [0, 3, 1, 4, -1, 5, 2]
            for item in data["SkillLevelList"]:
                # if item["Index"] == 5:
                #     continue
                role_info["技能"][index_conver[item["Index"]]] = item["Level"]
            role_info["影画"] = data["TalentLevel"]
            if role_info["影画"] >= 5:
                role_info["技能"] = [item + 2 for item in role_info["技能"]]
            if role_info["影画"] >= 3:
                role_info["技能"] = [item + 2 for item in role_info["技能"]]

            artifacts = [{}] * 6
            for artifact in data.get("EquippedList", []):
                artifact_info = {}
                suitid = equipments_json["Items"][str(artifact["Equipment"]["Id"])]["SuitId"]
                artifact_json = load_json(path=f"{json_path}/Suits/{suitid}.json")
                artifact_info["名称"] = artifact_json["Name"]
                artifact_info["图标"] = equipments_json["Suits"][str(suitid)]["Icon"]
                artifact_info["头像"] = role_info["头像"]
                artifact_info["部位"] = artifact["Slot"]
                artifact_info["所属套装"] = suitid
                artifact_info["等级"] = artifact["Equipment"]["Level"]
                artifact_info["星级"] = equipments_json["Items"][str(artifact["Equipment"]["Id"])]["Rarity"]
                val = 0
                for inffo in equipmentleveltemplatetb_json["MOFGFFKBLLC"]:
                    if inffo["DJEPJPBAFCE"] == artifact_info["等级"] and inffo["OANJJBHJLHD"] == artifact_info["星级"]:
                        val = inffo["GMJIPPMIIIF"]
                        break
                artifact_info["主属性"] = {
                    "属性名": locs.get(property_json.get(str(artifact["Equipment"]["MainPropertyList"][0]["PropertyId"]))["Name"]),
                    "属性值": artifact["Equipment"]["MainPropertyList"][0]["PropertyValue"] * (1 + val / 10000),
                }
                artifact_info["词条"] = []
                for reliquary in artifact["Equipment"].get("RandomPropertyList", []):
                    artifact_info["词条"].append(
                        {
                            "属性名": locs.get(property_json.get(str(reliquary["PropertyId"]))["Name"]),
                            "属性值": reliquary["PropertyValue"] * reliquary["PropertyLevel"],
                            "提升次数": reliquary["PropertyLevel"] - 1,
                        }
                    )
                artifacts[artifact_info["部位"] - 1] = artifact_info
            role_info["驱动盘"] = artifacts

            prop = {}
            prop_json = avatars_json[str(data["Id"])]
            for i in prop_list.items():
                growth_value = (prop_json["GrowthProps"].get(i[1], 0) * (data["Level"] - 1)) / 10000
                promotion_value = prop_json["PromotionProps"][data["PromotionLevel"] - 1].get(i[1], 0)
                core_enhancement_value = prop_json["CoreEnhancementProps"][data["CoreSkillEnhancement"]].get(i[1], 0)
                prop[f"基础{i[0]}"] = prop_json["BaseProps"].get(i[1], 0) + growth_value + promotion_value + core_enhancement_value

            weapon_info = {}
            if data.get("Weapon") is not None:
                weapon_data = data["Weapon"]
                weapon_json = load_json(path=f"{json_path}/Weapons/{weapon_data['Id']}.json")
                weapon_info["名称"] = weapon_json["ItemName"]
                weapon_info["图标"] = weapon_json["ImagePath"]
                weapon_info["类型"] = weapon_json["Profession"]["Name"]
                weapon_info["等级"] = weapon_data["Level"]
                weapon_info["星级"] = weapon_json["Rarity"]
                weapon_info["突破等级"] = weapon_data["BreakLevel"]
                weapon_info["精炼等级"] = weapon_data["UpgradeLevel"]
                weapon_info["基础攻击"] = weapon_json["MainStat"]["PropertyValue"] * (
                    1 + weaponleveltemplatetb_json["MOFGFFKBLLC"][weapon_info["等级"]]["GMJIPPMIIIF"] / 10000 + weaponstartemplatetb_json["MOFGFFKBLLC"][weapon_info["突破等级"]]["IDDHKNJKBBK"] / 10000
                )
                try:
                    weapon_info["副属性"] = {
                        "属性名": locs.get(property_json.get(str(weapon_json["SecondaryStat"]["PropertyId"]))["Name"]),
                        "属性值": weapon_json["SecondaryStat"]["PropertyValue"] * (1 + weaponstartemplatetb_json["MOFGFFKBLLC"][weapon_info["突破等级"]]["POLGGADDPLI"] / 10000),
                    }
                except IndexError:
                    weapon_info["副属性"] = {"属性名": "无属性", "属性值": 0}
                prop["基础攻击力"] += weapon_info["基础攻击"]

                for i in prop_list.keys():
                    if weapon_info["副属性"]["属性名"] == i:
                        prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + weapon_info["副属性"]["属性值"]
                        break
                    elif weapon_info["副属性"]["属性名"] == f"{i}百分比":
                        prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + prop[f"基础{i}"] * weapon_info["副属性"]["属性值"] / 10000
                        break
            role_info["武器"] = weapon_info
            for item in role_info["驱动盘"]:
                if not item:
                    continue
                for i in prop_list.keys():
                    if item["主属性"]["属性名"] == i:
                        prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + item["主属性"]["属性值"]
                        break
                    elif item["主属性"]["属性名"] == f"{i}百分比":
                        prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + prop[f"基础{i}"] * item["主属性"]["属性值"] / 10000
                        break
                if "伤害加成" in item["主属性"]["属性名"]:
                    prop["额外伤害加成"] = prop.get("额外伤害加成", 0) + item["主属性"]["属性值"]
                for vice in item["词条"]:
                    for i in prop_list.keys():
                        if vice["属性名"] == i:
                            prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + vice["属性值"]
                            break
                        elif vice["属性名"] == f"{i}百分比":
                            prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + prop[f"基础{i}"] * vice["属性值"] / 10000
                            break
            suit_4, suit_2 = get_artifact_suit([item.get("所属套装", "") for item in artifacts])
            relic_suit_prop = []
            if suit_2 + suit_4:
                for suit in dict.fromkeys(suit_2 + suit_4):
                    for key, val in equipments_json["Suits"][str(suit)]["SetBonusProps"].items():
                        suit_prop = {
                            "属性名": locs.get(property_json.get(str(key))["Name"]),
                            "属性值": val,
                        }
                        relic_suit_prop.append(suit_prop)
            for vice in relic_suit_prop:
                for i in prop_list.keys():
                    if vice["属性名"] == i:
                        prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + vice["属性值"]
                        break
                    elif vice["属性名"] == f"{i}百分比":
                        prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + prop[f"基础{i}"] * vice["属性值"] / 10000
                        break
                if "伤害加成" in vice["属性名"]:
                    prop["额外伤害加成"] = prop.get("额外伤害加成", 0) + vice["属性值"]

            if role_info["特性"] == "命破":
                prop["基础贯穿力"] = 0.3 * (prop["基础攻击力"] + prop.get("额外攻击力", 0)) + 0.1 * (prop["基础生命值"] + prop.get("额外生命值", 0))
            role_info["属性"] = prop

            role_info["更新时间"] = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
            self.roles[role_info["名称"]] = role_info

    def get_player_info(self):
        return self.player_info

    def get_update_roles_list(self):
        return self.player_info["角色列表"]

    def get_roles_list(self):
        return list(self.roles.keys())

    def get_artifact_list(self, pos):
        return list(self.data["驱动盘列表"][pos])

    def get_roles_info(self, role_name):
        if role_name in self.roles:
            return self.roles[role_name]
        else:
            return None

    def save(self):
        self.data["玩家信息"] = self.player_info
        self.data["角色"] = self.roles
        self.data["驱动盘列表"] = _normalize_artifact_cache(self.data["驱动盘列表"], self.roles)
        save_json(data=self.data, path=self.path)


def get_name_by_id(role_id: str):
    """
    根据角色id获取角色名
    :param role_id: 角色id
    :return: 角色名字符串
    """
    if os.path.exists(f"{json_path}/Avatars/{role_id}.json"):
        role_info_json = load_json(path=f"{json_path}/Avatars/{role_id}.json")
        return role_info_json.get("Name"), role_info_json
    print(f"未找到角色id对应的名称，id：{role_id}")
    return None, None


def dictlist_to_list(data):
    if not isinstance(data, list):
        return "unknown"
    new_data = []
    for d in data:
        name, _ = get_name_by_id(str(d["Id"]))
        new_data.append(name)
    return new_data


def get_font(size, font="hywh.ttf"):
    return ImageFont.truetype(str(font_path + "/" + font), size)
