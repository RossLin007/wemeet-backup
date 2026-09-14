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


class _FakeCleanClient:
    """Stub of TencentMeetingClient for cleaner tests."""

    def __init__(self, items, subs=None, fail_delete=False):
        self._items = items
        self._subs = subs or []
        self.deleted = []  # 每次 delete_record 的 uni_record_ids 参数
        self.fail_delete = fail_delete

    def get_all_user_meetings(self):
        return self._items

    def get_shared_record_middle_list(self, share_id):
        return {"topic": "合集主题", "meeting_id": "", "sub_items": self._subs}

    def delete_record(self, uni_record_ids):
        self.deleted.append(list(uni_record_ids))
        if self.fail_delete:
            raise RuntimeError("cookie expired")
        return {"code": 0}


class TestCleaner(unittest.TestCase):
    """清理模式：只删「线上有视频 + 状态完成 + 本地实物齐备」的记录，默认干跑。"""

    FORMATS = ["md"]

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def _backup_dir(self, ident, topic="主题", with_video=True, with_transcript=True):
        d = os.path.join(self.out, f"{topic}_{ident}")
        os.makedirs(d, exist_ok=True)
        if with_video:
            with open(os.path.join(d, f"video_{ident}.mp4"), "wb") as f:
                f.write(b"x" * 16)
        if with_transcript:
            for fmt in self.FORMATS:
                with open(os.path.join(d, f"transcript_{ident}.{fmt}"), "wb") as f:
                    f.write(b"t")
        return d

    @staticmethod
    def _done_entry(topic="主题"):
        entry = new_entry(topic)
        entry["transcript_done"] = True
        entry["video"] = VIDEO_DONE
        entry["audio"] = AUDIO_DONE
        return entry

    def _item(self, ident, uni="9001", **over):
        item = {"meeting_id": "m1", "recording_id": "9002", "detail_id": ident,
                "share_id": "", "uni_record_id": uni, "topic": "主题" + ident,
                "record_type": "cloud_record", "has_video": True,
                "is_shared_middle": False, "jump_path": "",
                "allow_delete": True, "cloud_size": 1000}
        item.update(over)
        return item

    def _state(self, *idents):
        return {"records": {i: self._done_entry() for i in idents}}

    def test_selects_fully_backed_video_record(self):
        from tencent_meeting.cleaner import select_deletable
        self._backup_dir("id1")
        self._backup_dir("id2")
        client = _FakeCleanClient([self._item("id1", uni="9001"),
                                   self._item("id2", uni="1000")])
        deletable, skipped = select_deletable(client, self._state("id1", "id2"), self.out, self.FORMATS)
        self.assertEqual(len(deletable), 2)
        self.assertEqual(skipped, [])
        # 旧记录（uni 小）排在前面，--limit 截断时优先删最旧的
        self.assertEqual([d["uni_record_id"] for d in deletable], ["1000", "9001"])

    def test_skips_when_local_video_missing(self):
        from tencent_meeting.cleaner import select_deletable
        self._backup_dir("id1", with_video=False)  # 状态完成但视频文件不在盘
        client = _FakeCleanClient([self._item("id1")])
        deletable, skipped = select_deletable(client, self._state("id1"), self.out, self.FORMATS)
        self.assertEqual(deletable, [])
        self.assertIn("本地视频文件缺失", skipped[0]["reason"])

    def test_skips_when_state_incomplete_or_ambiguous_dir(self):
        from tencent_meeting.cleaner import select_deletable
        # 状态缺失
        self._backup_dir("id1")
        client = _FakeCleanClient([self._item("id1")])
        deletable, skipped = select_deletable(client, self._state(), self.out, self.FORMATS)
        self.assertEqual(deletable, [])
        self.assertIn("备份状态未完成", skipped[0]["reason"])
        # 同一标识符有两个候选目录 → 无法唯一定位，跳过
        self._backup_dir("id2", topic="a")
        self._backup_dir("id2", topic="b")
        client = _FakeCleanClient([self._item("id2")])
        deletable, skipped = select_deletable(client, self._state("id2"), self.out, self.FORMATS)
        self.assertEqual(deletable, [])
        self.assertIn("无法唯一定位", skipped[0]["reason"])

    def test_ignores_no_video_and_allow_delete_false(self):
        from tencent_meeting.cleaner import select_deletable
        self._backup_dir("id1")
        self._backup_dir("id2")
        client = _FakeCleanClient([
            self._item("id1", has_video=False),
            self._item("id2", allow_delete=False),
        ])
        deletable, skipped = select_deletable(client, self._state("id1", "id2"), self.out, self.FORMATS)
        self.assertEqual(deletable, [])  # 无视频记录连跳过清单都不进
        self.assertEqual(len(skipped), 1)
        self.assertIn("allow_delete", skipped[0]["reason"])

    def test_container_requires_all_subs_backed_up(self):
        from tencent_meeting.cleaner import select_deletable
        parent = self._item("", uni="9005", detail_id="", share_id="parentS",
                            is_shared_middle=True, topic="合集",
                            recording_id="", meeting_id="")
        subs = [{"meeting_id": "", "recording_id": "r1", "detail_id": "d1",
                 "share_id": "sh-d1", "topic": "子1"},
                {"meeting_id": "", "recording_id": "r2", "detail_id": "d2",
                 "share_id": "sh-d2", "topic": "子2"}]
        self._backup_dir("d1")
        self._backup_dir("d2", with_video=False)  # 子2 视频缺失
        state = self._state("d1", "d2", "parentS")
        client = _FakeCleanClient([parent], subs=subs)
        deletable, skipped = select_deletable(client, state, self.out, self.FORMATS)
        self.assertEqual(deletable, [])
        self.assertIn("子记录备份不齐", skipped[0]["reason"])

        # 补齐子2 视频后整个合集可删
        with open(os.path.join(self.out, "主题_d2", "video_d2.mp4"), "wb") as f:
            f.write(b"x" * 16)
        deletable, skipped = select_deletable(client, state, self.out, self.FORMATS)
        self.assertEqual(len(deletable), 1)
        self.assertTrue(deletable[0]["is_container"])
        self.assertEqual(deletable[0]["sub_identifiers"], ["d1", "d2"])

    def test_dry_run_never_deletes(self):
        from tencent_meeting.cleaner import run_cleaner, DELETION_LOG_FILENAME
        self._backup_dir("id1")
        client = _FakeCleanClient([self._item("id1")])
        state = self._state("id1")
        rc = run_cleaner(client, state, self.out, self.FORMATS, apply=False)
        self.assertEqual(rc, 0)
        self.assertEqual(client.deleted, [])  # 干跑绝不调用删除
        self.assertFalse(os.path.exists(os.path.join(self.out, DELETION_LOG_FILENAME)))
        self.assertNotIn("deleted_online", state["records"]["id1"])

    def test_apply_deletes_marks_state_and_logs(self):
        from tencent_meeting.cleaner import run_cleaner, DELETION_LOG_FILENAME
        self._backup_dir("id1")
        client = _FakeCleanClient([self._item("id1")])
        state = self._state("id1")
        rc = run_cleaner(client, state, self.out, self.FORMATS,
                         apply=True, assume_yes=True)
        self.assertEqual(rc, 0)
        self.assertEqual(client.deleted, [["9001"]])
        self.assertTrue(state["records"]["id1"]["deleted_online"])  # 审计标记
        log_path = os.path.join(self.out, DELETION_LOG_FILENAME)
        self.assertTrue(os.path.exists(log_path))
        with open(log_path, "r", encoding="utf-8") as f:
            entry = json.loads(f.read().strip())
        self.assertEqual(entry["uni_record_id"], "9001")
        self.assertTrue(entry["ok"])
        # 本地备份原样保留
        self.assertTrue(os.path.getsize(os.path.join(self.out, "主题_id1", "video_id1.mp4")) > 0)

    def test_apply_confirm_mismatch_cancels(self):
        from tencent_meeting.cleaner import run_cleaner
        self._backup_dir("id1")
        client = _FakeCleanClient([self._item("id1")])
        rc = run_cleaner(client, self._state("id1"), self.out, self.FORMATS,
                         apply=True, prompt=lambda _: "错的输入")
        self.assertEqual(rc, 0)
        self.assertEqual(client.deleted, [])

    def test_apply_failure_circuit_breaker(self):
        from tencent_meeting.cleaner import run_cleaner, DELETION_LOG_FILENAME
        items = [self._item(f"id{i}", uni=str(9000 + i)) for i in range(1, 5)]
        for i in range(1, 5):
            self._backup_dir(f"id{i}")
        state = self._state(*[f"id{i}" for i in range(1, 5)])
        client = _FakeCleanClient(items, fail_delete=True)
        rc = run_cleaner(client, state, self.out, self.FORMATS,
                         apply=True, assume_yes=True)
        self.assertEqual(rc, 0)
        self.assertEqual(len(client.deleted), 3)  # 连续 3 次失败熔断，第 4 条不再尝试
        for i in range(1, 5):
            self.assertNotIn("deleted_online", state["records"][f"id{i}"])


