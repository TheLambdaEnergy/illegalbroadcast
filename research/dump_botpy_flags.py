"""打印 botpy flags.py 里事件名注册的那一段。"""

import os

import botpy

path = os.path.join(os.path.dirname(botpy.__file__), "flags.py")
lines = open(path, encoding="utf-8").read().splitlines()
print(f"{path}  共 {len(lines)} 行")
print("=" * 90)
for i in range(195, min(360, len(lines))):
    print(f"{i + 1:>4}| {lines[i]}")
