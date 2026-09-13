# AGENTS.md — 面向 AI 编码代理的项目约定

腾讯会议网页版自动备份工具（Python）：遍历账号下全部云录制记录，下载视频（`.mp4`）与转写逐字稿（md/txt/srt/json），默认增量模式。

## 必须遵守的原则

1. **变更必须记录 changelog**：任何行为性变更（代码逻辑、接口口径、构建/运行方式）完成后，在 `CHANGELOG.md` 顶部新增条目，说明**改了什么、为什么**；纯错别字类微调可不记。
2. **变更必须提交 git**：一组相关变更完成且自测通过后立即 `git commit`，不留长时间未提交的改动。提交信息用中文：标题行概括，正文列要点。

## 提交前自测

```bash
python3 -m pytest test_backup.py -q   # 全部用例须通过
```

涉及列表遍历/分页/增量状态的改动，另需用 `config.json` 中的真实 cookie **干跑验证**（只遍历不下载）：核对记录总数、标识符唯一性、有视频记录数与改前一致。

## 项目速览

| 文件 | 职责 |
| :--- | :--- |
| `main.py` | 入口：参数解析、输入调度（单条/批量文件/全自动）、增量主循环、状态更新、清理模式分支 |
| `tencent_meeting/client.py` | API 客户端：录制列表分页（30 条/页）、媒体直链（视频/音频，download/meeting）、逐字稿、合集（shared-record-middle）展开、线上删除（delete-record-info） |
| `tencent_meeting/state.py` | 增量状态清单：磁盘引导、原子写回、完成判定、失败熔断 |
| `tencent_meeting/cleaner.py` | 线上清理：可删判定（本地实物校验）、干跑报告、--apply 删除循环、熔断、审计日志 |
| `tencent_meeting/downloader.py` | 流式下载器：断点续传（Range）、进度显示 |
| `tencent_meeting/auto_crawler.py` | Playwright 无头浏览器：打开分享页拦截带 token 的 mp4 直链 |
| `tencent_meeting/formatter.py` / `url_parser.py` | 转写格式化 / 会议链接解析 |

- 状态清单 `downloads/.backup_state.json` 是增量模式的依据，**勿手动删除**。
- 记录标识符口径：`detail_id or recording_id or share_id or meeting_id`，与备份目录命名（`主题_标识符`）一致，改动前先读 `tencent_meeting/state.py`。

## 敏感信息红线（严禁提交）

以下内容已在 `.gitignore`，不得以任何形式带入被跟踪文件：

- `config.json`（含登录 Cookie）、`downloads/`（备份数据）、`有视频的会议记录.md`（个人核对报告）；
- Cookie 字符串、会议标题、回放链接等个人信息不得写入代码、文档或提交信息。

## 关键设计决策（勿回退）

- **列表遍历不做"整页已完成即提前停止"**：已登记 ≠ 已完成，历史中任意一整页已完成记录会挡住更早的未完成记录（如视频下载中断），使增量模式永远补不上（2026-09-13 修复过此缺陷，详见 CHANGELOG）。去重一律由逐条"已完成直跳"承担。
- **列表 `page_size=30`** 为网页端单页上限，勿随意增减；改动分页逻辑需先验证接口返回无重叠、按 `uni_record_id` 降序连续。
- **清理模式安全约定（`--clean`）**：删除线上录制不可恢复，四道关卡缺一不可——默认干跑、`--apply` + 交互确认才真删、可删判定必须含"本地实物校验"（状态完成 ≠ 文件在盘）、合集须全部子记录校验齐备。本地备份文件永不删除；删除动作必须留审计痕迹（`deleted_online` 状态标记 + `.deletion_log.jsonl` 日志）。
