#!/usr/bin/env python3
import os
import sys
import json
import argparse
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
    MAX_FAILURES,
    VIDEO_SKIPPED,
    is_complete,
    load_state,
    new_entry,
    record_identifier,
    save_state,
    touch
)


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
    minutes_paragraphs: List[Any] = None
) -> Dict[str, Any]:
    """Processes backup for a single meeting recording.

    Returns a result dict: {"ok": bool, "transcript": ..., "video": ...}，
    其中 transcript ∈ done/exists/failed/off，video ∈ done/exists/skipped/failed/none/off，
    供增量状态清单更新使用。
    """
    safe_topic = sanitize_filename(topic)
    identifier = record_identifier(
        detail_id=detail_id, recording_id=recording_id,
        share_id=share_id, meeting_id=meeting_id
    )
    folder_name = f"{safe_topic}_{identifier}"
    target_dir = os.path.join(output_dir, folder_name)
    os.makedirs(target_dir, exist_ok=True)

    print(f"\n==================================================")
    print(f"正在处理会议: {topic}")
    print(f"Meeting ID: {meeting_id} | Recording ID: {recording_id} | Detail ID: {detail_id}")
    print(f"保存路径: {target_dir}")
    print(f"==================================================")

    result = {"ok": False, "transcript": "off", "video": "none"}

    # 1. 下载录像封面资源
    if cover_url:
        print("[1/3] 正在获取并保存录像封面资源...")
        cover_path = os.path.join(target_dir, f"cover_{identifier}.png")
        download_file(cover_url, cover_path, overwrite=False)

    # 2. 下载会议视频 MP4 (非视频记录类型如纯实时转写则自动跳过)
    if download_video:
        print("[2/3] 正在检查/拉取会议视频 (.mp4)...")
        if not has_video:
            print(" -> [已跳过] 该记录类型为纯文字转写/语音记录，不包含视频画面。")
            result["video"] = "skipped"
        else:
            target_video_path = os.path.join(target_dir, f"video_{identifier}.mp4")
            if os.path.exists(target_video_path) and os.path.getsize(target_video_path) > 0:
                print(f" -> [已跳过] 视频文件已存在且非空: {target_video_path}")
                result["video"] = "exists"
            else:
                target_url = jump_path or (f"/meeting-record/shares?id={detail_id or share_id}" if (detail_id or share_id) else "")
                if not target_url:
                    print(" -> [已跳过] 未找到可解析的视频页面地址。")
                else:
                    downloaded = fetch_and_download_video_with_browser(
                        jump_path_or_url=target_url,
                        cookie_str=client.cookie_str,
                        dest_path=target_video_path
                    )
                    result["video"] = "done" if downloaded else "failed"
    else:
        result["video"] = "off"

    # 3. 导出转写记录 (如各格式转写文件均已存在则直接跳过)
    if export_transcript:
        print("[3/3] 正在获取会议转录记录 (Minutes)...")
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

    if video == "failed" or result["transcript"] == "failed":
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
    args = parser.parse_args()

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
    save_state(output_dir, state)

    client = TencentMeetingClient(cookie_str=cookie_str, user_agent=user_agent)

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
        known_identifiers = set(state["records"].keys()) if incremental else None
        if incremental:
            print(f"[增量模式] 状态清单已加载（{len(known_identifiers)} 条已登记），仅遍历新增记录；--full 可强制全量。")
        print("[全自动模式] 正在自动遍历您的腾讯会议账号并获取所有历史会议列表...")
        raw_items = client.get_all_user_meetings(known_identifiers=known_identifiers)

    if not raw_items:
        print("[提示] 账号中未检测到录制会议记录，或 Cookie 已过期。")
        sys.exit(0)

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
            minutes_paragraphs=item.get("minutes_paragraphs", [])
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

