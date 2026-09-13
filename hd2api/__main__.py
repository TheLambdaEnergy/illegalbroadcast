"""命令行入口：python -m hd2api <命令>"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, config
from .normalize import planet_summary
from .service import WarService
from .web import serve


def _service(no_poller: bool = True) -> WarService:
    svc = WarService(enable_poller=not no_poller)
    svc.refresh(force=True)
    return svc


def _emit(obj, args: argparse.Namespace) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2 if args.pretty else None,
                      separators=None if args.pretty else (",", ":"))
    if getattr(args, "out", None):
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"已写入 {args.out}（{len(text):,} 字符）")
    else:
        print(text)


def cmd_serve(args: argparse.Namespace) -> int:
    serve(host=args.host, port=args.port, quiet=not args.verbose)
    return 0


def cmd_war(args: argparse.Namespace) -> int:
    svc = _service()
    s = svc.snapshot()
    _emit({
        "generated_at": s["generated_at"],
        "war": s["war"],
        "totals": s["totals"],
        "impact_calibration": s["impact_calibration"],
        "galaxy_statistics": s["galaxy_statistics"],
    }, args)
    return 0


def cmd_planets(args: argparse.Namespace) -> int:
    svc = _service()
    s = svc.snapshot()
    rows = s["planets"]
    if args.active:
        rows = [p for p in rows if p["players"] > 0 or p.get("event")]
    if args.defending:
        rows = [p for p in rows if p.get("event")]
    if args.sector:
        rows = [p for p in rows if p["sector"].lower() == args.sector.lower()]
    rows = sorted(rows, key=lambda p: -p["players"])[: args.limit]
    _emit({
        "generated_at": s["generated_at"],
        "count": len(rows),
        "planets": [planet_summary(p, args.full) for p in rows],
    }, args)
    return 0


def cmd_planet(args: argparse.Namespace) -> int:
    from .web import find_planet
    svc = _service()
    s = svc.snapshot()
    _emit(find_planet(s, args.key), args)
    return 0


def cmd_defenses(args: argparse.Namespace) -> int:
    svc = _service()
    s = svc.snapshot()
    _emit({"generated_at": s["generated_at"], "defenses": s["defenses"]}, args)
    return 0


def cmd_dump(args: argparse.Namespace) -> int:
    svc = _service()
    s = svc.snapshot()
    if args.compact:
        s = dict(s)
        s["planets"] = [planet_summary(p, False) for p in s["planets"]]
    text = json.dumps(s, ensure_ascii=False, indent=1 if args.pretty else None,
                      separators=None if args.pretty else (",", ":"))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"已写入 {args.out}（{len(text):,} 字符）")
    else:
        print(text)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """自检：加载参照表、抓一次上游、跑一遍归一化，并核对覆盖率。"""
    from .reference import get_reference

    try:
        ref = get_reference()
    except Exception as exc:  # noqa: BLE001
        print(f"[!!] 参照表加载失败: {exc}")
        return 1
    print(f"[ok] 参照表: {ref.planet_count} 星球 / {ref.sector_count} 星区 "
          f"(生成于 {ref.generated_at})")

    svc = WarService(enable_poller=False)
    try:
        svc.refresh(force=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[!!] 上游抓取失败: {exc}")
        return 1

    s = svc.snapshot()
    totals = s["totals"]
    print(f"[ok] 快照生成于 {s['generated_at']}")
    print(f"     星球 {totals['planets_total']} / 在线绝地潜兵 {totals['players_online']:,} "
          f"/ 有人的星球 {totals['planets_with_divers']}")
    print(f"     解放战役 {totals['active_campaigns']} / 防御战 {totals['active_defenses']} "
          f"/ 进行中重大指令 {totals['active_major_orders']}")
    cal = s["impact_calibration"]
    print(f"     每绝地潜兵影响力 {cal['hp_per_diver_per_hour']} HP/h "
          f"({cal['source']}, {cal['samples_used']} 样本)")

    problems: list[str] = []
    unresolved = [p["index"] for p in s["planets"] if p["name"].startswith("PLANET-")]
    if unresolved:
        problems.append(f"{len(unresolved)} 颗星球没有可读名称: {unresolved[:10]}")
    no_sector = [p["index"] for p in s["planets"] if p["sector"] == "Unknown"]
    if no_sector:
        problems.append(f"{len(no_sector)} 颗星球没有星区: {no_sector[:10]}")
    no_biome = [p["index"] for p in s["planets"] if not (p.get("biome") or {}).get("en")]
    if no_biome:
        problems.append(f"{len(no_biome)} 颗星球缺少生物群系: {no_biome[:10]}")

    sample = max(s["planets"], key=lambda p: p["players"])
    print(f"[ok] 人口最多: {sample['name']} ({sample['sector']}) {sample['players']:,} 人 "
          f"· {sample['owner']['zh']} · 解放度 {sample['liberation_percent']}% "
          f"· 净增速 {sample['liberation_rate']['net_percent_per_hour']}%/h")

    with_rate = [p for p in s["planets"] if (p.get("liberation_rate") or {}).get("measured")]
    print(f"[ok] 有实测速率的星球: {len(with_rate)}")
    for d in s["defenses"]:
        print(f"[ok] 防御战: {d['planet_name']} 等级 {d['invasion_level']['current']}/"
              f"{d['invasion_level']['max']} 进度 {d['defense_progress_percent']}% "
              f"所需增援 {d.get('required_divers')} 当前 {d.get('players')} "
              f"预测 {d.get('predicted_outcome_text')} 剩余 {d['time_remaining_text']}")

    if problems:
        for item in problems:
            print(f"[!!] {item}")
        return 1
    print("[ok] 自检通过：全部星球都有名称、星区与生物群系")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="hd2api",
        description="《Helldivers 2》实时战报 API 与命令行工具（数据源 helldiverscompanion.com）",
    )
    ap.add_argument("--version", action="version", version=f"helldiversbot {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("serve", help="启动 HTTP API 服务")
    p.add_argument("--host", default=config.HOST)
    p.add_argument("--port", type=int, default=config.PORT)
    p.add_argument("-v", "--verbose", action="store_true", help="打印每个请求的访问日志")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("war", help="打印战争概览")
    p.add_argument("--pretty", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_war)

    p = sub.add_parser("planets", help="打印星球列表")
    p.add_argument("--active", action="store_true", help="只看有人/有战役的")
    p.add_argument("--defending", action="store_true", help="只看防御战中的")
    p.add_argument("--sector")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--full", action="store_true", help="输出完整字段而非摘要")
    p.add_argument("--pretty", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_planets)

    p = sub.add_parser("planet", help="打印单颗星球")
    p.add_argument("key", help="index / 名称 / slug")
    p.add_argument("--pretty", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_planet)

    p = sub.add_parser("defenses", help="打印防御战/入侵")
    p.add_argument("--pretty", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_defenses)

    p = sub.add_parser("dump", help="导出完整快照 JSON")
    p.add_argument("--out", help="输出文件；省略则打到 stdout")
    p.add_argument("--compact", action="store_true", help="星球字段精简")
    p.add_argument("--pretty", action="store_true")
    p.set_defaults(func=cmd_dump)

    p = sub.add_parser("check", help="自检：参照表 + 上游 + 归一化")
    p.set_defaults(func=cmd_check)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
