import re
import os
import time
import json
import random
import string
import base64
import urllib.parse
from typing import Any, Dict, List, Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False


def generate_nonce(length: int = 9) -> str:
    """Generates a random string for API nonce."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


class TencentMeetingClient:
    """
    HTTP Client for interacting with Tencent Meeting endpoints.
    """

    BASE_URL = "https://meeting.tencent.com"

    def __init__(self, cookie_str: str, user_agent: Optional[str] = None):
        self.cookie_str = cookie_str
        self.cookies = self._parse_cookies(cookie_str)
        self.account_corp_id = self.cookies.get("account_corp_id", "983619626")
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        )
        
        if HAS_REQUESTS:
            self.session = requests.Session()
            self.session.headers.update({
                "Accept": "application/json, text/plain, */*",
                "User-Agent": self.user_agent,
                "Referer": "https://meeting.tencent.com/user-center/meeting-record",
                "Origin": "https://meeting.tencent.com",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
            })
            for k, v in self.cookies.items():
                self.session.cookies.set(k, v)

    def _parse_cookies(self, cookie_str: str) -> Dict[str, str]:
        cookies = {}
        for item in cookie_str.split(";"):
            if "=" in item:
                k, v = item.split("=", 1)
                cookies[k.strip()] = v.strip()
        return cookies

    def _build_default_params(self) -> Dict[str, str]:
        nonce = generate_nonce()
        timestamp = str(int(time.time() * 1000))
        return {
            "c_app_id": "",
            "c_os_model": "web",
            "c_os": "web",
            "c_os_version": self.user_agent,
            "c_timestamp": timestamp,
            "c_nonce": nonce,
            "c_app_version": "",
            "c_instance_id": "5",
            "rnds": nonce,
            "platform": "Web",
            "c_account_corp_id": self.account_corp_id,
            "c_lang": "zh"
        }

    def _get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Performs a GET request to the specified Tencent Meeting API endpoint."""
        url = f"{self.BASE_URL}{endpoint}" if not endpoint.startswith("http") else endpoint
        full_params = self._build_default_params()
        for k, v in params.items():
            if v is not None and str(v) != "":
                full_params[k] = str(v)

        if HAS_REQUESTS:
            resp = self.session.get(url, params=full_params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        else:
            full_url = url + "?" + urllib.parse.urlencode(full_params)
            headers = {
                "Accept": "application/json, text/plain, */*",
                "User-Agent": self.user_agent,
                "Referer": "https://meeting.tencent.com/user-center/meeting-record",
                "Cookie": self.cookie_str
            }
            req = urllib.request.Request(full_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)

    def _post(self, endpoint: str, data_dict: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Performs a POST request with JSON payload."""
        url = f"{self.BASE_URL}{endpoint}" if not endpoint.startswith("http") else endpoint
        full_params = self._build_default_params()
        if params:
            full_params.update(params)

        if HAS_REQUESTS:
            headers = {"web-caller": "my_meetings", "Content-Type": "application/json"}
            resp = self.session.post(url, params=full_params, json=data_dict, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()
        else:
            full_url = url + "?" + urllib.parse.urlencode(full_params)
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "User-Agent": self.user_agent,
                "Referer": "https://meeting.tencent.com/user-center/meeting-record",
                "Origin": "https://meeting.tencent.com",
                "web-caller": "my_meetings",
                "Cookie": self.cookie_str
            }
            payload_bytes = json.dumps(data_dict).encode("utf-8")
            req = urllib.request.Request(full_url, data=payload_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)

    def get_my_record_list(self, page_index: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Fetches user meeting recording list using /wemeet-tapi/v2/meetlog/dashboard/my-record-list
        """
        endpoint = "/wemeet-tapi/v2/meetlog/dashboard/my-record-list"
        payload = {
            "begin_time": "0",
            "end_time": "0",
            "meeting_code": "",
            "page_index": page_index,
            "page_size": page_size,
            "aggregationFastRecording": 0,
            "cover_image_type": "meetlog_list_webp",
            "record_type_v4": "fast_record|cloud_record|user_upload|realtime_transcription|voice_record",
            "sort_by": "uni_record_id",
            "record_scene": 1
        }
        return self._post(endpoint, payload)

    def get_all_user_meetings(self) -> List[Dict[str, Any]]:
        """
        Automatically traverses all pages in user account and returns standardized meeting dicts.
        Includes video detection and shared-record-middle link parsing.
        """
        all_meetings = []
        page_index = 1
        page_size = 20

        while True:
            try:
                resp = self.get_my_record_list(page_index=page_index, page_size=page_size)
                records = resp.get("data", {}).get("records", []) or []
                if not records:
                    break

                for r in records:
                    m_info = r.get("meeting_info", {})
                    m_id = str(m_info.get("meeting_id") or "")
                    uuid_id = str(r.get("record_id") or r.get("encode_record_id") or "")
                    uni_id = str(r.get("uni_record_id") or r.get("file_id") or "")
                    title = r.get("title") or m_info.get("subject") or "腾讯会议"
                    jump_path = r.get("jump_path") or ""
                    rec_type = r.get("record_type") or ""

                    # Extract share_id if present in jump_path
                    s_match = re.search(r'[?&]s=([a-zA-Z0-9_\-]+)', jump_path)
                    share_id = s_match.group(1) if s_match else ""
                    is_middle = "shared-record-middle" in jump_path or bool(share_id)

                    # Calculate target recording_id for minutes API: uni_record_id + 1
                    rec_id = str(int(uni_id) + 1) if uni_id.isdigit() else uni_id

                    # Determine if record contains video
                    has_video = rec_type in ["cloud_record", "fast_record", "user_upload"] or is_middle

                    if m_id or rec_id or share_id:
                        all_meetings.append({
                            "meeting_id": m_id,
                            "recording_id": rec_id,
                            "detail_id": uuid_id,
                            "share_id": share_id,
                            "topic": title,
                            "record_type": rec_type,
                            "has_video": has_video,
                            "is_shared_middle": is_middle,
                            "jump_path": jump_path
                        })

                if len(records) < page_size:
                    break

                page_index += 1
            except Exception as e:
                print(f"[提示] 分页遍历第 {page_index} 页时提示: {e}")
                break

        return all_meetings

    def get_minutes_detail(
        self,
        meeting_id: str = "",
        recording_id: str = "",
        share_id: str = "",
        detail_id: str = "",
        limit: int = 100,
        start_pid: int = 0
    ) -> Dict[str, Any]:
        """
        Fetches meeting minutes / transcription detail.
        API: /wemeet-cloudrecording-webapi/v1/minutes/detail
        """
        endpoint = "/wemeet-cloudrecording-webapi/v1/minutes/detail"
        params = {
            "meeting_id": meeting_id,
            "recording_id": recording_id,
            "share_id": share_id,
            "short_url_code": share_id,
            "id": detail_id or "14906e39-0f89-4b57-909c-ebaaa5a27622",
            "limit": str(limit),
            "start_pid": str(start_pid),
            "lang": "zh",
            "minutes_version": "0",
            "return_ori": "0",
            "return_ori_minutes_translating": "1",
            "fview": "1",
            "page_source": "record"
        }
        return self._get(endpoint, params)

    def get_shared_record_middle_list(self, share_id: str) -> Dict[str, Any]:
        """
        Queries sub-records list for a shared-record-middle link / share_id.
        API: /wemeet-tapi/v2/meetlog/record-detail/page-query-record-files
        """
        endpoint = "/wemeet-tapi/v2/meetlog/record-detail/page-query-record-files"
        payload = {
            "page_index": 1,
            "page_size": 20,
            "cover_image_type": "meetlog_list_webp",
            "encode_uni_recordId": share_id
        }
        res = self._post(endpoint, payload)
        data = res.get("data", {})
        meeting_info = data.get("meeting_info", {})
        raw_subject = meeting_info.get("subject", "")

        decoded_subject = "腾讯会议"
        if raw_subject:
            try:
                decoded_subject = base64.b64decode(raw_subject).decode("utf-8")
            except Exception:
                decoded_subject = raw_subject

        records = data.get("records", [])
        sub_items = []
        for r in records:
            title = r.get("title") or "录制"
            rec_id = str(r.get("record_id") or "")
            sharing_id = str(r.get("sharing_id") or "")
            cover_url = r.get("cover_url") or ""
            jump_path = r.get("jump_path") or ""
            sub_items.append({
                "meeting_id": str(meeting_info.get("meeting_id") or ""),
                "recording_id": rec_id,
                "detail_id": sharing_id,
                "share_id": sharing_id,
                "topic": f"{decoded_subject}_{title}",
                "cover_url": cover_url,
                "jump_path": jump_path,
                "minutes_paragraphs": r.get("minutes_paragraphs") or []
            })

        return {
            "topic": decoded_subject,
            "meeting_id": str(meeting_info.get("meeting_id") or ""),
            "sub_items": sub_items
        }

