# 《Helldivers 2》Index 对照表

本文件由 `python scripts/build_index_map.py` 从 `data/reference.json` 生成，**不要手改**。

* 参照表生成时间：`2026-09-13T17:07:43.707018Z`
* 战争 ID：`801`　星球 **273** 颗　星区 **56** 个
* 机器可读版本：`planet_index.csv`
* 中文译名 14 个星球 / 5 个星区，来自 `data/translations_zh.json`（手写，不会被覆盖）

---

## 0. 三个容易混淆的「index」

| 名称 | 出现在哪 | 含义 |
|---|---|---|
| **星球 index** | `warInfo.planetInfos[].index`、`warStatus.planetStatus[].index`、本 API 的 `planets[].index` | 0–273 的连续编号，**本表的主键**。缺 263 |
| **settingsHash** | `warInfo.planetInfos[].settingsHash` | 星球跨战争稳定的身份标识。站点自己用它（线上包里的 `{WIDOWS_HARBOR: 2768073863, ...}` 枚举） |
| **载荷里的 `sector` 整数** | `warInfo.planetInfos[].sector` | ⚠️ **不是 wiki 星区**，见下 |

### ⚠️ 载荷里的 `sector` 整数 ≠ wiki 星区

两者是**两套不同的划分**，实测：

| | wiki 星区（本表的 `sector` 字段） | 载荷里的 `sector` 整数 |
|---|---|---|
| 取值个数 | 56 个名字 | 53 个整数 |
| 空间聚集度 | 紧密，成员半径中位数 **0.122** | 多数较紧，但 `sector 0` 半径 **0.926**、`sector 29` 达 1.144 |
| 一致性 | 一一对应 | **53 个里有 36 个与星区名冲突** |

例：`sector 0` 同时包含 Sol、Trigon、Rigel、Jin Xi、TBD 等散落全图的星球，是个兜底桶；
而 `Trigon` 这一个星区横跨 `sector` 0 / 32 / 46 / 48 / 49 五个整数。

本表两个都列（`载荷sector` 列），**请按 `星区` 列理解，不要用整数当星区**。

---

## 1. 星球 index 对照表

共 273 颗，按 index 升序。