class TestDownloaderForbiddenResume(unittest.TestCase):
    """续传被 403 拒（直链 token 失效/风控）：丢弃 .tmp 改整段重试；仍被拒则放弃且不留 .tmp。"""

    @staticmethod
    def _serve(handler_cls):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server, f"http://127.0.0.1:{server.server_address[1]}/file.bin"

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.dest = os.path.join(self._tmpdir.name, "media.mp4")
        self.addCleanup(self._tmpdir.cleanup)

    def test_restart_fresh_when_resume_forbidden(self):
        class _ForbiddenRangeHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.headers.get("Range"):
                    self.send_response(403)
                    self.end_headers()
                    return
                payload = _RangeAwareHandler.payload
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        server, url = self._serve(_ForbiddenRangeHandler)
        try:
            with open(self.dest + ".tmp", "wb") as f:
                f.write(b"PARTIAL")
            self.assertTrue(download_file(url, self.dest))
            with open(self.dest, "rb") as f:
                self.assertEqual(f.read(), _RangeAwareHandler.payload)
            self.assertFalse(os.path.exists(self.dest + ".tmp"))
        finally:
            server.shutdown()

    def test_give_up_and_cleanup_when_always_forbidden(self):
        class _AlwaysForbiddenHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(403)
                self.end_headers()

            def log_message(self, *args):
                pass

        server, url = self._serve(_AlwaysForbiddenHandler)
        try:
            with open(self.dest + ".tmp", "wb") as f:
                f.write(b"PARTIAL")
            self.assertFalse(download_file(url, self.dest))
            self.assertFalse(os.path.exists(self.dest + ".tmp"))
        finally:
            server.shutdown()


