#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess

# ========= 配置 =========
CHANNELS = [
    {"name": "凤凰卫视资讯台", "url": "https://www.youtube.com/@phoenixtvglobal/streams"},
    {"name": "CCTV4", "url": "https://www.youtube.com/@LiveNow24H/streams"},
    {"name": "中天新闻", "url": "https://www.youtube.com/@中天電視CtiTv/streams"},
    {"name": "寰宇新聞", "url": "https://www.youtube.com/@globalnewstw/streams"},
    {"name": "东森新闻", "url": "https://www.youtube.com/@newsebc/streams"},
    {"name": "民视新闻", "url": "https://www.youtube.com/@FTV_News/streams"},
    {"name": "TVBS新闻", "url": "https://www.youtube.com/@TVBSNEWS02/streams"},
    {"name": "非凡新闻", "url": "https://www.youtube.com/@ustv/streams"},
    {"name": "三立新闻", "url": "https://www.youtube.com/@setnews/streams"},
    {"name": "BBC News", "url": "https://www.youtube.com/@BBCNews/streams"},
    {"name": "NBC News", "url": "https://www.youtube.com/@nbcnews/streams"},
]

OUTPUT_FILE = "Global_Vision_list.json"


# ========= 抓取 =========
def fetch_channel(url):
    cmd = [
        "yt-dlp",
        "-J",
        "--no-check-certificate",
        "--user-agent",
        "Mozilla/5.0",
        url
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=90
        )

        if result.returncode != 0:
            print("yt-dlp error:", result.stderr)
            return None

        return json.loads(result.stdout)

    except Exception as e:
        print("error:", e)
        return None


# ========= 判断是否直播 =========
def is_live_item(item):
    if not item:
        return False

    status = item.get("live_status", "")
    if status in ["is_live", "live", "LIVE"]:
        return True

    # fallback
    if item.get("is_live") is True:
        return True

    return False


# ========= 主逻辑 =========
def build_json():
    output = {
        "直播": {
            "所有直播": []
        }
    }

    total = 0

    for ch in CHANNELS:
        print("正在抓取:", ch["name"])

        raw = fetch_channel(ch["url"])
        if not raw:
            continue

        entries = raw.get("entries", [])
        if not entries:
            continue

        for item in entries:
            if not is_live_item(item):
                continue

            video_id = item.get("id")
            if not video_id:
                continue

            output["直播"]["所有直播"].append({
                "group": ch["name"],
                "title": item.get("title", "NO_TITLE"),
                "id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}"
            })

            total += 1

    # 防止空 JSON
    if total == 0:
        output["直播"]["所有直播"].append({
            "group": "SYSTEM",
            "title": "NO LIVE FOUND",
            "id": "",
            "url": ""
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("完成：直播数量 =", total)


if __name__ == "__main__":
    build_json()
