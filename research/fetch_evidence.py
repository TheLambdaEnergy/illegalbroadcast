"""重新拉取反向工程所需的证据文件到 research/raw/。

体积较大（约 14 MB），因此这些文件不入库。

    python research/fetch_evidence.py            # 只拉 JSON 快照
    python research/fetch_evidence.py --with-js  # 连线上 JS 包一起爬
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
JS = os.path.join(RAW, "js")
BASE = "https://helldiverscompanion.com"

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Encoding": "gzip",
}

ENDPOINTS = {
    "live.json": "https://helldiverscompanion.com/api/hell-divers-2-api/get-api-data-live",
    "news.json": "https://helldiverscompanion.com/api/steam-api/news",
    "planetRegions_recent.json": "https://cdn.helldiverscompanion.com/live/planetRegions/recent.json",
    "planetEvents_2days.json": "https://cdn.helldiverscompanion.com/live/planetEvents/2days.json",
    "globalResources_recent.json": "https://cdn.helldiverscompanion.com/live/globalResources/recent.json",
    "assignments_recent.json": "https://cdn.helldiverscompanion.com/live/assignments/recent.json",
    "hd2dev_planets.json": "https://api.helldivers2.dev/api/v1/planets",
}

# 反向工程用到的几个候选星球索引（跨阵营、跨血量规模）
PLANET_SAMPLES = [0, 79, 114, 202, 225, 248, 253, 260, 262, 269]


def get(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers={
        **UA,
        "X-Super-Client": "helldiversbot-research",
        "X-Super-Contact": "local-research",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw


def fetch_endpoints() -> None:
    os.makedirs(RAW, exist_ok=True)
    urls = dict(ENDPOINTS)
    for i in PLANET_SAMPLES:
        urls[f"planet_{i}_recent.json"] = (
            f"https://cdn.helldiverscompanion.com/live/planets/{i}/recent.json")

    def one(item):
        name, url = item
        try:
            body = get(url)
            with open(os.path.join(RAW, name), "wb") as fh:
                fh.write(body)
            return name, len(body), None
        except Exception as exc:  # noqa: BLE001
            return name, 0, str(exc)

    with ThreadPoolExecutor(max_workers=8) as pool:
        for name, size, err in pool.map(one, urls.items()):
            print(f"  {'ERR ' if err else 'OK  '}{name:34s} {size:>9,} B  {err or ''}")


def crawl_js() -> None:
    os.makedirs(JS, exist_ok=True)
    html = get(BASE + "/").decode("utf-8", "replace")
    with open(os.path.join(RAW, "home.html"), "w", encoding="utf-8") as fh:
        fh.write(html)

    seeds = {m.lstrip(".") for m in re.findall(r'"(\.?/?_app/[^"]+\.js)"', html)}
    print(f"  入口 chunk: {len(seeds)}")

    seen: set[str] = set()
    queue = list(seeds)
    while queue:
        path = queue.pop()
        if path in seen:
            continue
        seen.add(path)
        url = urljoin(BASE, path)
        try:
            src = get(url).decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            print(f"  ERR {path}: {exc}")
            continue
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", path.split("/")[-1])
        with open(os.path.join(JS, name), "w", encoding="utf-8") as fh:
            fh.write(src)
        for ref in re.findall(r'["\']((?:\.\.?/)[^"\']+\.js)["\']', src):
            nxt = urljoin(url, ref)
            if nxt.startswith(BASE):
                rel = nxt[len(BASE):]
                if rel not in seen:
                    queue.append(rel)
    total = sum(os.path.getsize(os.path.join(JS, f)) for f in os.listdir(JS))
    print(f"  已抓取 {len(seen)} 个 chunk，共 {total / 1024 / 1024:.1f} MB -> {JS}")


def main() -> int:
    ap = argparse.ArgumentParser(description="拉取反向工程证据")
    ap.add_argument("--with-js", action="store_true", help="同时递归爬取线上 JS 包")
    args = ap.parse_args()

    print("[1/2] 接口快照")
    fetch_endpoints()
    if args.with_js:
        print("[2/2] 线上 JS 包")
        crawl_js()
    else:
        print("[2/2] 跳过 JS（加 --with-js 启用）")
    print(f"\n完成。证据目录: {RAW}")
    print("接着可以跑: python research/scan_js.py   /   node research/extract_tables.js")
    return 0


if __name__ == "__main__":
    sys.exit(main())