| index | 星球 | 中文名 | 星区 | 星区中文 | 载荷sector | settingsHash | 生物群系 | 环境危害 | 最大血量 | 初始阵营 | 区域 |
|---:|---|---|---|---|---:|---|---|---|---:|---|---|
| 0 | **SUPER EARTH** | 超级地球 | Sol | 太阳系 | 0 | `897386910` | Super Earth / 超级地球 | — | 1,000,000 | 超级地球 | EAGLEOPOLIS（巨型城市） / ADMINISTRATIVE CENTER 02（巨型城市） / REMEMBRANCE（巨型城市） / YORK SUPREME（巨型城市） / PORT MERCY（巨型城市） / PROSPERITY CITY（巨型城市） / EQUALITY-ON-SEA（巨型城市） |
| 1 | **KLEN DAHTH II** | 克伦达斯II | Altus | 阿尔特斯 | 1 | `3621417917` | Desert Dunes / 沙漠沙丘 | 沙暴 | 1,000,000 | 超级地球 | — |
| 2 | **PATHFINDER V** | 开拓者V | Altus | 阿尔特斯 | 1 | `2543303604` | Plains / 平原 | — | 1,000,000 | 超级地球 | — |
| 3 | **WIDOW'S HARBOR** | 寡妇港 | Altus | 阿尔特斯 | 1 | `2768073863` | Moon / 月球 | 流星风暴 | 1,000,000 | 超级地球 | — |
| 4 | **NEW HAVEN** | 纽黑文 | Altus | 阿尔特斯 | 1 | `158585041` | Ionic Jungle / 离子丛林 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 5 | **PILEN V** | 皮伦V | Altus | 阿尔特斯 | 1 | `1008084099` | Desert Cliffs / 沙漠峭壁 | 地震活动 | 1,000,000 | 超级地球 | — |
| 6 | **HYDROFALL PRIME** | 水瀑主星 | Barnard | 巴纳德 | 2 | `167872110` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,000,000 | 超级地球 | — |
| 7 | **ZEA RUGOSIA** | 泽亚鲁戈西亚 | Ferris | 费里斯 | 2 | `1138804949` | Desert Cliffs / 沙漠峭壁 | 地震活动 | 1,700,000 | 超级地球 | NEW COB（城镇） / GENE（定居点） / STARPASS（城市） |
| 8 | **DARROWSPORT** | 达罗斯波特 | Barnard | 巴纳德 | 2 | `3550298780` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 1,000,000 | 超级地球 | — |
| 9 | **FORNSKOGUR II** | 福恩斯科古尔II | Barnard | 巴纳德 | 2 | `1025193891` | Basic Swamp / 原始沼泽 | — | 1,000,000 | 超级地球 | — |
| 10 | **MIDASBURG** | 弥达斯堡 | Barnard | 巴纳德 | 2 | `2767954873` | Tundra / 苔原 | — | 1,000,000 | 超级地球 | — |
| 11 | **CERBERUS IIIc** | 刻耳柏洛斯IIIc | Cancri | 康谷利伊 | 3 | `688773671` | Desert Cliffs / 沙漠峭壁 | 地震活动 | 1,000,000 | 超级地球 | — |
| 12 | **PROSPERITY FALLS** | 繁荣瀑布 | Cancri | 康谷利伊 | 3 | `160818366` | Ionic Jungle / 离子丛林 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 13 | **OKUL VI** | — | Gothmar | — | 4 | `2877873656` | Icy Glaciers / 冰川 | 暴风雪 | 1,000,000 | 超级地球 | — |
| 14 | **MARTYR'S BAY** | — | Cantolus | — | 5 | `1529228469` | Boneyard / 骸骨场 | — | 1,000,000 | 超级地球 | — |
| 15 | **FREEDOM PEAK** | — | Cantolus | — | 5 | `3749877391` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 16 | **FORT UNION** | — | Orion | — | 5 | `4254371037` | Plains / 平原 | — | 1,000,000 | 超级地球 | OTARU'S PLEDGE（城镇） / XIAMEN ANEW（城市） / MUNITION CITY（城镇） / NEW HOPE CITY（巨型城市） |
| 17 | **KELVINOR** | — | Cantolus | — | 5 | `2273175182` | Icy Glaciers / 冰川 | 暴风雪 | 1,000,000 | 超级地球 | — |
| 18 | **WRAITH** | — | Idun | — | 6 | `3088889549` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 1,000,000 | 超级地球 | — |
| 19 | **IGLA** | — | Kelvin | — | 7 | `768352347` | Boneyard / 骸骨场 | — | 1,000,000 | 超级地球 | — |
| 20 | **NEW KIRUNA** | — | Kelvin | — | 7 | `1299274778` | Icy Glaciers / 冰川 | 暴风雪 | 1,000,000 | 超级地球 | — |
| 21 | **FORT JUSTICE** | — | Kelvin | — | 7 | `3992185257` | Ethereal Jungle / 空灵丛林 | — | 1,000,000 | 超级地球 | — |
| 22 | **ZEGEMA PARADISE** | — | Kelvin | — | 7 | `160106209` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,000,000 | 超级地球 | — |
| 23 | **PROVIDENCE** | — | Iptus | — | 8 | `1257502272` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 24 | **PRIMORDIA** | — | Iptus | — | 8 | `2862366365` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,000,000 | 超级地球 | — |
| 25 | **SULFURA** | — | Celeste | — | 9 | `1812451556` | Ethereal Jungle / 空灵丛林 | — | 1,000,000 | 超级地球 | — |
| 26 | **NUBLARIA I** | — | Celeste | — | 9 | `4068066596` | Haunted Swamp / 阴魂沼泽 | — | 1,000,000 | 超级地球 | — |
| 27 | **KRAKATWO** | — | Celeste | — | 9 | `2585302931` | Boneyard / 骸骨场 | — | 1,000,000 | 超级地球 | — |
| 28 | **VOLTERRA** | — | Korpus | — | 9 | `3650236983` | Plains / 平原 | — | 2,000,000 | 超级地球 | SCARLET HAVEN（城镇） / EDWARD'S GRAVE（城镇） / LIGHT-OF-LIBERTY（巨型城市） |
| 29 | **CRUCIBLE** | — | Korpus | — | 10 | `410562438` | Tundra / 苔原 | — | 2,500,000 | 超级地球 | KURRI KURRI（定居点） / ANNWN（城镇） / AGARTHA（巨型城市） / PROMINENCE（巨型城市） |
| 30 | **VEIL** | — | Barnard | 巴纳德 | 2 | `3538905431` | Deadlands / 死地 | — | 1,000,000 | 超级地球 | — |
| 31 | **MARRE IV** | — | Barnard | 巴纳德 | 2 | `529527934` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,000,000 | 超级地球 | — |
| 32 | **FORT SANCTUARY** | — | Cancri | 康谷利伊 | 3 | `3945891756` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 超级地球 | NEW YEARNING CITY（巨型城市） |
| 33 | **SEYSHEL BEACH** | — | Cancri | 康谷利伊 | 3 | `3266374354` | Ethereal Jungle / 空灵丛林 | — | 2,300,000 | 超级地球 | ACCOUNTANT GRAEBER（城镇） / BEACHVIEW（定居点） / THE VILLAS（城市） / NEW ALEXANDRIA（巨型城市） |
| 34 | **HELLMIRE** | — | Mirin | — | 3 | `3551496165` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,000,000 | 终结族 | — |
| 35 | **EFFLUVIA** | — | Cancri | 康谷利伊 | 3 | `2640422831` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,000,000 | 超级地球 | — |
| 36 | **SOLGHAST** | — | Gothmar | — | 4 | `3407890530` | Haunted Swamp / 阴魂沼泽 | — | 1,700,000 | 超级地球 | LUXE POINT（定居点） / SHADY OAKS（城镇） / DOSTOINSTVO（城市） |
| 37 | **DILUVIA** | — | Gothmar | — | 4 | `760056919` | Tundra / 苔原 | — | 2,000,000 | 超级地球 | GRACIOUS LIBERTY（城镇） / LUSCIOUS LIBERTY（城市） / COUNCILLOR RORA（城市） |
| 38 | **VIRIDIA PRIME** | — | Cantolus | — | 5 | `1831450049` | Desert Dunes / 沙漠沙丘 | 沙暴 | 1,000,000 | 超级地球 | — |
| 39 | **OBARI** | — | Cantolus | — | 5 | `298165685` | Plains / 平原 | — | 1,000,000 | 超级地球 | — |
| 40 | **MYRADESH** | — | Idun | — | 6 | `2146401321` | Desert Cliffs / 沙漠峭壁 | 地震活动 | 1,000,000 | 超级地球 | — |
| 41 | **ATRAMA** | — | Idun | — | 6 | `3508924100` | Haunted Swamp / 阴魂沼泽 | — | 1,000,000 | 超级地球 | — |
| 42 | **EMERIA** | — | Kelvin | — | 7 | `2243203717` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,600,000 | 超级地球 | NEW ASPIRATION CITY（巨型城市） |
| 43 | **BARABOS** | — | Marspira | — | 18 | `1678797801` | Basic Swamp / 原始沼泽 | — | 1,000,000 | 超级地球 | — |
| 44 | **FENMIRE** | — | Marspira | — | 18 | `3404343820` | Plains / 平原 | — | 2,400,000 | 超级地球 | BRAWFERMLAND（城镇） / NEW ABERDEEN（巨型城市） / SAORSA GLEN（巨型城市） |
| 45 | **MASTIA** | — | Marspira | — | 19 | `2969736642` | Desert Dunes / 沙漠沙丘 | 沙暴 | 1,000,000 | 超级地球 | — |
| 46 | **SHALLUS** | — | Talus | — | 19 | `1438199726` | Ethereal Jungle / 空灵丛林 | — | 1,000,000 | 超级地球 | — |
| 47 | **KRAKABOS** | — | Iptus | — | 8 | `2013504640` | Basic Swamp / 原始沼泽 | — | 1,000,000 | 超级地球 | — |
| 48 | **IRIDICA** | — | Iptus | — | 8 | `2525961073` | Ethereal Jungle / 空灵丛林 | — | 1,000,000 | 超级地球 | — |
| 49 | **AZTERRA** | — | Orion | — | 20 | `2151164116` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,000,000 | 超级地球 | — |
| 50 | **AZUR SECUNDUS** | — | Sten | — | 20 | `3265310936` | Desert Cliffs / 沙漠峭壁 | 地震活动 | 1,000,000 | 终结族 | — |
| 51 | **IVIS** | — | Celeste | — | 9 | `4148701638` | Basic Swamp / 原始沼泽 | — | 1,000,000 | 超级地球 | — |
| 52 | **SLIF** | — | Celeste | — | 9 | `1756822119` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 1,000,000 | 超级地球 | — |
| 53 | **CARAMOOR** | — | Korpus | — | 10 | `438925458` | Desert Dunes / 沙漠沙丘 | 沙暴 | 2,200,000 | 超级地球 | LEMURIA RISING（城市） / PIONEER'S DREAM（城市） / BASE CAMP 8（城市） |
| 54 | **KHARST** | — | Gallux | — | 11 | `4190033207` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 55 | **EUKORIA** | — | Morgon | — | 12 | `3951456049` | Boneyard / 骸骨场 | — | 1,000,000 | 超级地球 | — |
| 56 | **MYRIUM** | — | Morgon | — | 12 | `207323189` | Rocky Canyons / 岩石峡谷 | 地震活动 | 2,000,000 | 超级地球 | PILOT'S BERTH（城市） / PLETHORA（城镇） / ANTBOOT（城市） |
| 57 | **KERTH SECUNDUS** | — | Rictus | — | 13 | `3674393208` | Tundra / 苔原 | — | 2,000,000 | 超级地球 | SCHOLAR'S MOOR（城镇） / BLESTRAIL（城镇） / HILDOARA CENTRAL（巨型城市） |
| 58 | **PARSH** | — | Rictus | — | 13 | `430094434` | Basic Swamp / 原始沼泽 | — | 2,000,000 | 超级地球 | PORUGU（城市） / PADOSAN（巨型城市） |
| 59 | **REAF** | — | Saleria | — | 14 | `1018677806` | Plains / 平原 | — | 1,000,000 | 超级地球 | — |
| 60 | **IRULTA** | — | Saleria | — | 14 | `2414771368` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,700,000 | 超级地球 | RECON HEIGHTS（定居点） / SILO A（城镇） / VOTER'S FALLOW（城市） |
| 61 | **EMORATH** | — | Meridian | — | 15 | `635122119` | Ethereal Jungle / 空灵丛林 | — | 1,900,000 | 超级地球 | FARMHANDSTOWN（城镇） / FORT BOUNTY（定居点） / FUTURIA（巨型城市） |
| 62 | **ILDUNA PRIME** | — | Meridian | — | 15 | `3508592390` | Tundra / 苔原 | — | 1,000,000 | 超级地球 | — |
| 63 | **MAW** | — | Idun | — | 6 | `4056948497` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,000,000 | 超级地球 | — |
| 64 | **MERIDIA** | — | Umlaut | — | 17 | `215016124` | Supercolony / 超级虫巢 | — | 1,000,000 | 终结族 | — |
| 65 | **BOREA** | — | Sagan | — | 17 | `3293929397` | Icy Glaciers / 冰川 | 暴风雪 | 1,000,000 | 超级地球 | — |
| 66 | **CURIA** | — | Marspira | — | 18 | `1750606702` | Moon / 月球 | 流星风暴 | 1,000,000 | 超级地球 | — |
| 67 | **TARSH** | — | Marspira | — | 18 | `3882819373` | Haunted Swamp / 阴魂沼泽 | — | 1,300,000 | 超级地球 | FORTITUDE（定居点） / FREEDOM'S TORCH（定居点） / FEARLESS HOLLOW（定居点） |
| 68 | **SHELT** | — | Talus | — | 18 | `1223630977` | Tundra / 苔原 | — | 1,000,000 | 超级地球 | — |
| 69 | **IMBER** | — | Talus | — | 19 | `2115544264` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,000,000 | 超级地球 | — |
| 70 | **BLISTICA** | — | Gellert | — | 8 | `4206815834` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,000,000 | 超级地球 | — |
| 71 | **RATCH** | — | Iptus | — | 8 | `2898292715` | Haunted Swamp / 阴魂沼泽 | — | 1,000,000 | 超级地球 | — |
| 72 | **JULHEIM** | — | Nanos | — | 31 | `922433838` | Icy Glaciers / 冰川 | 暴风雪 | 1,600,000 | 超级地球 | FROSTOWN（巨型城市） |
| 73 | **VALGAARD** | — | Iptus | — | 8 | `3238002446` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 74 | **ARKTURUS** | — | Arturion | — | 20 | `670993741` | Icy Glaciers / 冰川 | 暴风雪 | 1,000,000 | 超级地球 | — |
| 75 | **ESKER** | — | Falstaff | — | 20 | `2729833133` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 1,000,000 | 超级地球 | — |
| 76 | **TERREK** | — | Orion | — | 20 | `910588397` | Moon / 月球 | 流星风暴 | 1,000,000 | 超级地球 | — |
| 77 | **CIRRUS** | — | Orion | — | 20 | `2112907641` | Deadlands / 死地 | — | 1,000,000 | 超级地球 | — |
| 78 | **CRIMSICA** | — | Draco | — | 21 | `1886266372` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,500,000 | 终结族 | LIL'OME（定居点） / LLANFAIRPWLLGWYNGYLLGOGERYCHWYRNDROBWLLLLANTYSILIOGOGOGOCH II（城市） |
| 79 | **HEETH** | — | Orion | — | 21 | `1391690878` | Icy Glaciers / 冰川 | 暴风雪 | 1,000,000 | 终结族 | — |
| 80 | **VELD** | — | Orion | — | 22 | `3659340575` | Ionic Jungle / 离子丛林 | 离子风暴 | 1,800,000 | 超级地球 | CLE ELUM REDIVIVA（城镇） / LAELIA（巨型城市） |
| 81 | **ALTA V** | — | Korpus | — | 22 | `572365311` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,300,000 | 超级地球 | PORTE LIBERTÉ（城镇） / UNDERVATTEN（定居点） |
| 82 | **URSICA XI** | — | Borgus | — | 10 | `4009717368` | Ethereal Jungle / 空灵丛林 | — | 1,600,000 | 超级地球 | NEW KATHMANDU（城镇） / PO'S RAVENNA（城市） |
| 83 | **INARI** | — | Korpus | — | 10 | `2623879324` | Boneyard / 骸骨场 | — | 1,000,000 | 超级地球 | — |
| 84 | **SKAASH** | — | Ursa | — | 24 | `1076755284` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 1,000,000 | 超级地球 | — |
| 85 | **MORADESH** | — | Celeste | — | 24 | `912379297` | Desert Dunes / 沙漠沙丘 | 沙暴 | 1,000,000 | 超级地球 | — |
| 86 | **RASP** | — | Gallux | — | 11 | `2598991571` | Moon / 月球 | 流星风暴 | 1,000,000 | 超级地球 | — |
| 87 | **BASHYR** | — | Gallux | — | 11 | `49391513` | Haunted Swamp / 阴魂沼泽 | — | 1,000,000 | 超级地球 | — |
| 88 | **REGNUS** | — | Morgon | — | 12 | `2299441253` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,800,000 | 超级地球 | PEOPLE'S HAND（城镇） / TOPSOIL（城镇） / HUMAN WILL（城市） |
| 89 | **MOG** | — | Morgon | — | 12 | `2695815635` | Icy Glaciers / 冰川 | 暴风雪 | 1,000,000 | 超级地球 | — |
| 90 | **VALMOX** | — | Rictus | — | 13 | `1922612740` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,900,000 | 超级地球 | REBELSGRAVE（定居点） / REFORMED-BY-TRUTH（城市） / OBEDIENCE（城市） |
| 91 | **IRO** | — | Rictus | — | 13 | `3172148623` | Haunted Swamp / 阴魂沼泽 | — | 1,000,000 | 超级地球 | — |
| 92 | **GRAFMERE** | — | Rictus | — | 13 | `3602852408` | Boneyard / 骸骨场 | — | 2,100,000 | 超级地球 | GRAFSART（城市） / GRAFSWALLIT（定居点） / GRAFSEAD（巨型城市） |
| 93 | **NEW STOCKHOLM** | — | Hanzo | — | 13 | `3515684391` | Icy Glaciers / 冰川 | 暴风雪 | 1,000,000 | 超级地球 | — |
| 94 | **OASIS** | — | Rictus | — | 13 | `997855239` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,400,000 | 超级地球 | RESPITE（城市） |
| 95 | **GENESIS PRIME** | — | Rictus | — | 13 | `910436923` | Ionic Jungle / 离子丛林 | 离子风暴 | 1,600,000 | 超级地球 | MALLSTRIP NODES（城镇） / BIRTH（城市） |
| 96 | **OUTPOST 32** | — | Saleria | — | 14 | `2306843160` | Desert Dunes / 沙漠沙丘 | 沙暴 | 1,000,000 | 超级地球 | — |
| 97 | **CALYPSO** | — | Saleria | — | 14 | `4011448258` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,000,000 | 超级地球 | — |
| 98 | **ELYSIAN MEADOWS** | — | Guang | — | 28 | `3533355425` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 99 | **SANGIS** | — | Guang | — | 28 | `104621771` | Deciduous Autumn Forest / 秋色落叶林 | — | 1,000,000 | 超级地球 | — |
| 100 | **TRANDOR** | — | Sten | — | 29 | `3515299681` | Tundra / 苔原 | — | 1,900,000 | 终结族 | NYA SKELLEFTEA（城市） / ÖDESHÖGRE（定居点） / GOTHENBURG III（城市） |
| 101 | **EAST IRIDIUM TRADING BAY** | — | Tarragon | — | 29 | `3115954791` | Basic Swamp / 原始沼泽 | — | 1,000,000 | 超级地球 | — |
| 102 | **LIBERTY RIDGE** | — | Meridian | — | 15 | `1017957570` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 超级地球 | VANQUISHMENT（定居点） / FREECREST（城市） |
| 103 | **BALDRICK PRIME** | — | Meridian | — | 15 | `1398996417` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,000,000 | 超级地球 | — |
| 104 | **THE WEIR** | — | Theseus | — | 16 | `701410047` | Plains / 平原 | — | 1,000,000 | 超级地球 | — |
| 105 | **KUPER** | — | Theseus | — | 16 | `2344219187` | Ionic Jungle / 离子丛林 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 106 | **OSLO STATION** | — | Sagan | — | 17 | `1496025116` | Boneyard / 骸骨场 | — | 1,000,000 | 超级地球 | — |
| 107 | **PÖPLI IX** | — | Xzar | — | 17 | `696145979` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,600,000 | 超级地球 | RESILIENCE（城镇） / HOT GATES（城市） |
| 108 | **GUNVALD** | — | Sagan | — | 31 | `435094671` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 109 | **DOLPH** | — | Nanos | — | 31 | `2131959183` | Moon / 月球 | 流星风暴 | 1,000,000 | 超级地球 | — |
| 110 | **BEKVAM III** | — | Nanos | — | 31 | `412801448` | Ethereal Jungle / 空灵丛林 | — | 1,600,000 | 超级地球 | CONVENIENCE（城镇） / FIREFLY MEADOWS（城市） |
| 111 | **DUMA TYR** | — | Nanos | — | 31 | `255676170` | Tundra / 苔原 | — | 1,000,000 | 超级地球 | — |
| 112 | **VERNEN WELLS** | — | Hydra | — | 32 | `2442155408` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,500,000 | 超级地球 | BLACKVEIN MINES（定居点） / BENEVOLENCE（城镇） / ANNE'S VIGIL（城镇） |
| 113 | **AESIR PASS** | — | Hydra | — | 32 | `3407029244` | Deadlands / 死地 | — | 1,000,000 | 超级地球 | — |
| 114 | **AURORA BAY** | — | Valdis | — | 19 | `975759959` | Tundra / 苔原 | — | 1,600,000 | 超级地球 | BATU BELIG（城市） / EAGLEMOUNT（城镇） |
| 115 | **PENTA** | — | Lacaille | — | 19 | `101741274` | Deadlands / 死地 | — | 1,000,000 | 超级地球 | — |
| 116 | **GAELLIVARE** | — | Talus | — | 19 | `2654907023` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,700,000 | 超级地球 | VÁHTJER（定居点） / MALMBERGET（巨型城市） |
| 117 | **VOG-SOJOTH** | — | Tanis | — | 19 | `2580049274` | Icy Glaciers / 冰川 | 暴风雪 | 1,200,000 | 超级地球 | HAERSTVIK（城镇） |
| 118 | **KIRRIK** | — | Arturion | — | 36 | `612402065` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,000,000 | 超级地球 | — |
| 119 | **MORTAX PRIME** | — | Arturion | — | 36 | `248400433` | Desert Cliffs / 沙漠峭壁 | 地震活动 | 1,000,000 | 超级地球 | — |
| 120 | **WILFORD STATION** | — | Arturion | — | 36 | `1423930789` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 1,000,000 | 超级地球 | — |
| 121 | **PIONEER II** | — | Arturion | — | 36 | `429955586` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,000,000 | 超级地球 | — |
| 122 | **ERSON SANDS** | — | Falstaff | — | 37 | `137703244` | Desert Cliffs / 沙漠峭壁 | 地震活动 | 1,000,000 | 超级地球 | — |
| 123 | **SOCORRO III** | — | Falstaff | — | 37 | `1156965013` | Haunted Swamp / 阴魂沼泽 | — | 1,000,000 | 超级地球 | — |
| 124 | **BORE ROCK** | — | Falstaff | — | 20 | `2435651414` | Basic Swamp / 原始沼泽 | — | 1,000,000 | 超级地球 | — |
| 125 | **FENRIR III** | — | Umlaut | — | 20 | `2875368439` | Moon / 月球 | 流星风暴 | 2,000,000 | 终结族 | LOKAHEIM（城镇） / PSEUDOTOPIA（城镇） / FAMEWOLF PEAK（巨型城市） |
| 126 | **TURING** | — | Umlaut | — | 21 | `2706883571` | Ethereal Jungle / 空灵丛林 | — | 2,000,000 | 终结族 | CHATOYANT（城市） / CARBONDALE（城镇） / PERIWINKLE MILLS（城市） |
| 127 | **ANGEL'S VENTURE** | — | Orion | — | 21 | `2003553249` | Tundra / 苔原 | — | 1,000,000 | 终结族 | — |
| 128 | **DARIUS II** | — | Borgus | — | 22 | `2658926073` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 1,400,000 | 超级地球 | BUJU（城市） |
| 129 | **ACAMAR IV** | — | Jin Xi | — | 39 | `1231076923` | Plains / 平原 | — | 1,500,000 | 超级地球 | DEMOCRACY ALWAYS（定居点） / ERIDANI（城市） |
| 130 | **ACHERNAR SECUNDUS** | — | Borgus | — | 23 | `984145086` | Plains / 平原 | — | 2,000,000 | 超级地球 | CURRENCY（城镇） / NEW NEWTONVILLE（城市） / OL' OLDHAM（城市） |
| 131 | **ACHIRD III** | — | Borgus | — | 23 | `3921453955` | Rocky Canyons / 岩石峡谷 | 地震活动 | 2,000,000 | 超级地球 | TIMELY（城镇） / APPROVAL CITY（城市） / OLD BRANCH（城市） |
| 132 | **ACRAB XI** | — | Ursa | — | 24 | `3215655918` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 133 | **ACRUX IX** | — | Ursa | — | 24 | `997215371` | Boneyard / 骸骨场 | — | 1,000,000 | 超级地球 | — |
| 134 | **ACUBENS PRIME** | — | Gallux | — | 11 | `2282459618` | Ethereal Jungle / 空灵丛林 | — | 1,000,000 | 超级地球 | — |
| 135 | **ADHARA** | — | Gallux | — | 11 | `1937725917` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,500,000 | 超级地球 | TRAITOR'S END（定居点） / STRENGTH（城市） |
| 136 | **AFOYAY BAY** | — | Gallux | — | 11 | `3715077297` | Plains / 平原 | — | 1,000,000 | 超级地球 | — |
| 137 | **AIN-5** | — | Hanzo | — | 26 | `4017257734` | Deadlands / 死地 | — | 1,000,000 | 超级地球 | — |
| 138 | **ALAIRT III** | — | Hanzo | — | 26 | `1534729714` | Ionic Jungle / 离子丛林 | 离子风暴 | 2,200,000 | 超级地球 | GREATER STOROUSE（城镇） / NEW STOROUSE（城镇） / SHED（城镇） / FREE TRADE（巨型城市） |
| 139 | **ALAMAK VII** | — | Hanzo | — | 26 | `3213455987` | Ethereal Jungle / 空灵丛林 | — | 2,300,000 | 超级地球 | KESUMA（城镇） / UNGU（城市） / NO COMPOUND（定居点） / FILIBUSTER（巨型城市） |
| 140 | **ALARAPH** | — | Akira | — | 27 | `2830340410` | Deadlands / 死地 | — | 1,800,000 | 超级地球 | PERMACURIS（城市） / HANGAR 6（城市） |
| 141 | **ALATHFAR XI** | — | Akira | — | 27 | `1297056046` | Icy Glaciers / 冰川 | 暴风雪 | 2,200,000 | 超级地球 | Region 0（城市） / WORKSONG（城镇） / SEVERITY（巨型城市） |
| 142 | **ANDAR** | — | Akira | — | 27 | `1526977116` | Tundra / 苔原 | — | 1,600,000 | 超级地球 | NEW TOKYO（巨型城市） |
| 143 | **ASPEROTH PRIME** | — | Akira | — | 27 | `770159872` | Basic Swamp / 原始沼泽 | — | 1,800,000 | 超级地球 | ASPEN HILLS（城市） / MEGACORPUS（城市） |
| 144 | **BELLATRIX** | — | Guang | — | 28 | `232742202` | Plains / 平原 | — | 1,000,000 | 超级地球 | — |
| 145 | **BOTEIN** | — | Guang | — | 28 | `784275392` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 1,000,000 | 超级地球 | — |
| 146 | **OSUPSAM** | — | Tarragon | — | 29 | `1986037000` | Desert Dunes / 沙漠沙丘 | 沙暴 | 1,000,000 | 超级地球 | — |
| 147 | **BRINK-2** | — | Tarragon | — | 29 | `2935376141` | Ionic Jungle / 离子丛林 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 148 | **BUNDA SECUNDUS** | — | Tarragon | — | 29 | `3228999359` | Tundra / 苔原 | — | 1,000,000 | 超级地球 | — |
| 149 | **CANOPUS** | — | Tarragon | — | 29 | `3482441182` | Desert Cliffs / 沙漠峭壁 | 地震活动 | 1,000,000 | 超级地球 | — |
| 150 | **CAPH** | — | Theseus | — | 16 | `3480296110` | Basic Swamp / 原始沼泽 | — | 2,200,000 | 超级地球 | EASTCLEFT（城市） / KINABATANGAN（城市） / DOWNPOUR（城市） |
| 151 | **CASTOR** | — | Theseus | — | 16 | `1043181` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,000,000 | 超级地球 | — |
| 152 | **DURGEN** | — | Severin | — | 31 | `572242261` | Desert Dunes / 沙漠沙丘 | 沙暴 | 1,000,000 | 机器人 | — |
| 153 | **DRAUPNIR** | — | Xzar | — | 31 | `1192040123` | Plains / 平原 | — | 1,800,000 | 超级地球 | EIGHTRINGS（城市） / BROKER'S WEALTH（城市） |
| 154 | **MORT** | — | Xzar | — | 31 | `457558822` | Deadlands / 死地 | — | 1,400,000 | 超级地球 | SAPPHIRE LAKE（城市） |
| 155 | **INGMAR** | — | Xzar | — | 31 | `2655630774` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,800,000 | 超级地球 | FORT SANGUINE（定居点） / KNIGHT'S HONOR（定居点） / SEVENSEAL（巨型城市） |
| 156 | **CHARBAL-VII** | — | Andromeda | — | 33 | `3531149629` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 2,000,000 | 超级地球 | UTOPIA VAREN（定居点） |
| 157 | **CHARON PRIME** | — | Andromeda | — | 32 | `2007360508` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 158 | **CHOEPESSA IV** | — | Trigon | — | 32 | `2564387350` | Boneyard / 骸骨场 | — | 3,200,000 | 超级地球 | HILJAISUUS（城镇） / KALASATAMA（城市） / YDINKESKUSTA（巨型城市） / EVOLUTION PLATS（定居点） |
| 159 | **CHOOHE** | — | Lacaille | — | 34 | `1159313659` | Desert Dunes / 沙漠沙丘 | 沙暴 | 1,000,000 | 超级地球 | — |
| 160 | **CHORT BAY** | — | Lacaille | — | 34 | `2695598028` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 1,000,000 | 超级地球 | — |
| 161 | **CLAORELL** | — | Tanis | — | 35 | `1109752394` | Moon / 月球 | 流星风暴 | 2,200,000 | 超级地球 | MAJOSYRI（城市） / QUASAR（城市） / ZENITH（巨型城市） |
| 162 | **CLASA** | — | Tanis | — | 35 | `4171074231` | Basic Swamp / 原始沼泽 | — | 1,700,000 | 超级地球 | SYCAMORE GARDENS（定居点） / KODIAK FALLS（城镇） / VOTING DISTRICT F-012357（城市） |
| 163 | **DEMIURG** | — | Tanis | — | 35 | `1270268663` | Tundra / 苔原 | — | 1,000,000 | 超级地球 | — |
| 164 | **DENEB SECUNDUS** | — | Arturion | — | 36 | `575825411` | Boneyard / 骸骨场 | — | 1,000,000 | 超级地球 | — |
| 165 | **ELECTRA BAY** | — | Arturion | — | 36 | `3031668844` | Plains / 平原 | — | 1,000,000 | 超级地球 | — |
| 166 | **ENULIALE** | — | L'estrade | — | 37 | `3692735566` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 终结族 | — |
| 167 | **EPSILON PHOENCIS VI** | — | L'estrade | — | 37 | `3517952761` | Icy Glaciers / 冰川 | 暴风雪 | 1,000,000 | 终结族 | — |
| 168 | **ERATA PRIME** | — | Umlaut | — | 38 | `3604506896` | Desert Cliffs / 沙漠峭壁 | 地震活动 | 1,500,000 | 终结族 | NEW DA NANG（城镇） / PHAM'S SITE（定居点） / OLD CHEMLAND（城镇） |
| 169 | **ESTANU** | — | Draco | — | 21 | `356540875` | Boneyard / 骸骨场 | — | 1,000,000 | 终结族 | — |
| 170 | **FORI PRIME** | — | Draco | — | 21 | `3087050848` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,000,000 | 终结族 | — |
| 171 | **GACRUX** | — | Jin Xi | — | 39 | `2036924050` | Basic Swamp / 原始沼泽 | — | 1,000,000 | 超级地球 | — |
| 172 | **GAR HAREN** | — | Jin Xi | — | 39 | `2254239637` | Haunted Swamp / 阴魂沼泽 | — | 1,000,000 | 超级地球 | — |
| 173 | **GATRIA** | — | Jin Xi | — | 39 | `1039531899` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,500,000 | 超级地球 | ALTONBURG（定居点） / ERSATZ（城市） |
| 174 | **GEMMA** | — | Ursa | — | 24 | `1730968584` | Ionic Jungle / 离子丛林 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 175 | **GRAND ERRANT** | — | Farsight | — | 24 | `3461540330` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,000,000 | 超级地球 | — |
| 176 | **HADAR** | — | Ferris | 费里斯 | 25 | `3671746797` | Icy Glaciers / 冰川 | 暴风雪 | 1,000,000 | 超级地球 | — |
| 177 | **HAKA** | — | Leo | — | 25 | `1969390828` | Deadlands / 死地 | — | 1,000,000 | 超级地球 | — |
| 178 | **HALDUS** | — | Ferris | 费里斯 | 25 | `3856827013` | Basic Swamp / 原始沼泽 | — | 1,000,000 | 超级地球 | — |
| 179 | **HALIES PORT** | — | Leo | — | 25 | `386932878` | Boneyard / 骸骨场 | — | 1,000,000 | 超级地球 | — |
| 180 | **HERTHON SECUNDUS** | — | Ferris | 费里斯 | 25 | `2517847560` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,800,000 | 超级地球 | PENSCEWT（城镇） / EAGLE'S LIKENESS（城镇） / CONSENSUS（城市） |
| 181 | **HESOE PRIME** | — | Rigel | — | 25 | `1581052380` | Icy Glaciers / 冰川 | 暴风雪 | 1,000,000 | 超级地球 | — |
| 182 | **HEZE BAY** | — | Hanzo | — | 26 | `4182360890` | Desert Dunes / 沙漠沙丘 | 沙暴 | 1,800,000 | 超级地球 | UNANIMITY（城市） / UNISON（城市） |
| 183 | **HORT** | — | Rigel | — | 26 | `2078192573` | Plains / 平原 | — | 2,200,000 | 超级地球 | ON-EARSAHOU（城市） / CLOCKSTOP（城市） / MAGNITUDE（城市） |
| 184 | **HYDROBIUS** | — | Omega | — | 43 | `1722929190` | Desert Cliffs / 沙漠峭壁 | 地震活动 | 1,400,000 | 超级地球 | GENERATORSVILLE（城市） |
| 185 | **KARLIA** | — | Omega | — | 43 | `101839064` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,400,000 | 超级地球 | ADNAN（城市） |
| 186 | **KEID** | — | Akira | — | 27 | `2563880739` | Desert Dunes / 沙漠沙丘 | 沙暴 | 1,000,000 | 超级地球 | — |
| 187 | **KHANDARK** | — | Guang | — | 28 | `1697634205` | Haunted Swamp / 阴魂沼泽 | — | 1,000,000 | 超级地球 | — |
| 188 | **KLAKA 5** | — | Alstrad | — | 30 | `1366049074` | Haunted Swamp / 阴魂沼泽 | — | 1,000,000 | 超级地球 | — |
| 189 | **KNETH PORT** | — | Alstrad | — | 30 | `4234355218` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,000,000 | 超级地球 | — |
| 190 | **KRAZ** | — | Alstrad | — | 30 | `2097290850` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,000,000 | 超级地球 | — |
| 191 | **KUMA** | — | Hawking | — | 30 | `3764590020` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,000,000 | 超级地球 | — |
| 192 | **LASTOFE** | — | Theseus | — | 16 | `3052439858` | Desert Dunes / 沙漠沙丘 | 沙暴 | 1,000,000 | 超级地球 | — |
| 193 | **LENG SECUNDUS** | — | Quintus | — | 16 | `2845725342` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 1,000,000 | 超级地球 | — |
| 194 | **LESATH** | — | Lacaille | — | 46 | `3837447591` | Boneyard / 骸骨场 | — | 1,000,000 | 超级地球 | SERENITY SUMMIT（城镇） / MORSKIE OKO（城镇） / CRYSTAL SLOPES（城市） / BUCU'S REST（巨型城市） |
| 195 | **MAIA** | — | Severin | — | 46 | `1126502547` | Moon / 月球 | 流星风暴 | 1,000,000 | 机器人 | — |
| 196 | **MALEVELON CREEK** | — | Severin | — | 33 | `3244992775` | Ionic Jungle / 离子丛林 | 离子风暴 | 1,400,000 | 机器人 | LIFEBLOOD（定居点） / REQUIEM（定居点） / DIVER'S REST（城镇） |
| 197 | **MANTES** | — | Xzar | — | 33 | `1806559160` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,000,000 | 超级地球 | — |
| 198 | **MARFARK** | — | Andromeda | — | 33 | `2831860380` | Icy Glaciers / 冰川 | 暴风雪 | 2,000,000 | 超级地球 | TECHNOLOCKIA ALLATEED（定居点） |
| 199 | **MARTALE** | — | Andromeda | — | 33 | `2016899055` | Tundra / 苔原 | — | 1,500,000 | 超级地球 | SONGGUO CUN（定居点） / XIN FUZHOU（城市） |
| 200 | **MATAR BAY** | — | Andromeda | — | 34 | `2071495162` | Plains / 平原 | — | 1,600,000 | 超级地球 | PARRHESIA（城市） / ISEGORIA（城镇） |
| 201 | **MEISSA** | — | Ymir | — | 34 | `996779072` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,000,000 | 超级地球 | — |
| 202 | **MEKBUDA** | — | Valdis | — | 34 | `1982461871` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,000,000 | 超级地球 | — |
| 203 | **MENKENT** | — | Hydra | — | 34 | `3161413384` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,000,000 | 超级地球 | — |
| 204 | **MERAK** | — | Valdis | — | 35 | `964201429` | Ionic Jungle / 离子丛林 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 205 | **MERGA IV** | — | Valdis | — | 35 | `319528443` | Haunted Swamp / 阴魂沼泽 | — | 1,000,000 | 超级地球 | — |
| 206 | **MINCHIR** | — | Gellert | — | 36 | `1805868079` | Ionic Jungle / 离子丛林 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 207 | **MINTORIA** | — | Gellert | — | 36 | `2174989502` | Plains / 平原 | — | 1,300,000 | 超级地球 | SEORAKSAN（定居点） / GYEONGSEONG（城镇） |
| 208 | **MORDIA 9** | — | Hawking | — | 36 | `1125831687` | Ethereal Jungle / 空灵丛林 | — | 1,000,000 | 超级地球 | — |
| 209 | **NABATEA SECUNDUS** | — | L'estrade | — | 37 | `2595930801` | Basic Swamp / 原始沼泽 | — | 1,000,000 | 终结族 | — |
| 210 | **NAVI VII** | — | L'estrade | — | 37 | `1644011282` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,000,000 | 终结族 | — |
| 211 | **NIVEL 43** | — | Mirin | — | 38 | `301092871` | Deadlands / 死地 | — | 1,000,000 | 终结族 | — |
| 212 | **OSHAUNE** | — | Mirin | — | 38 | `1344035939` | Hive World / 巢都世界 | — | 1,000,000 | 终结族 | — |
| 213 | **OVERGOE PRIME** | — | Sten | — | 38 | `2798506372` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 终结族 | — |
| 214 | **PANDION-XXIV** | — | Jin Xi | — | 39 | `2529588949` | Deadlands / 死地 | — | 1,000,000 | 超级地球 | — |
| 215 | **PARTION** | — | Sten | — | 39 | `2633633039` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,000,000 | 终结族 | — |
| 216 | **PEACOCK** | — | Sten | — | 39 | `3575106066` | Ionic Jungle / 离子丛林 | 离子风暴 | 1,300,000 | 终结族 | QUASAR（定居点） / SYZYGY（城镇） |
| 217 | **PHACT BAY** | — | Jin Xi | — | 39 | `1050117740` | Desert Dunes / 沙漠沙丘 | 沙暴 | 2,200,000 | 超级地球 | OLD DOVE（城镇） / BRNO（城市） / NEW EAGLE（巨型城市） |
| 218 | **PHERKAD SECUNDUS** | — | Farsight | — | 40 | `1272337220` | Basic Swamp / 原始沼泽 | — | 1,000,000 | 超级地球 | — |
| 219 | **POLARIS PRIME** | — | Farsight | — | 40 | `1029706994` | Desert Cliffs / 沙漠峭壁 | 地震活动 | 2,000,000 | 超级地球 | VILHELMINA DOROTHEA FREDRIKA（城市） / MOGO PLAINS（城镇） / KALASATAMA PORT（城市） |
| 220 | **POLLUX 31** | — | Farsight | — | 41 | `4039961663` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,000,000 | 超级地球 | — |
| 221 | **PRASA** | — | Farsight | — | 41 | `3290149632` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,000,000 | 超级地球 | HANDAKAS（城镇） / HAKU CITY（城市） |
| 222 | **PROPUS** | — | Leo | — | 41 | `3795087598` | Desert Dunes / 沙漠沙丘 | 沙暴 | 1,000,000 | 超级地球 | — |
| 223 | **RAS ALGETHI** | — | Leo | — | 41 | `4053031948` | Tundra / 苔原 | — | 1,000,000 | 超级地球 | — |
| 224 | **RD-4** | — | Rigel | — | 42 | `3659425534` | Moon / 月球 | 流星风暴 | 1,000,000 | 超级地球 | — |
| 225 | **ROGUE 5** | — | Rigel | — | 42 | `433678065` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,000,000 | 超级地球 | — |
| 226 | **RIRGA BAY** | — | Rigel | — | 42 | `1377257553` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 2,200,000 | 超级地球 | BLIGHTSMURK（城镇） / BASE CAMP 8（巨型城市） / ZONE 3（城市） |
| 227 | **SEASSE** | — | Omega | — | 42 | `264536752` | ACCESS DENIED / 机密（权限不足） | — | 1,000,000 | 超级地球 | — |
| 228 | **SENGE 23** | — | Omega | — | 43 | `3709894755` | Rocky Canyons / 岩石峡谷 | 地震活动 | 1,300,000 | 超级地球 | EXALT（城镇） / EAGLESTAR ETERNAL（定居点） |
| 229 | **SETIA** | — | Omega | — | 43 | `449319042` | Haunted Swamp / 阴魂沼泽 | — | 1,000,000 | 超级地球 | — |
| 230 | **SHETE** | — | Xi Tauri | — | 27 | `1531805760` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 1,400,000 | 超级地球 | HOLL（城市） |
| 231 | **SIEMNOT** | — | Xi Tauri | — | 27 | `3472221087` | Ionic Jungle / 离子丛林 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 232 | **SIRIUS** | — | Xi Tauri | — | 44 | `31903659` | Moon / 月球 | 流星风暴 | 1,000,000 | 超级地球 | — |
| 233 | **SKAT BAY** | — | Xi Tauri | — | 44 | `728004013` | Deadlands / 死地 | — | 1,000,000 | 超级地球 | — |
| 234 | **SPHERION** | — | Quintus | — | 45 | `33972203` | Volcanic Jungle / 火山丛林 | 火山活动 | 1,000,000 | 超级地球 | — |
| 235 | **STOR THA PRIME** | — | Quintus | — | 45 | `3339959103` | Boneyard / 骸骨场 | — | 1,000,000 | 超级地球 | — |
| 236 | **STOUT** | — | Quintus | — | 45 | `3478070727` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 237 | **TERMADON** | — | Quintus | — | 45 | `1923795699` | Plains / 平原 | — | 1,000,000 | 超级地球 | — |
| 238 | **TIBIT** | — | Severin | — | 46 | `2658611086` | Ethereal Jungle / 空灵丛林 | — | 1,000,000 | 机器人 | — |
| 239 | **TIEN KWAN** | — | Theseus | — | 46 | `2659689769` | Boneyard / 骸骨场 | 流星风暴 | 2,200,000 | 超级地球 | FOUNDRY（巨型城市） / STEEL RESOLVE（巨型城市） |
| 240 | **TROOST** | — | Trigon | — | 46 | `1049999007` | Deadlands / 死地 | — | 1,000,000 | 超级地球 | — |
| 241 | **UBANEA** | — | Severin | — | 46 | `2216912817` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,600,000 | 机器人 | FREEDOM ETERNAL（城镇） / NUOVA ROMA（城市） |
| 242 | **USTOTU** | — | Trigon | — | 48 | `260933067` | Desert Cliffs / 沙漠峭壁 | 地震活动 | 1,000,000 | 超级地球 | — |
| 243 | **VANDALON IV** | — | Trigon | — | 48 | `230950549` | Icy Glaciers / 冰川 | 暴风雪 | 1,000,000 | 超级地球 | — |
| 244 | **VARYLIA 5** | — | Trigon | — | 49 | `17046409` | Plains / 平原 | — | 1,400,000 | 超级地球 | SEQUIM（城市） |
| 245 | **WASAT** | — | Ymir | — | 49 | `3825459240` | Acidic Badlands / 酸性荒地 | 酸雨风暴 | 2,000,000 | 超级地球 | MIRAGE（城市） / DRYWELL（巨型城市） |
| 246 | **VEGA BAY** | — | Ymir | — | 50 | `229350423` | Icy Glaciers / 冰川 | 暴风雪 | 1,500,000 | 超级地球 | ONSEN（定居点） / GIRI（城镇） / SAPPORO（城镇） |
| 247 | **WEZEN** | — | Ymir | — | 50 | `1554138344` | Scorched Moor / 焦灼荒原 | 火焰龙卷 | 1,000,000 | 超级地球 | — |
| 248 | **VINDEMITARIX PRIME** | — | Valdis | — | 50 | `1826401325` | Ethereal Jungle / 空灵丛林 | — | 1,000,000 | 超级地球 | — |
| 249 | **X-45** | — | Ymir | — | 50 | `2165203458` | Basic Swamp / 原始沼泽 | — | 1,000,000 | 超级地球 | — |
| 250 | **YED PRIOR** | — | Tanis | — | 35 | `714233297` | Ionic Crimson / 赤红离子 | 离子风暴 | 1,000,000 | 超级地球 | — |
| 251 | **ZEFIA** | — | Tanis | — | 35 | `252504470` | Ethereal Jungle / 空灵丛林 | — | 1,000,000 | 超级地球 | — |
| 252 | **ZOSMA** | — | Gellert | — | 51 | `2360232252` | Moon / 月球 | 流星风暴 | 1,000,000 | 超级地球 | — |
| 253 | **ZZANIAH PRIME** | — | Gellert | — | 51 | `1524642040` | Desert Dunes / 沙漠沙丘 | 沙暴 | 2,000,000 | 超级地球 | GEMSTELLE GENERATOR（定居点） |
| 254 | **SKITTER** | — | Hawking | — | 52 | `3789806846` | Haunted Swamp / 阴魂沼泽 | — | 1,000,000 | 超级地球 | — |
| 255 | **EUPHORIA III** | — | Hawking | — | 52 | `3809134104` | Moon / 月球 | 流星风暴 | 1,000,000 | 超级地球 | — |
| 256 | **DIASPORA X** | — | L'estrade | — | 53 | `4020204519` | Desert Dunes / 沙漠沙丘 | 沙暴 | 1,000,000 | 终结族 | — |
| 257 | **GEMSTONE BLUFFS** | — | L'estrade | — | 53 | `1588671273` | Plains / 平原 | — | 1,000,000 | 终结族 | — |
| 258 | **ZAGON PRIME** | — | Mirin | — | 53 | `843081973` | Hive World / 巢都世界 | — | 2,000,000 | 终结族 | — |
| 259 | **OMICRON** | — | L'estrade | — | 53 | `3966660905` | Hive World / 巢都世界 | — | 3,000,000 | 终结族 | — |
| 260 | **CYBERSTAN** | — | Valdis | — | 49 | `3923589145` | Cyberstan Megafactory / 赛博斯坦巨型工厂 | — | 15,000,000 | 超级地球 | TRANSCENDENCE（巨型城市） / AUTONOMY（定居点） / STAR KIELD（城市） / OMNIPARITUS（城镇） / SOLIDARITET（定居点） / URSOOT NINE（城市） / LURZA（城镇） / CAMRAT FOR（城镇） |
| 261 | **FURY** | — | Xzar | — | 0 | `3487417548` | Magma / 熔岩 | — | 2,000,000 | 超级地球 | — |
| 262 | **K** | K | Trigon | — | 0 | `1143730827` | Magma / 熔岩 | — | 2,000,000 | 超级地球 | — |
| 264 | **NEW INSIGHT** | — | TBD | — | 0 | `3117259984` | Magma / 熔岩 | — | 2,000,000 | 超级地球 | — |
| 265 | **WAYWARD** | — | TBD | — | 0 | `3060137094` | Magma / 熔岩 | — | 2,000,000 | 超级地球 | — |
| 266 | **MOX** | — | Trigon | — | 0 | `1316898847` | Magma / 熔岩 | — | 2,000,000 | 超级地球 | — |
| 267 | **BIG ROCK** | — | Sten | — | 0 | `3844933373` | Desert Oasis / 沙漠绿洲 | — | 2,000,000 | 超级地球 | — |
| 268 | **LUXURIANT** | — | Jin Xi | — | 0 | `1653510998` | Deciduous Forest / 落叶林 | — | 2,000,000 | 超级地球 | — |
| 269 | **BRILLIANCE** | — | Orion | — | 0 | `224163544` | Deciduous Forest / 落叶林 | — | 2,000,000 | 超级地球 | — |
| 270 | **FRONTERIA** | — | Umlaut | — | 0 | `2807946366` | Desert Oasis / 沙漠绿洲 | — | 2,000,000 | 超级地球 | — |
| 271 | **ZYGOS** | — | Orion | — | 0 | `2871915822` | Desert Oasis / 沙漠绿洲 | — | 2,000,000 | 超级地球 | — |
| 272 | **BASQUINE VIII** | — | Rigel | — | 0 | `1367796466` | Deciduous Autumn Forest / 秋色落叶林 | — | 2,000,000 | 超级地球 | — |
| 273 | **ALDERIDGE COVE** | — | Omega | — | 43 | `1616302990` | Deadlands / 死地 | — | 2,000,000 | 超级地球 | — |

