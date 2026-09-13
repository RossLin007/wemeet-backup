"""线上云录制清理：删除"本地已完整备份"的有视频记录，释放腾讯会议云存储空间。

安全约定（勿回退）：
- 默认干跑只出报告，仅 apply=True 才真删；真删前交互确认（要求输入待删条数）。
- 可删判定（全部满足才算"备份好"）：
  1) 线上有视频（record_type 属于 cloud_record/fast_record/user_upload 或为合集）；
  2) 状态清单中该记录 is_complete；
  3) 本地实物二次校验：备份目录可唯一定位，且视频/转写/音频文件按配置全部在盘且非空；
  4) 线上 allow_delete 为真。
- 合集（shared-record-middle）以父级为删除单位（删父级连带全部子记录与分享链接），
  必须所有子记录都通过 2)+3) 校验才允许删除。
- 每删一条立即原子写回状态（deleted_online 审计标记）并追加删除日志
  downloads/.deletion_log.jsonl（位于 gitignored 目录，可含会议主题供回查）。
"""
import glob
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from .state import (
    is_complete,
    new_entry,
    record_identifier,
    save_state,
    touch
)

# 删除日志文件名（位于输出目录内，随 downloads/ 一起被 gitignore）
DELETION_LOG_FILENAME = ".deletion_log.jsonl"
# 连续删除失败达到该次数即熔断，停止后续删除（防 Cookie 失效/风控时空转）
MAX_CONSECUTIVE_FAILURES = 3
# 逐条删除的间隔（秒），避免请求过快触发风控
DELETE_INTERVAL_SECONDS = 0.8


def find_local_dir(output_dir: str, identifier: str) -> Optional[str]:
    """按 `主题_标识符` 命名约定唯一定位本地备份目录。

    0 个或多个匹配均返回 None（标识符歧义时宁可跳过也不误判）。
    """
    matches = []
    for path in glob.glob(os.path.join(output_dir, f"*_{identifier}")):
        if os.path.isdir(path) and os.path.basename(path).rsplit("_", 1)[-1] == identifier:
            matches.append(path)
    return matches[0] if len(matches) == 1 else None


def verify_local_artifacts(folder: str, identifier: str, formats: List[str],
                           need_transcript: bool = True,
                           need_audio: bool = False) -> Tuple[bool, str]:
    """逐项校验本地备份产物在盘且非空（删除线上数据前的最后一道实物关卡）。"""
    video_path = os.path.join(folder, f"video_{identifier}.mp4")
    if not (os.path.isfile(video_path) and os.path.getsize(video_path) > 0):
        return False, "本地视频文件缺失或为空"
    if need_transcript:
        for fmt in formats:
            path = os.path.join(folder, f"transcript_{identifier}.{fmt}")
            if not (os.path.isfile(path) and os.path.getsize(path) > 0):
                return False, f"本地转写文件缺失({fmt})"
    if need_audio:
        audios = [p for p in glob.glob(os.path.join(folder, f"audio_{identifier}.*"))
                  if not p.endswith(".tmp")]
        if not any(os.path.isfile(p) and os.path.getsize(p) > 0 for p in audios):
            return False, "本地音频文件缺失或为空"
    return True, ""


def _local_video_bytes(folder: str, identifier: str) -> int:
    try:
        return os.path.getsize(os.path.join(folder, f"video_{identifier}.mp4"))
    except OSError:
        return 0


def human_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.2f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.2f} TB"


def _check_one_record(state: Dict[str, Any], output_dir: str, identifier: str,
                      formats: List[str], need_transcript: bool,
                      need_audio: bool) -> Tuple[bool, str]:
    """单条（非合集）记录的可删校验：状态完成 + 本地实物齐备。"""
    entry = state["records"].get(identifier)
    if not is_complete(entry):
        return False, "备份状态未完成（先完整跑一次增量备份）"
    folder = find_local_dir(output_dir, identifier)
    if not folder:
        return False, "本地备份目录缺失或无法唯一定位"
    return verify_local_artifacts(folder, identifier, formats, need_transcript, need_audio)


