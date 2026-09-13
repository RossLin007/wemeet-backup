# 腾讯会议自动备份工具 (backup-tencent-meetings)

一键遍历并批量下载**腾讯会议网页版**账号下所有历史会议的云录制视频（`.mp4`）、纯音频（`.m4a`）与转写逐字稿（`.md` / `.txt` / `.srt` / `.json`）。默认增量运行：日常备份只处理新增或未完成的记录，通常一分钟内完成；配合断点续传与失败熔断，长时间无人值守跑全量也稳。

---

## ✨ 功能特性

- 🤖 **账号全量自动遍历**：无需手动收集会议链接，自动通过 API 分页拉取您账号下记录的所有历史会议列表。
- 🔗 **多类型场景兼容**：完美支持单会议录制、合集记录、以及包含多段视频的"中间记录页面"（`shared-record-middle`）自动递归展开。
- 📝 **多格式逐字稿导出**：转写纪要自动导出为 **Markdown (`.md`)**、**纯文本 (`.txt`)**、**SRT 字幕 (`.srt`)** 及**原始 JSON (`.json`)** 格式。
- 🎬 **音视频及封面自动拉取**：优先通过网页端"另存为"同源接口（`download/meeting`）直接解析带 token 的视频直链，流式下载（支持断点续传）；解析失败时回退无头浏览器拦截直链。
- 🎧 **纯音频文件备份**：与网页端"另存为 → 纯音频文件"同源，按 `audio_{标识符}.m4a` 保存，支持断点续传；`download_audio` 开关控制，中途开启也能自动补齐历史记录。
- 🔄 **默认增量备份**：本地状态清单（`downloads/.backup_state.json`）记录每条记录的处理状态，已完成记录不再调用任何接口、不再启动浏览器；列表始终完整遍历（30 条/页）以保证历史未完成记录（如中断的视频下载）总能被补齐。
- ⚡ **智能重用与断点跳过**：已完成备份的音视频与转写文件自动识别校验，防止重复下载浪费带宽；首次运行自动扫描本地已有备份生成初始清单，无需任何迁移操作。
- 📶 **大文件断点续传**：视频下载中断时自动保留已下载部分并携带 Range 头续传重试（最多 5 次），重试耗尽仍失败时保留进度，下次运行自动接着下，大文件不再前功尽弃。
- 🔁 **失败智能重试**：下载/导出失败的记录按次数有限重试（连续失败 3 次后不再自动重试），避免个别问题记录拖慢整体备份，`--full` 可强制重试。
- 📊 **实时下载进度条**：分块下载实时展示已下载大小、百分比与速度。
- ⚙️ **灵活配置与 CLI 命令**：既可通过 `config.json` 简易配置，也可通过丰富的命令行参数精准控制。

---

## 🧭 工作原理

### 备份流水线（单条录制记录）

```text
列表 API 拿到记录 (meeting_id / recording_id / detail_id / has_video / uni_record_id)
        │
        ├─ 解析媒体直链 (download/meeting)：视频 link + 纯音频 audio_link，
        │   按资源 ID 分发到单条记录或合集的各子记录
        │
        ├─ 合集记录？ ──是──> 调合集展开接口拆成子记录，逐条进入本流程
        │
        ├─ ① 录像封面：cover.png 直接下载
        ├─ ② 云录制视频：媒体直链流式下载（断点续传）；
        │     直链不可用时回退无头浏览器打开分享页拦截 /sign 直链
        ├─ ③ 纯音频文件：audio_link 直链下载 audio_{标识符}.m4a（断点续传）
        └─ ④ 转写逐字稿：调 minutes 接口 → 格式化导出 md/txt/srt/json
        │
        └─ 按处理结果更新增量状态清单（原子写回 .backup_state.json）
```

### 输入来源优先级

| 优先级 | 来源 | 说明 |
| :--- | :--- | :--- |
| 1 | 命令行单条参数 | `--meeting-id` / `--recording-id` / `--share-id` 任一指定时启用 |
| 2 | 批量文件 | `-f meetings.txt`，每行一个会议链接或 `meeting_id,recording_id` |
| 3 | 全自动模式（默认） | API 分页遍历账号下全部录制记录 |

