# 项目背景与原始需求 (Project Background & Owner Notes)

## 📌 原始需求概述

开发一个 Python 自动化备份工具，用于批量下载腾讯会议网页版（[meeting.tencent.com](https://meeting.tencent.com)）个人账号下的：
1. 云录制音频/视频文件（MP4/M4A 格式）。
2. 会议实时转写记录（Transcription / 逐字稿）。

---

## 🎯 关键设计目标

- **自动化**：登录 Cookie 配置一次后，自动全量拉取账号下的全部历史会议，无需人工逐个复制会议链接。
- **可靠性**：针对网络波动提供重试机制，针对重复运行提供文件存在校验与跳过功能。
- **多格式支持**：逐字稿转写支持 Markdown（带有时间戳与贯穿发言人）、纯文本 TXT、字幕 SRT 及原始 JSON 导出。
- **规范归档**：建立 `会议主题_记录ID` 的清晰目录层级结构，方便配合 Obsidian、Notion 或本地搜索系统进行知识管理。