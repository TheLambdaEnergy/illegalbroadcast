"""侦察已安装的 botpy：版本、事件处理器、Intents 标志、回复 API 签名。"""

import inspect
import os

import botpy

print("botpy 版本:", getattr(botpy, "__version__", "?"))
print("位置:", os.path.dirname(botpy.__file__))
print()

# ---------------------------------------------------------------- Intents
from botpy import Intents  # noqa: E402

print("=== Intents 支持的标志 ===")
try:
    sig = inspect.signature(Intents.__init__)
    for name in sig.parameters:
        if name != "self":
            print("   ", name)
except Exception as exc:  # noqa: BLE001
    print("  签名读取失败:", exc)
print()

# ---------------------------------------------------------------- 事件处理器
print("=== Client 上可用的事件处理器（on_*） ===")
from botpy.client import Client  # noqa: E402

handlers = sorted(n for n in dir(Client) if n.startswith("on_"))
for h in handlers:
    print("   ", h)
print()

# ---------------------------------------------------------------- 消息类型
print("=== botpy.message 里的消息类 ===")
import botpy.message as msg  # noqa: E402

for name in sorted(dir(msg)):
    obj = getattr(msg, name)
    if inspect.isclass(obj) and not name.startswith("_"):
        print(f"    {name}")
print()

# ---------------------------------------------------------------- reply 签名
print("=== 各消息类的 reply / _reply 签名 ===")
for cls_name in ("Message", "DirectMessage", "GroupMessage", "C2CMessage"):
    cls = getattr(msg, cls_name, None)
    if cls is None:
        print(f"    {cls_name}: 不存在")
        continue
    print(f"  --- {cls_name} ---")
    for meth in ("reply", "_reply", "reply_text"):
        fn = getattr(cls, meth, None)
        if fn is None:
            continue
        try:
            print(f"      {meth}{inspect.signature(fn)}")
        except Exception:  # noqa: BLE001
            print(f"      {meth}: 无法读取签名")
print()

# ---------------------------------------------------------------- api 方法
print("=== Client.api 上与消息回复相关的方法 ===")
from botpy.api import BotAPI  # noqa: E402

for name in sorted(dir(BotAPI)):
    if name.startswith("_"):
        continue
    if any(k in name for k in ("message", "dms", "post_", "group", "c2c")):
        try:
            print(f"    {name}{inspect.signature(getattr(BotAPI, name))}")
        except Exception:  # noqa: BLE001
            print(f"    {name}")