class TestRenameMigration(unittest.TestCase):
    """云端会议改名后：旧主题目录唯一存在时自动迁移目录名，避免同标识符双目录。"""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.out = self._tmpdir.name
        self.addCleanup(self._tmpdir.cleanup)

    def test_migrates_unique_legacy_dir(self):
        import main as main_mod
        os.makedirs(os.path.join(self.out, "旧主题_id1"), exist_ok=True)
        main_mod.migrate_legacy_dir(self.out, "新主题_id1", "id1")
        self.assertTrue(os.path.isdir(os.path.join(self.out, "新主题_id1")))
        self.assertFalse(os.path.exists(os.path.join(self.out, "旧主题_id1")))

    def test_noop_when_target_exists_or_ambiguous(self):
        import main as main_mod
        # 目标已存在：不动旧目录
        os.makedirs(os.path.join(self.out, "旧主题_id1"), exist_ok=True)
        os.makedirs(os.path.join(self.out, "新主题_id1"), exist_ok=True)
        main_mod.migrate_legacy_dir(self.out, "新主题_id1", "id1")
        self.assertTrue(os.path.isdir(os.path.join(self.out, "旧主题_id1")))
        # 旧目录有多个（歧义）：不迁移
        os.makedirs(os.path.join(self.out, "主题A_id2"), exist_ok=True)
        os.makedirs(os.path.join(self.out, "主题B_id2"), exist_ok=True)
        main_mod.migrate_legacy_dir(self.out, "新主题_id2", "id2")
        self.assertFalse(os.path.exists(os.path.join(self.out, "新主题_id2")))


if __name__ == "__main__":
    unittest.main()

