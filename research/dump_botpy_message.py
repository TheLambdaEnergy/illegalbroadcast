"""查看 botpy 里 GroupMessage / C2CMessage / Message 的 reply 实现细节。"""

import inspect
import os

import botpy
import botpy.message as msg

P = os.path.dirname(botpy.__file__)
src = open(os.path.join(P, "message.py"), encoding="utf-8").read()
lines = src.splitlines()

# 找到各个类的 __init__ / reply / _reply
import re  # noqa: E402

print("=" * 90)
print("message.py 里的类定义行号")
print("=" * 90)
for i, line in enumerate(lines, 1):
    if re.match(r"^class ", line):
        print(f"  {i:>4}  {line}")

print()
print("=" * 90)
print("GroupMessage / C2CMessage 的 reply 相关代码")
print("=" * 90)
for cls in ("GroupMessage", "C2CMessage", "Message"):
    idx = next((i for i, l in enumerate(lines) if l.startswith(f"class {cls}")), None)
    if idx is None:
        continue
    end = next((i for i in range(idx + 1, len(lines)) if lines[i].startswith("class ")), len(lines))
    print(f"--- {cls}  (行 {idx + 1}..{end}) ---")
    for i in range(idx, min(end, idx + 90)):
        print(f"{i + 1:>4}| {lines[i]}")
    print()

print("=" * 90)
print("msg_seq 在 botpy 里是怎么处理的")
print("=" * 90)
for i, line in enumerate(lines, 1):
    if "msg_seq" in line:
        print(f"{i:>4}| {line.rstrip()}")