---

## 2. 星区 → 星球

| 星区 | 中文名 | 星球数 | 星球（index 名称） |
|---|---|---:|---|
| **Akira** | — | 5 | 140 ALARAPH, 141 ALATHFAR XI, 142 ANDAR, 143 ASPEROTH PRIME, 186 KEID |
| **Alstrad** | — | 3 | 188 KLAKA 5, 189 KNETH PORT, 190 KRAZ |
| **Altus** | 阿尔特斯 | 5 | 1 KLEN DAHTH II, 2 PATHFINDER V, 3 WIDOW'S HARBOR, 4 NEW HAVEN, 5 PILEN V |
| **Andromeda** | — | 5 | 156 CHARBAL-VII, 157 CHARON PRIME, 198 MARFARK, 199 MARTALE, 200 MATAR BAY |
| **Arturion** | — | 7 | 74 ARKTURUS, 118 KIRRIK, 119 MORTAX PRIME, 120 WILFORD STATION, 121 PIONEER II, 164 DENEB SECUNDUS, 165 ELECTRA BAY |
| **Barnard** | 巴纳德 | 6 | 6 HYDROFALL PRIME, 8 DARROWSPORT, 9 FORNSKOGUR II, 10 MIDASBURG, 30 VEIL, 31 MARRE IV |
| **Borgus** | — | 4 | 82 URSICA XI, 128 DARIUS II, 130 ACHERNAR SECUNDUS, 131 ACHIRD III |
| **Cancri** | 康谷利伊 | 5 | 11 CERBERUS IIIc, 12 PROSPERITY FALLS, 32 FORT SANCTUARY, 33 SEYSHEL BEACH, 35 EFFLUVIA |
| **Cantolus** | — | 5 | 14 MARTYR'S BAY, 15 FREEDOM PEAK, 17 KELVINOR, 38 VIRIDIA PRIME, 39 OBARI |
| **Celeste** | — | 6 | 25 SULFURA, 26 NUBLARIA I, 27 KRAKATWO, 51 IVIS, 52 SLIF, 85 MORADESH |
| **Draco** | — | 3 | 78 CRIMSICA, 169 ESTANU, 170 FORI PRIME |
| **Falstaff** | — | 4 | 75 ESKER, 122 ERSON SANDS, 123 SOCORRO III, 124 BORE ROCK |
| **Farsight** | — | 5 | 175 GRAND ERRANT, 218 PHERKAD SECUNDUS, 219 POLARIS PRIME, 220 POLLUX 31, 221 PRASA |
| **Ferris** | 费里斯 | 4 | 7 ZEA RUGOSIA, 176 HADAR, 178 HALDUS, 180 HERTHON SECUNDUS |
| **Gallux** | — | 6 | 54 KHARST, 86 RASP, 87 BASHYR, 134 ACUBENS PRIME, 135 ADHARA, 136 AFOYAY BAY |
| **Gellert** | — | 5 | 70 BLISTICA, 206 MINCHIR, 207 MINTORIA, 252 ZOSMA, 253 ZZANIAH PRIME |
| **Gothmar** | — | 3 | 13 OKUL VI, 36 SOLGHAST, 37 DILUVIA |
| **Guang** | — | 5 | 98 ELYSIAN MEADOWS, 99 SANGIS, 144 BELLATRIX, 145 BOTEIN, 187 KHANDARK |
| **Hanzo** | — | 5 | 93 NEW STOCKHOLM, 137 AIN-5, 138 ALAIRT III, 139 ALAMAK VII, 182 HEZE BAY |
| **Hawking** | — | 4 | 191 KUMA, 208 MORDIA 9, 254 SKITTER, 255 EUPHORIA III |
| **Hydra** | — | 3 | 112 VERNEN WELLS, 113 AESIR PASS, 203 MENKENT |
| **Idun** | — | 4 | 18 WRAITH, 40 MYRADESH, 41 ATRAMA, 63 MAW |
| **Iptus** | — | 6 | 23 PROVIDENCE, 24 PRIMORDIA, 47 KRAKABOS, 48 IRIDICA, 71 RATCH, 73 VALGAARD |
| **Jin Xi** | — | 7 | 129 ACAMAR IV, 171 GACRUX, 172 GAR HAREN, 173 GATRIA, 214 PANDION-XXIV, 217 PHACT BAY, 268 LUXURIANT |
| **Kelvin** | — | 5 | 19 IGLA, 20 NEW KIRUNA, 21 FORT JUSTICE, 22 ZEGEMA PARADISE, 42 EMERIA |
| **Korpus** | — | 5 | 28 VOLTERRA, 29 CRUCIBLE, 53 CARAMOOR, 81 ALTA V, 83 INARI |
| **L'estrade** | — | 7 | 166 ENULIALE, 167 EPSILON PHOENCIS VI, 209 NABATEA SECUNDUS, 210 NAVI VII, 256 DIASPORA X, 257 GEMSTONE BLUFFS, 259 OMICRON |
| **Lacaille** | — | 4 | 115 PENTA, 159 CHOOHE, 160 CHORT BAY, 194 LESATH |
| **Leo** | — | 4 | 177 HAKA, 179 HALIES PORT, 222 PROPUS, 223 RAS ALGETHI |
| **Marspira** | — | 5 | 43 BARABOS, 44 FENMIRE, 45 MASTIA, 66 CURIA, 67 TARSH |
| **Meridian** | — | 4 | 61 EMORATH, 62 ILDUNA PRIME, 102 LIBERTY RIDGE, 103 BALDRICK PRIME |
| **Mirin** | — | 4 | 34 HELLMIRE, 211 NIVEL 43, 212 OSHAUNE, 258 ZAGON PRIME |
| **Morgon** | — | 4 | 55 EUKORIA, 56 MYRIUM, 88 REGNUS, 89 MOG |
| **Nanos** | — | 4 | 72 JULHEIM, 109 DOLPH, 110 BEKVAM III, 111 DUMA TYR |
| **Omega** | — | 6 | 184 HYDROBIUS, 185 KARLIA, 227 SEASSE, 228 SENGE 23, 229 SETIA, 273 ALDERIDGE COVE |
| **Orion** | — | 9 | 16 FORT UNION, 49 AZTERRA, 76 TERREK, 77 CIRRUS, 79 HEETH, 80 VELD, 127 ANGEL'S VENTURE, 269 BRILLIANCE, 271 ZYGOS |
| **Quintus** | — | 5 | 193 LENG SECUNDUS, 234 SPHERION, 235 STOR THA PRIME, 236 STOUT, 237 TERMADON |
| **Rictus** | — | 7 | 57 KERTH SECUNDUS, 58 PARSH, 90 VALMOX, 91 IRO, 92 GRAFMERE, 94 OASIS, 95 GENESIS PRIME |
| **Rigel** | — | 6 | 181 HESOE PRIME, 183 HORT, 224 RD-4, 225 ROGUE 5, 226 RIRGA BAY, 272 BASQUINE VIII |
| **Sagan** | — | 3 | 65 BOREA, 106 OSLO STATION, 108 GUNVALD |
| **Saleria** | — | 4 | 59 REAF, 60 IRULTA, 96 OUTPOST 32, 97 CALYPSO |
| **Severin** | — | 5 | 152 DURGEN, 195 MAIA, 196 MALEVELON CREEK, 238 TIBIT, 241 UBANEA |
| **Sol** | 太阳系 | 1 | 0 SUPER EARTH |
| **Sten** | — | 6 | 50 AZUR SECUNDUS, 100 TRANDOR, 213 OVERGOE PRIME, 215 PARTION, 216 PEACOCK, 267 BIG ROCK |
| **TBD** | — | 2 | 264 NEW INSIGHT, 265 WAYWARD |
| **Talus** | — | 4 | 46 SHALLUS, 68 SHELT, 69 IMBER, 116 GAELLIVARE |
| **Tanis** | — | 6 | 117 VOG-SOJOTH, 161 CLAORELL, 162 CLASA, 163 DEMIURG, 250 YED PRIOR, 251 ZEFIA |
| **Tarragon** | — | 5 | 101 EAST IRIDIUM TRADING BAY, 146 OSUPSAM, 147 BRINK-2, 148 BUNDA SECUNDUS, 149 CANOPUS |
| **Theseus** | — | 6 | 104 THE WEIR, 105 KUPER, 150 CAPH, 151 CASTOR, 192 LASTOFE, 239 TIEN KWAN |
| **Trigon** | — | 7 | 158 CHOEPESSA IV, 240 TROOST, 242 USTOTU, 243 VANDALON IV, 244 VARYLIA 5, 262 K, 266 MOX |
| **Umlaut** | — | 5 | 64 MERIDIA, 125 FENRIR III, 126 TURING, 168 ERATA PRIME, 270 FRONTERIA |
| **Ursa** | — | 4 | 84 SKAASH, 132 ACRAB XI, 133 ACRUX IX, 174 GEMMA |
| **Valdis** | — | 6 | 114 AURORA BAY, 202 MEKBUDA, 204 MERAK, 205 MERGA IV, 248 VINDEMITARIX PRIME, 260 CYBERSTAN |
| **Xi Tauri** | — | 4 | 230 SHETE, 231 SIEMNOT, 232 SIRIUS, 233 SKAT BAY |
| **Xzar** | — | 6 | 107 PÖPLI IX, 153 DRAUPNIR, 154 MORT, 155 INGMAR, 197 MANTES, 261 FURY |
| **Ymir** | — | 5 | 201 MEISSA, 245 WASAT, 246 VEGA BAY, 247 WEZEN, 249 X-45 |

