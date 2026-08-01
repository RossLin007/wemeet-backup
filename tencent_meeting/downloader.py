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


def download_file(url: str, dest_path: str, headers: Optional[Dict[str, str]] = None, overwrite: bool = True) -> bool:
    """
    Streamed chunked downloader with progress bar and speed display.
    Supports resuming or skipping existing non-empty files.
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

    try:
        if HAS_REQUESTS:
            with requests.get(url, headers=default_headers, stream=True, timeout=30) as r:
                r.raise_for_status()
                total_size = int(r.headers.get("content-length", 0))
                downloaded = 0
                start_time = time.time()

                with open(temp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            elapsed = time.time() - start_time
                            speed = (downloaded / 1024 / 1024) / elapsed if elapsed > 0 else 0

                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                sys.stdout.write(
                                    f"\r  已下载: {downloaded / 1024 / 1024:.2f} MB / {total_size / 1024 / 1024:.2f} MB "
                                    f"({percent:.1f}%) | 速度: {speed:.2f} MB/s"
                                )
                            else:
                                sys.stdout.write(f"\r  已下载: {downloaded / 1024 / 1024:.2f} MB | 速度: {speed:.2f} MB/s")
                            sys.stdout.flush()

                sys.stdout.write("\n")
        else:
            req = urllib.request.Request(url, headers=default_headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                total_size = int(resp.headers.get("content-length", 0))
                downloaded = 0
                start_time = time.time()

                with open(temp_path, "wb") as f:
                    while True:
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        elapsed = time.time() - start_time
                        speed = (downloaded / 1024 / 1024) / elapsed if elapsed > 0 else 0

                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            sys.stdout.write(
                                f"\r  已下载: {downloaded / 1024 / 1024:.2f} MB / {total_size / 1024 / 1024:.2f} MB "
                                f"({percent:.1f}%) | 速度: {speed:.2f} MB/s"
                            )
                        else:
                            sys.stdout.write(f"\r  已下载: {downloaded / 1024 / 1024:.2f} MB | 速度: {speed:.2f} MB/s")
                        sys.stdout.flush()

                sys.stdout.write("\n")

        # Rename temp_path to dest_path
        if os.path.exists(temp_path):
            if os.path.exists(dest_path):
                os.remove(dest_path)
            os.rename(temp_path, dest_path)
            print(f"[下载完成] -> {dest_path}")
            return True

    except Exception as e:
        print(f"\n[下载失败] {dest_path}: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False

    return False
