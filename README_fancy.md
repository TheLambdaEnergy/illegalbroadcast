Rare api response: (example)

/api/v1/planet/KARLIA

```json
{
  "generated_at": "2026-09-14T01:56:34.677Z",
  "planet": {
    "index": 185,
    "name": "KARLIA",
    "settings_hash": 101839064,
    "sector": "Omega",
    "biome": {
      "en": "Scorched Moor",
      "zh": "焦灼荒原",
      "description": "Scorching temperatures, high winds, and low precipitation cause a near-constant cycle of fires to sweep this planet, punctuated by short bursts of lush rebirth between infernos."
    },
    "hazards": [
      {
        "en": "Fire Tornadoes",
        "zh": "火焰龙卷",
        "description": "Planet is ravaged by deadly fire tornadoes."
      }
    ],
    "position": {
      "x": -0.1330078,
      "y": -0.6602936
    },
    "waypoints": [
      "SANGIS"
    ],
    "max_health": 1400000,
    "health": 203728,
    "health_percent": 14.552,
    "owner": {
      "id": 4,
      "en": "Illuminate",
      "zh": "光能者",
      "color": "#a855f7"
    },
    "enemy_faction": {
      "id": 4,
      "en": "Illuminate",
      "zh": "光能者",
      "color": "#a855f7"
    },
    "is_under_attack": false,
    "liberation_percent": 85.448,
    "is_liberated": false,
    "players": 2606,
    "player_share_percent": 2.7346,
    "resistance": {
      "regen_per_second": 0.000278,
      "regen_per_hour": 1,
      "percent_per_hour": 0.0001
    },
    "liberation_rate": {
      "impact_percent_per_hour": 0.0999,
      "impact_source": "measured",
      "net_percent_per_hour": 0.0998,
      "source": "measured",
      "measured": {
        "window_seconds": 901.8,
        "from": "2026-09-14T01:16:42.5219902Z",
        "to": "2026-09-14T01:31:44.2973993Z",
        "players_avg": 2528,
        "regen_clamped": false,
        "diver_rate_observable": true,
        "diver_rate_percent_per_hour": 0.0999,
        "net_rate_percent_per_hour": 0.0998,
        "health_delta": -350
      },
      "smoothed": {
        "windows": 4,
        "window_seconds": 3674.3,
        "from": "2026-09-14T00:30:30.0299617Z",
        "to": "2026-09-14T01:31:44.2973993Z",
        "net_percent_per_hour": 0.111,
        "impact_percent_per_hour": 0.1111,
        "observable_windows": 4,
        "players_avg": 2481.7
      },
      "estimated_diver_percent_per_hour": 0.1358,
      "estimated_net_percent_per_hour": 0.1357,
      "unclamped_net_percent_per_hour": 0.0998,
      "clamped_at_enemy_floor": false
    },
    "trend": "advancing",
    "trend_zh": "推进中",
    "eta_liberation_seconds": 524922,
    "eta_liberation_text": "6天1小时",
    "is_homeworld": false,
    "disabled": false,
    "active_effects": [
      {
        "id": 1402,
        "slug": "game_IllVoteSnatchers",
        "label": "Ill Vote Snatchers",
        "category": "战术行动"
      },
      {
        "id": 1403,
        "slug": "pawn_IllVoteSnatchers",
        "label": "Ill Vote Snatchers",
        "category": "敌人变种"
      }
    ],
    "active_effect_ids": [1402, 1403],
    "campaign": {
      "id": 51685,
      "planet_index": 185,
      "planet_name": "KARLIA",
      "type": 0,
      "type_label": "解放战役",
      "type_label_en": "Liberation",
      "count": 10,
      "faction": {
        "id": 1,
        "en": "Humans",
        "zh": "超级地球",
        "color": "#4a9de0"
      }
    },
    "event": null,
    "regions": [
      {
        "index": 0,
        "name": "ADNAN",
        "size": "City",
        "size_zh": "城市",
        "owner": {
          "id": 1,
          "en": "Humans",
          "zh": "超级地球",
          "color": "#4a9de0"
        },
        "health": 400000,
        "max_health": 400000,
        "health_percent": 100,
        "controlled_percent": 100,
        "regen_per_second": 0,
        "regen_percent_per_hour": 0,
        "availability_factor": 1,
        "is_available": false,
        "players": 0
      }
    ],
    "statistics": {
      "missions_won": 2471647,
      "missions_lost": 328855,
      "mission_time_seconds": 9481675737,
      "terminid_kills": 13356,
      "automaton_kills": 11443,
      "illuminate_kills": 1299969143,
      "bullets_fired": 7383648989,
      "bullets_hit": 7554077974,
      "time_played_seconds": 9481675737,
      "deaths": 21349083,
      "revives": 0,
      "accidental_deaths": 3271471,
      "mission_success_rate": 88.2572838726771,
      "missions_total": 2800502,
      "mission_success_rate_calc": 88.2573,
      "kills": {
        "terminids": 13356,
        "automatons": 11443,
        "illuminate": 1299969143,
        "total": 1299993942
      },
      "accuracy_percent": 102.3082,
      "accuracy_exceeds_100": true,
      "shots_per_hit": 0.9774,
      "kill_death_ratio": 60.8923,
      "accidental_death_percent": 15.3237,
      "time_played_hours": 2633798.82,
      "raw_gamemode_accuracy": 102.308194569567,
      "raw_accurracy_typo": 100
    },
    "status": "解放中"
  }
}
```

