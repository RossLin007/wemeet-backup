"""增量备份状态清单：记录每条录制记录的处理状态，支撑默认增量备份模式。

状态文件位于输出目录下（.backup_state.json），以记录标识符为键。
标识符取值口径与备份目录命名保持一致：detail_id or recording_id or share_id or meeting_id。
首次运行时若无状态文件，会扫描输出目录下已有备份产物自动生成初始清单（引导）。
"""
import glob
import json
import os
import time
from typing import Any, Dict, List, Optional

STATE_FILENAME = ".backup_state.json"
# 增量模式下连续失败达到该次数的记录不再自动重试（--full 可强制重试）
MAX_FAILURES = 3

# video 字段取值：
#   done=已有视频文件 / skipped=该记录类型本身无视频 / unknown=待确认 / failed=下载失败
VIDEO_DONE = "done"
VIDEO_SKIPPED = "skipped"
VIDEO_UNKNOWN = "unknown"
VIDEO_FAILED = "failed"

# audio 字段取值与 video 一致，另多一个 off：
#   off=配置未启用音频下载（不参与完成判定）；之后启用 download_audio 时，
#   已有的 off 会被重置为 unknown 重新对账，保证历史记录能补上音频。
AUDIO_DONE = VIDEO_DONE
AUDIO_SKIPPED = VIDEO_SKIPPED
AUDIO_UNKNOWN = VIDEO_UNKNOWN
AUDIO_FAILED = VIDEO_FAILED
AUDIO_OFF = "off"


def record_identifier(detail_id: str = "", recording_id: str = "",
                      share_id: str = "", meeting_id: str = "") -> str:
    """记录标识符的唯一取值口径（与备份目录命名中的 identifier 一致）。"""
    return detail_id or recording_id or share_id or meeting_id or "meeting"


def state_path_for(output_dir: str) -> str:
    return os.path.join(output_dir, STATE_FILENAME)


def new_entry(topic: str = "") -> Dict[str, Any]:
    return {
        "topic": topic,
        "transcript_done": False,
        "video": VIDEO_UNKNOWN,
        "audio": AUDIO_UNKNOWN,
        "fails": 0,
        "container": False,
        "updated_at": "",
    }


def touch(entry: Dict[str, Any]) -> None:
    entry["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")


def is_complete(entry: Optional[Dict[str, Any]]) -> bool:
    """转写已完成、视频已就绪（或该记录本身无视频）、且音频已对账即视为备份完成。

    audio 缺失（旧版状态文件）按 unknown 处理，会触发一次重新对账；
    off 表示配置未启用音频下载，不阻塞完成判定。
    """
    if not entry:
        return False
    return (
        bool(entry.get("transcript_done"))
        and entry.get("video") in (VIDEO_DONE, VIDEO_SKIPPED)
        and entry.get("audio", AUDIO_UNKNOWN) in (AUDIO_DONE, AUDIO_SKIPPED, AUDIO_OFF)
    )


def bootstrap_state(output_dir: str, formats: Optional[List[str]] = None) -> Dict[str, Any]:
    """首次运行引导：扫描输出目录下已有备份产物，生成初始状态清单。

    目录命名约定为 `会议主题_标识符`，标识符取最后一个下划线之后的部分。
    磁盘上无法区分"记录本身无视频"与"视频下载失败"，此类记录 video 置为 unknown，
    待运行中从 API 拿到 has_video 字段时再对账修正。
    """
    formats = [fmt.lower() for fmt in (formats or ["md", "txt", "json", "srt"])]
    records: Dict[str, Dict[str, Any]] = {}
    if os.path.isdir(output_dir):
        print("[增量初始化] 未发现状态文件，正在扫描本地已有备份生成初始清单...")
        for name in sorted(os.listdir(output_dir)):
            folder = os.path.join(output_dir, name)
            if not os.path.isdir(folder) or name.startswith(".") or "_" not in name:
                continue
            topic, identifier = name.rsplit("_", 1)
            entry = new_entry(topic)
            entry["transcript_done"] = all(
                os.path.exists(p) and os.path.getsize(p) > 0
                for p in (os.path.join(folder, f"transcript_{identifier}.{fmt}") for fmt in formats)
            )
            video_path = os.path.join(folder, f"video_{identifier}.mp4")
            if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                entry["video"] = VIDEO_DONE
            # 音频以 .m4a 为主、兼容 .mp3；磁盘扫描同样无法区分"无音频"与"未下载"，置 unknown 待对账
            audio_done = any(
                os.path.isfile(p) and not p.endswith(".tmp") and os.path.getsize(p) > 0
                for p in glob.glob(os.path.join(folder, f"audio_{identifier}.*"))
            )
            if audio_done:
                entry["audio"] = AUDIO_DONE
            records[identifier] = entry
        print(f"[增量初始化] 扫描完成，共登记 {len(records)} 条本地已有记录。")
    return {"version": 1, "records": records}


def load_state(output_dir: str, formats: Optional[List[str]] = None) -> Dict[str, Any]:
    """加载状态清单；文件缺失或损坏时回退到磁盘扫描引导。"""
    path = state_path_for(output_dir)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("records"), dict):
                return data
            print("[警告] 状态文件格式异常，将重新扫描本地备份生成初始清单。")
        except Exception as e:
            print(f"[警告] 状态文件读取失败({e})，将重新扫描本地备份生成初始清单。")
    return bootstrap_state(output_dir, formats)


def save_state(output_dir: str, state: Dict[str, Any]) -> None:
    """原子写回状态清单（先写临时文件再替换，避免中断产生半截文件）。"""
    os.makedirs(output_dir, exist_ok=True)
    state["version"] = 1
    state["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    path = state_path_for(output_dir)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
