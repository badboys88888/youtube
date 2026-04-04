#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import time
from datetime import datetime

# ===================== 频道 ===================== #

CHANNELS = [
    {"name": "凤凰卫视资讯台", "url": "https://www.youtube.com/watch?v=fN9uYWCjQaw"},
    {"name": "中天新闻台", "url": "https://www.youtube.com/watch?v=vr3XyVCR4T0"},
    {"name": "寰宇新闻台", "url": "https://www.youtube.com/watch?v=6IquAgfvYmc"},
    {"name": "寰宇台湾新闻台", "url": "https://www.youtube.com/watch?v=w87VGpgd90U"},

    {"name": "TVBS NEWS", "url": "https://www.youtube.com/@TVBSNEWS02/live"},
    {"name": "东森财经", "url": "https://www.youtube.com/@57ETFN/live"},
    {"name": "东森新闻", "url": "https://www.youtube.com/@newsebc/live"},
    {"name": "三立新闻", "url": "https://www.youtube.com/@setnews/live"},
    {"name": "民视新闻", "url": "https://www.youtube.com/@FTV_News/live"},
]

# ===================== 工具 ===================== #

def is_live_video(url):
    """
    判断是否正在直播（工业核心）
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
    获取 video id（稳定版）
    """

    # 1️⃣ v= 视频
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]

    # 2️⃣ live 频道
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
    output = []

    for ch in CHANNELS:
        print(f"🔍 检测: {ch['name']}")

        vid = get_video_id(ch["url"])

        if not vid:
            print("⚠️ 未直播 / 无效")
            continue

        output.append({
            "name": ch["name"],
            "id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}"
        })

        print("✅ 成功")

        # 👇 防封 + 模拟人类行为
        time.sleep(1.8)

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
