#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import time

# ========= 台湾直播频道 =========
CHANNELS = [
    {"name": "凤凰卫视资讯台", "url": "https://www.youtube.com/watch?v=fN9uYWCjQaw"},
    {"name": "中天新闻台", "url": "https://www.youtube.com/watch?v=vr3XyVCR4T0"},
    {"name": "寰宇新闻台", "url": "https://www.youtube.com/watch?v=6IquAgfvYmc"},
    {"name": "寰宇台湾新闻台", "url": "https://www.youtube.com/watch?v=w87VGpgd90U"},
    {"name": "TVBS新闻", "url": "https://www.youtube.com/@TVBSNEWS02/live"},
    {"name": "TVBS NEWS", "url": "https://www.youtube.com/@TVBSNEWS01/live"},
    {"name": "东森新闻", "url": "https://www.youtube.com/@newsebc/live"},
    {"name": "东森新闻二台", "url": "https://www.youtube.com/watch?v=cimbpAZUjzw"},
    {"name": "东森财经", "url": "https://www.youtube.com/@57ETFN/live"},
    {"name": "三立新闻", "url": "https://www.youtube.com/@setnews/live"},
    {"name": "三立iNEWS", "url": "https://www.youtube.com/@三立iNEWS/live"},
    {"name": "民视新闻", "url": "https://www.youtube.com/@FTV_News/live"},
    {"name": "台视新闻", "url": "https://www.youtube.com/@TTV_NEWS/live"},
    {"name": "华视新闻", "url": "https://www.youtube.com/@CtsTw/live"},
    {"name": "镜新闻", "url": "https://www.youtube.com/@mnews-tw/live"},
    {"name": "中视新闻", "url": "https://www.youtube.com/@twctvnews/live"},
    {"name": "非凡新闻", "url": "https://www.youtube.com/@ustv/live"},
    {"name": "运通财经台", "url": "https://www.youtube.com/@EFTV01/live"},
    {"name": "大爱一台", "url": "https://www.youtube.com/watch?v=pM-1ytfQhos"},
    {"name": "大爱二台", "url": "https://www.youtube.com/watch?v=QDxRJP-wfeI"},
]

OUTPUT_FILE = "output/Global_Vision_list.json"


# ========= 抓取函数 =========
def fetch_live(url):
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-playlist",

        "--user-agent",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)",

        "--socket-timeout", "10",
        "--retries", "1",

        url
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=40
        )

        if result.returncode != 0:
            print("❌ yt-dlp错误")
            return None

        return json.loads(result.stdout)

    except subprocess.TimeoutExpired:
        print("⏱ 超时")
        return None
    except Exception as e:
        print("❌ 异常:", e)
        return None


# ========= 判断是否直播 =========
def is_live(data):
    if not data:
        return False

    return (
        data.get("is_live") is True or
        data.get("live_status") in ["is_live", "live"]
    )


# ========= 主逻辑 =========
def main():
    output = {
        "直播": {
            "所有直播": []
        }
    }

    total = 0

    for ch in CHANNELS:
        print("🔍 抓取:", ch["name"])

        data = fetch_live(ch["url"])

        if not data:
            continue

        if not is_live(data):
            print("⚠️ 当前未直播")
            continue

        vid = data.get("id")
        if not vid:
            continue

        output["直播"]["所有直播"].append({
            "group": ch["name"],
            "title": data.get("title", "LIVE"),
            "id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}"
        })

        print("✅ 成功:", ch["name"])
        total += 1

        time.sleep(2)  # 防封（关键）

    # ========= 防空保护 =========
    if total == 0:
        print("⚠️ 没抓到任何直播，跳过写入（防止清空）")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 完成，共 {total} 个直播")


# ========= 入口 =========
if __name__ == "__main__":
    main()
