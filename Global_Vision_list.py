#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import time
import random

# ========= 你的完整频道 =========
CHANNELS = [
    {"name": "凤凰卫视资讯台", "url": "https://www.youtube.com/@phoenixtvglobal/streams"},
    {"name": "CCTV4", "url": "https://www.youtube.com/@LiveNow24H/streams"},
    {"name": "中天新闻", "url": "https://www.youtube.com/@中天電視CtiTv/streams"},
    {"name": "寰宇新聞", "url": "https://www.youtube.com/@globalnewstw/streams"},
    {"name": "東森綜合台", "url": "https://www.youtube.com/@ettv32/streams"},
    {"name": "东森新闻", "url": "https://www.youtube.com/@newsebc/streams"},
    {"name": "民视新闻", "url": "https://www.youtube.com/@FTV_News/streams"},
    {"name": "华视新闻", "url": "https://www.youtube.com/@CtsTw/streams"},
    {"name": "TVBS新闻", "url": "https://www.youtube.com/@TVBSNEWS02/streams"},
    {"name": "非凡新闻", "url": "https://www.youtube.com/@ustv/streams"},
    {"name": "TVBS NEWS", "url": "https://www.youtube.com/@TVBSNEWS01/streams"},
    {"name": "东森财经新闻", "url": "https://www.youtube.com/@57ETFN/streams"},
    {"name": "三立新闻", "url": "https://www.youtube.com/@setnews/streams"},
    {"name": "台视新闻", "url": "https://www.youtube.com/@TTV_NEWS/streams"},
    {"name": "三立iNEWS", "url": "https://www.youtube.com/@三立iNEWS/streams"},
    {"name": "镜新闻", "url": "https://www.youtube.com/@mnews-tw/streams"},
    {"name": "中视新闻", "url": "https://www.youtube.com/@twctvnews/streams"},
    {"name": "運通財經台", "url": "https://www.youtube.com/@EFTV01/streams"},
    {"name": "三大一台", "url": "https://www.youtube.com/@SDTV55ch/streams"},
    {"name": "大爱电视", "url": "https://www.youtube.com/@DaAiVideo/streams"},
    {"name": "新唐人電視台", "url": "https://www.youtube.com/@NTDAPTV/streams"},
    {"name": "澳廣視", "url": "https://www.youtube.com/@TDM_MACAU/streams"},
    {"name": "NBC News", "url": "https://www.youtube.com/@nbcnews/streams"},
    {"name": "BBC News", "url": "https://www.youtube.com/@BBCNews/streams"},
    {"name": "CNA", "url": "https://www.youtube.com/@channelnewsasia/streams"},
    {"name": "Al Jazeera", "url": "https://www.youtube.com/@aljazeeraenglish/streams"},
]

OUTPUT_FILE = "output/Global_Vision_list.json"

# ========= UA池 =========
UA_LIST = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 Chrome/90.0 Mobile",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0"
]


# ========= 抓取 =========
def fetch(url):
    ua = random.choice(UA_LIST)

    cmd = [
        "yt-dlp",
        "-J",
        "--user-agent", ua,
        "--add-header", "Accept-Language:zh-CN,zh;q=0.9",
        "--add-header", "Referer:https://www.youtube.com/",
        "--add-header", "X-YouTube-Client-Name: 2",
        "--add-header", "X-YouTube-Client-Version: 19.09.3",
        "--no-check-certificate",
        "--socket-timeout", "20",
        "--retries", "2",
        url
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            print("yt-dlp error:", result.stderr)
            return None

        return json.loads(result.stdout)

    except Exception as e:
        print("error:", e)
        return None


# ========= 判断直播 =========
def is_live(item):
    if not item:
        return False

    status = item.get("live_status", "")
    if status in ["is_live", "live", "LIVE"]:
        return True

    if item.get("is_live") is True:
        return True

    return False


# ========= 主逻辑 =========
def main():
    output = {"直播": {"所有直播": []}}
    total = 0

    batch_size = 5  # 每批5个频道（防封关键）

    for i in range(0, len(CHANNELS), batch_size):
        batch = CHANNELS[i:i + batch_size]

        print(f"\n=== 批次 {i//batch_size + 1} ===")

        for ch in batch:
            print("抓取:", ch["name"])

            raw = fetch(ch["url"])
            if not raw:
                continue

            for item in raw.get("entries", []):
                if not is_live(item):
                    continue

                vid = item.get("id")
                if not vid:
                    continue

                output["直播"]["所有直播"].append({
                    "group": ch["name"],
                    "title": item.get("title", "NO_TITLE"),
                    "id": vid,
                    "url": f"https://www.youtube.com/watch?v={vid}"
                })

                total += 1

            # 每频道延迟
            time.sleep(random.uniform(2, 5))

        # 每批延迟
        print("批次休息...")
        time.sleep(random.uniform(5, 10))

    # 防止空
    if total == 0:
        output["直播"]["所有直播"].append({
            "group": "SYSTEM",
            "title": "NO LIVE FOUND",
            "id": "",
            "url": ""
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n完成，直播数量:", total)


if __name__ == "__main__":
    main()
