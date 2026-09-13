#!/usr/bin/env python3
import os
import re
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tencent_meeting.formatter import (
    format_to_markdown,
    format_to_txt,
    format_to_srt,
    format_to_json,
    extract_paragraphs
)
from tencent_meeting.downloader import download_file
from tencent_meeting.state import (
    VIDEO_DONE,
    VIDEO_SKIPPED,
    VIDEO_UNKNOWN,
    bootstrap_state,
    is_complete,
    load_state,
    new_entry,
    record_identifier,
    save_state,
    state_path_for
)


class _FakeMiddleClient:
    """Stub of TencentMeetingClient.get_shared_record_middle_list for container tests."""

    def __init__(self, sub_items):
        self._sub_items = sub_items

    def get_shared_record_middle_list(self, share_id):
        return {"topic": "合集主题", "meeting_id": "m1", "sub_items": self._sub_items}


class TestExpandMiddleContainers(unittest.TestCase):
    """回归：父合集只有在全部子记录备份完成后才能标记为完成容器。

    此前父记录在展开成功时即被标完成，导致增量运行跳过整个合集，
    未完成视频的子记录（如 协同之舞-品德成功论_录制1）永远不会再被处理。
    """

    PARENT = {"meeting_id": "", "recording_id": "", "share_id": "parentS",
              "detail_id": "", "topic": "合集", "is_shared_middle": True}

    @staticmethod
    def _sub(detail_id):
        return {"meeting_id": "", "recording_id": "r-" + detail_id, "detail_id": detail_id,
                "share_id": "sh-" + detail_id, "topic": "子-" + detail_id}

    @staticmethod
    def _done_entry(topic):
        entry = new_entry(topic)
        entry["transcript_done"] = True
        entry["video"] = VIDEO_DONE
        return entry

    def test_parent_not_marked_when_some_subs_incomplete(self):
        import main as main_mod
        state = {"records": {"d1": self._done_entry("子-d1")}}  # d2 缺失 → 未完成
        client = _FakeMiddleClient([self._sub("d1"), self._sub("d2")])
        expanded = main_mod.expand_shared_middle_items(client, [dict(self.PARENT)], state, incremental=True)
        self.assertEqual(len(expanded), 2)
        self.assertNotIn("parentS", state["records"])  # 父记录不得提前标完成

    def test_parent_marked_and_skipped_when_all_subs_done(self):
        import main as main_mod
        state = {"records": {"d1": self._done_entry("子-d1"), "d2": self._done_entry("子-d2")}}
        client = _FakeMiddleClient([self._sub("d1"), self._sub("d2")])
        expanded = main_mod.expand_shared_middle_items(client, [dict(self.PARENT)], state, incremental=True)
        self.assertEqual(len(expanded), 2)  # 子记录仍进入列表，由主循环增量跳过
        self.assertTrue(state["records"]["parentS"]["container"])
        # 父记录完成后，下一次运行应整体跳过展开
        expanded2 = main_mod.expand_shared_middle_items(client, [dict(self.PARENT)], state, incremental=True)
        self.assertEqual(expanded2, [])

    def test_full_mode_always_expands(self):
        import main as main_mod
        state = {"records": {"d1": self._done_entry("子-d1"), "d2": self._done_entry("子-d2")}}
        client = _FakeMiddleClient([self._sub("d1"), self._sub("d2")])
        main_mod.expand_shared_middle_items(client, [dict(self.PARENT)], state, incremental=True)
        expanded = main_mod.expand_shared_middle_items(client, [dict(self.PARENT)], state, incremental=False)
        self.assertEqual(len(expanded), 2)  # --full 不跳过

