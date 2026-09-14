#!/usr/bin/env python3
import os
import sys
import glob
import json
import argparse
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List

from tencent_meeting.client import TencentMeetingClient
from tencent_meeting.formatter import (
    format_to_markdown,
    format_to_txt,
    format_to_srt,
    format_to_json
)
from tencent_meeting.downloader import download_file
from tencent_meeting.url_parser import parse_tencent_meeting_url
from tencent_meeting.auto_crawler import fetch_and_download_video_with_browser
from tencent_meeting.state import (
    AUDIO_OFF,
    AUDIO_SKIPPED,
    AUDIO_UNKNOWN,
    MAX_FAILURES,
    VIDEO_SKIPPED,
    is_complete,
    load_state,
    new_entry,
    record_identifier,
    save_state,
    touch
)
from tencent_meeting.cleaner import run_cleaner


def sanitize_filename(name: str) -> str:
    """Sanitizes strings for safe use in file/directory names."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, "_")
    return name.strip()


def load_config(config_path: str) -> Dict[str, Any]:
    """Loads configuration from JSON file."""
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[警告] 无法读取配置文件 {config_path}: {e}")
        return {}


def _find_dirs_by_identifier(output_dir: str, identifier: str) -> List[str]:
    """按 `主题_标识符` 命名约定列出该标识符的全部本地备份目录（精确后缀匹配）。"""
    if not identifier:
        return []
    hits = []
    for path in glob.glob(os.path.join(output_dir, f"*_{identifier}")):
        if os.path.isdir(path) and os.path.basename(path).rsplit("_", 1)[-1] == identifier:
            hits.append(path)
    return hits


def migrate_legacy_dir(output_dir: str, folder_name: str, identifier: str) -> None:
    """云端会议改名后主题变化：若新主题目录不存在而旧主题目录（同标识符）唯一存在，
    自动迁移目录名跟随改名；否则不动作（保持由本次备份正常创建/写入）。

    防止按新主题另建目录造成同标识符双目录——那会令清理模式的本地目录唯一定位失效。
    """
    target = os.path.join(output_dir, folder_name)
    if os.path.exists(target):
        return
    legacy = [d for d in _find_dirs_by_identifier(output_dir, identifier)
              if os.path.basename(d) != folder_name]
    if len(legacy) == 1:
        print(f"[改名迁移] 检测到该记录的旧主题目录，跟随云端改名迁移: "
              f"{os.path.basename(legacy[0])} -> {folder_name}")
        os.rename(legacy[0], target)


def process_single_backup(
    client: TencentMeetingClient,
    meeting_id: str,
    recording_id: str,
    share_id: str,
    detail_id: str,
    output_dir: str,
    download_video: bool,
    download_audio: bool,
    export_transcript: bool,
    formats: List[str],
    topic: str = "腾讯会议",
    cover_url: str = "",
    jump_path: str = "",
    has_video: bool = True,
    minutes_paragraphs: List[Any] = None,
    video_url: str = "",
    audio_url: str = "",
    media_links_ok: bool = False
) -> Dict[str, Any]:
    """Processes backup for a single meeting recording.

    Returns a result dict: {"ok": bool, "transcript": ..., "video": ..., "audio": ...}，
    其中 transcript ∈ done/exists/failed/off，video ∈ done/exists/skipped/failed/none/off，
    audio ∈ done/exists/skipped/failed/none/off（none=直链未解析到，保留原状态待重试），
    供增量状态清单更新使用。
    """
    safe_topic = sanitize_filename(topic)
    identifier = record_identifier(
        detail_id=detail_id, recording_id=recording_id,
        share_id=share_id, meeting_id=meeting_id
    )
    folder_name = f"{safe_topic}_{identifier}"
    target_dir = os.path.join(output_dir, folder_name)
    migrate_legacy_dir(output_dir, folder_name, identifier)
    os.makedirs(target_dir, exist_ok=True)

    print(f"\n==================================================")
    print(f"正在处理会议: {topic}")
    print(f"Meeting ID: {meeting_id} | Recording ID: {recording_id} | Detail ID: {detail_id}")
    print(f"保存路径: {target_dir}")
    print(f"==================================================")

    result = {"ok": False, "transcript": "off", "video": "none", "audio": "off"}
    dl_headers = {"Cookie": client.cookie_str, "Referer": "https://meeting.tencent.com/"}

    # 1. 下载录像封面资源
    if cover_url:
        print("[1/4] 正在获取并保存录像封面资源...")
        cover_path = os.path.join(target_dir, f"cover_{identifier}.png")
        download_file(cover_url, cover_path, overwrite=False)

    # 2. 下载会议视频 MP4 (优先媒体直链，失败回退浏览器；非视频记录类型自动跳过)
    if download_video:
        print("[2/4] 正在检查/拉取会议视频 (.mp4)...")
        if not has_video:
            print(" -> [已跳过] 该记录类型为纯文字转写/语音记录，不包含视频画面。")
            result["video"] = "skipped"
        else:
            target_video_path = os.path.join(target_dir, f"video_{identifier}.mp4")
            if os.path.exists(target_video_path) and os.path.getsize(target_video_path) > 0:
                print(f" -> [已跳过] 视频文件已存在且非空: {target_video_path}")
                result["video"] = "exists"
            else:
                downloaded = False
                attempted = False
                if video_url:
                    attempted = True
                    print(" -> 使用录制媒体直链下载（支持断点续传）...")
                    downloaded = download_file(video_url, target_video_path, headers=dl_headers)
                if not downloaded:
                    target_url = jump_path or (f"/meeting-record/shares?id={detail_id or share_id}" if (detail_id or share_id) else "")
                    if target_url:
                        attempted = True
                        if video_url:
                            print(" -> 直链下载未成功，回退无头浏览器抓取...")
                        downloaded = fetch_and_download_video_with_browser(
                            jump_path_or_url=target_url,
                            cookie_str=client.cookie_str,
                            dest_path=target_video_path
                        )
                if attempted:
                    result["video"] = "done" if downloaded else "failed"
                else:
                    print(" -> [已跳过] 未找到可解析的视频页面地址。")
    else:
        result["video"] = "off"

    # 3. 下载纯音频文件 (.m4a，与网页端"另存为-纯音频文件"同源)
    if download_audio:
        print("[3/4] 正在检查/拉取纯音频文件 (.m4a)...")
        if not has_video:
            print(" -> [已跳过] 该记录类型为纯文字转写/语音记录，无独立音频文件。")
            result["audio"] = "skipped"
        else:
            existing_audio = None
            for ext in (".m4a", ".mp3", ".aac", ".wav"):
                p = os.path.join(target_dir, f"audio_{identifier}{ext}")
                if os.path.exists(p) and os.path.getsize(p) > 0:
                    existing_audio = p
                    break
            if existing_audio:
                print(f" -> [已跳过] 音频文件已存在且非空: {existing_audio}")
                result["audio"] = "exists"
            elif not media_links_ok:
                # 直链接口未成功：不动音频状态（保留 unknown），下次运行重试
                print(" -> [待重试] 媒体直链未解析成功，音频保留待对账状态。")
                result["audio"] = "none"
            elif not audio_url:
                # 直链已解析但该录制无音频地址：视为本身无独立音频文件
                print(" -> [已跳过] 该录制不提供独立音频文件。")
                result["audio"] = "skipped"
            else:
                audio_ext = os.path.splitext(urllib.parse.urlsplit(audio_url).path)[1].lower()
                if audio_ext not in (".m4a", ".mp3", ".aac", ".wav"):
                    audio_ext = ".m4a"
                target_audio_path = os.path.join(target_dir, f"audio_{identifier}{audio_ext}")
                downloaded_audio = download_file(audio_url, target_audio_path, headers=dl_headers)
                result["audio"] = "done" if downloaded_audio else "failed"
    else:
        result["audio"] = "off"

    # 4. 导出转写记录 (如各格式转写文件均已存在则直接跳过)
    if export_transcript:
        print("[4/4] 正在获取会议转录记录 (Minutes)...")
        base_path = os.path.join(target_dir, f"transcript_{identifier}")
        all_formats_exist = all(
            os.path.exists(f"{base_path}.{fmt}") and os.path.getsize(f"{base_path}.{fmt}") > 0
            for fmt in formats
        )

        if all_formats_exist:
            print(f" -> [已跳过] 转写纪要文件已全部导出 ({', '.join(formats)}): {base_path}")
            result["transcript"] = "exists"
            result["ok"] = True
        else:
            try:
                minutes_data = client.get_minutes_detail(
                    meeting_id=meeting_id,
                    recording_id=recording_id,
                    share_id=share_id,
                    detail_id=detail_id
                )
                code = minutes_data.get("code") or minutes_data.get("retcode") or 0
                if (code != 0 or not minutes_data.get("minutes")) and minutes_paragraphs:
                    print(f" -> 提示: 结合预提取的 {len(minutes_paragraphs)} 条转写段落数据导出...")
                    minutes_data = {"minutes_paragraphs": minutes_paragraphs, "code": 0}

                if "md" in formats:
                    md_content = format_to_markdown(minutes_data, title=f"会议转录：{topic}")
                    with open(f"{base_path}.md", "w", encoding="utf-8") as f:
                        f.write(md_content)
                    print(f" -> 已导出 Markdown 格式: {base_path}.md")

                if "txt" in formats:
                    txt_content = format_to_txt(minutes_data, title=f"会议转录：{topic}")
                    with open(f"{base_path}.txt", "w", encoding="utf-8") as f:
                        f.write(txt_content)
                    print(f" -> 已导出纯文本 格式: {base_path}.txt")

                if "srt" in formats:
                    srt_content = format_to_srt(minutes_data)
                    with open(f"{base_path}.srt", "w", encoding="utf-8") as f:
                        f.write(srt_content)
                    print(f" -> 已导出 SRT 字幕格式: {base_path}.srt")

                if "json" in formats:
                    json_content = format_to_json(minutes_data)
                    with open(f"{base_path}.json", "w", encoding="utf-8") as f:
                        f.write(json_content)
                    print(f" -> 已导出原始 JSON 格式: {base_path}.json")

                result["transcript"] = "done"
                result["ok"] = True

            except Exception as e:
                print(f"[错误] 获取/保存转写记录失败: {e}")
                result["transcript"] = "failed"

    return result


def update_record_state(state: Dict[str, Any], identifier: str, item: Dict[str, Any], result: Dict[str, Any]) -> None:
    """根据单条记录的处理结果更新增量状态清单。"""
    entry = state["records"].setdefault(identifier, new_entry(item["topic"]))
    entry["topic"] = item["topic"]

    if result["transcript"] in ("done", "exists"):
        entry["transcript_done"] = True

    video = result["video"]
    if video in ("done", "exists"):
        entry["video"] = "done"
    elif video == "skipped":
        entry["video"] = VIDEO_SKIPPED
    elif video == "failed":
        entry["video"] = "failed"
    # video 为 none/off 时保留原状态（本次未尝试下载）

    audio = result.get("audio", "off")
    if audio in ("done", "exists"):
        entry["audio"] = "done"
    elif audio == "skipped":
        entry["audio"] = AUDIO_SKIPPED
    elif audio == "failed":
        entry["audio"] = "failed"
    elif audio == "off":
        entry["audio"] = AUDIO_OFF
    # audio 为 none 时保留原状态（直链未解析到，下次运行重试）

    if video == "failed" or audio == "failed" or result["transcript"] == "failed":
        entry["fails"] = entry.get("fails", 0) + 1
    if is_complete(entry):
        entry["fails"] = 0
    touch(entry)


def expand_shared_middle_items(
    client: TencentMeetingClient,
    items: List[Dict[str, Any]],
    state: Dict[str, Any],
    incremental: bool = True
) -> List[Dict[str, Any]]:
    """Expands shared-record-middle links into their underlying sub-records.

    增量模式下，已展开且全部子记录备份完成的合集（状态中标记为 container 完成）
    直接跳过，不再调用展开接口。
    """
    expanded = []
    for item in items:
        share_id = item.get("share_id") or ""
        is_middle = item.get("is_shared_middle", False)
        if share_id and (is_middle or (not item.get("recording_id") and not item.get("meeting_id"))):
            parent_ident = record_identifier(
                detail_id=item.get("detail_id", ""),
                recording_id=item.get("recording_id", ""),
                share_id=share_id,
                meeting_id=item.get("meeting_id", "")
            )
            if incremental and is_complete(state["records"].get(parent_ident)):
                print(f"\n[增量跳过] 合集记录已备份过，跳过展开 (share_id={share_id}): {item['topic']}")
                continue
            print(f"\n[中间记录] 正在解析 shared-record-middle 页面 (share_id={share_id})...")
            try:
                middle_info = client.get_shared_record_middle_list(share_id)
                sub_items = middle_info.get("sub_items", [])
                if sub_items:
                    print(f" -> 成功提取 shared-record-middle 列表：共 {len(sub_items)} 条子记录 (会议主题: {middle_info.get('topic')})")
                    # 将父记录解析到的媒体直链（视频/音频）按资源 ID 分发给各子记录
                    media = item.pop("_media_links", None)
                    links_ok = item.get("media_links_ok", False)
                    if media:
                        for s in sub_items:
                            urls = media.get(str(s.get("recording_id") or ""), {})
                            s["video_url"] = urls.get("video_url", "")
                            s["audio_url"] = urls.get("audio_url", "")
                            s["media_links_ok"] = links_ok
                    expanded.extend(sub_items)
                    # 仅当全部子记录均已备份完成时，才把父记录标记为"容器完成"；
                    # 否则保持未完成状态，后续运行会重新展开（一次接口调用的代价），
                    # 继续处理未完成的子记录，避免子记录被父记录的完成态挡在门外。
                    sub_identifiers = [
                        record_identifier(
                            detail_id=s.get("detail_id", ""),
                            recording_id=s.get("recording_id", ""),
                            share_id=s.get("share_id", ""),
                            meeting_id=s.get("meeting_id", "")
                        )
                        for s in sub_items
                    ]
                    if all(is_complete(state["records"].get(ident)) for ident in sub_identifiers):
                        parent_entry = state["records"].get(parent_ident) or new_entry(middle_info.get("topic", ""))
                        parent_entry.update({
                            "topic": middle_info.get("topic", parent_entry.get("topic", "")),
                            "transcript_done": True,
                            "video": VIDEO_SKIPPED,
                            "audio": AUDIO_SKIPPED,
                            "container": True
                        })
                        touch(parent_entry)
                        state["records"][parent_ident] = parent_entry
                else:
                    expanded.append(item)
            except Exception as e:
                print(f"[警告] 获取 shared-record-middle 列表失败: {e}")
                expanded.append(item)
        else:
            expanded.append(item)
    return expanded


def attach_media_links(client: TencentMeetingClient, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """为有视频的顶层记录解析 download/meeting 媒体直链（视频 + 纯音频）。

    单条记录按自身 recording_id（= uni_record_id + 1，与 COS 资源 ID 同口径）
    直接匹配；合集记录将整份 {resource_id: urls} 挂到 _media_links，由
    expand_shared_middle_items 分发给各子记录。解析失败不阻断流程：
    视频回退浏览器抓取，音频保留 unknown 待下次运行重试。
    """
    resolved = 0
    for item in items:
        if not item.get("has_video", False):
            continue
        uni = str(item.get("uni_record_id") or "")
        if not uni:
            continue
        try:
            media = client.get_download_links(uni)
            item["media_links_ok"] = True
            resolved += 1
        except Exception as e:
            print(f"[提示] 媒体直链解析失败（视频回退浏览器、音频待重试）: {item.get('topic')} ({e})")
            item["media_links_ok"] = False
            continue
        if item.get("is_shared_middle"):
            item["_media_links"] = media
        else:
            entry = media.get(str(item.get("recording_id") or ""), {})
            item["video_url"] = entry.get("video_url", "")
            item["audio_url"] = entry.get("audio_url", "")
    if items:
        print(f"[媒体直链] 已为 {resolved} 条有视频的记录解析出下载直链。")
    return items


def main():
    parser = argparse.ArgumentParser(description="腾讯会议网页版全自动全量备份脚本 (backup-tencent-meetings)")
    parser.add_argument("-c", "--config", default="config.json", help="配置文件路径 (默认: config.json)")
    parser.add_argument("-f", "--file", help="文本文件路径（可选，每行包含一个会议链接或 meeting_id,recording_id）")
    parser.add_argument("--cookie", help="腾讯会议网页端 Cookie 字符串")
    parser.add_argument("-o", "--output", help="备份下载输出目录 (默认: ./downloads)")
    parser.add_argument("--meeting-id", help="指定下载的 Meeting ID")
    parser.add_argument("--recording-id", help="指定下载的 Recording ID")
    parser.add_argument("--share-id", help="指定下载的 Share ID / 分享 Token (s)")
    parser.add_argument("--topic", default="腾讯会议", help="会议主题名称")
    parser.add_argument("--formats", default="md,txt,json,srt", help="转写记录导出格式列表（逗号分隔）")
    parser.add_argument("--no-video", action="store_true", help="跳过下载视频")
    parser.add_argument("--no-audio", action="store_true", help="跳过下载音频")
    parser.add_argument("--no-transcript", action="store_true", help="跳过导出转写记录")
    parser.add_argument("--full", action="store_true", help="忽略增量状态强制全量备份（重试失败记录、重新展开合集）")
    parser.add_argument("--clean", action="store_true", help="清理模式：核对本地备份后，列出可安全删除的线上有视频记录（默认干跑不删除）")
    parser.add_argument("--apply", action="store_true", help="配合 --clean 真正执行线上删除（不可恢复，本地备份保留）")
    parser.add_argument("--yes", action="store_true", help="配合 --clean --apply 跳过交互确认（脚本化场景）")
    parser.add_argument("--limit", type=int, help="配合 --clean --apply：本次最多删除 N 条（建议首删用 --limit 1 验证）")
    args = parser.parse_args()

    if args.apply and not args.clean:
        parser.error("--apply 仅在 --clean 清理模式下有效")
    if args.clean and (args.file or args.meeting_id or args.recording_id or args.share_id):
        parser.error("--clean 清理模式基于账号全量列表核对，不支持 -f/--meeting-id/--recording-id/--share-id")

    # Load configuration
    cfg = load_config(args.config)
    cookie_str = args.cookie or cfg.get("cookie", "")
    output_dir = args.output or cfg.get("output_dir", "./downloads")
    download_video = not args.no_video if args.no_video else cfg.get("download_video", True)
    download_audio = not args.no_audio if args.no_audio else cfg.get("download_audio", False)
    export_transcript = not args.no_transcript if args.no_transcript else cfg.get("export_transcript", True)
    formats = [fmt.strip().lower() for fmt in (args.formats or "").split(",") if fmt.strip()]
    user_agent = cfg.get("user_agent")

    if not cookie_str or "xxxx" in cookie_str:
        print("[错误] 未配置有效的 Cookie！")
        print("请在 config.json 中填入最新的 Cookie 字符串后重新运行。")
        sys.exit(1)

    # 增量状态清单：默认增量模式；--full 强制全量
    incremental = not args.full
    state = load_state(output_dir, formats)

    # 启用音频下载后，把此前因"未启用"而标记为 off 的记录重置为待对账，
    # 保证历史已完成的记录也能补上纯音频文件（与视频 unknown 对账同一机制）。
    if download_audio and incremental:
        swept = 0
        for entry in state["records"].values():
            if entry.get("audio") == AUDIO_OFF:
                entry["audio"] = AUDIO_UNKNOWN
                swept += 1
        if swept:
            print(f"[音频启用] 已将 {swept} 条此前未启用音频下载的记录重置为待对账。")

    save_state(output_dir, state)

    client = TencentMeetingClient(cookie_str=cookie_str, user_agent=user_agent)

    # 清理模式：只核对与删除，不下载（无需解析媒体直链），在备份调度前短路
    if args.clean:
        sys.exit(run_cleaner(
            client=client,
            state=state,
            output_dir=output_dir,
            formats=formats,
            need_transcript=export_transcript,
            need_audio=download_audio,
            apply=args.apply,
            assume_yes=args.yes,
            limit=args.limit,
        ))

    raw_items = []

    # 1. Check CLI single item args
    if args.meeting_id or args.recording_id or args.share_id:
        raw_items.append({
            "meeting_id": args.meeting_id or "",
            "recording_id": args.recording_id or "",
            "share_id": args.share_id or "",
            "detail_id": "",
            "topic": args.topic or "腾讯会议",
            "is_shared_middle": bool(args.share_id and not args.meeting_id and not args.recording_id)
        })

    # 2. Check batch file if explicitly provided
    elif args.file:
        print(f"正在从文件加载批量备份列表: {args.file}")
        with open(args.file, "r", encoding="utf-8") as f:
            for line in f:
                parsed = parse_tencent_meeting_url(line)
                if parsed["meeting_id"] or parsed["recording_id"] or parsed["share_id"]:
                    parsed["detail_id"] = ""
                    raw_items.append(parsed)

    # 3. Default: Automatically traverse and fetch all user meetings from account API!
    if not raw_items:
        if incremental:
            done = sum(1 for entry in state["records"].values() if is_complete(entry))
            print(f"[增量模式] 状态清单已加载（{done}/{len(state['records'])} 条已完成），"
                  f"遍历全部记录但跳过已完成项；--full 可强制全量。")
        print("[全自动模式] 正在自动遍历您的腾讯会议账号并获取所有历史会议列表...")
        raw_items = client.get_all_user_meetings()

    if not raw_items:
        print("[提示] 账号中未检测到录制会议记录，或 Cookie 已过期。")
        sys.exit(0)

    # 解析媒体直链（视频/音频，download/meeting 同源接口），再展开合集分发给子记录
    if download_video or download_audio:
        attach_media_links(client, raw_items)

    # Expand any shared-record-middle items into their sub-records (typically ~3 sub-records)
    items_to_process = expand_shared_middle_items(client, raw_items, state, incremental)
    save_state(output_dir, state)

    print(f"\n==================================================")
    print(f"🚀 开始备份，共处理 {len(items_to_process)} 场录制记录/子记录" + ("（全量模式）" if not incremental else "") + "！")
    print(f"==================================================")
    success_count = 0

    for idx, item in enumerate(items_to_process, start=1):
        identifier = record_identifier(
            detail_id=item.get("detail_id", ""),
            recording_id=item.get("recording_id", ""),
            share_id=item.get("share_id", ""),
            meeting_id=item.get("meeting_id", "")
        )
        entry = state["records"].get(identifier)

        if incremental and is_complete(entry):
            print(f"\n进度 [{idx}/{len(items_to_process)}] [增量跳过] 已备份过: {item['topic']}")
            success_count += 1
            continue

        if incremental and entry and entry.get("fails", 0) >= MAX_FAILURES:
            print(f"\n进度 [{idx}/{len(items_to_process)}] [增量跳过] 该记录已连续失败 {entry['fails']} 次，本轮不再重试"
                  f"（如需重试请使用 --full）: {item['topic']}")
            continue

        print(f"\n进度 [{idx}/{len(items_to_process)}]")
        result = process_single_backup(
            client=client,
            meeting_id=item["meeting_id"],
            recording_id=item["recording_id"],
            share_id=item.get("share_id", ""),
            detail_id=item.get("detail_id", ""),
            output_dir=output_dir,
            download_video=download_video,
            download_audio=download_audio,
            export_transcript=export_transcript,
            formats=formats,
            topic=item["topic"],
            cover_url=item.get("cover_url", ""),
            jump_path=item.get("jump_path", ""),
            has_video=item.get("has_video", True),
            minutes_paragraphs=item.get("minutes_paragraphs", []),
            video_url=item.get("video_url", ""),
            audio_url=item.get("audio_url", ""),
            media_links_ok=item.get("media_links_ok", False)
        )
        update_record_state(state, identifier, item, result)
        save_state(output_dir, state)
        if result["ok"]:
            success_count += 1

    print(f"\n==================================================")
    print(f"🎉 账号全量自动备份完成！成功备份: {success_count}/{len(items_to_process)} 场会议/子记录")
    print(f"文件存储根路径: {os.path.abspath(output_dir)}")
    print(f"==================================================")


if __name__ == "__main__":
    main()

