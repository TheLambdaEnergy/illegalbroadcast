# research —— 反向工程记录

这里保存的是「**为什么指标是这么算的**」的证据链。`hd2api/normalize.py` 里的每个
派生公式都能在这里找到出处，将来上游改版时也能照着重新推导。

历史快照与线上 JS 包体积太大（约 14 MB），没有入库，用下面的脚本可以随时重新拉取。

## 1. 如何重新获取证据

```bash
# 拉取 4 个已知接口到 research/raw/
python research/fetch_evidence.py

# 递归爬取站点 JS chunk 并扫描出全部接口字符串
python research/scan_js.py

# 从 JS 包里定位并提取数据表（需要 Node.js）
node research/extract_tables.js
```

## 2. 已确认的接口清单

主快照（一次拿到 warInfo + warStatus + warStats + news + episodes，约 400 KB）：

```
https://helldiverscompanion.com/api/hell-divers-2-api/get-api-data-live
https://helldiverscompanion.com/api/hell-divers-2-api/get-api-data-beta   # 另一条通道
```

CDN —— 站点用两个主机名，**不要混用**（线上代码里分别是 `slowCDN` / `fastCDN`）：

```
slowCDN = https://cdn.helldiverscompanion.com/live
fastCDN = https://livedatacdn.helldiverscompanion.com/live

slowCDN/extendedApiInformation/2days.json        ← 全银河时间序列（总在线人数在这）
slowCDN/planets/{index}/recent.json
slowCDN/planetEvents/2days.json
slowCDN/planetRegions/recent.json
slowCDN/globalResources/recent.json
slowCDN/globalResources/2days.json
slowCDN/assignments/recent.json
slowCDN/warSummary/planets/{index}/recent.json
slowCDN/spaceStations/{id32}/2days.json
slowCDN/personalOrders/current.json
slowCDN/store/current.json
fastCDN/elections/current.json
fastCDN/freedomallianceradio/stats.json
```

其他：

```
https://helldiverscompanion.com/api/steam-api/news
```

接口清单是从站点 JS 里扫出来的。线上代码中：

```js
const H7 = ["live", "beta"], Qk = H7[0];
async function Ybe() {
  const e = Sz(), t = e || Qk;                 // Sz() 读 localStorage["API"]
  const i = await fetch(`/api/hell-divers-2-api/get-api-data-${t}`, {...});
}
```

`extendedApiInformation/2days.json` 是最有价值的一个补充：它给出站点自己记录的
`totalPlayerCount`、分阵营在线人数、`impactMultiplier` 和全部累计统计，
每约 15 分钟一个采样点、覆盖近两天。**这是校验在线人数口径的权威依据。**

## 3. 已确认的公式

全部来自线上包 `BImFknRy.js` / `2.CadSs0XM.js`。

```js
// 进度换算
function vw(r, e) { return (1 - r / e) * 100 }   // 解放度 %
function yw(r, e) { return r / e * 100 }

// 敌方抵抗度（%/h）：站点内部叫 healthPctRegenPerHour
get impactPctEnemy() {
  return this.isEventful
    ? Zt(3600 / (this.timeExpire - this.timeStart), 5)   // 防御战：按事件时长反推
    : Zt(this.healthPctRegenPerHour, 5);                 // 常规：regen/秒 换算成 %/h
}

// 绝地潜兵的贡献（%/h）—— 这就是官网卡片上显示的
// 「Helldivers planetary control impact per hour」
get impactPctDiver() {
  if (this.isAccessible && this.isProgressive) {
    if (this.isEventful) return this.healthPctDeltaPerHour;
    const i = this.healthPctRegenPerHour, r = -this.healthPctDeltaPerHour;
    return Math.max(r + i, 0);      // <- 关键：divers = -Δhealth + regen，且夹到非负
  } else return 0;
}

// 等价的另一种写法（用于校验）
get healthAmtImpactPerSecond(){ return this.healthAmtRegenPerSecond - this.healthAmtDeltaPerSecond }
get healthPctImpactPerHour(){ return this.healthAmtImpactPerHour / this.healthAmtMaximum }
```

