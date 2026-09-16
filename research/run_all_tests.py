"""跑全量测试并打印统计（含按模块拆分）。

pwsh 里 `python ... | Select-Object` 和 `> file` 都会被沙箱拦（原生命令的管道/重定向
不可用），所以统一从这个脚本里跑，靠标准输出本身收集结果。

用法：
    python research/run_all_tests.py              # 全量，附按模块统计表
    python research/run_all_tests.py test_qqbot   # 只跑指定模块
"""

from __future__ import annotations

import importlib
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))


def module_names() -> list[str]:
    return sorted(p.stem for p in TESTS.glob("test_*.py"))


def suite_for(name: str) -> unittest.TestSuite:
    return unittest.TestLoader().loadTestsFromModule(importlib.import_module(name))


def main(argv: list[str]) -> int:
    names = argv[1:] or module_names()

    rows: list[tuple[str, int]] = []
    suite = unittest.TestSuite()
    for name in names:
        one = suite_for(name)
        suite.addTests(one)
        rows.append((name, one.countTestCases()))

    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=1, stream=sys.stderr).run(suite)
    elapsed = time.monotonic() - started

    # 按「测试 id 所属模块」重新归集失败/错误/跳过
    def owner(test_id: str) -> str:
        return test_id.split(".")[0]

    tally: dict[str, list[int]] = {name: [count, 0, 0, 0] for name, count in rows}
    for bucket, index in ((result.failures, 1), (result.errors, 2), (result.skipped, 3)):
        for test, _ in bucket:
            key = owner(test.id())
            if key in tally:
                tally[key][index] += 1

    width = max(len(name) for name in tally) if tally else 10
    print()
    print("=" * 62)
    print(f"{'模块'.ljust(width)}  用例  失败  错误  跳过")
    for name, counts in tally.items():
        print(f"{name.ljust(width)}  {counts[0]:>4}  {counts[1]:>4}  {counts[2]:>4}  {counts[3]:>4}")
    total = [sum(c[0] for c in tally.values()),
             len(result.failures), len(result.errors), len(result.skipped)]
    print("-" * 62)
    print(f"{'合计'.ljust(width)}  {total[0]:>4}  {total[1]:>4}  {total[2]:>4}  {total[3]:>4}")
    print(f"耗时 {elapsed:.3f}s  结果 {'OK' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 62)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
