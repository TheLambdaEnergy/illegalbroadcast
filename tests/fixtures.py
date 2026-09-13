"""测试夹具：一份结构完整、完全离线的 live 载荷与参照表。

放在单独模块里，以便 test_normalize.py 与 test_web.py 共用，
并让 Web 层测试也能在没有网络的情况下跑起来。
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hd2api.normalize import ImpactCalibration, build_snapshot  # noqa: E402
from hd2api.reference import Reference  # noqa: E402

BASE_MS = 1_789_000_000_000  # 固定时间，保证测试可复现
WAR_TIME = 1000


def iso_ago(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def history(points: list[tuple[str, float, int, float]], max_health: float) -> dict:
    return {"data": [
        {"timestampUtc": ts, "health": h, "maxHealth": max_health,
         "players": p, "regenPerSecond": r}
        for ts, h, p, r in points
    ]}


def make_live() -> dict:
    """一份最小的、结构完整的 live 载荷（字段名与上游保持一致）。"""
    return {
        "warId": 801,
        "clientTime": BASE_MS,
        "timeSinceStart": 1000,
        "appVersion": {"HD2": "01.007.002"},
        "majorOrders": [],
        "episodes": [
            {
                "id32": 111, "title": "TEST ORDER", "description": "<i=1>desc</i>",
                "introMessage": "", "outroMessage": "", "race": 3,
                "startWarTime": 900, "endWarTime": 1100, "bannerImageId32": 0,
                "status": 2, "rewards": [{"mixId": 42, "amount": 1}],
                "phases": [{"id32": 555, "introTitle": "P1",
                            "introMessage": "hello <i=1>world</i>",
                            "outroTitle": "O1", "outroMessage": "bye"}],
            },
            {
                "id32": 222, "title": "OPEN ENDED", "description": "no end",
                "race": 4, "startWarTime": 950, "endWarTime": None,
                "status": 0, "rewards": [], "phases": [],
            },
        ],
        "episodesStatus": [{"episodeId32": 111, "latestPhaseId32": 555}],
        "warInfo": {
            "warId": 801,
            "layoutVersion": 716,
            "startDate": 1_700_000_000,
            "planetInfos": [
                {"index": 0, "settingsHash": 111, "position": {"x": 0, "y": 0},
                 "sector": 0, "maxHealth": 1_000_000, "disabled": False,
                 "initialOwner": 1, "waypoints": []},
                {"index": 1, "settingsHash": 222, "position": {"x": 1, "y": 1},
                 "sector": 1, "maxHealth": 2_000_000, "disabled": False,
                 "initialOwner": 3, "waypoints": [0]},
                {"index": 2, "settingsHash": 333, "position": {"x": 2, "y": 2},
                 "sector": 1, "maxHealth": 1_000_000, "disabled": False,
                 "initialOwner": 2, "waypoints": []},
            ],
            "homeWorlds": [{"race": 1, "planetIndices": [0]}],
            "planetRegions": [],
            "capitalInfos": [],
            "planetPermanentEffects": [],
        },
        "warStatus": {
            "warId": 801,
            "time": WAR_TIME,
            "impactMultiplier": 0.0131,
            "storyBeatId32": 0,
            "planetStatus": [
                {"index": 0, "owner": 1, "health": 1_000_000, "regenPerSecond": 0.0,
                 "players": 10, "position": {"x": 0, "y": 0}},
                {"index": 1, "owner": 3, "health": 1_500_000, "regenPerSecond": 20.0,
                 "players": 5000, "position": {"x": 1, "y": 1}},
                {"index": 2, "owner": 2, "health": 1_000_000, "regenPerSecond": 5.0,
                 "players": 0, "position": {"x": 2, "y": 2}},
            ],
            "planetAttacks": [{"source": 0, "target": 1}],
            "campaigns": [{"id": 9, "planetIndex": 1, "type": 0, "count": 12, "race": 1}],
            "communityTargets": [],
            "jointOperations": [],
            "planetEvents": [
                {"id": 7, "planetIndex": 0, "eventType": 1, "race": 3,
                 "health": 1_500_000, "maxHealth": 2_000_000,
                 "startTime": 400, "expireTime": 2200, "campaignId": 9,
                 "jointOperationIds": [7], "potentialBuildUp": 0}
            ],
            "planetActiveEffects": [{"index": 1, "galacticEffectId": 1190}],
            "planetRegions": [
                {"planetIndex": 1, "regionIndex": 0, "owner": 3, "health": 200_000,
                 "regerPerSecond": 2.0, "availabilityFactor": 0.5,
                 "isAvailable": True, "players": 120},
            ],
            "activeElectionPolicyEffects": [],
            "globalEvents": [
                {"eventId": 1, "id32": 2, "title": "NEWS", "message": "<i=3>hi</i> there",
                 "race": 1, "expireTime": 2000}
            ],
            "superEarthWarResults": [],
            "spaceStations": [
                # 精简条目：只有这里才有 activeEffectIds
                {"id32": 749875195, "planetIndex": 0,
                 "currentElectionEndWarTime": 1500, "flags": 1,
                 "activeEffectIds": [1209, 1212]},
            ],
            "globalResources": [],
            "layoutVersion": 716,
        },
        "warStats": {
            "galaxy_stats": {
                "missionsWon": 100, "missionsLost": 25, "missionTime": 3600,
                "bugKills": 10, "automatonKills": 20, "illuminateKills": 30,
                "bulletsFired": 1000, "bulletsHit": 500, "timePlayed": 7200,
                "deaths": 5, "revives": 0, "friendlies": 1,
                "missionSuccessRate": 80.0, "accurracy": 100, "accuracy": 50.0,
            },
            "planets_stats": [
                # 上游混入的哨兵记录，应被丢弃
                {"planetIndex": -1337, "missionsWon": 0, "bulletsFired": 0},
                {"planetIndex": 1, "missionsWon": 50, "missionsLost": 10,
                 "missionTime": 100, "bugKills": 1, "automatonKills": 2,
                 "illuminateKills": 3, "bulletsFired": 400, "bulletsHit": 100,
                 "timePlayed": 200, "deaths": 4, "revives": 0, "friendlies": 0,
                 "missionSuccessRate": 83.33, "accurracy": 100, "accuracy": 25.0},
            ],
        },
        "news": [
            {"id": 1, "published": 900, "type": 0, "tagIds": [],
             "message": "<i=3>MAJOR ORDER WON</i>\n\nWe did it."},
            {"id": 2, "published": 1100, "type": 0, "tagIds": [],
             "message": "newer dispatch"},
        ],
        "spaceStations": [
            {"id32": 749875195, "planetIndex": 0, "lastElectionId": "a",
             "currentElectionId": "b", "currentElectionEndWarTime": 1500, "flags": 1,
             "tacticalActions": [
                 {"id32": 1, "name": "EAGLE STORM", "description": "d",
                  "strategicDescription": "s", "status": 3,
                  "statusExpireAtWarTimeSeconds": 1600,
                  "effectIds": [1, 2], "activeEffectIds": [],
                  "cost": [{"itemMixId": 3992382197, "targetValue": 86400,
                            "currentValue": 0, "deltaPerSecond": 0.42,
                            "maxDonationAmount": 75, "maxDonationPeriodSeconds": 86400}]}
             ]},
        ],
        "galacticWarEffects": [],
    }


def make_reference() -> Reference:
    """内存参照表：格式与 data/reference.json 完全一致。"""
    ref = Reference.__new__(Reference)
    ref.path = "<in-memory>"
    ref._doc = {
        "generated_at": "2026-01-01T00:00:00Z",
        "source": "test",
        "war_id": 801,
        "biomes_zh": {"Moon": "月球"},
        "hazards_zh": {"None": "无"},
        "region_size_zh": {"City": "城市"},
        "sectors": {"Sol": {"name": "Sol", "planets": [0]},
                    "Altus": {"name": "Altus", "planets": [1, 2]}},
        "planets": {
            "0": {"index": 0, "name": "SUPER EARTH", "sector": "Sol",
                  "biome": {"en": "Moon", "zh": "月球", "description": "d"},
                  "hazards": [{"en": "None", "zh": "无", "description": "n"}],
                  "hash": 111, "position": {"x": 0, "y": 0}, "waypoints": [],
                  "max_health": 1_000_000, "initial_owner": 1, "regions": {}},
            "1": {"index": 1, "name": "AURORA BAY", "sector": "Altus",
                  "biome": {"en": "Moon", "zh": "月球", "description": "d"},
                  "hazards": [], "hash": 222, "position": {"x": 1, "y": 1},
                  "waypoints": [0], "max_health": 2_000_000, "initial_owner": 3,
                  "regions": {"0": {"index": 0, "name": "BATU BELIG", "size": "City",
                                    "size_zh": "城市", "hash": 1}}},
            "2": {"index": 2, "name": "HEETH", "sector": "Altus",
                  "biome": {"en": "Moon", "zh": "月球", "description": "d"},
                  "hazards": [], "hash": 333, "position": {"x": 2, "y": 2},
                  "waypoints": [], "max_health": 1_000_000, "initial_owner": 2,
                  "regions": {}},
        },
    }
    ref._planets = {int(k): v for k, v in ref._doc["planets"].items()}
    ref._sectors = dict(ref._doc["sectors"])
    # 效果名称表（生产环境来自 data/effects.json；这里放两条用于断言）
    ref._effects = {1190: "mark_Hidden", 1239: "mark_JetBrigadeFactory"}
    ref._presence = {4065921374: "pres_SecureCity1"}
    return ref


DEFAULT_HISTORY = {
    1: history([(iso_ago(30), 1_510_000, 5000, 20.0),
                (iso_ago(15), 1_500_000, 5000, 20.0)], 2_000_000),
}


class StubSources:
    """替代真实上游，让 Web 层测试完全离线。"""

    def __init__(self, histories=None):
        self.histories = histories or DEFAULT_HISTORY
        self.planet_history_calls: list[int] = []

    def planet_history(self, index: int):
        self.planet_history_calls.append(index)
        return self.histories.get(index, {"data": []})

    def planet_histories(self, indices):
        return {i: self.histories.get(i) for i in indices}

    def live(self, channel: str = "live"):
        return make_live()

    def steam_news(self):
        return {"appnews": {"newsitems": [
            {"gid": "1", "title": "Patch", "url": "http://x", "author": "AH",
             "contents": "<b>notes</b>", "feedlabel": "steam", "date": 1_700_000_000},
        ]}}

    def extended_api_information_2days(self):
        return make_extended_info()


def make_extended_info() -> dict:
    """站点 extendedApiInformation/2days.json 的最小等价物。"""
    base = datetime(2026, 9, 13, 12, 0, 0, tzinfo=timezone.utc)
    rows = []
    for i in range(5):
        ts = (base + timedelta(minutes=15 * i)).isoformat().replace("+00:00", "Z")
        rows.append({
            "timestampUtc": ts,
            "totalPlayerCount": 1000 + 100 * i,
            "playerCountHumans": 100,
            "playerCountTerminids": 200 + 10 * i,
            "playerCountAutomatons": 600 + 80 * i,
            "playerCountIlluminate": 100 + 10 * i,
            "impactMultiplier": 0.013 + 0.0001 * i,
            "missionsWon": 100 + i,
        })
    return {"timestampUtc": rows[-1]["timestampUtc"], "data": rows}


class StubService:
    """只实现 Web 层会用到的那部分接口。"""

    def __init__(self, histories=None):
        self.ref = make_reference()
        self.sources = StubSources(histories)
        self._live = make_live()
        self._calibration = ImpactCalibration(
            0.0004443, [(0.000444, 5000), (0.000444, 5000)])
        self._snapshot = build_snapshot(
            self._live, self.ref, self.sources.histories, self._calibration)
        self._steam = None
        self.last_error = None
        self.last_error_at = None
        self.refresh_count = 1
        self.enable_poller = False

    def snapshot(self, auto_refresh: bool = True):
        return self._snapshot

    def raw(self):
        return self._live

    def calibration(self):
        return self._calibration

    def refresh_steam_news(self, force: bool = False):
        if self._steam is None:
            from hd2api.normalize import steam_news_block
            self._steam = steam_news_block(self.sources.steam_news())
        return self._steam

    def health(self):
        return {
            "state": "ok",
            "snapshot_age_seconds": 0.0,
            "snapshot_generated_at": self._snapshot["generated_at"],
            "refresh_count": self.refresh_count,
            "tracked_planet_histories": len(self.sources.histories),
            "calibration": self._calibration.to_dict(),
            "last_error": None,
            "last_error_at": None,
            "poller_enabled": False,
            "reference": {"generated_at": self.ref.generated_at,
                          "planets": self.ref.planet_count,
                          "sectors": self.ref.sector_count},
        }


def build_test_snapshot(histories=None):
    ref = make_reference()
    return build_snapshot(make_live(), ref, histories or DEFAULT_HISTORY,
                          ImpactCalibration(0.0004443, [(0.000444, 5000)] * 2))
