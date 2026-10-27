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

def ytdlp_print_ids(url, timeout=30):
    """
    用 yt-dlp 输出所有匹配条目的 id，每行一个。
    返回 id 列表，失败返回空列表。
    """
    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "--print", "%(id)s",
        "--match-filter", "live_status = is_live",
        url
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        lines = (r.stdout or "").strip().splitlines()
        return [l.strip() for l in lines if l.strip()]
    except Exception:
        return []


def is_channel_home(url):
    markers = ["/@", "/channel/", "/c/", "/user/"]
    return any(m in url for m in markers)


def get_video_ids(url):
    """
    返回该频道/链接下所有正在直播的 video id 列表。
    """
    # 普通视频：直接返回单个
    if "v=" in url:
        vid = url.split("v=")[1].split("&")[0]
        return [vid] if vid else []

    # 频道主页：走 /streams + live_status 过滤
    if is_channel_home(url):
        base = url.rstrip("/")
        if base.endswith("/streams"):
            streams_url = base
        elif base.endswith("/live"):
            # 如果用户写了 /live，改成 /streams 才能拿多个
            streams_url = base[:-len("/live")] + "/streams"
        else:
            streams_url = base + "/streams"
        return ytdlp_print_ids(streams_url)

    # 其他链接兜底
    return ytdlp_print_ids(url)


# ===================== 主流程 ===================== #

def run():
    CHANNELS = load_channels()
    output = []

    if not CHANNELS:
        print("⚠️ 没有加载到频道数据")
        return

    for ch in CHANNELS:
        name = ch.get("name", "unknown")
        print(f"🔍 检测: {name}")

        url = ch.get("url")
        if not url:
            continue

        vids = get_video_ids(url)

        if not vids:
            print("⚠️ 未直播 / 无效")
            time.sleep(1.5)
            continue

        for vid in vids:
            output.append({
                "name": name,
                "group": ch.get("group", "LIVE"),
                "id": vid,
                "url": f"https://www.youtube.com/watch?v={vid}"
            })
            print(f"✅ 成功: {vid}")

        time.sleep(1.5)

    result = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(output),
        "data": output
    }

    with open("Global_Vision_list.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\n🎉 JSON生成完成")


if __name__ == "__main__":
    run()
