import json
from datetime import timedelta
from typing import Any, Dict, List, Optional


def ms_to_timestamp(ms: int, srt_format: bool = False) -> str:
    """Converts milliseconds to HH:MM:SS format or HH:MM:SS,mmm format for SRT."""
    seconds = ms / 1000.0
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - total_seconds) * 1000)

    if srt_format:
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def extract_text_from_item(item: Dict[str, Any]) -> str:
    """Extracts text content from a paragraph or sentence item."""
    if "text" in item and isinstance(item["text"], str):
        return item["text"]
    if "content" in item and isinstance(item["content"], str):
        return item["content"]
    if "msg" in item and isinstance(item["msg"], str):
        return item["msg"]

    text_parts = []
    # If item has sentences list
    sentences = item.get("sentences") or []
    if isinstance(sentences, list):
        for s in sentences:
            if isinstance(s, dict):
                text_parts.append(extract_text_from_item(s))
            elif isinstance(s, str):
                text_parts.append(s)

    # If item has words list
    words = item.get("words") or []
    if isinstance(words, list):
        for w in words:
            if isinstance(w, dict):
                w_text = w.get("text") or w.get("word") or w.get("content") or ""
                text_parts.append(w_text)
            elif isinstance(w, str):
                text_parts.append(w)

    return "".join(text_parts)


def extract_paragraphs(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts standardized list of paragraph dicts from raw Tencent Meeting API response.
    Each returned dict has: 'speaker', 'start_ms', 'end_ms', 'text'.
    """
    paragraphs = []
    
    # 1. Try to find the list of paragraph items
    raw_list = []
    if isinstance(data, dict):
        minutes_obj = data.get("minutes") or {}
        detail_obj = data.get("detail") or {}
        
        if isinstance(minutes_obj, dict) and "paragraphs" in minutes_obj:
            raw_list = minutes_obj.get("paragraphs") or []
        elif isinstance(minutes_obj, list):
            raw_list = minutes_obj
        elif "minutes_paragraphs" in data:
            raw_list = data.get("minutes_paragraphs") or []
        elif "pid_list" in data:
            raw_list = data.get("pid_list") or []
        elif "paragraphs" in data:
            raw_list = data.get("paragraphs") or []
        elif isinstance(detail_obj, dict):
            raw_list = detail_obj.get("pid_list") or detail_obj.get("paragraphs") or []
    elif isinstance(data, list):
        raw_list = data

    if not isinstance(raw_list, list):
        raw_list = []

    for item in raw_list:
        if not isinstance(item, dict):
            continue

        # Extract Speaker
        speaker = "发言人"
        speaker_info = item.get("speaker_info") or item.get("speaker") or {}
        if isinstance(speaker_info, dict):
            speaker = (
                speaker_info.get("user_name")
                or speaker_info.get("name")
                or speaker_info.get("nickname")
                or speaker_info.get("username")
                or "发言人"
            )
        elif isinstance(speaker_info, str) and speaker_info.strip():
            speaker = speaker_info.strip()

        # Extract Time
        start_ms = item.get("start_ms") or item.get("start_time") or item.get("startTime") or 0
        end_ms = item.get("end_ms") or item.get("end_time") or item.get("endTime") or 0

        # Extract Text
        text = extract_text_from_item(item).strip()

        if text:
            paragraphs.append({
                "speaker": speaker,
                "start_ms": int(start_ms),
                "end_ms": int(end_ms),
                "text": text
            })

    return paragraphs


def format_to_markdown(data: Dict[str, Any], title: str = "会议转录记录") -> str:
    """Formats transcript data into Markdown document."""
    paragraphs = extract_paragraphs(data)
    md_lines = [
        f"# {title}",
        "",
        f"> 转换发言段落数：{len(paragraphs)}",
        "",
        "---",
        ""
    ]

    for p in paragraphs:
        time_str = ms_to_timestamp(p["start_ms"])
        speaker = p["speaker"]
        text = p["text"]
        md_lines.append(f"### `[{time_str}]` **{speaker}**")
        md_lines.append(f"{text}")
        md_lines.append("")

    return "\n".join(md_lines)


def format_to_txt(data: Dict[str, Any], title: str = "会议转录记录") -> str:
    """Formats transcript data into plain text."""
    paragraphs = extract_paragraphs(data)
    txt_lines = [f"=== {title} ===", ""]

    for p in paragraphs:
        time_str = ms_to_timestamp(p["start_ms"])
        speaker = p["speaker"]
        text = p["text"]
        txt_lines.append(f"[{time_str}] {speaker}: {text}")

    return "\n".join(txt_lines)


def format_to_srt(data: Dict[str, Any]) -> str:
    """Formats transcript data into SRT subtitle format."""
    paragraphs = extract_paragraphs(data)
    srt_blocks = []

    for idx, p in enumerate(paragraphs, start=1):
        start_str = ms_to_timestamp(p["start_ms"], srt_format=True)
        end_str = ms_to_timestamp(p["end_ms"], srt_format=True)
        if p["end_ms"] <= p["start_ms"]:
            end_str = ms_to_timestamp(p["start_ms"] + 3000, srt_format=True)

        speaker = p["speaker"]
        text = p["text"]
        srt_blocks.append(f"{idx}\n{start_str} --> {end_str}\n{speaker}: {text}\n")

    return "\n".join(srt_blocks)


def format_to_json(data: Dict[str, Any]) -> str:
    """Formats raw transcript data into pretty JSON."""
    return json.dumps(data, ensure_ascii=False, indent=2)
