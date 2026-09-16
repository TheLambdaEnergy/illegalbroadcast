"""命令解析与回复生成。

刻意**不依赖 botpy**：这样命令逻辑可以脱离 QQ 平台单独测试，
也方便以后换别的接入方式。

命令表来自 `qqbot.md`：

| 命令 | 参数 | 说明 |
|---|---|---|
| `/p` `/planet` | 星球名或 index | 单颗星球战报 |
| `/d` `/dispatch` | 无 | 最新一条游戏内快讯 |
| `/t` `/trending` | 无 | 在线绝地潜兵最多的星球 |
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from hd2_api import Hd2ApiError, Hd2Client

# --------------------------------------------------------------------------- 常量
COMMAND_ALIASES: dict[str, str] = {
    "p": "planet", "planet": "planet",
    "d": "dispatch", "dispatch": "dispatch",
    "t": "trending", "trending": "trending",
    "h": "help", "help": "help",
}

USAGE = """\
/p 或 /planet <星球名/星球索引> : 获取星球数据
/d 或 /dispatch : 获取当前的战役新闻
/t 或 /trending : 获取当前热门星球
/help : 显示此帮助信息

示例：
/p CYBERSTAN 显示生化斯坦的详细信息
/planet 0 显示超级地球的详细信息"""

#: 解析不出命令或参数时统一回这句（规格来自 qqbot.md）
UNKNOWN_INPUT = "未知的参数或命令。请使用/help查看相关帮助"

#: `/p` 缺参数时给更具体的提示——这是「少给」而不是「给错」
MISSING_PLANET_ARG = "请给出星球名或编号，例如 `/p BEKVAM III`、`/p 262`。"

#: 这几个命令不接受参数。`/help` 不在此列——`/help anything` 照常显示帮助更友好。
NO_ARG_COMMANDS = frozenset({"dispatch", "trending"})

# 频道/群里 @机器人 时，正文前面会带上 <@!1234> 这样的 mention 标记
_MENTION_RE = re.compile(r"^\s*(?:<@!?\w+>\s*)+")
# 命令名只允许字母，避免把 "/p 你好" 里的中文误当成命令
_COMMAND_RE = re.compile(r"^/([A-Za-z]+)\s*(.*)$", re.S)

DEFAULT_TRENDING_LIMIT = 5


@dataclass(frozen=True)
class Command:
    name: str          # planet / dispatch / trending / help
    arg: str           # 原始参数（仅 planet 用）
    raw: str           # 去掉 @前缀 后的原文，便于排查


def strip_mention(content: str) -> str:
    """去掉正文前面的 @机器人 标记。

    频道消息形如 `<@!123456> /p KARLIA`，群消息形如 `<@123456> /p KARLIA`；
    有的客户端只留下空格分隔的纯文本，所以再去一次首尾空白。
    """
    if not content:
        return ""
    return _MENTION_RE.sub("", content).strip()


def parse_command(content: str) -> Command | None:
    """把一条消息解析成命令。不是命令就返回 None。"""
    text = strip_mention(content or "")
    if not text.startswith("/"):
        return None
    m = _COMMAND_RE.match(text)
    if not m:
        return None
    name = COMMAND_ALIASES.get(m.group(1).lower())
    if name is None:
        # 形如 `/xyz`，当作未知命令，交给 help 处理
        return Command(name="unknown", arg=m.group(2).strip(), raw=text)
    return Command(name=name, arg=m.group(2).strip(), raw=text)


# --------------------------------------------------------------------------- 格式化
def _num(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def format_trending(planets: list[dict[str, Any]], totals: dict[str, Any] | None = None,
                    limit: int = DEFAULT_TRENDING_LIMIT) -> str:
    """`/t` 的回复。

    防御战显示「防御 X%」，解放战显示「解放 X%」——两者用的是不同字段，
    直接显示 `liberation_percent` 会让防御中的己方星球永远是 100%。
    """
    if not planets:
        return "暂时拿不到星球数据。"

    total_online = (totals or {}).get("players_online")
    head = f"🔥 在线绝地潜兵最多的 {min(limit, len(planets))} 颗星球"
    if total_online:
        head += f"（全银河 {total_online:,} 人）"

    lines = [head, ""]
    for i, p in enumerate(planets[:limit], 1):
        faction = p.get("enemy_faction_zh") or p.get("owner_zh") or "?"
        if p.get("is_defending"):
            progress = f"防御 {_num(p.get('defense_progress_percent'))}%"
        else:
            progress = f"解放 {_num(p.get('liberation_percent'))}%"
        lines.append(
            f"{i}. {p.get('name')}｜{faction}｜{progress}｜{_num(p.get('players'))}人"
        )
    return "\n".join(lines)


def truncate(text: str, limit: int) -> str:
    """按字符数截断，并明确标出来（避免用户以为数据就这么多）。"""
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: max(0, limit - 12)].rstrip() + "\n…（已截断）"


# --------------------------------------------------------------------------- 执行
async def execute_command(
    content: str,
    client: Hd2Client,
    *,
    max_reply_chars: int = 900,
    trending_limit: int = DEFAULT_TRENDING_LIMIT,
) -> str:
    """把一条消息变成一句回复文本。任何异常都会变成可读的中文提示。

    解析不出命令、或给不接受参数的命令塞了参数，都回 `UNKNOWN_INPUT`；
    `/p` 少给参数则给更具体的提示。
    """
    cmd = parse_command(content)
    if cmd is None:
        return UNKNOWN_INPUT
    if cmd.name in ("help", "unknown"):
        # 未知命令回错误提示；/help 本身回帮助
        return USAGE if cmd.name == "help" else UNKNOWN_INPUT
    if cmd.name in NO_ARG_COMMANDS and cmd.arg:
        # /d /t /help 不接受参数，给了就是未知参数
        return UNKNOWN_INPUT

    try:
        if cmd.name == "planet":
            if not cmd.arg:
                return MISSING_PLANET_ARG
            return truncate(await client.planet_text(cmd.arg), max_reply_chars)

        if cmd.name == "dispatch":
            return truncate(await client.dispatch_text(), max_reply_chars)

        if cmd.name == "trending":
            data = await client.trending(trending_limit)
            return truncate(
                format_trending(data["planets"], data["totals"], trending_limit),
                max_reply_chars,
            )
    except Hd2ApiError as exc:
        return exc.message

    return UNKNOWN_INPUT