Formatted fancy text:

if provided parameter is '?mode=pt': (default mode)
```plaintext
星球名：KARLIA              // planet.name
分区：OMEGA                 // planet.sector 
所属阵营：光能者             // planet.owner.zh
解放进度：85.448%            // planet.liberation_percent
解放预计剩余时间：6天1小时    // planet.eta_liberation_text
部署的绝地潜兵数：2606        // planet.players
数据获取时间：2026-09-14T01:31:44.2973993Z   // generated_at
```

/api/v1/dispatches

```json
{
  "generated_at": "2026-09-14T02:50:46.853Z",
  "count": 126,
  "dispatches": [
    {
      "id": 3920,
      "type": 0,
      "published_war_time": 81364178,
      "published_at": "2026-09-13T12:07:24.448Z",
      "tag_ids": [],
      "message": "MAJOR ORDER FAILED\n\nThe Helldivers recaptured CHARBAL-VII, by the Cyborgs retained hold of ZZANIAH PRIME. \n\nMassive server banks were discovered in the captured Megafactories. Cybersecurity specialists have confirmed that these server banks could be used in the conduct of cyberattacks—confirming the enemy's intent beyond doubt.",
      "message_raw": "\u003Ci=3\u003EMAJOR ORDER FAILED\u003C/i\u003E\n\nThe Helldivers recaptured \u003Ci=3\u003ECHARBAL-VII\u003C/i\u003E, by the Cyborgs retained hold of \u003Ci=3\u003EZZANIAH PRIME\u003C/i\u003E. \n\nMassive server banks were discovered in the captured Megafactories. Cybersecurity specialists have confirmed that these server banks could be used in the conduct of cyberattacks—confirming the enemy's intent beyond doubt."
    }
    ......
```

Formatted fancy text:

```plaintext
时间：2026-09-13T12:07:24.448Z   // published_at
信息：MAJOR ORDER FAILED\n\nThe Helldivers recaptured CHARBAL-VII, by the Cyborgs retained hold of ZZANIAH PRIME. \n\nMassive server banks were discovered in the captured Megafactories. Cybersecurity specialists have confirmed that these server banks could be used in the conduct of cyberattacks—confirming the enemy's intent beyond doubt.
```

(Only show the latest dispatch.Usually the maxmium id(3920))

Additional info:if provided parameter is '?mode=raw':
Return raw JSON data.
