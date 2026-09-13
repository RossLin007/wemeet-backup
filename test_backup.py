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
    AUDIO_DONE,
    AUDIO_OFF,
    AUDIO_UNKNOWN,
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
        entry["audio"] = AUDIO_DONE
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
        self.assertFalse(is_complete(entry))  # 音频未对账（unknown）时不视为完成

        entry["audio"] = AUDIO_UNKNOWN
        self.assertFalse(is_complete(entry))

        entry["audio"] = AUDIO_DONE
        self.assertTrue(is_complete(entry))

        entry["video"] = VIDEO_SKIPPED
        entry["audio"] = AUDIO_OFF
        self.assertTrue(is_complete(entry))  # 纯转写记录 / 未启用音频下载均视为完成

        entry["video"] = "failed"
        self.assertFalse(is_complete(entry))

        # 旧版状态文件无 audio 键：按 unknown 处理，需重新对账
        legacy = {"transcript_done": True, "video": VIDEO_DONE}
        self.assertFalse(is_complete(legacy))
        legacy["audio"] = AUDIO_DONE
        self.assertTrue(is_complete(legacy))

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

            # 补上视频文件后音频仍未对账，不视为完整
            with open(os.path.join(folder, f"video_{ident}.mp4"), "wb") as f:
                f.write(b"video")
            state = bootstrap_state(tmp)
            self.assertEqual(state["records"][ident]["video"], VIDEO_DONE)
            self.assertFalse(is_complete(state["records"][ident]))

            # 再补上音频文件后引导结果应为完整
            with open(os.path.join(folder, f"audio_{ident}.m4a"), "wb") as f:
                f.write(b"audio")
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
            state["records"]["id-1"]["audio"] = AUDIO_OFF
            save_state(tmp, state)
            loaded = load_state(tmp)
            self.assertTrue(is_complete(loaded["records"]["id-1"]))
            self.assertTrue(os.path.exists(state_path_for(tmp)))


class TestMediaLinks(unittest.TestCase):
    """媒体直链（download/meeting）解析、分发与状态更新。"""

    class _FakeLinkClient:
        def __init__(self, media=None, error=False):
            self.media = media or {}
            self.error = error
            self.calls = []

        def get_download_links(self, uni):
            self.calls.append(uni)
            if self.error:
                raise RuntimeError("boom")
            return self.media

    def test_get_download_links_parsing(self):
        from unittest.mock import patch
        from tencent_meeting.client import TencentMeetingClient
        fake = {"code": 0, "links": [
            {"link": "https://x/cos/200000001/111/222/a.mp4?token=1",
             "audio_link": "https://x/cos/200000001/111/222/a.m4a?token=2"},
            {"link": "https://x/cos/200000001/111/333/b.mp4?token=1",
             "audio_link": ""},
        ]}
        client = TencentMeetingClient("web_uid=u")
        with patch.object(client, "_get", return_value=fake):
            media = client.get_download_links("111")
        self.assertEqual(set(media), {"222", "333"})
        self.assertTrue(media["222"]["video_url"].endswith("a.mp4?token=1"))
        self.assertTrue(media["222"]["audio_url"].endswith("a.m4a?token=2"))
        self.assertEqual(media["333"]["audio_url"], "")  # 无独立音频的录制

    def test_attach_media_links_distribution(self):
        import main as main_mod
        media = {"111": {"video_url": "v111", "audio_url": "a111"}}
        client = self._FakeLinkClient(media)
        items = [
            {"topic": "单条", "has_video": True, "uni_record_id": "110",
             "recording_id": "111", "is_shared_middle": False, "share_id": ""},
            {"topic": "合集", "has_video": True, "uni_record_id": "9",
             "recording_id": "10", "is_shared_middle": True, "share_id": "sX"},
            {"topic": "纯转写", "has_video": False, "uni_record_id": "5", "recording_id": "6"},
        ]
        out = main_mod.attach_media_links(client, items)
        self.assertEqual(client.calls, ["110", "9"])  # 纯转写记录不解析
        self.assertEqual(out[0]["video_url"], "v111")
        self.assertEqual(out[0]["audio_url"], "a111")
        self.assertTrue(out[0]["media_links_ok"])
        self.assertEqual(out[1]["_media_links"], media)  # 合集挂整份映射待分发
        self.assertNotIn("_media_links", items[2])

    def test_attach_media_links_failure_keeps_fallback(self):
        import main as main_mod
        client = self._FakeLinkClient(error=True)
        items = [{"topic": "t", "has_video": True, "uni_record_id": "1",
                  "recording_id": "2", "is_shared_middle": False}]
        out = main_mod.attach_media_links(client, items)
        self.assertFalse(out[0]["media_links_ok"])
        self.assertEqual(out[0].get("video_url", ""), "")
        self.assertEqual(out[0].get("audio_url", ""), "")

    def test_expand_propagates_links_to_subs(self):
        import main as main_mod
        media = {"r-d2": {"video_url": "vd2", "audio_url": "ad2"}}
        parent = {"meeting_id": "", "recording_id": "", "share_id": "pS", "detail_id": "",
                  "topic": "合集", "is_shared_middle": True,
                  "_media_links": media, "media_links_ok": True}
        subs = [{"meeting_id": "", "recording_id": "r-d1", "detail_id": "d1",
                 "share_id": "sh-d1", "topic": "s1"},
                {"meeting_id": "", "recording_id": "r-d2", "detail_id": "d2",
                 "share_id": "sh-d2", "topic": "s2"}]
        state = {"records": {}}
        expanded = main_mod.expand_shared_middle_items(_FakeMiddleClient(subs), [parent], state, incremental=True)
        by_rid = {e["recording_id"]: e for e in expanded}
        self.assertEqual(by_rid["r-d2"]["video_url"], "vd2")
        self.assertEqual(by_rid["r-d2"]["audio_url"], "ad2")
        self.assertEqual(by_rid["r-d1"].get("video_url", ""), "")  # 无匹配资源保持为空
        self.assertTrue(by_rid["r-d1"]["media_links_ok"])

    def test_update_record_state_audio_mapping(self):
        import main as main_mod
        item = {"topic": "t"}
        cases = [
            ("done", "done"), ("exists", "done"), ("skipped", "skipped"),
            ("failed", "failed"), ("off", AUDIO_OFF),
        ]
        for i, (result_audio, expected) in enumerate(cases):
            state = {"records": {}}
            main_mod.update_record_state(state, f"i{i}", item,
                                         {"transcript": "done", "video": "skipped", "audio": result_audio})
            self.assertEqual(state["records"][f"i{i}"]["audio"], expected)

        # none：直链未解析到，保留原状态（unknown）待重试，且不计失败
        state = {"records": {"keep": new_entry("t")}}
        state["records"]["keep"]["transcript_done"] = True
        state["records"]["keep"]["video"] = VIDEO_SKIPPED
        state["records"]["keep"]["audio"] = AUDIO_UNKNOWN
        main_mod.update_record_state(state, "keep", item,
                                     {"transcript": "done", "video": "skipped", "audio": "none"})
        self.assertEqual(state["records"]["keep"]["audio"], AUDIO_UNKNOWN)
        self.assertEqual(state["records"]["keep"]["fails"], 0)

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

