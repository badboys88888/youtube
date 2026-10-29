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

def get_longest_live_id(streams_url, timeout=120, playlist_end=15):
    """
    拉取频道 /streams 页面，真正解析前 playlist_end 条，
    筛选 live_status == 'is_live' 的条目，
    返回时长最长的那个 video id；没有直播返回 None。
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
    print(f"   执行: {' '.join(cmd)}")

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0 and r.stderr:
            print(f"   ⚠️ yt-dlp stderr: {r.stderr.strip()[:300]}")

        live_items = []
        for line in (r.stdout or "").strip().splitlines():
            if not line.strip():
                continue
            try:
                info = json.loads(line)
            except json.JSONDecodeError:
                continue

            live_status = info.get("live_status")
            vid = info.get("id") or ""

            # 只看正在直播、且 id 像正常 YouTube video id 的条目
            if live_status != "is_live" or len(vid) < 10:
                continue

            duration = info.get("duration") or 0
            title = info.get("title", "")
            live_items.append((vid, duration, title))
            print(f"   🎥 直播: {vid} | 时长: {duration}s | {title[:50]}")

        if not live_items:
            return None

        # 选时长最长的
        live_items.sort(key=lambda x: x[1], reverse=True)
        best_vid, best_dur, best_title = live_items[0]
        print(f"   🏆 选中最长直播: {best_vid} ({best_dur}s) | {best_title[:50]}")
        return best_vid

    except subprocess.TimeoutExpired:
        print(f"   ⏱ 超时({timeout}s): {streams_url}")
        return None
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return None


def is_channel_home(url):
    markers = ["/@", "/channel/", "/c/", "/user/"]
    return any(m in url for m in markers)


def get_video_id(url):
    """
    返回该频道下时长最长的正在直播 video id，没有则 None。
    """
    # 普通视频
    if "v=" in url:
        vid = url.split("v=")[1].split("&")[0]
        return vid if vid else None

    # 频道主页：统一走 /streams
    if is_channel_home(url):
        base = url.rstrip("/")
        if base.endswith("/streams"):
            streams_url = base
        elif base.endswith("/live"):
            streams_url = base[:-len("/live")] + "/streams"
        else:
            streams_url = base + "/streams"
        return get_longest_live_id(streams_url)

    # 其他链接兜底
    return get_longest_live_id(url)


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
            vid = get_video_id(url)
        except Exception as e:
            print(f"   ❌ 处理异常: {e}")
            vid = None

        if not vid:
            print("   ⚠️ 未直播 / 无效")
            time.sleep(1.5)
            continue

        output.append({
            "name": name,
            "group": ch.get("group", "LIVE"),
            "id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}"
        })
        print(f"   ✅ 成功: {vid}")

        time.sleep(1.5)

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