class TestTencentMeetingBackup(unittest.TestCase):

    def setUp(self):
        self.sample_data = {
            "code": 0,
            "msg": "ok",
            "minutes": {
                "lang": "zh",
                "paragraphs": [
                    {
                        "pid": "0",
                        "speaker_info": {"user_name": "张三"},
                        "start_time": 1000,
                        "end_time": 5000,
                        "sentences": [
                            {
                                "words": [{"text": "大家好，今天我们来讨论一下项目规划。"}]
                            }
                        ]
                    },
                    {
                        "pid": "1",
                        "speaker_info": {"user_name": "李四"},
                        "start_time": 5500,
                        "end_time": 9000,
                        "sentences": [
                            {
                                "words": [{"text": "好的，我认为备份工具的抓取与导出模块非常关键。"}]
                            }
                        ]
                    }
                ]
            }
        }

    def test_extract_paragraphs(self):
        paragraphs = extract_paragraphs(self.sample_data)
        self.assertEqual(len(paragraphs), 2)
        self.assertEqual(paragraphs[0]["speaker"], "张三")
        self.assertEqual(paragraphs[0]["start_ms"], 1000)
        self.assertIn("项目规划", paragraphs[0]["text"])

    def test_format_to_markdown(self):
        md = format_to_markdown(self.sample_data, title="测试会议")
        self.assertIn("# 测试会议", md)
        self.assertIn("`[00:00:01]` **张三**", md)
        self.assertIn("大家好，今天我们来讨论一下项目规划。", md)

    def test_format_to_txt(self):
        txt = format_to_txt(self.sample_data, title="测试会议")
        self.assertIn("[00:00:01] 张三: 大家好，今天我们来讨论一下项目规划。", txt)

    def test_format_to_srt(self):
        srt = format_to_srt(self.sample_data)
        self.assertIn("00:00:01,000 --> 00:00:05,000", srt)
        self.assertIn("张三: 大家好，今天我们来讨论一下项目规划。", srt)

    def test_downloader_file_skip(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"existing data")
            tmp_path = tmp.name

        try:
            # Downloading without overwrite should skip existing non-empty file
            result = download_file("http://example.com/fake", tmp_path, overwrite=False)
            self.assertTrue(result)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_parse_shared_record_middle_url(self):
        from tencent_meeting.url_parser import parse_tencent_meeting_url
        url = "https://meeting.tencent.com/user-center/shared-record-middle?s=sKOvc8uzP0m3wKeqOf4B4-dbRcitkw6MS48i412MBh4&from=0"
        parsed = parse_tencent_meeting_url(url)
        self.assertTrue(parsed["is_shared_middle"])
        self.assertEqual(parsed["share_id"], "sKOvc8uzP0m3wKeqOf4B4-dbRcitkw6MS48i412MBh4")