**注意 `Math.max(..., 0)`**：官网那个数字**永远非负**，因为它是「绝地潜兵贡献」。
它不代表星球在变好——ZZANIAH PRIME 官网显示 `+0.88%/h`，实际净增速是 `-0.62%/h`。
本 API 两个都给：`impact_percent_per_hour`（同官网）与 `net_percent_per_hour`（真相）。

```js
// 敌人入侵等级
const current = Math.ceil(e.healthAmtCurrent / 5e4);
const max     = Math.floor(e.healthAmtMaximum / 5e4);

// 防御战守住所需速率（%/h）
get impactPctDiverRequired() {
  return this.isEventful
    ? (1 - this.progressPctDiver) / this.timeRemainAdj * 3600
    : this.impactPctEnemy;
}

// 每绝地潜兵影响力（站点也是实测的，不是常数）
get impactPctPerDiver() { return this.diversAmt > 0 ? this.impactPctDiver / this.diversAmt : 0 }
registerImpact() { dr.setImpactPerDiver(this.settingsHash, this.impactAmtDiver / this.diversAmt) }
```

### 单窗口噪声有多大

CDN 每约 15 分钟落一个点，**相邻窗口之间本身就能差 10% 以上**。
实测 KARLIA 连续四个窗口的绝地潜兵影响力：

```
0.1096   0.1190   0.1199   0.1244   %/h     极差 0.0148，相对 12.6%
```

所以拿单个窗口去和官网对数字，差 10% 属于窗口错位。
`hd2api/normalize.py` 里的 `empirical_windows()` + `smooth_windows()`
会把最近最多 1 小时的窗口汇总，得到稳定得多的值。
复现：`python research/diagnose_rate_windows.py KARLIA`

**注意 `vw` / `yw` 的符号**：`health` 代表**敌方掌控度**，所以
`dHealth/dt = regen - divers`，即 `divers = regen - dHealth/dt`。
第一版实现写成了 `divers = regen + dHealth/dt`，方向反了，已修正
（`tests/test_normalize.py::TestTrendAndFloorClamping` 是这条的回归测试）。

### 在线人数口径（本轮新查明）

站点的「总在线潜兵数」与「分阵营在线人数」：

```js
// 总数 = 所有星球 players 求和（B.playerTotal，喂给 dr.setDiversTotal）
dr.setDiversTotal(B.playerTotal)

// 分阵营用的是 enemyRace（正在对抗的敌人），不是星球占有者！
const ue = `playerCount${ro(ge.enemyRace)}`;
oe[ue] = (oe[ue] ?? 0) + ge.diversAmt;

// 星球上的占比
get diversPct(){ return this.diversAmt / this.diversTotal }

// enemyRace 的推导：正在被谁打，就算谁
get enemyRace(){ return this._state.attackingRace == Ji.Humans ? this._status.owner : this._state.attackingRace }

// 星球自身的占比（和 diversPct 不是一回事）
get diversPctPlanet(){ return 1 - this.diversPctAllRegions }
get diversPctNormalized(){ return this.diversMaximum ? this.diversAmt / this.diversMaximum : 0 }
// 其中 diversMaximum = 全银河人口最多的那颗星球（不是总数！）
let $ = 0; T.forEach(le => { le.diversAmt > $ && ($ = le.diversAmt) }); dr.setDiversMaximum($)
```

**结论**：`playerCountHumans` 不是「超级地球星球上的人」，而是
「当前没有敌人在打的地方的人」。己方星球被攻击时，那批防守者算在**攻击方**名下。
第一版实现按 `owner` 归类，导致 Humans 虚高 2 万多人，已修正。

实测比对（`research/verify_both_frontends.py`）：

```
automatons  本 API=60,229   站点=60,239   偏差 0.02%
terminids   本 API=31,142   站点=31,160   偏差 0.06%
illuminate  本 API= 5,699   站点= 5,704   偏差 0.09%
humans      本 API= 2,095   站点= 2,035   偏差 2.95%
```