---

## 3. 按名称反查 index

星区归属也一并给出，方便对照 wiki。

| 星球 | 中文名 | index | 星区 | 星区中文 |
|---|---|---:|---|---|
| ACAMAR IV | — | 129 | Jin Xi | — |
| ACHERNAR SECUNDUS | — | 130 | Borgus | — |
| ACHIRD III | — | 131 | Borgus | — |
| ACRAB XI | — | 132 | Ursa | — |
| ACRUX IX | — | 133 | Ursa | — |
| ACUBENS PRIME | — | 134 | Gallux | — |
| ADHARA | — | 135 | Gallux | — |
| AESIR PASS | — | 113 | Hydra | — |
| AFOYAY BAY | — | 136 | Gallux | — |
| AIN-5 | — | 137 | Hanzo | — |
| ALAIRT III | — | 138 | Hanzo | — |
| ALAMAK VII | — | 139 | Hanzo | — |
| ALARAPH | — | 140 | Akira | — |
| ALATHFAR XI | — | 141 | Akira | — |
| ALDERIDGE COVE | — | 273 | Omega | — |
| ALTA V | — | 81 | Korpus | — |
| ANDAR | — | 142 | Akira | — |
| ANGEL'S VENTURE | — | 127 | Orion | — |
| ARKTURUS | — | 74 | Arturion | — |
| ASPEROTH PRIME | — | 143 | Akira | — |
| ATRAMA | — | 41 | Idun | — |
| AURORA BAY | — | 114 | Valdis | — |
| AZTERRA | — | 49 | Orion | — |
| AZUR SECUNDUS | — | 50 | Sten | — |
| BALDRICK PRIME | — | 103 | Meridian | — |
| BARABOS | — | 43 | Marspira | — |
| BASHYR | — | 87 | Gallux | — |
| BASQUINE VIII | — | 272 | Rigel | — |
| BEKVAM III | — | 110 | Nanos | — |
| BELLATRIX | — | 144 | Guang | — |
| BIG ROCK | — | 267 | Sten | — |
| BLISTICA | — | 70 | Gellert | — |
| BORE ROCK | — | 124 | Falstaff | — |
| BOREA | — | 65 | Sagan | — |
| BOTEIN | — | 145 | Guang | — |
| BRILLIANCE | — | 269 | Orion | — |
| BRINK-2 | — | 147 | Tarragon | — |
| BUNDA SECUNDUS | — | 148 | Tarragon | — |
| CALYPSO | — | 97 | Saleria | — |
| CANOPUS | — | 149 | Tarragon | — |
| CAPH | — | 150 | Theseus | — |
| CARAMOOR | — | 53 | Korpus | — |
| CASTOR | — | 151 | Theseus | — |
| CERBERUS IIIc | 刻耳柏洛斯IIIc | 11 | Cancri | 康谷利伊 |
| CHARBAL-VII | — | 156 | Andromeda | — |
| CHARON PRIME | — | 157 | Andromeda | — |
| CHOEPESSA IV | — | 158 | Trigon | — |
| CHOOHE | — | 159 | Lacaille | — |
| CHORT BAY | — | 160 | Lacaille | — |
| CIRRUS | — | 77 | Orion | — |
| CLAORELL | — | 161 | Tanis | — |
| CLASA | — | 162 | Tanis | — |
| CRIMSICA | — | 78 | Draco | — |
| CRUCIBLE | — | 29 | Korpus | — |
| CURIA | — | 66 | Marspira | — |
| CYBERSTAN | — | 260 | Valdis | — |
| DARIUS II | — | 128 | Borgus | — |
| DARROWSPORT | 达罗斯波特 | 8 | Barnard | 巴纳德 |
| DEMIURG | — | 163 | Tanis | — |
| DENEB SECUNDUS | — | 164 | Arturion | — |
| DIASPORA X | — | 256 | L'estrade | — |
| DILUVIA | — | 37 | Gothmar | — |
| DOLPH | — | 109 | Nanos | — |
| DRAUPNIR | — | 153 | Xzar | — |
| DUMA TYR | — | 111 | Nanos | — |
| DURGEN | — | 152 | Severin | — |
| EAST IRIDIUM TRADING BAY | — | 101 | Tarragon | — |
| EFFLUVIA | — | 35 | Cancri | 康谷利伊 |
| ELECTRA BAY | — | 165 | Arturion | — |
| ELYSIAN MEADOWS | — | 98 | Guang | — |
| EMERIA | — | 42 | Kelvin | — |
| EMORATH | — | 61 | Meridian | — |
| ENULIALE | — | 166 | L'estrade | — |
| EPSILON PHOENCIS VI | — | 167 | L'estrade | — |
| ERATA PRIME | — | 168 | Umlaut | — |
| ERSON SANDS | — | 122 | Falstaff | — |
| ESKER | — | 75 | Falstaff | — |
| ESTANU | — | 169 | Draco | — |
| EUKORIA | — | 55 | Morgon | — |
| EUPHORIA III | — | 255 | Hawking | — |
| FENMIRE | — | 44 | Marspira | — |
| FENRIR III | — | 125 | Umlaut | — |
| FORI PRIME | — | 170 | Draco | — |
| FORNSKOGUR II | 福恩斯科古尔II | 9 | Barnard | 巴纳德 |
| FORT JUSTICE | — | 21 | Kelvin | — |
| FORT SANCTUARY | — | 32 | Cancri | 康谷利伊 |
| FORT UNION | — | 16 | Orion | — |
| FREEDOM PEAK | — | 15 | Cantolus | — |
| FRONTERIA | — | 270 | Umlaut | — |
| FURY | — | 261 | Xzar | — |
| GACRUX | — | 171 | Jin Xi | — |
| GAELLIVARE | — | 116 | Talus | — |
| GAR HAREN | — | 172 | Jin Xi | — |
| GATRIA | — | 173 | Jin Xi | — |
| GEMMA | — | 174 | Ursa | — |
| GEMSTONE BLUFFS | — | 257 | L'estrade | — |
| GENESIS PRIME | — | 95 | Rictus | — |
| GRAFMERE | — | 92 | Rictus | — |
| GRAND ERRANT | — | 175 | Farsight | — |
| GUNVALD | — | 108 | Sagan | — |
| HADAR | — | 176 | Ferris | 费里斯 |
| HAKA | — | 177 | Leo | — |
| HALDUS | — | 178 | Ferris | 费里斯 |
| HALIES PORT | — | 179 | Leo | — |
| HEETH | — | 79 | Orion | — |
| HELLMIRE | — | 34 | Mirin | — |
| HERTHON SECUNDUS | — | 180 | Ferris | 费里斯 |
| HESOE PRIME | — | 181 | Rigel | — |
| HEZE BAY | — | 182 | Hanzo | — |
| HORT | — | 183 | Rigel | — |
| HYDROBIUS | — | 184 | Omega | — |
| HYDROFALL PRIME | 水瀑主星 | 6 | Barnard | 巴纳德 |
| IGLA | — | 19 | Kelvin | — |
| ILDUNA PRIME | — | 62 | Meridian | — |
| IMBER | — | 69 | Talus | — |
| INARI | — | 83 | Korpus | — |
| INGMAR | — | 155 | Xzar | — |
| IRIDICA | — | 48 | Iptus | — |
| IRO | — | 91 | Rictus | — |
| IRULTA | — | 60 | Saleria | — |
| IVIS | — | 51 | Celeste | — |
| JULHEIM | — | 72 | Nanos | — |
| K | K | 262 | Trigon | — |
| KARLIA | — | 185 | Omega | — |
| KEID | — | 186 | Akira | — |
| KELVINOR | — | 17 | Cantolus | — |
| KERTH SECUNDUS | — | 57 | Rictus | — |
| KHANDARK | — | 187 | Guang | — |
| KHARST | — | 54 | Gallux | — |
| KIRRIK | — | 118 | Arturion | — |
| KLAKA 5 | — | 188 | Alstrad | — |
| KLEN DAHTH II | 克伦达斯II | 1 | Altus | 阿尔特斯 |
| KNETH PORT | — | 189 | Alstrad | — |
| KRAKABOS | — | 47 | Iptus | — |
| KRAKATWO | — | 27 | Celeste | — |
| KRAZ | — | 190 | Alstrad | — |
| KUMA | — | 191 | Hawking | — |
| KUPER | — | 105 | Theseus | — |
| LASTOFE | — | 192 | Theseus | — |
| LENG SECUNDUS | — | 193 | Quintus | — |
| LESATH | — | 194 | Lacaille | — |
| LIBERTY RIDGE | — | 102 | Meridian | — |
| LUXURIANT | — | 268 | Jin Xi | — |
| MAIA | — | 195 | Severin | — |
| MALEVELON CREEK | — | 196 | Severin | — |
| MANTES | — | 197 | Xzar | — |
| MARFARK | — | 198 | Andromeda | — |
| MARRE IV | — | 31 | Barnard | 巴纳德 |
| MARTALE | — | 199 | Andromeda | — |
| MARTYR'S BAY | — | 14 | Cantolus | — |
| MASTIA | — | 45 | Marspira | — |
| MATAR BAY | — | 200 | Andromeda | — |
| MAW | — | 63 | Idun | — |
| MEISSA | — | 201 | Ymir | — |
| MEKBUDA | — | 202 | Valdis | — |
| MENKENT | — | 203 | Hydra | — |
| MERAK | — | 204 | Valdis | — |
| MERGA IV | — | 205 | Valdis | — |
| MERIDIA | — | 64 | Umlaut | — |
| MIDASBURG | 弥达斯堡 | 10 | Barnard | 巴纳德 |
| MINCHIR | — | 206 | Gellert | — |
| MINTORIA | — | 207 | Gellert | — |
| MOG | — | 89 | Morgon | — |
| MORADESH | — | 85 | Celeste | — |
| MORDIA 9 | — | 208 | Hawking | — |
| MORT | — | 154 | Xzar | — |
| MORTAX PRIME | — | 119 | Arturion | — |
| MOX | — | 266 | Trigon | — |
| MYRADESH | — | 40 | Idun | — |
| MYRIUM | — | 56 | Morgon | — |
| NABATEA SECUNDUS | — | 209 | L'estrade | — |
| NAVI VII | — | 210 | L'estrade | — |
| NEW HAVEN | 纽黑文 | 4 | Altus | 阿尔特斯 |
| NEW INSIGHT | — | 264 | TBD | — |
| NEW KIRUNA | — | 20 | Kelvin | — |
| NEW STOCKHOLM | — | 93 | Hanzo | — |
| NIVEL 43 | — | 211 | Mirin | — |
| NUBLARIA I | — | 26 | Celeste | — |
| OASIS | — | 94 | Rictus | — |
| OBARI | — | 39 | Cantolus | — |
| OKUL VI | — | 13 | Gothmar | — |
| OMICRON | — | 259 | L'estrade | — |
| OSHAUNE | — | 212 | Mirin | — |
| OSLO STATION | — | 106 | Sagan | — |
| OSUPSAM | — | 146 | Tarragon | — |
| OUTPOST 32 | — | 96 | Saleria | — |
| OVERGOE PRIME | — | 213 | Sten | — |
| PANDION-XXIV | — | 214 | Jin Xi | — |
| PARSH | — | 58 | Rictus | — |
| PARTION | — | 215 | Sten | — |
| PATHFINDER V | 开拓者V | 2 | Altus | 阿尔特斯 |
| PEACOCK | — | 216 | Sten | — |
| PENTA | — | 115 | Lacaille | — |
| PHACT BAY | — | 217 | Jin Xi | — |
| PHERKAD SECUNDUS | — | 218 | Farsight | — |
| PILEN V | 皮伦V | 5 | Altus | 阿尔特斯 |
| PIONEER II | — | 121 | Arturion | — |
| POLARIS PRIME | — | 219 | Farsight | — |
| POLLUX 31 | — | 220 | Farsight | — |
| PRASA | — | 221 | Farsight | — |
| PRIMORDIA | — | 24 | Iptus | — |
| PROPUS | — | 222 | Leo | — |
| PROSPERITY FALLS | 繁荣瀑布 | 12 | Cancri | 康谷利伊 |
| PROVIDENCE | — | 23 | Iptus | — |
| PÖPLI IX | — | 107 | Xzar | — |
| RAS ALGETHI | — | 223 | Leo | — |
| RASP | — | 86 | Gallux | — |
| RATCH | — | 71 | Iptus | — |
| RD-4 | — | 224 | Rigel | — |
| REAF | — | 59 | Saleria | — |
| REGNUS | — | 88 | Morgon | — |
| RIRGA BAY | — | 226 | Rigel | — |
| ROGUE 5 | — | 225 | Rigel | — |
| SANGIS | — | 99 | Guang | — |
| SEASSE | — | 227 | Omega | — |
| SENGE 23 | — | 228 | Omega | — |
| SETIA | — | 229 | Omega | — |
| SEYSHEL BEACH | — | 33 | Cancri | 康谷利伊 |
| SHALLUS | — | 46 | Talus | — |
| SHELT | — | 68 | Talus | — |
| SHETE | — | 230 | Xi Tauri | — |
| SIEMNOT | — | 231 | Xi Tauri | — |
| SIRIUS | — | 232 | Xi Tauri | — |
| SKAASH | — | 84 | Ursa | — |
| SKAT BAY | — | 233 | Xi Tauri | — |
| SKITTER | — | 254 | Hawking | — |
| SLIF | — | 52 | Celeste | — |
| SOCORRO III | — | 123 | Falstaff | — |
| SOLGHAST | — | 36 | Gothmar | — |
| SPHERION | — | 234 | Quintus | — |
| STOR THA PRIME | — | 235 | Quintus | — |
| STOUT | — | 236 | Quintus | — |
| SULFURA | — | 25 | Celeste | — |
| SUPER EARTH | 超级地球 | 0 | Sol | 太阳系 |
| TARSH | — | 67 | Marspira | — |
| TERMADON | — | 237 | Quintus | — |
| TERREK | — | 76 | Orion | — |
| THE WEIR | — | 104 | Theseus | — |
| TIBIT | — | 238 | Severin | — |
| TIEN KWAN | — | 239 | Theseus | — |
| TRANDOR | — | 100 | Sten | — |
| TROOST | — | 240 | Trigon | — |
| TURING | — | 126 | Umlaut | — |
| UBANEA | — | 241 | Severin | — |
| URSICA XI | — | 82 | Borgus | — |
| USTOTU | — | 242 | Trigon | — |
| VALGAARD | — | 73 | Iptus | — |
| VALMOX | — | 90 | Rictus | — |
| VANDALON IV | — | 243 | Trigon | — |
| VARYLIA 5 | — | 244 | Trigon | — |
| VEGA BAY | — | 246 | Ymir | — |
| VEIL | — | 30 | Barnard | 巴纳德 |
| VELD | — | 80 | Orion | — |
| VERNEN WELLS | — | 112 | Hydra | — |
| VINDEMITARIX PRIME | — | 248 | Valdis | — |
| VIRIDIA PRIME | — | 38 | Cantolus | — |
| VOG-SOJOTH | — | 117 | Tanis | — |
| VOLTERRA | — | 28 | Korpus | — |
| WASAT | — | 245 | Ymir | — |
| WAYWARD | — | 265 | TBD | — |
| WEZEN | — | 247 | Ymir | — |
| WIDOW'S HARBOR | 寡妇港 | 3 | Altus | 阿尔特斯 |
| WILFORD STATION | — | 120 | Arturion | — |
| WRAITH | — | 18 | Idun | — |
| X-45 | — | 249 | Ymir | — |
| YED PRIOR | — | 250 | Tanis | — |
| ZAGON PRIME | — | 258 | Mirin | — |
| ZEA RUGOSIA | 泽亚鲁戈西亚 | 7 | Ferris | 费里斯 |
| ZEFIA | — | 251 | Tanis | — |
| ZEGEMA PARADISE | — | 22 | Kelvin | — |
| ZOSMA | — | 252 | Gellert | — |
| ZYGOS | — | 271 | Orion | — |
| ZZANIAH PRIME | — | 253 | Gellert | — |

