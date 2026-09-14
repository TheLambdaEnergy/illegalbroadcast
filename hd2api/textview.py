"""`?mode=pt` / `?mode=md` 的可读文本渲染。

规格来自项目根目录的 `README_fancy.md`。目前**只覆盖该文档明确给出的两个端点**：

* `GET /api/v1/planets/{key}`（文档写作单数 `/api/v1/planet/{key}`，两个都注册了）
* `GET /api/v1/dispatches`

星球有两种版式，按 `planet.is_under_attack` 自动切换：

* **解放战役**（默认）7 行：星球名 / 分区 / 所属阵营 / 解放进度 / 解放预计剩余时间 /
  部署的绝地潜兵数 / 数据获取时间
* **防御战役**（敌人入侵）8 行：星球名 / 分区 / 所属阵营 / 已防御 / 预测 / 剩余时间 /
  部署的绝地潜兵数 / 数据获取时间

参数取值：

| `?mode=` | 行为 |
|---|---|
| 省略 / 其它值 | 返回 JSON（**默认不变**，保持向后兼容） |
| `pt` | 返回纯文本 |
| `md` | 同 `pt`（两个名字等价） |
| `raw` | 返回 JSON（显式声明） |

关于文档里那些 `// planet.name` 这样的行尾注释：它们是**文档作者标注的字段来源**，
不是输出内容（证据：`数据获取时间` 那行标的是 `generated_at`，但示例值其实是
`measured.to`，说明注释是凭记忆手写的）。因此这里不输出它们。

有一处注释与示例值冲突且**以示例值为准**：防御战版式里的 `所属阵营`，注释写
`planet.owner.zh`，但示例星球 K 的 owner 是超级地球，文档写的却是「机器人」——
那是入侵方，等于 `event.faction.zh`。两种版式都按「这颗星球当下与谁有关」取阵营。
"""

from __future__ import annotations

from typing import Any

# 文档里的注释只是标注来源，不是输出的一部分
TEXT_MODES = frozenset({"pt", "md"})
JSON_MODES = frozenset({"raw", "json"})
_NULL = "—"

# `预测` 只允许这三个值（见 README_fancy.md 的 `// 失败/成功/不确定`）
OUTCOME_LABELS: dict[str, str] = {
    "defense_will_hold": "成功",
    "defense_will_fail": "失败",
}
OUTCOME_UNCERTAIN = "不确定"


def wants_text(req: Any) -> bool:
    """请求是否要求可读文本。`pt` 与 `md` 等价，其余（含缺省）都走 JSON。"""
    mode = (req.get("mode") or "").strip().lower()
    return mode in TEXT_MODES


def _num(value: Any) -> str:
    """把数值渲染成人读的样子：100.0 -> 100，85.448 -> 85.448。"""
    if value is None:
        return _NULL
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    return str(value)


def _text(value: Any) -> str:
    if value is None:
        return _NULL
    text = str(value).strip()
    return text or _NULL


def data_timestamp(planet: dict[str, Any], generated_at: str | None) -> str:
    """`数据获取时间` 用哪个时间戳。

    文档的注释写的是 `generated_at`，但示例值 `2026-09-14T01:31:44.2973993Z`
    恰好等于同一份 JSON 里 `liberation_rate.measured.to`，而 `generated_at`
    是 `01:56:34.677Z`。这里**跟示例值走**：优先用实测窗口的结束时刻
    （那才是「数据是什么时候的」），没有实测时退回 `generated_at`。
    """
    measured = (planet.get("liberation_rate") or {}).get("measured") or {}
    return _text(measured.get("to") or generated_at)


def outcome_label(event: dict[str, Any]) -> str:
    """防御战预测结论：成功 / 失败 / 不确定。

    文档只允许这三个值。本 API 的 `predicted_outcome` 有四种取值
    （hold / fail / too_close_to_call / unknown）+ 可能为 null，
    除「确定守住」「确定失守」外一律归为「不确定」。
    """
    return OUTCOME_LABELS.get(event.get("predicted_outcome") or "", OUTCOME_UNCERTAIN)


def is_defense(planet: dict[str, Any]) -> bool:
    """是否走防御战格式。

    文档给的条件是 `planet.is_under_attack == true`；这里再要求 `event` 确实存在，
    因为渲染要用它的字段（两者同源于 planetEvents，实际总是一起出现）。
    """
    return bool(planet.get("is_under_attack")) and bool(planet.get("event"))


def _common_head(planet: dict[str, Any]) -> list[str]:
    return [
        f"星球名：{_text(planet.get('name'))}",
        # 文档示例是 OMEGA / TRIGON，而 JSON 里是 "Omega" / "Trigon" -> 转大写
        f"分区：{_text((planet.get('sector') or '').upper())}",
    ]


def _common_tail(planet: dict[str, Any], generated_at: str | None) -> list[str]:
    return [
        f"部署的绝地潜兵数：{_num(planet.get('players'))}",
        f"数据获取时间：{data_timestamp(planet, generated_at)}",
    ]


def _render_liberation(planet: dict[str, Any], generated_at: str | None) -> str:
    lines = _common_head(planet)
    lines.append(f"所属阵营：{_text((planet.get('owner') or {}).get('zh'))}")
    lines += [
        f"解放进度：{_num(planet.get('liberation_percent'))}%",
        f"解放预计剩余时间：{_text(planet.get('eta_liberation_text'))}",
    ]
    lines += _common_tail(planet, generated_at)
    return "\n".join(lines) + "\n"


def _render_defense(planet: dict[str, Any], generated_at: str | None) -> str:
    event = planet["event"]
    lines = _common_head(planet)
    # 防御战里显示的是**入侵方**。文档示例 K 的 owner 是超级地球，
    # 但它写的是「机器人」，与 event.faction.zh 一致。
    lines.append(f"所属阵营：{_text((event.get('faction') or {}).get('zh'))}")
    lines += [
        f"已防御：{_num(event.get('defense_progress_percent'))}%",
        f"预测：{outcome_label(event)}",
        f"剩余时间：{_text(event.get('time_remaining_text'))}",
    ]
    lines += _common_tail(planet, generated_at)
    return "\n".join(lines) + "\n"


def render_planet(planet: dict[str, Any], generated_at: str | None = None) -> str:
    """单颗星球的可读文本。

    防御战役（敌人入侵）与普通解放战役的字段不同，见 README_fancy.md。
    """
    if is_defense(planet):
        return _render_defense(planet, generated_at)
    return _render_liberation(planet, generated_at)


def latest_dispatch(dispatches: list[dict[str, Any]]) -> dict[str, Any] | None:
    """取最新一条。

    文档说「通常是最大 id」；实测本站 `id` 与 `published_at` 完全同序
    （最大 id 3920 也正是最新一条），所以直接按 id 取，与文档措辞一致。
    """
    if not dispatches:
        return None
    return max(dispatches, key=lambda d: d.get("id") or -1)


def render_dispatch(dispatches: list[dict[str, Any]]) -> str:
    """最新一条游戏内快讯的可读文本。"""
    item = latest_dispatch(dispatches)
    if item is None:
        return f"时间：{_NULL}\n信息：（暂无快讯）\n"
    # message 里的换行是真实换行（JSON 里是转义的 \n），原样输出更易读
    return f"时间：{_text(item.get('published_at'))}\n信息：{_text(item.get('message'))}\n"
