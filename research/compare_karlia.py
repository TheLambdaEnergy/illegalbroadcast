"""拿用户从官网读到的数字，与本 API 逐项对照。

用法：把官网读到的值填进 SITE 里再跑。

    python research/compare_karlia.py
"""

import json
import urllib.request

BASE = "http://127.0.0.1:8808"

# 用户在官网上读到的值（Helldivers Companion 星球卡片）
SITE = {
    "name": "KARLIA",
    "liberated_percent": 84.3270,
    "impact_percent_per_hour": 0.113,   # "Helldivers planetary control impact per hour"
    "divers_deployed": 2232,
}


def get(path, timeout=120):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read())


p = get("/api/v1/planets/" + SITE["name"])["planet"]
lr = p["liberation_rate"]
m = lr.get("measured") or {}

print("=" * 84)
print(f"{p['name']}  (index {p['index']}, {p['sector']})")
print("=" * 84)
print(f"{'指标':<34}{'官网':>14}{'本 API':>16}{'差值':>14}")
print("-" * 84)


def row(label, site, mine, unit="", nd=4):
    if mine is None:
        print(f"{label:<34}{site:>14}{'（无）':>16}{'':>14}")
        return
    print(f"{label:<34}{site:>14.{nd}f}{mine:>16.{nd}f}{mine - site:>+14.{nd}f}{unit}")


row("解放度 %", SITE["liberated_percent"], p["liberation_percent"], " %")
row("绝地潜兵影响力 %/h（官网口径）", SITE["impact_percent_per_hour"],
    lr.get("impact_percent_per_hour"), " %/h")
row("净增速 %/h（官网不显示）", float("nan"),
    lr["net_percent_per_hour"], " %/h")
row("平滑绝地潜兵影响力 %/h（1h）", float("nan"),
    (lr.get("smoothed") or {}).get("impact_percent_per_hour"), " %/h")
row("平滑净增速 %/h（1h）", float("nan"),
    (lr.get("smoothed") or {}).get("net_percent_per_hour"), " %/h")
row("在线绝地潜兵", SITE["divers_deployed"], p["players"], " 人", nd=0)
row("抵抗度 %/h", float("nan"), p["resistance"]["percent_per_hour"], " %/h")

print()
print("计数类字段官网不显示，仅列出本 API 的值：")
for k in ("health", "max_health", "player_share_percent"):
    print(f"  {k:<24}{p[k]}")
print(f"  {'regen_per_second':<24}{p['resistance']['regen_per_second']}")
print()
print(f"速率来源: {lr['source']}")
print(f"实测窗口: {m.get('from')}  ->  {m.get('to')}  ({m.get('window_seconds')}s)")
print(f"          窗口内平均在线 {m.get('players_avg')} 人；"
      f"绝地潜兵贡献可否观测 = {m.get('diver_rate_observable')}")
print()
print("三种速率口径：")
print(f"  liberation_rate.impact_percent_per_hour = {lr.get('impact_percent_per_hour')}"
      "   <- 官网的「planetary control impact per hour」")
print(f"  liberation_rate.net_percent_per_hour    = {lr['net_percent_per_hour']}"
      "   <- 扣掉抵抗度后的净变化（可能为负）")
print(f"  resistance.percent_per_hour             = {p['resistance']['percent_per_hour']}")
print(f"  恒等式: {lr.get('impact_percent_per_hour')} - "
      f"{p['resistance']['percent_per_hour']} = {lr['net_percent_per_hour']}")
if lr.get("smoothed"):
    sm = lr["smoothed"]
    print()
    print(f"1 小时平滑（{sm['windows']} 个窗口 / {sm['window_seconds']}s，"
          f"平均在线 {sm['players_avg']}）：")
    print(f"  impact = {sm['impact_percent_per_hour']} %/h   net = {sm['net_percent_per_hour']} %/h")
    print("  （单窗口噪声可差 10% 以上，跟官网对数字时应优先看平滑值）")