---

## 4. 按星区分组的 index 区间

| 星区 | 中文名 | index 列表 |
|---|---|---|
| Akira | — | 140, 141, 142, 143, 186 |
| Alstrad | — | 188, 189, 190 |
| Altus | 阿尔特斯 | 1, 2, 3, 4, 5 |
| Andromeda | — | 156, 157, 198, 199, 200 |
| Arturion | — | 74, 118, 119, 120, 121, 164, 165 |
| Barnard | 巴纳德 | 6, 8, 9, 10, 30, 31 |
| Borgus | — | 82, 128, 130, 131 |
| Cancri | 康谷利伊 | 11, 12, 32, 33, 35 |
| Cantolus | — | 14, 15, 17, 38, 39 |
| Celeste | — | 25, 26, 27, 51, 52, 85 |
| Draco | — | 78, 169, 170 |
| Falstaff | — | 75, 122, 123, 124 |
| Farsight | — | 175, 218, 219, 220, 221 |
| Ferris | 费里斯 | 7, 176, 178, 180 |
| Gallux | — | 54, 86, 87, 134, 135, 136 |
| Gellert | — | 70, 206, 207, 252, 253 |
| Gothmar | — | 13, 36, 37 |
| Guang | — | 98, 99, 144, 145, 187 |
| Hanzo | — | 93, 137, 138, 139, 182 |
| Hawking | — | 191, 208, 254, 255 |
| Hydra | — | 112, 113, 203 |
| Idun | — | 18, 40, 41, 63 |
| Iptus | — | 23, 24, 47, 48, 71, 73 |
| Jin Xi | — | 129, 171, 172, 173, 214, 217, 268 |
| Kelvin | — | 19, 20, 21, 22, 42 |
| Korpus | — | 28, 29, 53, 81, 83 |
| L'estrade | — | 166, 167, 209, 210, 256, 257, 259 |
| Lacaille | — | 115, 159, 160, 194 |
| Leo | — | 177, 179, 222, 223 |
| Marspira | — | 43, 44, 45, 66, 67 |
| Meridian | — | 61, 62, 102, 103 |
| Mirin | — | 34, 211, 212, 258 |
| Morgon | — | 55, 56, 88, 89 |
| Nanos | — | 72, 109, 110, 111 |
| Omega | — | 184, 185, 227, 228, 229, 273 |
| Orion | — | 16, 49, 76, 77, 79, 80, 127, 269, 271 |
| Quintus | — | 193, 234, 235, 236, 237 |
| Rictus | — | 57, 58, 90, 91, 92, 94, 95 |
| Rigel | — | 181, 183, 224, 225, 226, 272 |
| Sagan | — | 65, 106, 108 |
| Saleria | — | 59, 60, 96, 97 |
| Severin | — | 152, 195, 196, 238, 241 |
| Sol | 太阳系 | 0 |
| Sten | — | 50, 100, 213, 215, 216, 267 |
| TBD | — | 264, 265 |
| Talus | — | 46, 68, 69, 116 |
| Tanis | — | 117, 161, 162, 163, 250, 251 |
| Tarragon | — | 101, 146, 147, 148, 149 |
| Theseus | — | 104, 105, 150, 151, 192, 239 |
| Trigon | — | 158, 240, 242, 243, 244, 262, 266 |
| Umlaut | — | 64, 125, 126, 168, 270 |
| Ursa | — | 84, 132, 133, 174 |
| Valdis | — | 114, 202, 204, 205, 248, 260 |
| Xi Tauri | — | 230, 231, 232, 233 |
| Xzar | — | 107, 153, 154, 155, 197, 261 |
| Ymir | — | 201, 245, 246, 247, 249 |

