"""列出 botpy 注册的全部事件名，以及每个事件对应的 Intents 标志。"""

import os
import re

import botpy

P = os.path.dirname(botpy.__file__)

print("=" * 80)
print("flags.py 里注册的事件（行号 / 事件名）")
print("=" * 80)
src = open(os.path.join(P, "flags.py"), encoding="utf-8").read()
for i, line in enumerate(src.splitlines(), 1):
    m = re.search(r'"(on_[a-z_]+)"', line)
    if m:
        print(f"  {i:>4}  {m.group(1)}")

print()
print("=" * 80)
print("Intents 的合法标志（VALID_FLAGS）")
print("=" * 80)
from botpy import Intents  # noqa: E402

valid = getattr(Intents, "VALID_FLAGS", None)
if valid:
    for k, v in sorted(valid.items()):
        print(f"  {k:<32} {v}")

print()
print("=" * 80)
print("消息相关的 Intents 展开值（用于确认该开哪些）")
print("=" * 80)
for kwargs in (
    {"public_guild_messages": True},
    {"direct_message": True},
    {"public_messages": True},
    {"public_guild_messages": True, "direct_message": True, "public_messages": True},
):
    try:
        i = Intents(**kwargs)
        print(f"  {kwargs} -> value={i.value}")
    except Exception as exc:  # noqa: BLE001
        print(f"  {kwargs} -> 失败: {exc}")
