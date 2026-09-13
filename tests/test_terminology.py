"""术语一致性检查。

README 的「术语对照」表是约定；这个测试把它变成可执行的约束，
避免以后改代码时又把译名改回去（或者一个文件写「机器人」另一个写别的）。

    python tests/test_terminology.py
"""

from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixtures import build_test_snapshot  # noqa: E402
from hd2api.reference import FACTION_FALLBACK  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# README「术语对照」表里确定的唯一译名
CANONICAL = {1: "超级地球", 2: "终结族", 3: "机器人", 4: "光能者"}

# 明令禁止的旧写法。
# 注意：这里必须拆开拼，否则本文件自己就会被下面的扫描判为违规。
FORBIDDEN = ["机械" + "体", "光明" + "者", "潜" + "水员"]

# 这些目录里是站点 JS 的原始证据快照 / 依赖 / 缓存，不参与扫描
SKIP_DIRS = {".deps", ".tmp", ".venv", "__pycache__", "raw", "analysis", ".git"}
SCAN_EXT = (".py", ".md", ".txt", ".json")

# 行级豁免标记：术语表本身需要举反例说明「不要写成什么」，
# 那种地方显式标注，而不是把文档写糊。
IGNORE_MARKER = "terminology-lint:ignore"


def iter_scannable():
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.endswith(SCAN_EXT):
                path = os.path.join(root, name)
                yield os.path.relpath(path, ROOT).replace("\\", "/"), path


def read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return ""


class TestForbiddenTerms(unittest.TestCase):
    def test_no_forbidden_translations_anywhere(self):
        offenders: list[tuple[str, str]] = []
        for rel, path in iter_scannable():
            for lineno, line in enumerate(read_text(path).splitlines(), 1):
                if IGNORE_MARKER in line:
                    continue
                for term in FORBIDDEN:
                    if term in line:
                        offenders.append((f"{rel}:{lineno}", term))
        self.assertEqual(
            offenders, [],
            "发现旧译名（见 README「术语对照」）：\n" +
            "\n".join(f"  {where}: {term}" for where, term in offenders),
        )


class TestFactionNamesAgree(unittest.TestCase):
    """译名有三个来源，必须完全一致。"""

    def test_runtime_table(self):
        for race, zh in CANONICAL.items():
            self.assertEqual(FACTION_FALLBACK[race]["zh"], zh,
                             f"hd2api/reference.py 的 race={race} 译名不对")

    def test_shipped_reference_json(self):
        path = os.path.join(ROOT, "data", "reference.json")
        doc = json.loads(read_text(path))
        for race, zh in CANONICAL.items():
            entry = doc["factions"].get(str(race))
            self.assertIsNotNone(entry, f"data/reference.json 缺少 race={race}")
            self.assertEqual(entry["zh"], zh,
                             f"data/reference.json 的 race={race} 译名不对")

    def test_generator_script(self):
        """data/reference.json 是脚本生成的，脚本里的译名也必须对。"""
        from scripts.refresh_reference import FACTIONS
        for race, zh in CANONICAL.items():
            self.assertEqual(FACTIONS[race]["zh"], zh,
                             f"scripts/refresh_reference.py 的 race={race} 译名不对")


class TestOwnerAliases(unittest.TestCase):
    """中文译名要能直接用在 ?owner= 过滤上。"""

    def test_chinese_names_are_accepted(self):
        from hd2api.web import OWNER_ALIASES
        for race, zh in CANONICAL.items():
            self.assertEqual(OWNER_ALIASES.get(zh), race,
                             f"?owner={zh} 应当解析为 race={race}")

    def test_english_names_still_work(self):
        from hd2api.web import OWNER_ALIASES
        for name, race in (("humans", 1), ("terminids", 2),
                           ("automatons", 3), ("illuminate", 4),
                           ("bots", 3), ("squids", 4)):
            self.assertEqual(OWNER_ALIASES.get(name), race, f"?owner={name} 失效")


class TestFactionLabelsMap(unittest.TestCase):
    """汇总里的英文阵营键要能通过 faction_labels 映射到统一译名。"""

    def setUp(self):
        self.snap = build_test_snapshot()

    def test_labels_cover_every_key_used_in_totals(self):
        labels = self.snap["faction_labels"]
        used = set(self.snap["totals"]["owned_by_faction"])
        used |= set(self.snap["totals"]["players_by_owner_faction"])
        used |= set(self.snap["totals"]["players_by_enemy_faction"])
        for sec in self.snap["sectors"]:
            used |= set(sec.get("owned_by") or {})
        missing = used - set(labels)
        self.assertEqual(missing, set(), f"这些阵营键没有中文映射: {missing}")

    def test_labels_match_the_glossary(self):
        labels = self.snap["faction_labels"]
        for race, zh in CANONICAL.items():
            self.assertEqual(labels[FACTION_FALLBACK[race]["en"]], zh)

    def test_none_faction_is_excluded(self):
        self.assertNotIn("None", self.snap["faction_labels"])


class TestGlossaryIsDocumented(unittest.TestCase):
    def test_readme_has_glossary_with_all_terms(self):
        readme = read_text(os.path.join(ROOT, "README.md"))
        for english in ("Humans", "Helldivers", "Terminids", "Automatons", "Illuminate"):
            self.assertIn(english, readme, f"README 术语表缺少 {english}")
        for zh in CANONICAL.values():
            self.assertIn(zh, readme, f"README 术语表缺少 {zh}")
        # 「绝地潜兵」是玩家，不在 CANONICAL（那是阵营表）里，单独查
        self.assertIn("绝地潜兵", readme)


if __name__ == "__main__":
    unittest.main(verbosity=2)
