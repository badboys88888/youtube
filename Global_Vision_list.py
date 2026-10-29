#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import time
from datetime import datetime

# ===================== 频道加载 ===================== #

def load_channels():
    try:
        with open("channels.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ channels.json 读取失败: {e}")
        return []


# ===================== 工具函数 ===================== #

def _run_ytdlp(cmd, timeout=120):
    """
    执行 yt-dlp，返回 (ids, stderr_text)。
    即使 returncode != 0，只要 stdout 里有有效条目也返回。
    """
    print(f"   执行: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        stderr = (r.stderr or "")
        if r.returncode != 0 and stderr:
            print(f"   ⚠️ yt-dlp stderr: {stderr.strip()[:300]}")

        ids = []
        for line in (r.stdout or "").strip().splitlines():
            if not line.strip():
                continue
            try:
                info = json.loads(line)
            except json.JSONDecodeError:
                continue
            vid = info.get("id") or ""
            if info.get("live_status") == "is_live" and len(vid) >= 10:
                ids.append(vid)
                print(f"   🎥 直播: {vid} | {info.get('title', '')[:60]}")
        return ids, stderr
    except subprocess.TimeoutExpired:
        print(f"   ⏱ 超时({timeout}s)")
        return [], "timeout"
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return [], str(e)


def get_live_ids_from_streams(streams_url, timeout=120, playlist_end=15):
    """
    解析 /streams 前 playlist_end 条，筛选 is_live。
    命中风控或空结果时重试一次。
    """
    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "--dump-json",
        "--playlist-end", str(playlist_end),
        "--no-check-certificates",
        streams_url
    ]

    ids, stderr = _run_ytdlp(cmd, timeout)
    if ids:
        return ids

    # 空结果：如果是风控或超时，重试一次
    if ("Sign in to confirm" in stderr) or ("not a bot" in stderr) or (stderr == "timeout"):
        print("   🔁 空结果/风控，3 秒后重试一次")
        time.sleep(3)
        ids, stderr = _run_ytdlp(cmd, timeout)
        if ids:
            return ids

    return []


def get_live_id_from_live_page(live_url, timeout=60):
    """
    兜底：直接解析 /live 页面，拿单个当前直播 id。
    """
    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "--print", "%(id)s",
        "--no-check-certificates",
        live_url
    ]
    print(f"   兜底执行: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        vid = (r.stdout or "").strip().splitlines()
        vid = vid[0].strip() if vid else ""
        if vid and len(vid) >= 10:
            print(f"   🎥 兜底直播: {vid}")
            return [vid]
        if r.stderr:
            print(f"   ⚠️ 兜底 stderr: {r.stderr.strip()[:200]}")
    except Exception as e:
        print(f"   ❌ 兜底错误: {e}")
    return []


def is_channel_home(url):
    markers = ["/@", "/channel/", "/c/", "/user/"]
    return any(m in url for m in markers)


def get_video_ids(url):
    """
    返回该频道下所有正在直播的 video id 列表。
    /streams 优先，拿不到再兜底 /live。
    """
    if "v=" in url:
        vid = url.split("v=")[1].split("&")[0]
        return [vid] if vid else []

    if is_channel_home(url):
        base = url.rstrip("/")
        if base.endswith("/streams"):
            streams_url = base
            live_url = base[:-len("/streams")] + "/live"
        elif base.endswith("/live"):
            live_url = base
            streams_url = base[:-len("/live")] + "/streams"
        else:
            streams_url = base + "/streams"
            live_url = base + "/live"

        ids = get_live_ids_from_streams(streams_url)
        if ids:
            return ids

        # /streams 没拿到，兜底 /live
        print("   🔄 /streams 未拿到，尝试 /live 兜底")
        return get_live_id_from_live_page(live_url)

    return get_live_ids_from_streams(url)


# ===================== 主流程 ===================== #

def run():
    CHANNELS = load_channels()
    output = []

    if not CHANNELS:
        print("⚠️ 没有加载到频道数据")
        return

    total = len(CHANNELS)
    for idx, ch in enumerate(CHANNELS, 1):
        name = ch.get("name", "unknown")
        print(f"🔍 [{idx}/{total}] 检测: {name}")

        url = ch.get("url")
        if not url:
            print("   ⚠️ 缺少 url，跳过")
            continue

        try:
            vids = get_video_ids(url)
        except Exception as e:
            print(f"   ❌ 处理异常: {e}")
            vids = []

        if not vids:
            print("   ⚠️ 未直播 / 无效")
            time.sleep(3)
            continue

        for vid in vids:
            output.append({
                "name": name,
                "group": ch.get("group", "LIVE"),
                "id": vid,
                "url": f"https://www.youtube.com/watch?v={vid}"
            })
            print(f"   ✅ 成功: {vid}")

        time.sleep(3)

    result = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(output),
        "data": output
    }

    with open("Global_Vision_list.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 JSON生成完成，共 {len(output)} 条直播")


if __name__ == "__main__":
    run()
