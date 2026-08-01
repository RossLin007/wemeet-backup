import re
import time
import json
import urllib.parse
from typing import List, Dict, Any

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def parse_cookie_str_to_list(cookie_str: str, domain: str = ".meeting.tencent.com") -> List[Dict[str, Any]]:
    """Converts raw Cookie string to Playwright cookie format."""
    cookies = []
    for item in cookie_str.split(";"):
        if "=" in item:
            k, v = item.split("=", 1)
            cookies.append({
                "name": k.strip(),
                "value": v.strip(),
                "domain": domain,
                "path": "/"
            })
    return cookies


def fetch_all_meetings_with_browser(cookie_str: str, headless: bool = True) -> List[Dict[str, str]]:
    """
    Automated browser crawler using Playwright:
    1. Injects Cookie.
    2. Opens https://meeting.tencent.com/user-center/meeting-record.
    3. Intercepts XHR/Fetch API responses to capture exact meeting_id, recording_id, topic.
    4. Automatically scrolls down to load all pages/meetings.
    5. Extracts meeting links and details from page DOM and network traffic.
    """
    if not HAS_PLAYWRIGHT:
        print("[错误] 未安装 playwright 模块，请先运行: python3 -m pip install playwright")
        return []

    discovered_meetings: Dict[str, Dict[str, str]] = {}

    def handle_response(response):
        try:
            url = response.url
            # Intercept API responses containing meeting list or minutes
            if "meeting" in url or "record" in url or "minutes" in url:
                try:
                    data = response.json()
                    # Check if response contains record_list or meetings
                    items = []
                    if isinstance(data, dict):
                        items = (
                            data.get("record_list") or
                            data.get("data", {}).get("record_list") or
                            data.get("data", {}).get("list") or
                            data.get("list") or []
                        )
                    for it in items:
                        if isinstance(it, dict):
                            m_id = str(it.get("meeting_id") or it.get("meeting_code") or "")
                            r_id = str(it.get("recording_id") or it.get("id") or "")
                            topic = it.get("subject") or it.get("topic") or "腾讯会议"
                            key = f"{m_id}_{r_id}"
                            if m_id and r_id and key not in discovered_meetings:
                                discovered_meetings[key] = {
                                    "meeting_id": m_id,
                                    "recording_id": r_id,
                                    "share_id": "",
                                    "topic": topic
                                }
                except Exception:
                    pass
        except Exception:
            pass

    print("[自动抓取] 正在启动自动化浏览器拉取您的会议列表...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        )

        # Inject Cookie
        playwright_cookies = parse_cookie_str_to_list(cookie_str)
        context.add_cookies(playwright_cookies)

        page = context.new_page()
        page.on("response", handle_response)

        print("[自动抓取] 正在访问腾讯会议个人中心录制页面...")
        try:
            page.goto("https://meeting.tencent.com/user-center/meeting-record", wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"[自动抓取] 页面加载提示: {e}")

        # Auto scroll down to trigger lazy loading / pagination
        print("[自动抓取] 正在自动滚动页面，遍历拉取所有历史会议记录...")
        prev_height = 0
        scroll_attempts = 0
        max_scrolls = 15

        while scroll_attempts < max_scrolls:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.5)
            curr_height = page.evaluate("document.body.scrollHeight")
            
            # DOM extraction fallback: search for meeting links in DOM
            hrefs = page.eval_on_selector_all("a[href]", "elements => elements.map(el => el.href)")
            for href in hrefs:
                if "meeting_id" in href and "recording_id" in href:
                    m_match = re.search(r'meeting_id[=_](\d+)', href)
                    r_match = re.search(r'recording_id[=_](\d+)', href)
                    if m_match and r_match:
                        m_id = m_match.group(1)
                        r_id = r_match.group(1)
                        key = f"{m_id}_{r_id}"
                        if key not in discovered_meetings:
                            discovered_meetings[key] = {
                                "meeting_id": m_id,
                                "recording_id": r_id,
                                "share_id": "",
                                "topic": "腾讯会议"
                            }
                elif "shared-record-middle" in href or "shared-record" in href:
                    s_match = re.search(r'[?&]s=([a-zA-Z0-9_\-]+)', href)
                    if s_match:
                        s_id = s_match.group(1)
                        key = f"share_{s_id}"
                        if key not in discovered_meetings:
                            discovered_meetings[key] = {
                                "meeting_id": "",
                                "recording_id": "",
                                "share_id": s_id,
                                "topic": "腾讯会议"
                            }

            if curr_height == prev_height:
                break
            prev_height = curr_height
            scroll_attempts += 1

        browser.close()

    result_list = list(discovered_meetings.values())
    print(f"[自动抓取] 遍历完成！共抓取到 {len(result_list)} 场会议记录。")
    return result_list


def fetch_and_download_video_with_browser(jump_path_or_url: str, cookie_str: str, dest_path: str) -> bool:
    """
    Uses Playwright to capture tokenized MP4 stream URL and download video file.
    """
    if not HAS_PLAYWRIGHT:
        return False

    from tencent_meeting.downloader import download_file

    url = f"https://meeting.tencent.com{jump_path_or_url}" if jump_path_or_url.startswith("/") else jump_path_or_url
    captured_mp4_url = None

    print(f"[视频抓取] 正在通过浏览器解析录像下载链接: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        )
        context.add_cookies(parse_cookie_str_to_list(cookie_str))
        page = context.new_page()

        def handle_response(res):
            nonlocal captured_mp4_url
            u = res.url
            if ".mp4" in u or "recording-1.mp4" in u:
                captured_mp4_url = u

        page.on("response", handle_response)
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(2)
        except Exception as e:
            print(f"[视频抓取] 页面加载提示: {e}")

        browser.close()

    if captured_mp4_url:
        headers = {
            "Cookie": cookie_str,
            "Referer": "https://meeting.tencent.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        }
        print(f"[视频抓取] 捕获到高清视频资源地址，开始下载 -> {dest_path}")
        return download_file(captured_mp4_url, dest_path, headers=headers)
    else:
        print(f"[视频抓取] 未在页面中捕获到有效视频媒体数据。")

    return False

