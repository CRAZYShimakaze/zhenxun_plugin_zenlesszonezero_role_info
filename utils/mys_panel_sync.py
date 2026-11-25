"""米游社面板同步的账号选择、缓存合并和原子写入。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
from typing import Any, NamedTuple

from loguru import logger


class PanelSyncResult(NamedTuple):
    status: str
    uid: str | None = None
    role_count: int = 0
    error: str = ""
    role_names: tuple[str, ...] = ()
    skipped_count: int = 0


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("本地面板缓存格式错误，已保留原文件")
    return data


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4, allow_nan=False)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def select_role(user: dict, game: str, existing_uid: str | None = None) -> dict:
    roles = user.get("game_roles", {}).get(game, [])
    roles = [r for r in roles if isinstance(r, dict)] if isinstance(roles, list) else []
    if not roles:
        raise ValueError("当前米游社账号没有该游戏角色，请重新扫码登录刷新账号信息")
    if existing_uid:
        matched = [r for r in roles if str(r.get("game_uid", "")) == existing_uid]
        if len(matched) != 1:
            raise ValueError("已绑定 UID 不属于当前米游社账号，请先解绑并绑定正确 UID")
        role = matched[0]
    elif len(roles) == 1:
        role = roles[0]
    else:
        chosen = [r for r in roles if r.get("is_chosen") is True]
        if len(chosen) != 1:
            raise ValueError("检测到多个 UID，请先绑定要更新的游戏 UID")
        role = chosen[0]
    uid = str(role.get("game_uid", ""))
    if not uid.isdigit() or not role.get("region"):
        raise ValueError("米游社游戏 UID 或区服信息不完整，请重新扫码登录")
    return role


def get_binding(directory: Path, qq_id: int) -> str | None:
    value = read_json(directory / "qq2uid.json").get(str(qq_id))
    return str(value) if value is not None and str(value).isdigit() else None


def save_cache(
    directory: Path,
    uid: str,
    account: dict,
    details: dict,
    converter: Callable[[dict], dict],
    equipment: str,
) -> tuple[str, ...]:
    avatars = details.get("avatar_list")
    if not isinstance(avatars, list) or not avatars:
        raise ValueError("米游社未返回可用角色详情，已保留旧缓存")
    converted = {}
    for avatar in avatars:
        # 所有转换完成后才落盘，字段错误不能覆盖旧缓存。
        try:
            role = converter(avatar)
        except ValueError as error:
            role_id = (
                avatar.get("id", "unknown") if isinstance(avatar, dict) else "unknown"
            )
            role_name = (
                avatar.get("name", "unknown") if isinstance(avatar, dict) else "unknown"
            )
            role_id = " ".join(str(role_id).split())[:32]
            role_name = " ".join(str(role_name).split())[:80]
            error_text = " ".join(str(error).split())[:240]
            game_name = {"遗器": "星铁", "驱动盘": "绝区零"}.get(equipment, "未知")
            logger.error(
                f"米游社{game_name}角色详情转换失败: role_id={role_id}, "
                f"role_name={role_name}, error_type={type(error).__name__}, "
                f"error={error_text}"
            )
            raise
        if role is None:  # 本地资源尚未支持的新角色保留其旧记录。
            continue
        converted[role["名称"]] = role
    if not converted:
        raise ValueError("返回的角色暂不受本地资源支持，已保留旧缓存")
    path = directory / f"{uid}.json"
    data = copy.deepcopy(read_json(path))
    roles = data.setdefault("角色", {})
    roles.update(converted)
    player = data.setdefault("玩家信息", {})
    player.update(
        {
            "昵称": account.get("nickname") or player.get("昵称", "unknown"),
            "等级": account.get("level") or player.get("等级", "unknown"),
            "角色列表": list(converted),
            "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    data.setdefault(f"{equipment}列表", [[], [], [], [], [], []])
    data[f"{equipment}榜单"] = []
    data[f"大毕业{equipment}"] = 0
    data[f"小毕业{equipment}"] = 0
    atomic_write(path, data)
    return tuple(converted)


async def sync_panel(
    qq_id: int,
    user: dict,
    api: Any,
    directory: Path,
    game: str,
    save: Callable[[str, dict, dict], tuple[str, ...]],
    captcha_notifier: Callable[[str], Awaitable[None]] | None = None,
) -> PanelSyncResult:
    original_binding = get_binding(directory, qq_id)
    role = select_role(user, game, original_binding)
    uid = str(role["game_uid"])
    method = (
        api.get_starrail_character_details
        if game == "starrail"
        else api.get_zzz_character_details
    )
    try:
        details = await method(
            user, uid=uid, region=role["region"], captcha_notifier=captcha_notifier
        )
        if get_binding(directory, qq_id) != original_binding:
            return PanelSyncResult(
                "failed", uid, error="更新期间 UID 绑定发生变化，请重新发送更新命令"
            )
        bindings = read_json(directory / "qq2uid.json")
        names = save(uid, role, details)
        # 成功取得并保存数据后再绑定；中间没有 await，避免并发覆盖绑定表。
        bindings[str(qq_id)] = int(uid)
        atomic_write(directory / "qq2uid.json", bindings)
        return PanelSyncResult(
            "synced",
            uid,
            len(names),
            role_names=names,
            skipped_count=max(0, len(details["avatar_list"]) - len(names)),
        )
    except RuntimeError as error:
        # 只允许本插件接口的固定中文提示进入回复，拒绝底层异常和 URL。
        message = str(error)
        if (
            not message.startswith(
                ("米游社", "请先在米游社", "等待玩家", "完成人机验证")
            )
            or "http" in message.lower()
        ):
            message = "米游社角色更新失败，请稍后重试"
        return PanelSyncResult("failed", uid, error=message)
    except ValueError as error:
        message = str(error)
        if not message.startswith(("米游社", "返回的角色", "本地面板")):
            message = "角色详情转换失败，已保留旧缓存"
        return PanelSyncResult("failed", uid, error=message)
    except Exception:
        return PanelSyncResult("failed", uid, error="角色详情处理失败，请稍后重试")