class TestBackupState(unittest.TestCase):

    def test_record_identifier_precedence(self):
        # 与目录命名一致的优先级：detail_id > recording_id > share_id > meeting_id
        self.assertEqual(record_identifier("d", "r", "s", "m"), "d")
        self.assertEqual(record_identifier("", "r", "s", "m"), "r")
        self.assertEqual(record_identifier("", "", "s", "m"), "s")
        self.assertEqual(record_identifier("", "", "", "m"), "m")
        self.assertEqual(record_identifier(), "meeting")

    def test_is_complete_variants(self):
        self.assertFalse(is_complete(None))
        self.assertFalse(is_complete(new_entry("t")))

        entry = new_entry("t")
        entry["transcript_done"] = True
        entry["video"] = VIDEO_UNKNOWN
        self.assertFalse(is_complete(entry))  # 视频状态未知时不视为完成

        entry["video"] = VIDEO_DONE
        self.assertTrue(is_complete(entry))

        entry["video"] = VIDEO_SKIPPED
        self.assertTrue(is_complete(entry))  # 纯转写类记录（无视频）视为完成

        entry["video"] = "failed"
        self.assertFalse(is_complete(entry))

    def test_bootstrap_from_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            ident = "abc-123"
            folder = os.path.join(tmp, f"测试会议_{ident}")
            os.makedirs(folder)
            for fmt in ("md", "txt", "json", "srt"):
                with open(os.path.join(folder, f"transcript_{ident}.{fmt}"), "w", encoding="utf-8") as f:
                    f.write("内容")

            state = bootstrap_state(tmp)
            entry = state["records"][ident]
            self.assertTrue(entry["transcript_done"])
            self.assertEqual(entry["video"], VIDEO_UNKNOWN)  # 无视频文件时状态未知，待与 API 对账
            self.assertFalse(is_complete(entry))

            # 补上视频文件后引导结果应为完整
            with open(os.path.join(folder, f"video_{ident}.mp4"), "wb") as f:
                f.write(b"video")
            state = bootstrap_state(tmp)
            self.assertTrue(is_complete(state["records"][ident]))
            self.assertEqual(state["records"][ident]["topic"], "测试会议")

    def test_bootstrap_ignores_non_record_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "无标识符目录"))
            os.makedirs(os.path.join(tmp, ".backup_state.json"))
            with open(os.path.join(tmp, "loose_file.txt"), "w") as f:
                f.write("x")
            state = bootstrap_state(tmp)
            self.assertEqual(state["records"], {})

    def test_load_state_fallback_on_corrupt_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            ident = "xyz-789"
            folder = os.path.join(tmp, f"会议_{ident}")
            os.makedirs(folder)
            for fmt in ("md", "txt", "json", "srt"):
                with open(os.path.join(folder, f"transcript_{ident}.{fmt}"), "w", encoding="utf-8") as f:
                    f.write("内容")

            # 损坏的状态文件应回退到磁盘扫描引导
            with open(state_path_for(tmp), "w", encoding="utf-8") as f:
                f.write("{broken json")
            state = load_state(tmp)
            self.assertIn(ident, state["records"])

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = {"records": {"id-1": new_entry("会议A")}}
            state["records"]["id-1"]["transcript_done"] = True
            state["records"]["id-1"]["video"] = VIDEO_SKIPPED
            save_state(tmp, state)
            loaded = load_state(tmp)
            self.assertTrue(is_complete(loaded["records"]["id-1"]))
            self.assertTrue(os.path.exists(state_path_for(tmp)))

class _RangeAwareHandler(BaseHTTPRequestHandler):
    """本地测试服务器：honor_range=True 时按 Range 返回 206 部分内容。"""

    honor_range = True
    payload = bytes(range(256)) * 64  # 16 KB 测试数据

    def do_GET(self):
        start = 0
        range_header = self.headers.get("Range")
        if self.honor_range and range_header:
            m = re.search(r"bytes=(\d+)-", range_header)
            if m and int(m.group(1)) < len(self.payload):
                start = int(m.group(1))
        if start > 0:
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(self.payload) - 1}/{len(self.payload)}")
        else:
            start = 0
            self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload) - start))
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(self.payload[start:])

    def log_message(self, *args):
        pass


class TestDownloaderResume(unittest.TestCase):
    """断点续传：中断后保留 .tmp 携带 Range 续传；服务端忽略 Range 时从头重写。"""

    @staticmethod
    def _serve(handler_cls):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server, f"http://127.0.0.1:{server.server_address[1]}/file.bin"

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.dest = os.path.join(self._tmpdir.name, "video.mp4")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_resume_partial_download(self):
        server, url = self._serve(_RangeAwareHandler)
        try:
            payload = _RangeAwareHandler.payload
            cut = len(payload) // 3
            with open(self.dest + ".tmp", "wb") as f:
                f.write(payload[:cut])  # 模拟上次中断留下的半截文件
            self.assertTrue(download_file(url, self.dest))
            with open(self.dest, "rb") as f:
                self.assertEqual(f.read(), payload)
            self.assertFalse(os.path.exists(self.dest + ".tmp"))
        finally:
            server.shutdown()

    def test_restart_when_range_ignored(self):
        class _NoRangeHandler(_RangeAwareHandler):
            honor_range = False

        server, url = self._serve(_NoRangeHandler)
        try:
            with open(self.dest + ".tmp", "wb") as f:
                f.write(b"STALE-GARBAGE")  # 服务端忽略 Range，必须丢弃旧内容从头写
            self.assertTrue(download_file(url, self.dest))
            with open(self.dest, "rb") as f:
                self.assertEqual(f.read(), _NoRangeHandler.payload)
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()