def select_deletable(client: Any, state: Dict[str, Any], output_dir: str,
                     formats: List[str], need_transcript: bool = True,
                     need_audio: bool = False) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """遍历线上录制列表，产出（可删清单, 跳过清单）。

    只考察有视频的顶层记录；无视频记录不在清理范围（占用小，保留线上转写）。
    """
    items = client.get_all_user_meetings()
    deletable: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for item in items:
        topic = str(item.get("topic") or "")
        if not item.get("has_video", False):
            continue
        if item.get("allow_delete") is False:
            skipped.append({"topic": topic, "reason": "线上不允许删除(allow_delete=false)"})
            continue
        uni = str(item.get("uni_record_id") or "")
        if not uni:
            skipped.append({"topic": topic, "reason": "缺少 uni_record_id，无法定位删除"})
            continue

        cloud_bytes = 0
        try:
            cloud_bytes = int(item.get("cloud_size") or 0)
        except (TypeError, ValueError):
            cloud_bytes = 0

        parent_ident = record_identifier(
            detail_id=item.get("detail_id", ""),
            recording_id=item.get("recording_id", ""),
            share_id=item.get("share_id", ""),
            meeting_id=item.get("meeting_id", "")
        )

        if item.get("is_shared_middle"):
            # 合集：删父级会连带全部子记录，须逐一校验所有子记录
            try:
                middle = client.get_shared_record_middle_list(item.get("share_id", ""))
                subs = middle.get("sub_items", [])
            except Exception as e:
                skipped.append({"topic": topic, "reason": f"合集展开失败({e})"})
                continue
            if not subs:
                skipped.append({"topic": topic, "reason": "合集无子记录"})
                continue
            if not is_complete(state["records"].get(parent_ident)):
                skipped.append({"topic": topic, "reason": "合集容器状态未完成（先完整跑一次增量备份）"})
                continue
            problems = []
            sub_idents = []
            for s in subs:
                ident = record_identifier(
                    detail_id=s.get("detail_id", ""),
                    recording_id=s.get("recording_id", ""),
                    share_id=s.get("share_id", ""),
                    meeting_id=s.get("meeting_id", "")
                )
                sub_idents.append(ident)
                ok, why = _check_one_record(state, output_dir, ident, formats,
                                            need_transcript, need_audio)
                if not ok:
                    problems.append(why)
            if problems:
                head = "；".join(sorted(set(problems))[:3])
                more = "" if len(sorted(set(problems))) <= 3 else " 等"
                skipped.append({"topic": topic,
                                "reason": f"合集子记录备份不齐（{head}{more}，共 {len(problems)}/{len(subs)} 条不满足）"})
                continue
            deletable.append({
                "topic": topic,
                "identifier": parent_ident,
                "sub_identifiers": sub_idents,
                "uni_record_id": uni,
                "folder": "",
                "video_bytes": 0,
                "cloud_bytes": cloud_bytes,
                "is_container": True,
            })
        else:
            ok, why = _check_one_record(state, output_dir, parent_ident, formats,
                                        need_transcript, need_audio)
            if not ok:
                skipped.append({"topic": topic, "reason": why})
                continue
            folder = find_local_dir(output_dir, parent_ident) or ""
            deletable.append({
                "topic": topic,
                "identifier": parent_ident,
                "sub_identifiers": [],
                "uni_record_id": uni,
                "folder": folder,
                "video_bytes": _local_video_bytes(folder, parent_ident),
                "cloud_bytes": cloud_bytes,
                "is_container": False,
            })

    # 按线上记录序（uni_record_id 数值升序）旧→新排序：--limit 截断时优先删最旧记录
    deletable.sort(key=lambda d: int(d["uni_record_id"]) if d["uni_record_id"].isdigit() else 0)
    return deletable, skipped


def _print_report(deletable: List[Dict[str, Any]], skipped: List[Dict[str, Any]]) -> None:
    total_cloud = sum(d["cloud_bytes"] for d in deletable)
    print("\n" + "=" * 60)
    print(f"🧹 待删除清单：{len(deletable)} 条线上有视频记录，预计释放 {human_size(total_cloud)}")
    print("=" * 60)
    for idx, d in enumerate(deletable, start=1):
        if d["is_container"]:
            desc = f"合集（{len(d['sub_identifiers'])} 条子记录均已本地备份）"
        else:
            rel = os.path.relpath(d["folder"]) if d["folder"] else "?"
            desc = f"本地 {rel}（视频 {human_size(d['video_bytes'])}）"
        print(f"  {idx:>3}. {d['topic']} | {desc} | 线上占用 {human_size(d['cloud_bytes'])}")
    if skipped:
        print("-" * 60)
        print(f"⛔ 暂不可删除：{len(skipped)} 条")
        for s in skipped:
            print(f"       {s['topic']} —— {s['reason']}")


