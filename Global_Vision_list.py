#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import time
from datetime import datetime

# ========= 台湾直播频道（已整合你的全部） =========
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

# ========= 控制参数 =========
BATCH_SIZE = 4          # 每批频道数量
SLEEP_EACH = 6          # 每个频道间隔
SLEEP_BATCH = 15        # 每批冷却


# ========= 轻检测 =========
def is_live_fast(url):
    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "--skip-download",
        "--print", "is_live",
        url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return "True" in result.stdout
    except:
        return False


# ========= 重抓取 =========
def fetch_detail(url):
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-playlist",
        "--socket-timeout", "10",
        "--retries", "1",
        url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except:
        return None


# ========= 主逻辑 =========
def main():
    output = {
        "直播": {
            "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "所有直播": []
        }
    }

    total = 0

    for i, ch in enumerate(CHANNELS):
        print(f"\n🔍 检测: {ch['name']}")

        # ===== ① 轻检测 =====
        if not is_live_fast(ch["url"]):
            print("⚠️ 未直播")
            time.sleep(SLEEP_EACH)
            continue

        print("📡 直播中，获取详情...")

        # ===== ② 重抓取 =====
        data = fetch_detail(ch["url"])

        if not data:
            print("❌ 获取失败")
            time.sleep(SLEEP_EACH)
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

        time.sleep(SLEEP_EACH)

        # ===== 分批冷却 =====
        if (i + 1) % BATCH_SIZE == 0:
            print("\n⏸ 分批冷却...\n")
            time.sleep(SLEEP_BATCH)

    # ========= 防空写入 =========
    if total == 0:
        print("⚠️ 没有抓到直播，跳过写入")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 完成，共 {total} 个直播")


if __name__ == "__main__":
    main()
