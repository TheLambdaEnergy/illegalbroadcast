"""根目录下的 index 对照表是否与 data/reference.json 保持同步。

这两个文件是生成的，容易在改了参照表之后忘记重新生成。
这里直接按生成器的逻辑重算一遍，与磁盘上的内容比对。

    python tests/test_index_map.py
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.build_index_map import (  # noqa: E402
    CSV_HEADER,
    CSV_PATH,
    MD_PATH,
    REF_PATH,
    TRANS_PATH,
    build_markdown,
    csv_rows,
    load_translations,
)

HINT = "请运行: python scripts/build_index_map.py"


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class TestGeneratedFilesExist(unittest.TestCase):
    def test_files_present_at_project_root(self):
        for path in (MD_PATH, CSV_PATH):
            self.assertTrue(os.path.exists(path),
                            f"缺少 {os.path.basename(path)}；{HINT}")

    def test_reference_present(self):
        self.assertTrue(os.path.exists(REF_PATH))


def norm_row(row: list) -> list[str]:
    """CSV 读写会把所有值变成字符串，比较前先统一（None 写出来是空串）。"""
    return ["" if v is None else str(v) for v in row]


class TestIndexMapInSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(read_text(REF_PATH))
        cls.trans = load_translations()
        cls.planets = cls.doc["planets"]

    def test_markdown_matches_regenerated_content(self):
        disk = read_text(MD_PATH)
        expected = build_markdown(self.doc, self.trans)
        if disk != expected:
            disk_lines = disk.splitlines()
            exp_lines = expected.splitlines()
            diff_at = next(
                (i for i, (a, b) in enumerate(zip(disk_lines, exp_lines)) if a != b),
                min(len(disk_lines), len(exp_lines)),
            )
            self.fail(
                f"INDEX_MAP.md 与 data/reference.json 不同步（第 {diff_at + 1} 行起）。{HINT}\n"
                f"  磁盘: {disk_lines[diff_at][:100] if diff_at < len(disk_lines) else '<EOF>'}\n"
                f"  应为: {exp_lines[diff_at][:100] if diff_at < len(exp_lines) else '<EOF>'}"
            )

    def test_csv_matches_regenerated_rows(self):
        with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader)
            rows = list(reader)
        self.assertEqual(header, CSV_HEADER, f"CSV 表头不对；{HINT}")

        expected = [norm_row(r) for r in csv_rows(self.doc, self.trans)]
        rows = [norm_row(r) for r in rows]
        self.assertEqual(len(rows), len(expected),
                         f"CSV 行数 {len(rows)} != {len(expected)}；{HINT}")
        # 逐行比，失败时指出第一处不同
        for i, (got, want) in enumerate(zip(rows, expected)):
            if got != want:
                self.fail(
                    f"planet_index.csv 第 {i + 2} 行不同步；{HINT}\n"
                    f"  磁盘: {got}\n"
                    f"  应为: {want}"
                )


class TestTranslationsArePreserved(unittest.TestCase):
    """`data/translations_zh.json` 是手写数据，重新生成对照表**绝不能**弄丢它。

    这条回归是有来历的：这些译名最早是直接填在 planet_index.csv 里的，
    而那个文件是生成物，跑一次 build_index_map.py 就没了。
    """

    @classmethod
    def setUpClass(cls):
        cls.trans = load_translations()
        with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
            cls.rows = {r["index"]: r for r in csv.DictReader(fh) if r.get("index", "").strip()}
        cls.md = read_text(MD_PATH)

    def test_file_exists_and_is_wellformed(self):
        self.assertTrue(os.path.exists(TRANS_PATH),
                        f"缺少 {os.path.basename(TRANS_PATH)}")
        self.assertIn("planets", self.trans)
        self.assertIn("sectors", self.trans)

    def test_every_planet_translation_reaches_the_csv(self):
        for index, zh in self.trans["planets"].items():
            self.assertIn(index, self.rows, f"CSV 里没有 index={index}")
            self.assertEqual(self.rows[index]["name_zh"], zh,
                             f"index={index} 的中文名在 CSV 里丢了")

    def test_every_sector_translation_reaches_the_csv(self):
        for sector, zh in self.trans["sectors"].items():
            matched = [r for r in self.rows.values() if r["sector"] == sector]
            self.assertTrue(matched, f"CSV 里没有星区 {sector}")
            for r in matched:
                self.assertEqual(r["sector_zh"], zh,
                                 f"星区 {sector} 的中文名在 CSV 里丢了")

    def test_translations_reach_the_markdown(self):
        for zh in self.trans["planets"].values():
            self.assertIn(zh, self.md, f"INDEX_MAP.md 里没有星球译名 {zh}")
        for zh in self.trans["sectors"].values():
            self.assertIn(zh, self.md, f"INDEX_MAP.md 里没有星区译名 {zh}")

    def test_untranslated_entries_are_blank_not_invented(self):
        """没填的项留空，不要拿英文名顶替——否则看不出哪些还没翻译。"""
        untranslated = [i for i in self.rows if i not in self.trans["planets"]]
        self.assertTrue(untranslated, "所有星球都已翻译？那这条断言可以删掉")
        for index in untranslated[:20]:
            self.assertEqual(self.rows[index]["name_zh"], "",
                             f"index={index} 没翻译，name_zh 应当留空")

    def test_translations_are_not_written_into_reference_json(self):
        """reference.json 是 refresh_reference.py 的产物，手工译名不能混进去。"""
        doc = json.loads(read_text(REF_PATH))
        for index in self.trans["planets"]:
            entry = doc["planets"].get(index, {})
            self.assertNotIn("name_zh", entry,
                             "译名混进了 reference.json，重新生成参照表时会丢")


class TestIndexMapCompleteness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(read_text(REF_PATH))
        cls.trans = load_translations()
        cls.planets = cls.doc["planets"]
        cls.sectors = cls.doc["sectors"]
        cls.md = read_text(MD_PATH)

    def test_every_planet_appears_in_the_table(self):
        missing = [p["name"] for p in self.planets.values() if p["name"] not in self.md]
        self.assertEqual(missing, [], f"这些星球没出现在 INDEX_MAP.md 里: {missing[:10]}")

    def test_every_sector_appears(self):
        missing = [s for s in self.sectors if f"| **{s}** |" not in self.md]
        self.assertEqual(missing, [], f"这些星区没出现在 INDEX_MAP.md 里: {missing}")

    def test_every_settings_hash_appears(self):
        missing = [p["index"] for p in self.planets.values()
                   if p.get("hash") and f"`{p['hash']}`" not in self.md]
        self.assertEqual(missing, [], f"这些星球的 settingsHash 没出现: {missing[:10]}")

    def test_explains_that_payload_sector_is_not_the_wiki_sector(self):
        """最容易踩的坑，必须在表里写清楚。"""
        self.assertIn("不是 wiki 星区", self.md)
        self.assertIn("载荷sector", self.md)

    def test_sector_membership_matches_reference(self):
        """星区 -> 星球 的列表要和 reference.json 一致。"""
        sector_zh = self.trans["sectors"]
        for name, sec in self.sectors.items():
            expected = ", ".join(
                f"{i} {self.planets[str(i)]['name']}"
                for i in sec["planets"] if str(i) in self.planets
            )
            row = (f"| **{name}** | {sector_zh.get(name) or '—'} | "
                   f"{len(sec['planets'])} | {expected} |")
            self.assertIn(row, self.md, f"星区 {name} 的成员行对不上；{HINT}")


class TestIndexMapAgainstReferenceJson(unittest.TestCase):
    """CSV 的关键列要和参照表逐条对得上。"""

    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(read_text(REF_PATH))
        with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
            cls.rows = list(csv.DictReader(fh))

    def test_row_per_planet_and_indices_match(self):
        expected = sorted(p["index"] for p in self.doc["planets"].values())
        got = sorted(int(r["index"]) for r in self.rows)
        self.assertEqual(got, expected)

    def test_hashes_and_names_match(self):
        by_index = {int(r["index"]): r for r in self.rows}
        for p in self.doc["planets"].values():
            row = by_index[p["index"]]
            self.assertEqual(row["name"], p["name"])
            self.assertEqual(row["sector"], p.get("sector") or "")
            self.assertEqual(row["settings_hash"], str(p["hash"]))

    def test_planet_263_is_absent(self):
        """实时载荷里没有 index 263，对照表也不该凭空造一个。"""
        indices = {int(r["index"]) for r in self.rows}
        self.assertNotIn(263, indices)

    def test_index_range(self):
        indices = sorted(int(r["index"]) for r in self.rows)
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 273)


if __name__ == "__main__":
    unittest.main(verbosity=2)