## 4. 名称映射是怎么解决的

上游载荷**不含任何可读文本**：

```
planetInfos[].planetNameId32  = 0   （273 颗全是 0）
planetInfos[].planetBiomeId32 = 0   （273 颗全是 0）
planetInfos[].sector          = 整数
```

站点自己靠一张硬编码表渲染名称，`2.CadSs0XM.js` 里能提取到：

```js
const KT = ["SUPER EARTH","KLEN DAHTH II","PATHFINDER V","WIDOW'S HARBOR", ...]   // 260 项
const s1 = { WIDOWS_HARBOR: 2768073863, NEW_HAVEN: 158585041, ..., MARS: 1893896155 }
```

但 `KT` 只有 260 项（星球索引到 273），且 `s1` 是 slug→`settingsHash`。
最终采用的是社区镜像 `https://api.helldivers2.dev/api/v1/planets`：

* 它给出的 `hash` 与载荷里的 `settingsHash` **273/273 逐条相等**；
* 它的 `currentOwner` 与载荷里的 `owner` **273/273 逐条相等**，
  由此确定 `1=Humans, 2=Terminids, 3=Automatons, 4=Illuminate`；
* 它还额外提供了生物群系描述、环境危害、区域名称与尺寸。

这份数据被固化进 `data/reference.json`，运行时不再访问。

## 5. 排查过的坑

| 现象 | 结论 |
|---|---|
| `warStats.planets_stats` 里有 `planetIndex: -1337`、`-420` 这类记录 | 哨兵/垃圾数据，必须按 `index >= 0` 过滤 |
| `galaxy_stats.bulletsHit` > `bulletsFired`（命中率 109.7%） | 游戏自身计数器口径，不是算错；用 `accuracy_exceeds_100` 标记而非静默修正 |
| `galaxy_stats.revives` 恒为 0 或 2 | 上游字段不可信 |
| `warStatus.planetRegions[].regerPerSecond` | 上游**拼写就是错的**（少个 `n`），照原样解析 |
| `warStatus.spaceStations`（5 字段）与顶层 `live.spaceStations`（7 字段）并存 | 战术行动只在顶层，`activeEffectIds` 只在 `warStatus` 里，必须合并 |
| 最后一期重大指令没有 `endWarTime` | 只看 `start <= warTime <= end` 会漏掉进行中的指令；改为 `end is None` 也算进行中 |
| 星球 262 的官方名称是 `K` | 不是脱敏，游戏里真就叫 K（站点枚举里也有 `K: 1143730827`） |
| `diversPct` 与本 API 的 `player_share_percent` 曾对不上 | 站点的 `diversTotal` = 全星球 `players` 求和，与本 API 一致（实测偏差 0.027%）；用户看到的「3%」可能来自 `diversPctPlanet` 或 `diversPctNormalized` 这类**别的**占比，而星球卡片上的 `%` 具体是哪一个还没定论 |
| 分阵营在线人数曾严重不符 | 站点按 `enemyRace`（正在对抗的敌人）归类，不是按 `owner`；已修正 |
| `pip install` 在本机全部失败 | pip 下载元数据时要写 `tempfile.gettempdir()`，被文件沙箱拒绝。见 `scripts/vendor_deps.py` 的绕行方案 |
| 手动装 wheel 时装到了 `cp314t`（自由线程 ABI） | 普通构建的 CPython 导入会失败；`vendor_deps.py` 现在按 `Py_GIL_DISABLED` 过滤 ABI 标签 |
| `warInfo.planetInfos[].sector` 被当成星区 | **不是**。它是另一套更粗的空间划分：53 个整数里 36 个与星区名冲突，`sector 0` 半径 0.926 是兜底桶。wiki 星区要按坐标聚（中位半径 0.122）。见 `research/check_sector_index.py` |
| `data/reference.json` 里区域只有 84 颗星球有 | 正常。区域是**静态定义**，只有 211 条，恰好等于 `warInfo.planetRegions` 的 211 条；其余星球压根没有区域划分 |