### 增量模式核心机制

- **状态清单**：`downloads/.backup_state.json` 以记录标识符（`detail_id` or `recording_id` or `share_id` or `meeting_id`，与目录命名口径一致）为键，跟踪每条记录的状态。
- **首次引导**：无状态文件时自动扫描 `downloads/` 已有备份目录（目录名按最后一个 `_` 拆分取标识符）生成初始清单；磁盘上无法区分"记录本身无视频"与"视频下载失败"，此类记录视频状态先记 `unknown`，运行中按 API 的 `has_video` 字段对账修正。
- **完整遍历**：录制列表按新→旧排序、30 条/页（网页端单页上限）拉全，不做"整页已完成即提前停止"——历史中任意一整页已完成记录都会挡住更早的未完成记录，使其永远补不上；翻页只是轻量 API 调用，去重开销由"已完成直跳"承担。
- **已完成直跳**：转写与视频均就绪的记录不再调逐字稿接口、不再展开合集、不启动浏览器；文件级校验保留作双保险。
- **失败熔断**：连续失败 3 次的记录增量模式不再自动重试。
- **合集容器**：合集父记录仅在**全部子记录备份完成**后才标记为完成容器，否则每次运行重新展开，确保未完成的子记录不会被父记录的完成态挡住。
- **`--full` 强制全量**：无视完成状态逐条重检（重试失败熔断记录、重新展开合集），已存在的文件仍不会重复下载。

---

## 🏗️ 项目结构

```text
backup-tencent-meetings/
├── main.py                     # 入口：参数解析、输入调度、增量主循环、状态更新
├── config.example.json         # 配置文件模板（复制为 config.json 后填写）
├── requirements.txt            # Python 依赖
├── test_backup.py              # 单元测试（python3 test_backup.py）
├── meetings.txt                # 批量备份链接列表（可选）
├── docs/                       # 深入文档
│   ├── architecture.md         # 系统架构与模块设计
│   ├── api.md                  # 腾讯会议 API 逆向参考
│   └── owner.md                # 原始需求与开发背景
└── tencent_meeting/
    ├── client.py               # API 客户端：录制列表分页（30 条/页）、逐字稿、合集展开、线上删除
    ├── state.py                # 增量状态清单：加载/磁盘引导/原子写回/完成判定/失败计数
    ├── cleaner.py              # 线上清理：可删判定（本地实物校验）、干跑报告、--apply 删除/熔断/审计日志
    ├── auto_crawler.py         # Playwright 无头浏览器：打开分享页拦截带 token 的 mp4 直链
    ├── downloader.py           # 流式分块下载器：断点续传（Range）、进度显示、临时文件改名
    ├── formatter.py            # 转写数据格式化：Markdown / TXT / SRT / JSON
    └── url_parser.py           # 会议链接解析（含 shared-record-middle 合集链接）
```

### 调用的腾讯会议接口

| 接口 | 用途 |
| :--- | :--- |
| `POST /wemeet-tapi/v2/meetlog/dashboard/my-record-list` | 录制列表，分页遍历（page_size=30，网页端单页上限） |
| `GET /wemeet-cloudrecording-webapi/v1/download/meeting` | 媒体下载直链（视频 `link` + 纯音频 `audio_link`），网页端"另存为"菜单同源 |
| `GET /wemeet-cloudrecording-webapi/v1/minutes/detail` | 转写逐字稿 |
| `POST /wemeet-tapi/v2/meetlog/record-detail/page-query-record-files` | 合集（shared-record-middle）展开为子记录 |
| `POST /wemeet-tapi/v2/meetlog/dashboard/delete-record-info` | 删除线上录制记录（清理模式，网页端"管理→删除"同源） |
| `GET /wemeet-cloudrecording-webapi/v1/sign` | 分享页内签发的带 token 视频直链（浏览器拦截获取） |

---

## 🚀 快速开始

### 1. 安装依赖环境

确保本地已安装 Python 3.8+，克隆项目后运行：

```bash
pip install -r requirements.txt
```

如需下载**视频**（默认启用），还需要 Playwright 及其 Chromium 内核（仅导出转写逐字稿可跳过此步）：

