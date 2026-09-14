# helldiversbot —— 《Helldivers 2》实时战报 API

把 [helldiverscompanion.com](https://helldiverscompanion.com/) 那些「全是游戏内 ID、几乎读不懂」的
JSON，翻译成一个**人类可读、可直接消费**的本地 REST API。

两种前端，**共用同一套业务逻辑**（所以不存在文档与实际行为不一致的问题）：

| 前端 | 依赖 | 文档 | 启动 |
|---|---|---|---|
| 标准库 `http.server`（默认） | **零依赖** | `/docs` + `/guide` | `python run.py` |
| FastAPI + uvicorn（可选） | `.deps/` | `/docs`(Swagger) + `/redoc` | `python run.py --fastapi` |

```bash
python run.py
# -> http://127.0.0.1:8808        API 索引
# -> http://127.0.0.1:8808/docs   可视化文档（可点「试一下」）
```

想用 Swagger UI：

```bash
python scripts/vendor_deps.py     # 把 FastAPI 装进 .deps/（绕开不可用的 pip）
python run.py --fastapi           # 自动把 .deps 加进 sys.path
```

---

## 0. 术语对照（全项目统一）

文档、代码注释、API 返回的中文标签一律使用下表译名，**不要混用其它写法**：

| 英文 | 中文 | 备注 |
|---|---|---|
| Humans / Super Earth | **超级地球** | 玩家阵营；站点 `playerCountHumans` 指的是「当前无敌人可打的地方的人」 |
| Helldivers | **绝地潜兵** | 玩家；速率类指标里的「每绝地潜兵影响力」即 per-Helldiver impact |
| Terminids | **终结族** | |
| Automatons | **机器人** | 禁用旧译名<!-- terminology-lint:ignore -->「机械体」「自动机」 |
| Illuminate | **光能者** | 禁用旧译名<!-- terminology-lint:ignore -->「光明者」 |

> 这份对照表由 `tests/test_terminology.py` 强制执行：任何文件里出现旧译名都会让测试失败。
> 表里这两处「禁用旧译名」的举例用 `<!-- terminology-lint:ignore -->` 显式豁免。

对应的**机器可读标识**（不要翻译，`/api/v1/planets?owner=` 也认中文）：

| 阵营 | `race` | `owner.en` | `owner.zh` |
|---|---|---|---|
| 超级地球 | 1 | `Humans` | 超级地球 |
| 终结族 | 2 | `Terminids` | 终结族 |
| 机器人 | 3 | `Automatons` | 机器人 |
| 光能者 | 4 | `Illuminate` | 光能者 |

代码里译名的**唯一来源**是 `hd2api/reference.py` 的 `FACTION_FALLBACK`
（`data/reference.json` 由 `scripts/refresh_reference.py` 生成，两处的译名必须一致）。

**汇总里的英文键怎么办？** `totals.owned_by_faction`、`totals.players_by_*`、
`sectors[].owned_by` 这类计数 map 用英文阵营名做键——它们是稳定标识，
也和站点的 `playerCountXXX` 同名。为了让消费方不必硬编码中文，
`/api/v1/war`、`/api/v1/sectors`、`/api/v1/snapshot` 都会带上一份映射：

```json
"faction_labels": {
  "Humans": "超级地球", "Terminids": "终结族",
  "Automatons": "机器人", "Illuminate": "光能者"
}
```

```bash
python tests/test_terminology.py        # 术语一致性检查（10 项）
python tests/test_index_map.py          # index 对照表同步检查（13 项）
python research/verify_terminology.py   # 起服务后看实际输出
```

---

## 1. 这个项目解决什么问题

上游 `get-api-data-live` 返回约 400 KB 的 JSON，但它**不含任何人能看懂的文本**：

```json
{"index": 114, "settingsHash": 975759959, "planetNameId32": 0, "planetBiomeId32": 0,
 "sector": 2, "maxHealth": 1600000, "initialOwner": 1}
{"index": 114, "owner": 3, "health": 1600000, "regenPerSecond": 13.888889, "players": 490}
```

- `planetNameId32` / `planetBiomeId32` **全部为 0**，星球名与地形被彻底抹掉了；
- `sector` 只是个整数；
- `owner` / `race` 是 1~4 的数字；
- 没有任何「解放度」「每小时增速」「预计解放时间」这类派生指标。

本项目做两件事：

1. **外挂静态参照表**（`data/reference.json` + `data/effects.json`），把 ID 映射成可读文本；
2. **实现派生指标的计算**，公式全部从站点线上代码反推并用真实数据验证过。

翻译后：

```json
{
  "index": 114, "name": "AURORA BAY", "sector": "Valdis", "status": "解放中",
  "biome": {"en": "Tundra", "zh": "苔原", "description": "A perennially chilly climate..."},
  "hazards": [{"en": "None", "zh": "无"}],
  "owner": {"id": 3, "en": "Automatons", "zh": "机器人", "color": "#e04545"},
  "enemy_faction": {"id": 3, "en": "Automatons", "zh": "机器人"},
  "liberation_percent": 0.0, "players": 490, "player_share_percent": 0.4941,
  "resistance": {"regen_per_second": 13.888889, "regen_per_hour": 50000.0, "percent_per_hour": 3.125},
  "liberation_rate": {"net_percent_per_hour": 0.0, "source": "measured", "...": "..."},
  "trend": "contested_stalled", "trend_zh": "被抵抗抵消",
  "active_effects": [{"id": 1239, "slug": "mark_JetBrigadeFactory",
                      "label": "Jet Brigade Factory", "category": "设施 / 标记"}],
  "regions": [{"name": "BATU BELIG", "size": "City", "size_zh": "城市", "controlled_percent": 100.0,
               "players": 0, "is_available": false}],
  "statistics": {"missions_won": 5902331, "kills": {"automatons": 1429756722, "total": 1429786916}, "...": "..."}
}
```

---

## 2. 快速开始

```bash
# 1) 启动服务（首次启动会抓一次数据，约 10~30 秒）
python run.py

# 常用参数
python run.py --port 9000        # 换端口
python run.py --fastapi          # 用 FastAPI（需先跑 scripts/vendor_deps.py）
python run.py --no-poller        # 关闭后台轮询，改为按需刷新
python run.py -v                 # 打印访问日志
```

命令行工具（不启服务，直接看数据）：

```bash
python -m hd2api check                      # 自检：参照表 + 上游 + 归一化覆盖率
python -m hd2api war                        # 战争概览
python -m hd2api planets --active --limit 15 # 当前有人/有战役的星球
python -m hd2api planet KARLIA --pretty      # 单颗星球（支持中文/名称/slug/index/settingsHash）
python -m hd2api defenses --pretty           # 防御战与入侵预测
python -m hd2api dump --out snap.json        # 导出完整快照
```

跑测试：

```bash
python -m unittest discover -s tests -t tests
# 237 项：归一化 58 + 标准库 Web 层 45 + FastAPI 14 + 可读文本 47 + QQ 机器人 44 + 术语 10 + 对照表 19
```

**全部离线**——测试用夹具喂数据，不碰网络。

### 逐条核对需求覆盖

```bash
python research/audit_metric_coverage.py
# 29 项指标，缺失 0 项（每项都打印真实取值）
```

---

## 3. 接口一览

| 端点 | 说明 |
|---|---|
| `GET /` | API 索引 |
| `GET /docs` | 可视化文档（含「试一下」链接） |
| `GET /openapi.json` | OpenAPI 3.1 描述 |
| `GET /health` | 快照新鲜度、标定状态、上游错误 |
| `GET /api/v1/war` | 战争概览：warId、warTime、银河影响系数、总在线人数、各阵营星球数 |
| `GET /api/v1/stats` | 银河累计统计：任务、击杀、开火/命中、死亡、K/D |
| `GET /api/v1/population` | **在线人数趋势**：近两天时间序列 + 分阵营明细 + 银河影响系数历史 |
| `GET /api/v1/planets` | **主力端点**：星球列表，支持筛选/排序/字段裁剪 |
| `GET /api/v1/planets/{key}` | 单颗星球详情（key = index / 名称 / slug / settingsHash） |
| `GET /api/v1/planets/{key}/history` | 近期采样历史（约 15 分钟一个点），用于画曲线 |
| `GET /api/v1/planets/{key}/regions` | 区域战况：区域名、尺寸、控制阵营、控制度、区域在线人数 |
| `GET /api/v1/sectors` | 星区列表：星球数、已解放数、各阵营占有、在线人数 |
| `GET /api/v1/sectors/{name}` | 单个星区 + 其下全部星球 |
| `GET /api/v1/campaigns` | 战役列表（解放 + 防御），含战役等级 |
| `GET /api/v1/defenses` | **防御战**：入侵等级、防守进度、敌方推进速率、所需增援、胜负预测、倒计时 |
| `GET /api/v1/major-orders` | 重大指令（默认只返回进行中的） |
| `GET /api/v1/dispatches` | 游戏内快讯（已剥离 `<i=N>` 富文本标记） |
| `GET /api/v1/news` | Steam 官方公告 |
| `GET /api/v1/space-stations` | 民主空间站：所在星球、战术行动、投票状态 |
| `GET /api/v1/global-events` | 银河级叙事事件 |
| `GET /api/v1/reference` | 静态参照表（`?full=1` 返回整张表） |
| `GET /api/v1/raw` | 上游原始载荷（调试用，`?part=warInfo` 只取一部分） |

### `/api/v1/planets` 的查询参数

```
?sector=Altus                          按星区名过滤
?owner=3                               按阵营：1-4 或 humans/terminids/automatons/illuminate（也认 机器人）
?status=防御中                          按状态
?q=aurora                              名称/星区模糊匹配（至少 2 字符）
?active=1                              只看有绝地潜兵或有战役的
?defending=1                           只看正在防御战的
?contested=1                           只看有绝地潜兵且尚未解放的
?min_players=1000                      最少在线人数
?sort=players&order=desc               index|name|sector|players|liberation|rate|resistance|eta|health
?limit=50&offset=100                   分页
?compact=1                             精简字段（推荐给列表消费）
?fields=name,players,liberation_percent 字段白名单
?pretty=1                              缩进输出
```

### 调用示例

```bash
# 当前最激烈的 10 颗星球
curl "http://127.0.0.1:8808/api/v1/planets?contested=1&sort=players&limit=10&compact=1"

# 正在挨打、且按当前投入预计守不住的星球
curl "http://127.0.0.1:8808/api/v1/defenses?outcome=defense_will_fail"

# 终结族控制下的星球，按解放度排序
curl "http://127.0.0.1:8808/api/v1/planets?owner=terminids&sort=liberation&compact=1"
```

---

## 3.5 可读文本输出（`?mode=pt` / `?mode=md`）

**只有两个端点支持**（规格见根目录 `README_fancy.md`）：

| 端点 | `?mode=pt` / `?mode=md` 的输出 |
|---|---|
| `GET /api/v1/planets/{key}`（也认文档里的单数 `/api/v1/planet/{key}`） | 星球摘要，**按是否处于防御战自动切换版式** |
| `GET /api/v1/dispatches` | 只输出**最新一条**快讯 |

### 版式一：解放战役（7 行）

```bash
curl "http://127.0.0.1:8808/api/v1/planet/KARLIA?mode=pt"
```

```plaintext
星球名：KARLIA
分区：OMEGA
所属阵营：光能者
解放进度：85.6582%
解放预计剩余时间：4天15小时
部署的绝地潜兵数：2341
数据获取时间：2026-09-14T03:16:56.8288321Z
```

### 版式二：防御战役 / 敌人入侵（8 行）

当 `planet.is_under_attack == true` 时自动切换：

```bash
curl "http://127.0.0.1:8808/api/v1/planet/BEKVAM%20III?mode=pt"
```

```plaintext
星球名：BEKVAM III
分区：NANOS
所属阵营：机器人
已防御：6.2535%
预测：失败
剩余时间：15小时59分
部署的绝地潜兵数：12937
数据获取时间：2026-09-14T03:16:56.8288321Z
```

字段映射：

| 输出行 | 来源 |
|---|---|
| `已防御` | `event.defense_progress_percent` |
| `预测` | `event.predicted_outcome` → **成功 / 失败 / 不确定** |
| `剩余时间` | `event.time_remaining_text` |

`预测` 只允许三个值：

| `event.predicted_outcome` | 输出 |
|---|---|
| `defense_will_hold` | 成功 |
| `defense_will_fail` | 失败 |
| `too_close_to_call` | 不确定 |
| `unknown` / `null` / 其它 | 不确定 |

> ⚠️ **防御战里的 `所属阵营` 是入侵方，不是星球占有者。**
> 上面 BEKVAM III 的 `owner.zh` 其实是**超级地球**（是我们的星球在挨打），
> 输出的却是入侵方**机器人**（`event.faction.zh`）。这与文档示例一致——
> 文档里 K 的 owner 同样是超级地球，写的却是「机器人」。

### 版式三：游戏内快讯（只输出最新一条）

```bash
curl "http://127.0.0.1:8808/api/v1/dispatches?mode=pt"
```

```plaintext
时间：2026-09-13T12:07:20.895Z
信息：MAJOR ORDER FAILED

The Helldivers recaptured CHARBAL-VII, by the Cyborgs retained hold of ZZANIAH PRIME. 
...
```

### 参数取值

| `?mode=` | 行为 |
|---|---|
| 省略 / 其它值 | **返回 JSON**（默认不变，向后兼容） |
| `pt` | 返回纯文本 |
| `md` | 同 `pt`（两个名字等价） |
| `raw` | 返回 JSON（显式声明） |

其它端点即使带上 `mode` 也照常返回 JSON——`mode` 只对上面两个端点生效。

### 与文档示例的三处差异（实现时的判断）

1. **没有输出 `// planet.name` 这类行尾注释。** 它们是文档作者标注的**字段来源**，不是输出内容。
   证据：`数据获取时间` 那行标的是 `generated_at`，但示例值 `2026-09-14T01:31:44.2973993Z`
   恰好等于同一份 JSON 里的 `liberation_rate.measured.to`，而 `generated_at` 是 `01:56:34.677Z`
   —— 说明注释是凭记忆手写的。
2. **`数据获取时间` 跟示例值走**：优先用实测窗口的结束时刻（`liberation_rate.measured.to`，
   那才是「数据是什么时候的」），没有实测时才退回 `generated_at`。
3. **`信息` 里的换行是真实换行**，不是字面量 `\n`。JSON 里 `"a\n\nb"` 本来就是真换行，
   输出成多行更易读。

空值统一渲染成 `—`（例如已解放星球的 `解放预计剩余时间`）。

```bash
python tests/test_textview.py           # 47 项，逐字比对文档的两套示例
python research/verify_text_modes.py    # 起服务后核对真实输出（会自动找一颗正在防御的星球）
```

---

## 3.6 QQ 机器人

`bot/` 下是一个把本 API 接到 QQ 的机器人（基于 [botpy](https://github.com/tencent-connect/botpy/)）。
功能规格见 [`qqbot.md`](qqbot.md)，用法见 [`bot/README.md`](bot/README.md)。

```bash
python run.py            # 先起 API
python bot/qqbot.py      # 再起机器人
```

| 命令 | 说明 |
|---|---|
| `/p` `/planet` `<星球名或index>` | 单颗星球战报（`?mode=md`） |
| `/d` `/dispatch` | 最新一条游戏内快讯（`?mode=md`） |
| `/t` `/trending` | 在线绝地潜兵最多的 5 颗星球 |

支持 QQ 的**频道 / 频道私信 / QQ群 / QQ私聊**四类消息。凭据放
`bot/config.yaml`（已 gitignore）或用环境变量 `QQBOT_APPID` / `QQBOT_SECRET`。

```bash
python tests/test_qqbot.py       # 44 项，离线逻辑 + 对着真实 API 的端到端
```

---

## 4. 指标口径（每个派生字段的公式出处）

所有速率单位是 **百分比/小时**，所有时长单位是 **秒**。
数据不足时返回 `null`，**不返回 0**——0 和「不知道」是两回事。

| 字段 | 公式 | 说明 |
|---|---|---|
| `liberation_percent` | `(1 - health / max_health) × 100` | 敌方星球。己方星球恒为 100 |
| `resistance.percent_per_hour` | `regenPerSecond × 3600 / max_health × 100` | **敌人抵抗度**。站点内部叫 `healthPctRegenPerHour` |
| `liberation_rate.net_percent_per_hour` | 来自 CDN 历史实测：`-Δhealth/Δt / max_health × 3600 × 100` | **解放度每小时净增长**。正数=在推进 |
| `liberation_rate.measured.diver_rate_percent_per_hour` | `(regen - Δhealth/Δt) / max_health × 3600 × 100` | 绝地潜兵的贡献（不含抵抗度） |
| `liberation_rate.estimated_*` | `players × 每绝地潜兵影响力 × 3600 / max_health × 100` | 按当前在线人数的模型估算 |
| `eta_liberation_seconds` | `(100 - liberation_percent) / net_rate × 3600` | 仅在 `net_rate > 0` 时给出 |
| `defenses[].invasion_level` | `ceil(health / 50000)` / `floor(maxHealth / 50000)` | **敌人入侵等级**，站点显示为「37/40」 |
| `defenses[].enemy_rate_percent_per_hour` | `3600 / (expireTime - startTime) × 100` | 防御战中敌方的推进速率 |
| `defenses[].required_rate_percent_per_hour` | `(1 - 防守进度) / 剩余秒数 × 3600 × 100` | 守住所需的总速率 |
| `defenses[].required_divers` | `required_rate / (每绝地潜兵影响力 × 3600 / max_health × 100)` | **需要的增援量** |
| `defenses[].diver_coverage_ratio` | `当前速率估算 / required_rate` | ≥1 稳守，0.8~1 难料，<0.8 预计失守 |
| `trend` | 见下 | 比绝对数值更有信息量 |

**恒等式**（已在 273 颗星球上验证，0 例外）：

```
impact_percent_per_hour - resistance.percent_per_hour == net_percent_per_hour
```

### ⚠️ 两个速率不是一回事，别搞混

官网星球卡片上那个「**Helldivers planetary control impact per hour**」是**绝地潜兵贡献**，
不含敌方抵抗度，**永远非负**。而「解放度到底在不在涨」要看**净增速**。两者在高抵抗星球上会完全背离：

| 星球 | 官网口径 `impact` | 本 API `net` | 抵抗度 | 实际 |
|---|---|---|---|---|
| KARLIA | +0.1087%/h | +0.1087%/h | 0.0001%/h | 在推进 |
| **ZZANIAH PRIME** | **+0.8824%/h** | **−0.6176%/h** | 1.5000%/h | **在丢地** |

ZZANIAH PRIME 官网会给你一个漂亮的正数，但它其实正在被反推。
本 API 两个都给：

| 字段 | 含义 |
|---|---|
| `liberation_rate.impact_percent_per_hour` | **与官网同口径**，绝地潜兵贡献，非负 |
| `liberation_rate.net_percent_per_hour` | 扣掉抵抗度后的净变化，可正可负 |
| `liberation_rate.smoothed.*` | 最近最多 1 小时的平滑值（单窗口噪声约 ±12%） |

### 为什么要有平滑值

CDN 每约 15 分钟落一个采样点，**相邻窗口之间天然就能差 12%**。实测 KARLIA 连续四个窗口：

```
0.1096   0.1190   0.1199   0.1244   %/h     （极差 0.0148，相对 12.6%）
```

所以拿「某一个 15 分钟窗口」去和官网对数字，差 10% 是正常的窗口错位，不是算错。
`liberation_rate.smoothed` 给出最近最多 1 小时（约 4 个窗口）的汇总，稳得多。

### 关键物理模型

`health` 表示**敌方对该星球的掌控度**，因此：

```
dHealth/dt = regen - divers        =>   divers = regen - dHealth/dt
```

有两个容易踩的坑，代码里都显式处理了：

1. **满血时 `regen` 被游戏截断。** 当 `health == maxHealth` 时敌人不再回血，
   此时 `divers` 不能加 `regen`。若满血且掌控度没有下降，说明绝地潜兵输出被
   regen 掩盖，**该数值不可观测**——我们返回 `null` 而不是 0。
2. **解放度不可能低于 0。** 已经 100% 被敌方控制的星球，`-抵抗度` 只是模型的
   外推，不是正在发生的丢失。此时 `net_percent_per_hour` 夹取到 `0`
   （原始外推值保留在 `unclamped_net_percent_per_hour`），趋势标记为
   `uncontested`（被占领·无进攻）而不是 `losing`。

### 每绝地潜兵影响力：运行时自动标定

站点自己也是实测的（线上代码 `registerImpact()` 用 `impactAmtDiver / diversAmt`）。
我们做同样的事：从 CDN 的星球历史里统计

```
每绝地潜兵影响力 = Σ(regen - Δhealth/Δt) / Σ(在线人数)
```

样本不足 500 人时回退到常量（`HD2_HP_PER_DIVER`，默认 `0.0004443` HP/秒）。
当前实测值约 **0.75 HP/绝地潜兵/小时**，会在 `/api/v1/war` 的
`impact_calibration` 里连同样本数一起暴露出来，来源是 `measured` 还是 `default` 一目了然。

> ⚠️ **这是本项目唯一带模型假设的字段。** `measured` 的速率来自真实历史增量，
> 可信；`estimated` 的速率依赖上面这个线性假设，仅作参考。
> `/api/v1/planets` 的 `liberation_rate.source` 会告诉你当前用的是哪一种。

---

## 5. 数据流

```
helldiverscompanion.com/api/hell-divers-2-api/get-api-data-live     ← 主快照（40s）
cdn.helldiverscompanion.com/live/planets/{i}/recent.json            ← 星球历史（5min，仅活跃星球）
cdn.helldiverscompanion.com/live/planetEvents/2days.json            ← 事件历史
cdn.helldiverscompanion.com/live/planetRegions/recent.json          ← 区域历史
cdn.helldiverscompanion.com/live/globalResources/recent.json        ← 银河资源
helldiverscompanion.com/api/steam-api/news                          ← Steam 新闻（15min）

        ↓  归一化（ID→文本、派生指标计算）

   内存快照  ←  后台轮询线程（单线程，各数据源独立 TTL）
        ↓
   HTTP 层（ThreadingHTTPServer + 极简路由）
```

**降级策略**：上游抓取失败时**保留上一份快照继续服务**，并把错误记在
`/health` 的 `last_error` 里；`state` 会变成 `degraded`。
只有从未成功抓取过时才返回 `503`。

---

## 6. 静态参照表与它的一次性构建

`data/reference.json` 把游戏内 ID 对齐到可读文本，包含 273 颗星球 / 56 个星区 /
26 种生物群系 / 9 种环境危害 / 区域名称。

它的权威性依据是：参照表里的 `hash` 与实时载荷里的 `settingsHash`
**逐条严格相等**（273/273 已验证）。`settingsHash` 是星球跨战争稳定的身份标识，
站点自己也用它（线上代码里那张 `{WIDOWS_HARBOR: 2768073863, ...}` 枚举表）。

阵营编号也用同样方式验证过：把参照表的 `currentOwner` 与实时载荷的 `owner`
逐条比对，**273 颗星球 0 处不一致**，因此确定：

| race | 阵营 | 中文 |
|---|---|---|
| 1 | Humans | 超级地球 |
| 2 | Terminids | 终结族 |
| 3 | Automatons | 机器人 |
| 4 | Illuminate | 光能者 |

重建参照表（只在游戏新增星球后才需要）：

```bash
python scripts/refresh_reference.py          # 重新抓取并覆盖
python scripts/refresh_reference.py --check  # 只校验现有文件是否仍与实时载荷对齐
```

参照表是**一次性快照**——服务运行时**完全不会访问**它的来源。

### 根目录的 index 对照表

`data/reference.json` 是给程序读的；给人翻的版本在**项目根目录**：

| 文件 | 用途 |
|---|---|
| `INDEX_MAP.md` | 星球 index 对照表、星区→星球、按名称反查 index、按星区分组的 index 列表 |
| `planet_index.csv` | 同样内容的机器可读版（utf-8-sig，Excel 双击直接打开） |

```bash
python scripts/build_index_map.py     # 改了参照表后重新生成
```

两个文件都由生成器产出，**不要手改**——`tests/test_index_map.py` 会重算一遍并逐行比对，
不同步就直接失败。

#### ⚠️ 载荷里的 `sector` 整数不是 wiki 星区

这是最容易踩的坑，对照表里专门写了一节。实测：

| | wiki 星区（`planets[].sector`） | 载荷里的 `sector` 整数 |
|---|---|---|
| 取值 | 56 个名字（Altus / Sol / Valdis …） | 53 个整数 |
| 空间聚集度 | 紧密，成员半径中位数 **0.122** | 多数较紧，但 `sector 0` 半径 **0.926**、`sector 29` 达 1.144 |
| 一致性 | 一一对应 | **53 个里有 36 个与星区名冲突** |

`sector 0` 同时装着 Sol、Trigon、Rigel、Jin Xi、TBD 等散落全图的星球，是个兜底桶；
而 `Trigon` 这一个星区横跨 `sector` 0 / 32 / 46 / 48 / 49 五个整数。

对照表把两者分列（`星区` 与 `载荷sector`），**请按 `星区` 理解，不要拿整数当星区**。

### 效果 / 敌人变种名称（`data/effects.json`）

`planetActiveEffects[].galacticEffectId` 是一串数字，而 `galacticWarEffects` 里
只有哈希、没有文案。站点自己在 JS 里硬编码了两张 ES 枚举（`m1` / `Yt`），
`research/extract_effects.js` 会把它们提取出来：

```bash
node research/extract_effects.js
# -> data/effects.json：312 条 effect_ids + 90 条 presence_ids
```

由此得到的可读效果：

| ID | slug | label | category |
|---|---|---|---|
| 1188 | `fog_GloomM2` | Gloom M2 | 环境异常 |
| 1239 | `mark_JetBrigadeFactory` | Jet Brigade Factory | 设施 / 标记 |
| 1363 | `extract_PilotShortage8` | Pilot Shortage 8 | 撤离修正 |
| 1209 | `game_EAGLE_STORM` | EAGLE STORM | 战术行动 |

这份表是**可选**的：缺了它 API 照常工作，`active_effects` 退化成只给数字 ID。

---

## 7. 配置

全部通过环境变量覆盖，见 `hd2api/config.py`：

| 变量 | 默认 | 说明 |
|---|---|---|
| `HD2_HOST` / `HD2_PORT` | `127.0.0.1` / `8808` | 监听地址 |
| `HD2_POLLER` | `1` | 设为 `0` 关闭后台轮询 |
| `HD2_LIVE_REFRESH_SECONDS` | `40` | 主快照刷新间隔 |
| `HD2_HISTORY_REFRESH_SECONDS` | `300` | 星球历史刷新间隔 |
| `HD2_NEWS_REFRESH_SECONDS` | `900` | Steam 新闻刷新间隔 |
| `HD2_MAX_STALE_SECONDS` | `300` | 超过则 `/health` 报 `degraded` |
| `HD2_HTTP_TIMEOUT` / `HD2_HTTP_RETRIES` | `30` / `3` | 网络超时与重试 |
| `HD2_HP_PER_DIVER` | `0.0004443` | 每绝地潜兵影响力兜底值（HP/秒） |

---

## 8. 与官网数值的核对

### 8.1 在线人数分母：已确认一致 ✅

站点自己在 `live/extendedApiInformation/2days.json` 里记录了 `totalPlayerCount`
时间序列（约 15 分钟一个采样点，覆盖近两天）。直接拿它比对：

| | 数值 |
|---|---|
| 站点 `totalPlayerCount` | 99,138 |
| 本 API `totals.players_online` | 99,165 |
| 偏差 | **+0.027%** |

差异纯粹来自采样时差，**分母口径完全相同** —— 都是「所有星球 `players` 之和」。

### 8.2 分阵营在线人数：已确认一致 ✅

站点的 `playerCountHumans / playerCountTerminids / playerCountAutomatons / playerCountIlluminate`
用的**不是**「星球占有者」，而是「**正在对抗的敌人**」（线上代码里叫 `enemyRace`）：

```js
const ue = `playerCount${ro(ge.enemyRace)}`;
oe[ue] = (oe[ue] ?? 0) + ge.diversAmt;
```

即：己方星球被攻击时，防守的人算在**攻击方**名下，不算在 Humans 名下。
本 API 两个口径都给：

| 阵营（按交战对象） | 本 API | 站点 | 偏差 |
|---|---|---|---|
| automatons | 60,229 | 60,239 | 0.02% |
| terminids | 31,142 | 31,160 | 0.06% |
| illuminate | 5,699 | 5,704 | 0.09% |
| humans | 2,095 | 2,035 | 2.95% |

（`humans` 基数只有 2,000，所以相对偏差看起来大一些，绝对差 60 人。）

字段选择：

* `totals.players_by_enemy_faction` —— **与站点同口径**，推荐使用
* `totals.players_by_owner_faction` —— 按星球占有者归类的直觉口径

> ⚠️ 注意：早期版本的本 API 只有「按占有者」这一种口径，会把防守方 2 万多人
> 错误地算进 `Humans`。已修正并加了回归测试。

### 8.3 单颗星球：KARLIA 逐项对照 ✅

用户从官网卡片读到的值 vs 本 API（同一时刻）：

| 指标 | 官网 | 本 API | 差值 |
|---|---|---|---|
| 解放度 | 84.3270% | 84.3301% | **+0.0031pp** |
| 绝地潜兵影响力 %/h | 0.113 | 0.1087 | −0.0043 |
| 在线绝地潜兵 | 2232 | 2226 | −6 人 |

速率那 0.004 的差来自窗口错位——官网的窗口与我的窗口错开约一个采样间隔，
而相邻窗口的极差本身就有 0.0148（见 §4「为什么要有平滑值」）。
0.113 落在实测的 `0.1087 / 0.1096 / 0.1190 / 0.1199 / 0.1244` 区间之内。

**这条对照还确认了官网那个数字的口径**：卡片上的标签是
"Helldivers planetary control impact per hour"，即**绝地潜兵贡献**，不是净增速。

### 8.4 一键复现上述核对

```bash
python research/verify_both_frontends.py    # 人数口径 + 两个前端一致性
python research/compare_karlia.py           # 与官网读数的逐项对照（改 SITE 字典即可复用）
python research/diagnose_rate_windows.py KARLIA   # 展示窗口间的自然波动
python research/audit_metric_coverage.py    # 需求条目逐项覆盖
```

---

## 9. 需求条目覆盖情况

`research/audit_metric_coverage.py` 会逐条打印真实取值，当前结果 **29/29，缺失 0**：

| 需求 | API 字段 |
|---|---|
| 星区数量 / 星球数量 | `/api/v1/sectors`、`/api/v1/planets` |
| 区域内的潜兵在线数 | `planets[].regions[].players` |
| 区域控制度 | `planets[].regions[].controlled_percent` |
| 解放程度 / 解放度 | `planets[].liberation_percent` |
| 星球所属区域 | `planets[].sector` |
| 占领星球的阵营 | `planets[].owner` |
| 交战对象阵营 | `planets[].enemy_faction` |
| 星球环境参数 | `planets[].biome` + `planets[].hazards` |
| **敌人变种** | `planets[].active_effects[].label`（如 `Bot Cyborgs`、`Gloom M2`） |
| 解放战役进度 | `planets[].campaign.count` |
| 解放度每小时增长速度 | `planets[].liberation_rate.net_percent_per_hour`（净）；官网同口径见 `.impact_percent_per_hour` |
| 星球影响系数 / 敌人抵抗度 | `planets[].resistance.percent_per_hour` |
| 防御战役双方推进速度 | `defenses[].enemy_rate_percent_per_hour`、`.estimated_diver_rate_percent_per_hour` |
| 敌人入侵等级 | `defenses[].invasion_level`（`37/40`） |
| 需要的增援量 | `defenses[].required_divers` |
| 防御预测胜利 / 失败 | `defenses[].predicted_outcome_text` + `.diver_coverage_ratio` |
| 已完成 / 失败任务数 | `galaxy_statistics.missions_won` / `.missions_lost` |
| 总开火数 / 总命中数 | `galaxy_statistics.bullets_fired` / `.bullets_hit` |
| 开火/击中比 | `galaxy_statistics.shots_per_hit` + `.accuracy_percent` |
| 击杀/死亡比 | `galaxy_statistics.kill_death_ratio` |
| 三大敌对阵营击杀数 | `galaxy_statistics.kills` |
| 绝地潜兵死亡数 | `galaxy_statistics.deaths` |
| 意外阵亡数 | `galaxy_statistics.accidental_deaths` |
| 银河影响系数 | `war.galactic_impact_multiplier` |

---

## 10. 项目结构

```
helldiversbot/
├── run.py                        一键启动（--fastapi 切换前端）
├── INDEX_MAP.md                  ★ index 对照表（给人看的，生成物）
├── planet_index.csv              ★ 同上，机器可读（Excel 直接打开）
├── qqbot.md                      QQ 机器人的功能规格
├── bot/                          QQ 机器人（基于 botpy）
│   ├── qqbot.py                  入口：四类消息事件的接线
│   ├── commands.py               命令解析与回复生成（不依赖 botpy，可单测）
│   ├── hd2_api.py                战报 API 的异步客户端
│   ├── config.example.yaml       配置模板（真凭据放 config.yaml，已 gitignore）
│   └── README.md                 机器人用法
├── data/
│   ├── reference.json            静态参照表（273 星球 / 56 星区 / 生物群系 / 区域名）
│   ├── translations_zh.json      星球与星区的中文译名（**手写**，不会被覆盖）
│   └── effects.json              效果与敌人变种名称（402 条）
├── scripts/
│   ├── refresh_reference.py      重建/校验参照表
│   ├── build_index_map.py        生成根目录的 INDEX_MAP.md 与 planet_index.csv
│   ├── extract_translations.py   把 CSV 里手填的中文名抢救进 translations_zh.json
│   └── vendor_deps.py            绕开 pip 装 FastAPI 到 .deps/
├── hd2api/
│   ├── config.py                 配置（全部可用环境变量覆盖）
│   ├── httpclient.py             带重试/并发/降级的 HTTP 客户端
│   ├── sources.py                上游接口封装
│   ├── reference.py              参照表查询 + 阵营枚举 + 效果名解析
│   ├── normalize.py              ★ 核心：ID→文本、派生指标、快照组装
│   ├── textview.py               `?mode=pt` / `?mode=md` 的可读文本渲染（见 README_fancy.md）
│   ├── service.py                TTL 缓存 + 后台轮询 + 自动标定
│   ├── web.py                    路由 + 查询过滤 + OpenAPI + 文档页（标准库前端）
│   ├── asgi.py                   FastAPI 前端（复用 web.Handlers，可选）
│   └── __main__.py               命令行
├── tests/
│   ├── fixtures.py               离线夹具（各测试文件共用）
│   ├── test_normalize.py         58 项归一化测试
│   ├── test_web.py               45 项标准库 Web 层测试（真起 HTTP 服务）
│   ├── test_asgi.py              14 项 FastAPI 测试（纯 stdlib ASGI 调用，不需要 httpx）
│   ├── test_textview.py          47 项可读文本输出测试（逐字比对 README_fancy.md 的两套示例）
│   ├── test_qqbot.py             44 项 QQ 机器人测试（离线逻辑 + 真实 API 端到端）
│   ├── test_terminology.py       10 项术语一致性检查
│   └── test_index_map.py         19 项对照表同步检查 + 译名保护
└── research/                     反向工程记录与核对脚本
```

### 为什么两个前端不会漂移

`asgi.py` **不重写任何业务逻辑**——它从 `web.build_routes()` 取同一张路由表，
调用同一批 `web.Handlers` 方法，只是把 FastAPI 的请求适配成内部的 `Request`。
`tests/test_asgi.py::test_same_snapshot_served_by_both_frontends` 会实际起一个
标准库服务和一个 ASGI 应用，断言两者返回**逐字段相同**的数据。

---

## 11. 已知限制

- **`estimated` 速率是线性模型。** 游戏里每绝地潜兵影响力可能随星球大小、
  区域分割、玩家行为浮动。用 `liberation_rate.source` 区分实测与估算。
- **区域数据只覆盖正在打区域战的星球**（当前 41 颗），其余星球 `regions` 为空数组。
- **效果名是从压缩后的 JS 枚举还原的 slug**（`mark_JetBrigadeFactory` → `Jet Brigade Factory`），
  可读但不是官方文案；`category` 是按前缀推断的分类。
- **上游 `bulletsHit` 统计口径使命中率可能 >100%**（约 109.7%）。
  这是游戏自身计数器的特性，我们原样保留并额外用
  `accuracy_exceeds_100` 标出来，不做静默「修正」。
- **`revives` 字段上游恒为 0 或 2**，数据不可信，未做二次加工。
- **FastAPI 前端需要手动装依赖**：本机 pip 在沙箱里用不了（它写临时目录时被拒），
  因此 `scripts/vendor_deps.py` 自己解析 PyPI 并解压 wheel。标准库前端不受影响。