def _append_deletion_log(output_dir: str, record: Dict[str, Any]) -> None:
    path = os.path.join(output_dir, DELETION_LOG_FILENAME)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _mark_deleted(state: Dict[str, Any], identifiers: List[str], topic: str) -> None:
    """在状态清单中打审计标记：本地保留，线上已删除。"""
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    for ident in identifiers:
        entry = state["records"].get(ident) or new_entry(topic)
        entry["topic"] = topic or entry.get("topic", "")
        entry["deleted_online"] = True
        entry["deleted_at"] = now
        touch(entry)
        state["records"][ident] = entry


def run_cleaner(client: Any, state: Dict[str, Any], output_dir: str,
                formats: List[str], need_transcript: bool = True,
                need_audio: bool = False, apply: bool = False,
                assume_yes: bool = False, limit: Optional[int] = None,
                prompt: Callable[[str], str] = input) -> int:
    """清理入口：干跑出报告 / apply 真删。返回退出码（0 正常）。"""
    print("[清理模式] 正在遍历线上录制列表并核对本地备份…")
    deletable, skipped = select_deletable(client, state, output_dir, formats,
                                          need_transcript, need_audio)
    _print_report(deletable, skipped)

    if not deletable:
        print("\n[清理模式] 没有可删除的记录。")
        return 0

    if limit is not None and limit >= 0:
        deletable = deletable[:limit]

    if not apply:
        print("\n[清理模式] 干跑完成，未删除任何线上数据。"
              "确认无误后加 --apply 执行删除（可先 --apply --limit 1 试删一条）。")
        return 0

    n = len(deletable)
    if not assume_yes:
        answer = prompt(f"\n⚠️  即将永久删除 {n} 条线上录制（连同线上转写与分享链接，不可恢复），"
                        f"本地备份保留。确认请输入数字 {n}（其他任意输入取消）: ")
        if answer.strip() != str(n):
            print("[清理模式] 未确认，已取消。")
            return 0

    print(f"\n[清理模式] 开始删除 {n} 条线上录制…")
    ok_count = 0
    fail_count = 0
    consecutive_failures = 0
    freed_bytes = 0
    for idx, d in enumerate(deletable, start=1):
        try:
            resp = client.delete_record([d["uni_record_id"]])
            ok = resp.get("code") == 0
            detail = json.dumps(resp, ensure_ascii=False)[:200]
        except Exception as e:
            ok = False
            detail = str(e)[:200]
            resp = {}

        log_record = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "identifier": d["identifier"],
            "topic": d["topic"],
            "uni_record_id": d["uni_record_id"],
            "ok": ok,
            "resp": detail,
            "cloud_bytes": d["cloud_bytes"],
        }
        _append_deletion_log(output_dir, log_record)

        if ok:
            ok_count += 1
            freed_bytes += d["cloud_bytes"]
            consecutive_failures = 0
            idents = [d["identifier"]] + list(d.get("sub_identifiers") or [])
            _mark_deleted(state, idents, d["topic"])
            save_state(output_dir, state)
            print(f"  [{idx}/{n}] ✅ 已删除: {d['topic']}")
        else:
            fail_count += 1
            consecutive_failures += 1
            print(f"  [{idx}/{n}] ❌ 删除失败: {d['topic']} ({detail})")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(f"\n[清理模式] 连续 {MAX_CONSECUTIVE_FAILURES} 次删除失败，"
                      f"已熔断停止（剩余 {n - idx} 条未删）。请检查 Cookie 是否过期。")
                break

        if idx < n:
            time.sleep(DELETE_INTERVAL_SECONDS)

    print("\n" + "=" * 60)
    print(f"🧹 清理完成：成功 {ok_count} 条，失败 {fail_count} 条，"
          f"预计释放线上空间 {human_size(freed_bytes)}。")
    print(f"删除日志: {os.path.join(output_dir, DELETION_LOG_FILENAME)}")
    print("=" * 60)
    return 0