## 6. 文件说明

入库的都是小体积的分析输出：

| 文件 | 内容 |
|---|---|
| `analysis/shape.txt` | live 载荷的整体结构树 + 关键字段分布（含「ID 被抹掉」的证据） |
| `analysis/js_scan2.txt` | 从全部 JS chunk 里扫出的接口与资源路径（**接口清单的出处**） |
| `analysis/js_scan.txt` | 早期一版扫描结果（HTML 里只有动态 `import()`，所以是空的） |
| `analysis/formula_hunt.txt` | `impactMultiplier` / `regenPerSecond` / `diversRequired` 的上下文 |
| `analysis/formula2.txt` | `impactPerDiver` / `libDiversNeededPct` 的上下文 |
| `analysis/formula3.txt` | `setImpactPerDiver` / `ENEMY INVASION LEVEL` 的上下文 |
| `analysis/name_hunt.txt` | 名称来源排查（`sectorName`、`planetNameId32`、大写字符串表） |
| `analysis/divers_total_hunt.txt` | `setDiversTotal` / `diversPct` / `diversMaximum` 的上下文 |
| `analysis/player_total_hunt.txt` | `playerTotal` / `enemyRace` / `filterCount` 的上下文 |
| `analysis/cdn_urls.txt` | 全部 CDN 端点与 `get*History*` 方法定义 |
| `analysis/tables_raw2.txt` | `KT` 名称数组及其周边表 |
| `analysis/tables_raw.txt` | 第一次定位 `KT` 时的原始上下文 |
| `analysis/enum_hunt.txt` | `s1`（slug → settingsHash）枚举的定位结果 |
| `analysis/samples.txt` | live 载荷各子对象的字段与样例 |
| `analysis/extract1.txt`、`analysis/extract_node.txt` | 提取 `KT` 数组的两次尝试（Python / Node） |
| `analysis/endpoint_samples.txt` | 本 API 各端点的真实返回样例 |

脚本：

| 文件 | 用途 |
|---|---|
| `fetch_evidence.py` | 重新拉取接口快照与线上 JS 包到 `raw/` |
| `scan_js.py` | 递归爬 JS 并扫描接口字符串、摘录关键实现片段 |
| `extract_tables.js` | 从 JS 里提取 `KT` / `s1` 等硬编码数据表（需 Node.js） |
| `extract_effects.js` | 提取 `m1` / `Yt` 效果枚举 → `data/effects.json`（需 Node.js） |
| `hunt_divers_total.js` | 排查在线人数分母与 `diversPct` 的定义 |
| `hunt_player_total.js` | 定位 `playerTotal` / `enemyRace` 的计算方式 |
| `hunt_cdn_urls.js` | 枚举全部 CDN 端点 |
| `probe_extended.py` | 拉取 `extendedApiInformation` 做人数口径比对 |
| `describe_shape.py` | 输出载荷结构树与字段分布（可直接读本地服务） |
| `audit_metric_coverage.py` | 逐条核对需求指标覆盖，打印真实取值 |
| `compare_karlia.py` | 拿官网读到的数字与本 API 逐项对照（改 `SITE` 字典即可复用） |
| `diagnose_rate_windows.py` | 展示相邻 15 分钟窗口的速率波动，判断差异是否只是窗口错位 |
| `verify_both_frontends.py` | 两个前端一致性 + 人数口径交叉验证 |
| `verify_terminology.py` | 确认译名统一后 API 的实际中文输出 |
| `check_sector_index.py` | 排查「载荷里的 sector 整数」与 wiki 星区的对应关系（结论：不是一回事） |
| `probe_sector_int.py` | 用坐标离散度证明 sector 整数是另一套空间划分，`sector 0` 是兜底桶 |
| `test_endpoints_fastapi.py` | FastAPI 前端的端点检查 |
| `test_endpoints.py` | 两个前端通用的端点检查（`--both` 一次查两个） |
| `check_wheel_tags.py` | 诊断：检查某个包在 cpXXX/win_amd64 上有没有可用 wheel |

