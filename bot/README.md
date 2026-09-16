# HELLDIVERSBOT —— QQ 机器人

把 [helldiversbot](../README.md) 的战报 API 接到 QQ 上。功能规格见 [`qqbot.md`](../qqbot.md)。

## 快速开始

```bash
# 1) 起战报 API（另开一个终端，保持运行）
python run.py

# 2) 配置凭据
cp bot/config.example.yaml bot/config.yaml
#    然后填入 appid / secret（示例文件里这两项是空串）

# 3) 安装机器人依赖
pip install -r bot/requirements.txt      # 实际只装 qq-botpy-v2 及其依赖

# 4) 起机器人
python bot/qqbot.py
```

> ⚠️ `bot/config.yaml` 已在 `.gitignore` 里。**不要**把 appid/secret 提交到仓库
> （见根目录 `HINT.md`）。也可以用环境变量注入，见下。

## 部署到 Linux 服务器

### 依赖装在 venv 里（Debian/Ubuntu 必须）

较新的 Debian/Ubuntu 会拦住全局 `pip install`：

```
error: externally-managed-environment
× This environment is externally managed
```

这是 [PEP 668](https://peps.python.org/pep-0668/) 的保护机制，**不要**用
`--break-system-packages` 绕过（可能弄坏系统 Python）。正确做法是虚拟环境：

```bash
# 只在报「No module named venv」时才需要
sudo apt install -y python3-venv python3-full

cd ~/hd2/illegalbroadcast
python3 -m venv .venv
source .venv/bin/activate

pip install -r bot/requirements.txt
python bot/qqbot.py
```

之后每次启动都要先 `source .venv/bin/activate`。

### ⚠️ 包名别打错

| 包名 | 说明 |
|---|---|
| **`qq-botpy-v2`** | ✅ 本项目用的就是这个（导入名仍是 `botpy`） |
| `qq-botpy` | ⚠️ 腾讯官方原版，**是另一个库**，不保证有 QQ群 / C2C 那套 v2 接口 |
| `qqbot` | ⚠️ 完全无关的老项目（SmartQQ） |
| `qqbot-py-v2` | ❌ **不存在**（PyPI 404） |

### 部署后是两个进程

| 进程 | 命令 | 端口 |
|---|---|---|
| 战报 API | `python run.py` | 8808（仅本机） |
| QQ 机器人 | `python bot/qqbot.py` | 无（主动连 QQ 网关） |

API 只用标准库，**不需要**装任何依赖；机器人反过来跟 `--fastapi` 那套无关。
`config.yaml` 里的 `api_base` 同机部署时保持 `http://127.0.0.1:8808` 即可。

### systemd 示例

```ini
# /etc/systemd/system/helldivers-api.service
[Unit]
Description=helldiversbot API
After=network-online.target

[Service]
User=scmt
WorkingDirectory=/home/scmt/hd2/illegalbroadcast
ExecStart=/home/scmt/hd2/illegalbroadcast/.venv/bin/python run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/helldivers-bot.service
[Unit]
Description=helldiversbot QQ bot
After=network-online.target helldivers-api.service

[Service]
User=scmt
WorkingDirectory=/home/scmt/hd2/illegalbroadcast
ExecStart=/home/scmt/hd2/illegalbroadcast/.venv/bin/python bot/qqbot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now helldivers-api helldivers-bot
journalctl -u helldivers-bot -f
```

> `WorkingDirectory` 设成项目根目录：botpy 把 `botpy.log` 写在**当前工作目录**，
> 从根目录起就落在 `./botpy.log`（已在 `.gitignore` 里）。

## 命令

| 命令 | 别名 | 参数 | 说明 |
|---|---|---|---|
| `/p` | `/planet` | 星球名或 index | 单颗星球战报 |
| `/d` | `/dispatch` | 无 | 最新一条游戏内快讯 |
| `/t` | `/trending` | 无 | 在线绝地潜兵最多的 5 颗星球 |
| `/help` | `/h` | 无 | 帮助信息 |

私聊里直接发命令；群聊/频道里 `@机器人` 再加命令。命令大小写不敏感。

### 帮助信息

`/help` 的文案以 [`qqbot.md`](../qqbot.md) 的 **Help Message** 段为准：

```plaintext
/p 或 /planet <星球名/星球索引> : 获取星球数据
/d 或 /dispatch : 获取当前的战役新闻
/t 或 /trending : 获取当前热门星球
/help : 显示此帮助信息

示例：
/p CYBERSTAN 显示生化斯坦的详细信息
/planet 0 显示超级地球的详细信息
```

`tests/test_qqbot.py::test_help_message_matches_qqbot_md` 会校验
`commands.USAGE` 与 `qqbot.md` 里那段逐字一致——改了文档忘了改代码会直接测试失败。

### 解析不出命令时

未知命令（`/xyz`）、不接受参数的命令被塞了参数（`/d foo`、`/t 5`）、
以及压根不是命令的消息，都统一回：

```plaintext
未知的参数或命令。请使用/help查看相关帮助
```

两种例外：

* `/p` **少给**参数（这是「没给」而不是「给错」）→ `请给出星球名或编号，例如 /p BEKVAM III、/p 262。`
* `/help` 后面跟东西（`/help me`）→ 照常显示帮助

### 示例

```
/p BEKVAM III          →  防御战版式（8 行）
/p 262                 →  用 index 查
/p CHARBAL-VII         →  名字里有连字符也没问题
/d                     →  最新快讯
/t                     →  最激烈的星球排行
```

`/p` 的实际输出由 API 的 `?mode=md` 决定，解放战和防御战是两套版式
（见 [README_fancy.md](../README_fancy.md) 与主 README 的 §3.5）：

```plaintext
星球名：BEKVAM III
分区：NANOS
所属阵营：机器人
已防御：15.0787%
预测：失败
剩余时间：4小时14分
部署的绝地潜兵数：7223
数据获取时间：2026-09-14 23:00:47
```

最后一行的**北京时间**由 API 侧格式化好（精确到秒），机器人原样转发。

## 支持的消息类型

QQ 开放平台有四类消息能触发机器人，本实现全都覆盖：

| 场景 | botpy 事件 | Intents 标志 |
|---|---|---|
| 频道里 @机器人 | `on_at_message_create` | `public_guild_messages` |
| 频道的私信 | `on_direct_message_create` | `direct_message` |
| QQ 群里 @机器人 | `on_group_at_message_create` | `public_messages` |
| QQ 私聊 | `on_c2c_message_create` | `public_messages` |

四者走同一套处理流程，回复都带引用。`@机器人` 前缀（`<@!1234>` / `<@1234>`）
会被剥掉再解析命令。

## 配置

优先级：**环境变量 > `config.yaml` > 默认值**。

| config.yaml | 环境变量 | 默认 | 说明 |
|---|---|---|---|
| `appid` | `QQBOT_APPID` | — | QQ 机器人 AppID（必填） |
| `secret` | `QQBOT_SECRET` | — | QQ 机器人 Secret（必填） |
| `api_base` | `QQBOT_API_BASE` | `http://127.0.0.1:8808` | 战报 API 地址 |
| `max_reply_chars` | `QQBOT_MAX_CHARS` | `900` | 单条回复字符上限，超出会截断并标注 |
| `http_timeout` | `QQBOT_HTTP_TIMEOUT` | `20` | 请求 API 的超时（秒） |

全部用环境变量启动（不落盘任何密钥）：

```powershell
$env:QQBOT_APPID="123456"; $env:QQBOT_SECRET="xxx"; python bot/qqbot.py
```

```bash
QQBOT_APPID=123456 QQBOT_SECRET=xxx python bot/qqbot.py
```

## 文件说明

| 文件 | 作用 |
|---|---|
| `qqbot.py` | 入口：botpy 客户端，四类事件的接线 |
| `commands.py` | 命令解析与回复生成（**不依赖 botpy**，可单独测） |
| `hd2_api.py` | 战报 API 的异步客户端，把各种失败翻译成中文提示 |
| `requirements.txt` | 机器人依赖（只有 `qq-botpy-v2`） |
| `config.example.yaml` | 配置模板 |
| `config.yaml` | 真实凭据（**不入库**） |
| `demo_at_reply.py` / `demo_dms_reply.py` | botpy 官方示例，保留作参考 |

## 出错时的表现

机器人不会因为出错掉线，也不会把堆栈甩给用户：

| 情况 | 回复 |
|---|---|
| API 没启动 | `战报服务连不上（http://127.0.0.1:8808）。请先在项目根目录运行 python run.py 启动 API。` |
| 星球不存在 | `未找到星球: XXX` |
| API 拿不到上游数据 | `战报服务暂时拿不到上游数据，稍后再试。` |
| 请求超时 | `战报服务响应超时，稍后再试。` |
| 未知命令 / 未知参数 / 不是命令 | `未知的参数或命令。请使用/help查看相关帮助` |
| `/p` 少给参数 | `请给出星球名或编号，例如 /p BEKVAM III、/p 262。` |
| 其它意外异常 | `处理这条命令时出错了，稍后再试。`（详情写进日志） |

## 日志

botpy 把日志写在**当前工作目录**的 `botpy.log`：

* 从根目录启动 → `./botpy.log`
* 从 `bot/` 里启动 → `bot/botpy.log`

两个位置都在 `.gitignore` 里。想看机器人收了什么、回了什么，看这个文件即可
（每条消息都会以 `[频道@]` / `[QQ群@]` / `[QQ私聊]` / `[频道私信]` 打点）。

## 测试

```bash
python tests/test_qqbot.py          # 55 项（含 11 项端到端）
# 或者从项目根目录跑全量：
python research/run_all_tests.py
```

* **离线**：命令解析、`@前缀` 剥离、格式化、错误分支、截断（用假客户端）
* **在线**：对着真实 API 跑三个命令的端到端流程

关于那 11 项在线用例：API 没起时它们会被**跳过**，同时往 stderr 打一条醒目警告
（不会静默通过）。如果是在部署验证 / CI 里跑，希望「API 没起」直接算失败：

```bash
QQBOT_REQUIRE_LIVE=1 python tests/test_qqbot.py
```

## 已知限制

* **无法在本机端到端自测。** 消息由 QQ 服务器推过来，只能验证到「机器人连上网关」
  和「命令处理逻辑正确」这两层；真正的收发要在 QQ 里发消息试。
* **`/t` 的格式是本项目自定的。** `qqbot.md` 只写了「Planets have most players」，
  没给示例，所以按防御/解放两种状态分别显示进度。要改格式改
  `commands.py::format_trending` 即可。
* **回复长度上限 900 字符**是保守估计。QQ 的具体限额随消息类型不同，
  如果发现长快讯被平台截断，调小 `max_reply_chars`。