```bash
pip install playwright
playwright install chromium
```

> 说明：`requests` 未安装时下载器会自动回退到 Python 内置的 `urllib`，功能不受影响。

### 2. 获取并配置 Cookie (`config.json`)

1. 复制配置文件模板：
   ```bash
   cp config.example.json config.json
   ```
2. 用浏览器打开并登录 [腾讯会议网页版个人中心](https://meeting.tencent.com/user-center/meeting-record)。
3. 按 `F12` 开启开发者工具（Developer Tools），切换到 **Network (网络)** 标签页。
4. 刷新页面，点击任意一个 `meeting.tencent.com` 的网络请求。
5. 在请求头 (Request Headers) 中找到 `Cookie`，复制其完整的字符串值。
6. 粘贴至 `config.json` 中的 `"cookie"` 属性（见下方配置说明）。

> Cookie 存在有效期（关键字段如 `we_meet_token`），过期后列表拉取会失败，重新登录复制一份即可。

### 3. 执行一键备份

```bash
python3 main.py
```

首次运行会自动扫描本地已有备份生成增量清单，之后默认增量运行；脚本将自动遍历账号下全部历史会议并把结果保存到 `./downloads/`。

---

## ⚙️ 配置说明（config.json）

| 字段 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `cookie` | string | 必填 | 腾讯会议网页端完整 Cookie 字符串 |
| `output_dir` | string | `./downloads` | 备份输出根目录 |
| `download_video` | bool | `true` | 是否下载云录制视频 |
| `download_audio` | bool | `false` | 是否下载纯音频文件（`audio_{标识符}.m4a`，网页端"另存为-纯音频文件"同源）；中途开启会自动补齐历史记录 |
| `export_transcript` | bool | `true` | 是否导出转写逐字稿 |
| `transcript_formats` | list | `["md","txt","json","srt"]` | 转写导出格式 |
| `user_agent` | string | Chrome UA | 自定义请求 User-Agent（一般无需修改） |

---

## 💡 CLI 参数与示例

命令行参数优先级高于 `config.json`：

| 命令行参数 | 简写 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `--config` | `-c` | `config.json` | 指定配置文件路径 |
| `--output` | `-o` | `./downloads` | 自定义下载输出根目录 |
| `--cookie` | | 无 | 在命令行直接指定 Cookie 字符串 |
| `--meeting-id` | | 无 | 仅备份指定的单个 Meeting ID |
| `--recording-id` | | 无 | 仅备份指定的单个 Recording ID |
| `--share-id` | | 无 | 仅备份指定的 Share ID (分享 Token `s`)，支持合集链接 |
| `--file` | `-f` | 无 | 从文本文件批量读取链接列表备份 |
| `--topic` | | `腾讯会议` | 配合单条参数指定会议主题命名 |
| `--formats` | | `md,txt,json,srt` | 指定导出的转写文本格式（逗号分隔） |
| `--no-video` | | `False` | 加上此参数跳过视频 MP4 下载 |
| `--no-audio` | | `False` | 跳过音频（预留，当前无独立音频流） |
| `--no-transcript` | | `False` | 加上此参数跳过转写逐字稿导出 |
| `--full` | | `False` | 忽略增量状态强制全量备份（重试失败记录、重新展开合集，已存在文件不重复下载） |
| `--clean` | | `False` | 清理模式：核对本地备份后列出可安全删除的线上有视频记录（默认干跑不删除） |
| `--apply` | | `False` | 配合 `--clean` 真正执行线上删除（不可恢复；本地备份保留） |
| `--yes` | | `False` | 配合 `--clean --apply` 跳过交互确认（脚本化场景） |
| `--limit` | | 无 | 配合 `--clean --apply`：本次最多删除 N 条（旧记录优先） |

#### 示例 1：仅导出转写逐字稿，不下载视频

```bash
python3 main.py --no-video
```

#### 示例 2：备份单个特定会议

```bash
python3 main.py --share-id "sKOvc8uzP0m3wKeqOf4B4" --topic "重要项目周会"
```

> `--share-id` 以 `-` 开头时需用 `=` 赋值：`--share-id="-310xfpSk1TbfjGuE502rd83u08f"`

#### 示例 3：批量备份链接文件

```bash
python3 main.py -f meetings.txt
```

#### 示例 4：强制全量（补齐失败记录 / 合集新增了子记录 / 怀疑有遗漏）

```bash
python3 main.py --full
```

#### 示例 5：清理线上已备份的录制，释放云存储空间

```bash
python3 main.py --clean                     # ① 干跑：列出可安全删除的清单（不删任何数据）
python3 main.py --clean --apply --limit 1   # ② 试删最旧的 1 条，到网页端确认后再放开
python3 main.py --clean --apply             # ③ 批量删除（交互确认需输入待删条数）
```

> **删除不可恢复**（连带线上转写与分享链接），因此工具设有硬性关卡：只有「线上有视频 + 增量状态已完成 + 本地视频/转写/音频文件逐一在盘校验 + 线上 allow_delete」全部满足才进入待删清单；合集须全部子记录校验齐备。本地备份文件永不删除。每次删除写入审计日志 `downloads/.deletion_log.jsonl` 并在状态清单标记 `deleted_online`。建议先跑一次常规增量备份（`python3 main.py`）再清理。

---

## 📁 备份保存结构

备份文件按 `会议主题_记录标识符` 建立独立文件夹分类存放：

```text
downloads/
├── .backup_state.json                                          # 增量状态清单（勿手动删除）
├── 选修课总结复盘_b4d20ddb-9464-41e2-a613-e3259c67baa6/
│   ├── cover_b4d20ddb-9464-41e2-a613-e3259c67baa6.png          # 录像封面
│   ├── video_b4d20ddb-9464-41e2-a613-e3259c67baa6.mp4          # 云录制视频
│   ├── audio_b4d20ddb-9464-41e2-a613-e3259c67baa6.m4a          # 纯音频文件（可选）
│   ├── transcript_b4d20ddb-9464-41e2-a613-e3259c67baa6.md      # Markdown 转写
│   ├── transcript_b4d20ddb-9464-41e2-a613-e3259c67baa6.txt     # 纯文本转写
│   ├── transcript_b4d20ddb-9464-41e2-a613-e3259c67baa6.srt     # SRT 播放字幕
│   └── transcript_b4d20ddb-9464-41e2-a613-e3259c67baa6.json    # 原始 API 数据
└── ...
```

下载中的文件以 `video_xxx.mp4.tmp` 暂存，完成后原子改名；中断保留的 `.tmp` 会在下次运行时断点续传。

### 状态清单字段说明（.backup_state.json）

```jsonc
{
  "records": {
    "b4d20ddb-9464-41e2-a613-e3259c67baa6": {   // 键 = 记录标识符
      "topic": "选修课总结复盘",                   // 会议主题
      "transcript_done": true,                    // 转写是否已导出
      "video": "done",                            // done | skipped | unknown | failed
      "audio": "done",                            // done | skipped | unknown | failed | off
      "fails": 0,                                 // 连续失败次数（达 3 次增量不再自动重试）
      "container": false,                         // 是否为已完成的合集容器记录
      "updated_at": "2026-09-13 16:09:00"
    }
  }
}
```

`video` 取值：`done`=视频已下载；`skipped`=该记录类型本身无视频（纯转写）；`unknown`=磁盘引导时无法判断、待与 API 对账；`failed`=下载失败。`audio` 取值同 `video`，另多一个 `off`=配置未启用音频下载（启用后会自动重置为待对账，补齐历史记录）。

---

## 🧪 运行测试

```bash
python3 test_backup.py
```

覆盖转写格式化、链接解析、下载器跳过/断点续传（本地 HTTP 服务实测 Range 续传与服务端忽略 Range 时的从头重写）、增量状态清单（磁盘引导、损坏回退、标识符口径）、合集容器误标回归等 17 个用例。

---

## ❓ 常见问题 FAQ & 避坑指南

> [!IMPORTANT]
> **Q: 运行提示 `[错误] 未配置有效的 Cookie！` 或获取列表为空？**
> * **原因**：腾讯会议网页端 Cookie 已失效或未复制完整。
> * **解决**：在腾讯会议网页端重新登录后，重新复制包含 `we_meet_token` 与 `account_corp_id` 的完整 Cookie 并更新至 `config.json`。

> [!NOTE]
> **Q: 为什么部分会议显示 `[已跳过] 该记录类型为纯文字转写/语音记录`？**
> * **原因**：腾讯会议区分"云录制"（有视频画面）与"实时转写/语音记录"（仅有文字/音频）。对于后者，腾讯会议服务器本身不提供视频文件，脚本会自动跳过视频下载并成功导出转写文本。

> [!TIP]
> **Q: 重复运行脚本会重新下载已有文件吗？**
> * **原因**：脚本内置了文件校验机制，如果目标文件已存在且文件大小大于 0，会自动提示 `[已跳过]` 并快速继续下一场会议，无需担心重复消耗带宽。

> [!TIP]
> **Q: 增量模式是怎么工作的？什么情况需要 `--full`？**
> * **原理**：脚本在 `downloads/.backup_state.json` 维护一份状态清单，记录每条录制记录的备份状态。默认运行时：完整遍历列表（30 条/页，账号记录多时约半分钟）但已完成的记录直接跳过（不调转写接口、不启动浏览器解析视频）；之前失败的记录最多自动重试 3 次。
> * **首次运行**会自动扫描本地已有备份目录生成初始清单，无需手动迁移。
> * **需要 `--full` 的场景**：怀疑有遗漏、需要重试连续失败 3 次以上的记录、或合集页面在服务端新增了子记录。全量模式会重新遍历所有页面并逐条检查，但已存在的文件仍不会重复下载。

> [!NOTE]
> **Q: 手动移动/整理过 `downloads/` 里的文件会影响增量判断吗？**
> * 状态清单以记录 ID（而非文件路径）为键，目录位置变动不影响"已备份"的判定；但若删除了某个产物文件，增量模式默认不会重新下载（清单已标记完成），此时用 `--full` 可补齐。

> [!IMPORTANT]
> **Q: 视频下载报 `HTTP Error 403: Forbidden`，但浏览器里能正常播放？**
> * **原因**：腾讯服务端可能对旧会话的媒体访问整体拒绝（连之前能下载的记录也一起 403），而列表与转写接口不受影响。此时往往是本地 Cookie 对应的会话已失效。
> * **解决**：在浏览器重新打开录制分享页确认视频可播放，然后复制**最新** Cookie 更新到 `config.json` 再运行；若浏览器里同样无法播放，则是腾讯侧问题，等待恢复后用 `--full` 补齐即可（失败记录已被状态清单记录，不会遗漏）。

> [!NOTE]
> **Q: 网页端"另存为"菜单有 4 种下载（视频内容/纯音频文件/逐字稿文本/时间轴文本），本工具都有备份吗？**
> * **视频内容** → `video_{标识符}.mp4`；**纯音频文件** → `audio_{标识符}.m4a`（需开启 `download_audio`）。
> * **逐字稿文本 / 时间轴文本** → 由转写导出覆盖：`transcript_{标识符}.md` / `.txt`（逐字稿阅读版）与 `.srt`（带时间轴的字幕版）、`.json`（原始数据）。

> [!NOTE]
> **Q: 视频下载到一半失败（超时/连接中断），之前的进度白下了吗？**
> * 不会。下载器会保留 `.tmp` 已下载部分并自动携带 Range 头断点续传（最多重试 5 次）；即使重试耗尽，下次运行（或 `--full`）也会从断点接着下。

> [!NOTE]
> **Q: 日志里出现 `Page.goto: Timeout 30000ms exceeded` / `networkidle` 超时提示？**
> * 属正常现象：分享页持续有网络请求，`networkidle` 条件基本不会满足。脚本已做了容错处理，只要后续出现"捕获到高清视频资源地址"即表示直链拦截成功。

---

## 📚 更多文档

- 🛠️ [系统架构与模块设计文档](docs/architecture.md)
- 📡 [腾讯会议 API 逆向工程参考](docs/api.md)
- 📝 [原始需求与开发背景说明](docs/owner.md)
- 📋 [更新日志](CHANGELOG.md)
