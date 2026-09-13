"""递归爬取站点 JS chunk 并扫描出全部接口/资源字符串 -> research/analysis/js_scan.txt

依赖 research/raw/js（先跑 python research/fetch_evidence.py --with-js）。
本脚本自身也会递归补抓缺失的 chunk。

    python research/scan_js.py
"""

from __future__ import annotations

import gzip
import os
import re
import sys
import urllib.request
from urllib.parse import urljoin

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
JS = os.path.join(RAW, "js")
ANALYSIS = os.path.join(HERE, "analysis")
BASE = "https://helldiverscompanion.com"

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Encoding": "gzip",
    "Referer": BASE + "/",
}

OUT: list[str] = []


def p(*a) -> None:
    line = " ".join(str(x) for x in a)
    OUT.append(line)
    print(line)


def get(url: str, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", "replace")


def crawl() -> dict[str, str]:
    os.makedirs(JS, exist_ok=True)
    html_path = os.path.join(RAW, "home.html")
    if os.path.exists(html_path):
        html = open(html_path, encoding="utf-8").read()
    else:
        html = get(BASE + "/")
        os.makedirs(RAW, exist_ok=True)
        open(html_path, "w", encoding="utf-8").write(html)

    seeds = {m.lstrip(".") for m in re.findall(r'"(\.?/?_app/[^"]+\.js)"', html)}
    queue = list(seeds)
    chunks: dict[str, str] = {}
    while queue:
        path = queue.pop()
        if path in chunks:
            continue
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", path.split("/")[-1])
        local = os.path.join(JS, name)
        if os.path.exists(local):
            src = open(local, encoding="utf-8", errors="replace").read()
        else:
            try:
                src = get(urljoin(BASE, path))
            except Exception as exc:  # noqa: BLE001
                p(f"  ERR {path}: {exc}")
                chunks[path] = ""
                continue
            open(local, "w", encoding="utf-8").write(src)
        chunks[path] = src
        for ref in re.findall(r'["\']((?:\.\.?/)[^"\']+\.js)["\']', src):
            nxt = urljoin(urljoin(BASE, path), ref)
            if nxt.startswith(BASE):
                rel = nxt[len(BASE):]
                if rel not in chunks:
                    queue.append(rel)
    return chunks


def main() -> int:
    chunks = crawl()
    p(f"chunks: {sum(1 for v in chunks.values() if v)} / 访问 {len(chunks)}")

    p("")
    p("=" * 100)
    p("URL / 路径字面量")
    p("=" * 100)
    pat = re.compile(r'["\'`]((?:https?://|/|\./)[^"\'`\s\\]{2,220})["\'`]')
    hits: set[str] = set()
    for src in chunks.values():
        for m in pat.findall(src):
            if re.search(r"(?:/api/|\.json|helldivers|cdn\.|/live/|/steam-|/planet)", m, re.I):
                hits.add(m)
    for h in sorted(hits):
        p("  ", h)

    p("")
    p("=" * 100)
    p("模板化 URL 片段")
    p("=" * 100)
    frag: set[str] = set()
    for src in chunks.values():
        frag |= set(re.findall(r'["\'`](/[a-z0-9\-/_.]{4,80})["\'`]', src, re.I))
        frag |= set(re.findall(r'["\'`]([a-z0-9\-/_.]{4,60}\.json)["\'`]', src, re.I))
    for f in sorted(frag):
        p("  ", f)

    p("")
    p("=" * 100)
    p("关键实现片段（揭示公式与数据源选择逻辑）")
    p("=" * 100)
    for needle in (
        "get-api-data-",          # 主接口名由哪来的
        "impactMultiplier",
        "libDiversNeededPct",
        "impactPctDiverRequired",
        "registerImpact",
        "healthPctRegenPerHour",
    ):
        p(f"--- [{needle}] ---")
        for name, src in chunks.items():
            i = src.find(needle)
            if i >= 0:
                p(f"  在 {name} @{i}")
                p("  " + src[max(0, i - 500): i + 700].replace("\n", " "))
                p("")
                break

    os.makedirs(ANALYSIS, exist_ok=True)
    out = os.path.join(ANALYSIS, "js_scan.txt")
    open(out, "w", encoding="utf-8").write("\n".join(OUT))
    print(f"\n已写入 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
