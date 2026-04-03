#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess

# ========= 配置 =========
CHANNEL_URL = "https://www.youtube.com/@nbcnews/streams"
OUTPUT_FILE = "Global_Vision_list.json"

# ========= 抓取 =========
def fetch_data():
    cmd = [
        "yt-dlp",
        "-J",
        "--flat-playlist",
        CHANNEL_URL
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=90
        )

        if result.returncode != 0:
            print("yt-dlp错误:", result.stderr)
            return None

        return json.loads(result.stdout)

    except Exception as e:
        print("异常:", e)
        return None


# ========= 处理 =========
def build_json():
    raw = fetch_data()

    if not raw:
        print("没有获取到数据")
        return

    entries = raw.get("entries", []) or []

    output = {
        "直播": {
            "所有直播": []
        }
    }

    count = 0

    for item in entries:
        if not item:
            continue

        # 兼容字段（yt-dlp在不同环境可能不同）
        is_live = item.get("is_live") or item.get("live_status") == "is_live"

        if is_live:
            output["直播"]["所有直播"].append({
                "title": item.get("title"),
                "id": item.get("id"),
                "url": item.get("url") or item.get("webpage_url")
            })
            count += 1

    # 防止完全空（避免 JSON 变空结构）
    if count == 0:
        output["直播"]["所有直播"].append({
            "title": "NO LIVE FOUND",
            "id": "",
            "url": ""
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"完成，直播数量: {count}")


# ========= 入口 =========
if __name__ == "__main__":
    build_json()
