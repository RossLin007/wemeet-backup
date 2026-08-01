#!/usr/bin/env python3
import os
import tempfile
import unittest
from tencent_meeting.formatter import (
    format_to_markdown,
    format_to_txt,
    format_to_srt,
    format_to_json,
    extract_paragraphs
)
from tencent_meeting.downloader import download_file

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

if __name__ == "__main__":
    unittest.main()

