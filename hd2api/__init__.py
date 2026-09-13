"""hd2api —— 《Helldivers 2》实时战报 API。

数据源: helldiverscompanion.com（实时载荷 + CDN 历史）
参照表: 由 scripts/refresh_reference.py 固化的静态 ID->名称映射

仅依赖 Python 标准库。
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
