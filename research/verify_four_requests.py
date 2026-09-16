"""逐条复验用户这轮提的四点要求，直接打印真实输出。

跑之前请先启动战报 API（python run.py），否则会看到连不上的提示。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bot"))

from bot import commands  # noqa: E402
from bot import hd2_api  # noqa: E402


def rule(title: str) -> None:
    print()
    print("=" * 66)
    print(title)
    print("=" * 66)


def main() -> int:
    client = hd2_api.Hd2Client()

    rule("① 数据获取时间 = 北京时间，精确到秒")

    async def show_time() -> None:
        text = await client.planet_text("KARLIA")
        for line in text.splitlines():
            if "数据获取时间" in line:
                print("  ", line.strip())

    asyncio.run(show_time())

    rule("② 未知参数/命令的固定文案")
    print("   UNKNOWN_INPUT =", repr(commands.UNKNOWN_INPUT))
    cases = ["/d foo", "/t 5", "/xyz", "你好", "/p"]
    for case in cases:
        reply = asyncio.run(commands.execute_command(case, client))
        first = (reply or "").splitlines()[0]
        print(f"   {case!r:12} -> {first}")
    print("   注意 /p 少参数时走的是更具体的提示，不是 UNKNOWN_INPUT")

    rule("③ /help 文案（以 qqbot.md 为准）")
    print(asyncio.run(commands.execute_command("/help", client)))

    rule("④ config.example.yaml：凭据留空")
    example = (ROOT / "bot" / "config.example.yaml").read_text(encoding="utf-8")
    for line in example.splitlines():
        if line.startswith(("appid:", "secret:", "api_base:", "max_reply_chars:", "http_timeout:")):
            print("  ", line)
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    print("   .gitignore 含 bot/config.yaml:", "bot/config.yaml" in ignored)

    asyncio.run(client.close())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
