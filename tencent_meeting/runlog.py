"""运行日志：main.py 每次执行的完整留档与结果摘要。

- 终端输出照常实时显示，同时双写（tee）到 logs/run-<时间戳>-<模式>.log；
- 运行结束向 logs/run_index.jsonl 追加一行机器可读摘要（成功/失败数、
  失败记录及原因、清理模式统计），便于直接回查任意一次运行的结果。
- 文件侧抑制以 \\r 开头的单行进度刷新（下载器进度条），避免日志膨胀。

日志包含会议标题/标识符等个人信息，logs/ 目录已在 .gitignore 中，严禁提交。
"""
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, TextIO

# 运行摘要索引文件（位于日志目录内，JSONL，每次运行追加一行）
RUN_INDEX_FILENAME = "run_index.jsonl"
# 摘要中失败明细最多保留条数（防止极端情况下索引行过长）
MAX_FAILURES_IN_SUMMARY = 50


class Tee:
    """stdout/stderr 双写分流器：终端原样透传，文件侧抑制 \\r 进度刷新行。"""

    def __init__(self, stream: TextIO, log_file: TextIO):
        self._stream = stream
        self._file = log_file
        self._in_progress_line = False  # 当前正处在一个 \r 刷新行内，其内容不落盘

    def write(self, text: str) -> int:
        try:
            self._stream.write(text)
        except Exception:
            pass  # 终端异常（如管道关闭）不阻断业务
        try:
            self._write_to_file(text)
        except Exception:
            pass  # 日志写入失败绝不影响业务
        return len(text)

    def _write_to_file(self, text: str) -> None:
        pos = 0
        while pos < len(text):
            if self._in_progress_line:
                # 丢弃刷新行内容，直到行结束（\n）为止
                nl = text.find("\n", pos)
                if nl == -1:
                    return  # 整段都在进度行内，全部丢弃
                self._in_progress_line = False
                pos = nl + 1
            else:
                cr = text.find("\r", pos)
                nl = text.find("\n", pos)
                if cr != -1 and (nl == -1 or cr < nl):
                    # \r 出现在行中：先把 \r 之前的部分写入文件，随后进入进度行
                    self._file.write(text[pos:cr])
                    self._in_progress_line = True
                    pos = cr + 1
                elif nl != -1:
                    self._file.write(text[pos:nl + 1])
                    pos = nl + 1
                else:
                    self._file.write(text[pos:])
                    return

    def flush(self) -> None:
        try:
            self._stream.flush()
        except Exception:
            pass
        try:
            self._file.flush()
        except Exception:
            pass

    def __getattr__(self, name: str) -> Any:
        # isatty / encoding 等属性透传给原终端流
        return getattr(self._stream, name)


