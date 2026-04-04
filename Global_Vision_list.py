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

def is_live_video(url):
    """
    判断是否正在直播
    """
    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "--print", "is_live",
        url
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return "True" in r.stdout
    except:
        return False


def get_video_id(url):
    """
    获取 video id（兼容 watch + live）
    """

    # 普通视频
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]

    # 直播频道
    if "/live" in url:

        if not is_live_video(url):
            return None

        cmd = [
            "yt-dlp",
            "--quiet",
            "--no-warnings",
            "--print", "%(id)s",
            url
        ]

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            vid = r.stdout.strip()
            return vid if vid else None
        except:
            return None

    return None


# ===================== 主流程 ===================== #

def run():
    CHANNELS = load_channels()
    output = []

    if not CHANNELS:
        print("⚠️ 没有加载到频道数据")
        return

    for ch in CHANNELS:
        print(f"🔍 检测: {ch.get('name','unknown')}")

        url = ch.get("url")
        if not url:
            continue

        vid = get_video_id(url)

        if not vid:
            print("⚠️ 未直播 / 无效")
            continue

        output.append({
            "name": ch.get("name"),
            "group": ch.get("group", "LIVE"),
            "id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}"
        })

        print("✅ 成功")

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
