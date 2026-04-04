#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import time
from datetime import datetime

# ===================== 频道列表 ===================== #

# 🟢 1. 固定 v= 视频（直接可用）
CHANNELS = [
    {"name": "凤凰卫视资讯台", "url": "https://www.youtube.com/watch?v=fN9uYWCjQaw"},
    {"name": "中天新闻台", "url": "https://www.youtube.com/watch?v=vr3XyVCR4T0"},
    {"name": "寰宇新闻台", "url": "https://www.youtube.com/watch?v=6IquAgfvYmc"},
    {"name": "寰宇台湾新闻台", "url": "https://www.youtube.com/watch?v=w87VGpgd90U"},
    {"name": "TVBS新闻", "url": "https://www.youtube.com/watch?v=c1mB7aExample"},
    
    # 🔵 直播频道（/live）
    {"name": "TVBS NEWS", "url": "https://www.youtube.com/@TVBSNEWS02/live"},
    {"name": "东森财经", "url": "https://www.youtube.com/@57ETFN/live"},
    {"name": "东森新闻", "url": "https://www.youtube.com/@newsebc/live"},
    {"name": "三立新闻", "url": "https://www.youtube.com/@setnews/live"},
    {"name": "民视新闻", "url": "https://www.youtube.com/@FTV_News/live"},
]

# ===================== 工具函数 ===================== #

def get_video_id(url):
    """
    统一提取 video id：
    1. v= 直接解析
    2. /live 用 yt-dlp 获取
    """

    # 🟢 v= 直接处理
    if "v=" in url:
        try:
            return url.split("v=")[1].split("&")[0]
        except:
            return None

    # 🔵 live 用 yt-dlp
    if "/live" in url:
        cmd = [
            "yt-dlp",
            "--quiet",
            "--no-warnings",
            "--print", "%(id)s",
            url
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            vid = result.stdout.strip()
            return vid if vid else None
        except:
            return None

    return None


# ===================== 主处理 ===================== #

def run():
    output = []

    for ch in CHANNELS:
        print(f"🔍 检测: {ch['name']}")

        vid = get_video_id(ch["url"])

        if not vid:
            print("⚠️ 未直播 / 无效")
            continue

        item = {
            "name": ch["name"],
            "id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}"
        }

        output.append(item)

        print("✅ 成功")

        # 模拟人类行为（防止太快）
        time.sleep(1.5)

    result = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(output),
        "data": output
    }

    # 输出 JSON 文件
    with open("live_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\n🎉 完成，已生成 live_result.json")


# ===================== 运行 ===================== #

if __name__ == "__main__":
    run()