class RunLog:
    """一次 main.py 运行的日志上下文：双写安装、结果采集、摘要落盘。

    用法：
        run = RunLog("incremental")
        try:
            ...业务...
        except BaseException as e:
            run.finish(status=...)
            raise
        run.finish()
    """

    def __init__(self, mode: str, log_dir: str = "logs", meta: Optional[Dict[str, Any]] = None):
        self.mode = mode
        self.log_dir = log_dir
        self.meta = meta or {}
        self.counters: Dict[str, int] = {
            "processed": 0, "success": 0, "failed": 0,
            "videos": 0, "audios": 0, "transcripts": 0,
        }
        self.extra: Dict[str, Any] = {}     # 各模式自定义统计（如清理模式的删除数）
        self.failures: List[Dict[str, str]] = []
        self._start_ts = time.time()
        self.ts_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        os.makedirs(log_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S.%f")[:-3]  # 毫秒，防同秒冲突
        self.log_path = os.path.join(log_dir, f"run-{stamp}-{mode}.log")
        self._file = open(self.log_path, "w", encoding="utf-8", buffering=1)

        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        sys.stdout = Tee(self._orig_stdout, self._file)
        sys.stderr = Tee(self._orig_stderr, self._file)
        self._emit(f"[运行日志] mode={mode} start={self.ts_start} file={self.log_path}")

    # ---- 业务侧采集接口 ----

    def bump(self, key: str, n: int = 1) -> None:
        """累加计数器（processed/success/failed/videos/audios/transcripts）。"""
        self.counters[key] = self.counters.get(key, 0) + n

    def record_failure(self, identifier: str, topic: str, reason: str) -> None:
        """登记一条失败记录（含原因），写入当次日志与最终摘要。"""
        self.failures.append({
            "identifier": str(identifier)[:64],
            "topic": str(topic)[:80],
            "reason": str(reason)[:160],
        })
        self._emit(f"[失败] {topic} ({identifier}): {reason}")

    # ---- 收尾 ----

    def finish(self, status: str = "ok", error: str = "") -> None:
        if getattr(self, "_finished", False):
            return
        self._finished = True
        duration = round(time.time() - self._start_ts, 1)
        ts_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if sys.stdout is not None and isinstance(sys.stdout, Tee):
            sys.stdout = self._orig_stdout
        if isinstance(sys.stderr, Tee):
            sys.stderr = self._orig_stderr

        summary = {
            "ts_start": self.ts_start,
            "ts_end": ts_end,
            "duration_s": duration,
            "mode": self.mode,
            "status": status,
            "error": error[:500],
            **self.counters,
            "failures": self.failures[:MAX_FAILURES_IN_SUMMARY],
            "failures_total": len(self.failures),
            **self.extra,
        }
        if self.meta:
            summary["meta"] = self.meta

        # 人读摘要写入当次日志尾部
        self._emit("=" * 56)
        self._emit(f"[运行摘要] mode={self.mode} status={status} 耗时={duration}s")
        self._emit(f"处理 {self.counters['processed']} | 成功 {self.counters['success']}"
                   f" | 失败 {self.counters['failed']}"
                   f" | 视频 {self.counters['videos']} | 音频 {self.counters['audios']}"
                   f" | 转写 {self.counters['transcripts']}")
        for k, v in self.extra.items():
            self._emit(f"{k}: {v}")
        if self.failures:
            self._emit(f"失败明细（{len(self.failures)} 条）：")
            for f in self.failures[:MAX_FAILURES_IN_SUMMARY]:
                self._emit(f"  - {f['topic']} ({f['identifier']}): {f['reason']}")
        if error:
            self._emit(f"异常: {error[:500]}")
        self._emit("=" * 56)
        self._file.close()

        # 机器可读索引：每次运行追加一行
        try:
            index_path = os.path.join(self.log_dir, RUN_INDEX_FILENAME)
            with open(index_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(summary, ensure_ascii=False) + "\n")
        except Exception as e:
            # 摘要索引写失败不影响业务，但要让人在当次日志里能看到
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(f"[警告] 运行摘要索引写入失败: {e}\n")
            except Exception:
                pass

        # 摘要一行同步到终端，方便直接看结果
        print(f"[运行日志] 本次运行已留档: {self.log_path} ({self.mode}, {status}, "
              f"成功 {self.counters['success']}/{self.counters['processed']})")

    def _emit(self, line: str) -> None:
        """直接写一行到日志文件（不经过 Tee，避免自我递归）。"""
        try:
            self._file.write(line + "\n")
            self._file.flush()
        except Exception:
            pass


def mode_label(args) -> str:
    """根据命令行参数推断本次运行的模式标签（用于日志文件名与摘要）。"""
    if getattr(args, "clean", False):
        return "clean-apply" if getattr(args, "apply", False) else "clean"
    if getattr(args, "meeting_id", None) or getattr(args, "recording_id", None) \
            or getattr(args, "share_id", None):
        return "single"
    if getattr(args, "file", None):
        return "batch"
    return "full" if getattr(args, "full", False) else "incremental"
