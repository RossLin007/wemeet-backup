import os
import sys
import time
from typing import Optional, Dict

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False


def _format_size(num_bytes: float) -> str:
    return f"{num_bytes / 1024 / 1024:.2f} MB"


def download_file(url: str, dest_path: str, headers: Optional[Dict[str, str]] = None,
                  overwrite: bool = True, max_retries: int = 5) -> bool:
    """
    Streamed chunked downloader with progress and speed display.

    支持断点续传：下载中断（网络停滞/连接重置）时保留 .tmp 已下载部分，
    自动携带 Range 头从断点处继续，最多重试 max_retries 次；重试耗尽仍失败时
    保留 .tmp，下次运行自动续传，避免大文件前功尽弃。
    """
    if not url:
        print(f"[跳过下载] URL 为空: {dest_path}")
        return False

    if not overwrite and os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        print(f"[跳过下载] 文件已存在: {dest_path}")
        return True

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    temp_path = dest_path + ".tmp"

    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
        "Referer": "https://meeting.tencent.com/",
        "Accept": "*/*"
    }
    if headers:
        default_headers.update(headers)

    print(f"\n[开始下载] -> {dest_path}")

    for attempt in range(max_retries + 1):
        resume_from = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
        if resume_from > 0:
            print(f"  [断点续传] 从已下载的 {_format_size(resume_from)} 处继续...")

        try:
            req_headers = dict(default_headers)
            if resume_from > 0:
                req_headers["Range"] = f"bytes={resume_from}-"

            downloaded = 0
            start_time = time.time()

            def _print_progress() -> None:
                elapsed = time.time() - start_time
                speed = (downloaded / 1024 / 1024) / elapsed if elapsed > 0 else 0
                done = resume_from + downloaded
                if total_size > 0:
                    percent = (done / total_size) * 100
                    sys.stdout.write(
                        f"\r  已下载: {_format_size(done)} / {_format_size(total_size)} "
                        f"({percent:.1f}%) | 速度: {speed:.2f} MB/s"
                    )
                else:
                    sys.stdout.write(f"\r  已下载: {_format_size(done)} | 速度: {speed:.2f} MB/s")
                sys.stdout.flush()

            if HAS_REQUESTS:
                with requests.get(url, headers=req_headers, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    if resume_from > 0 and r.status_code != 206:
                        # 服务端忽略 Range 返回了完整文件，从头写入
                        resume_from = 0
                    total_size = resume_from + int(r.headers.get("content-length", 0))

                    with open(temp_path, "ab" if resume_from > 0 else "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                _print_progress()
            else:
                req = urllib.request.Request(url, headers=req_headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    status = getattr(resp, "status", None) or resp.getcode()
                    if resume_from > 0 and status != 206:
                        # 服务端忽略 Range 返回了完整文件，从头写入
                        resume_from = 0
                    total_size = resume_from + int(resp.headers.get("content-length", 0))

                    with open(temp_path, "ab" if resume_from > 0 else "wb") as f:
                        while True:
                            chunk = resp.read(1024 * 1024)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            _print_progress()

            sys.stdout.write("\n")
            if os.path.exists(temp_path):
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                os.rename(temp_path, dest_path)
                print(f"[下载完成] -> {dest_path}")
                return True
            return False

        except Exception as e:
            sys.stdout.write("\n")
            forbidden = getattr(e, "code", None) == 403 or " 403 " in f" {e} "
            # 403 属于直链 token 失效/风控拒绝：携带 Range 的续传请求会被直接拒掉，
            # 原地重试毫无意义。丢弃半截 .tmp 改为整段 GET 重试一次（链接尚有效即可救回），
            # 仍被拒则放弃且不留无用的 .tmp。
            if forbidden and resume_from > 0 and attempt < max_retries:
                print(f"  [续传被拒] {e}；丢弃已下载部分，改为整段重试...")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                time.sleep(2)
                continue
            saved = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
            if attempt < max_retries and saved > 0:
                print(f"[下载中断] {e}；已保留 {_format_size(saved)}，第 {attempt + 1}/{max_retries} 次断点续传重试...")
                time.sleep(2)
                continue
            if saved > 0:
                print(f"[下载失败] {dest_path}: {e}；已保留 {_format_size(saved)} 临时文件，下次运行将自动续传。")
            else:
                print(f"[下载失败] {dest_path}: {e}")
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
            return False

    return False
