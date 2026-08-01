import re
import urllib.parse
from typing import Dict, Optional, Any


def parse_tencent_meeting_url(url_or_str: str) -> Dict[str, Any]:
    """
    Parses a Tencent Meeting URL or raw line into meeting_id, recording_id, share_id, and topic.
    Examples:
      - https://meeting.tencent.com/user-center/meeting-record?meeting_id=123&recording_id=456
      - https://meeting.tencent.com/user-center/shared-record-middle?s=sKOvc8uzP...
      - 13477124180492978577,2082589889613090817,晨读会
    """
    result = {
        "meeting_id": "",
        "recording_id": "",
        "share_id": "",
        "topic": "腾讯会议",
        "is_shared_middle": False
    }

    line = url_or_str.strip()
    if not line or line.startswith("#"):
        return result

    if "shared-record-middle" in line:
        result["is_shared_middle"] = True

    # Check comma-separated values: meeting_id,recording_id,topic
    if "," in line and not line.startswith("http"):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            result["meeting_id"] = parts[0]
            result["recording_id"] = parts[1]
            if len(parts) >= 3:
                result["topic"] = parts[2]
            return result

    # Parse URL query parameters
    try:
        parsed = urllib.parse.urlparse(line)
        query_params = urllib.parse.parse_qs(parsed.query)

        if "meeting_id" in query_params:
            result["meeting_id"] = query_params["meeting_id"][0]
        if "recording_id" in query_params:
            result["recording_id"] = query_params["recording_id"][0]
        if "s" in query_params:
            result["share_id"] = query_params["s"][0]
        if "share_id" in query_params:
            result["share_id"] = query_params["share_id"][0]
        if "topic" in query_params:
            result["topic"] = query_params["topic"][0]
    except Exception:
        pass

    # Regex search as fallback for meeting_id and recording_id
    if not result["meeting_id"]:
        m_match = re.search(r'meeting_id[=_](\d+)', line)
        if m_match:
            result["meeting_id"] = m_match.group(1)

    if not result["recording_id"]:
        r_match = re.search(r'recording_id[=_](\d+)', line)
        if r_match:
            result["recording_id"] = r_match.group(1)

    if not result["share_id"]:
        s_match = re.search(r'[?&]s=([a-zA-Z0-9_\-]+)', line)
        if s_match:
            result["share_id"] = s_match.group(1)

    return result

