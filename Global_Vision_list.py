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

def get_live_ids_from_streams(streams_url, timeout=60):
    """
    拉取频道 /streams 页面，筛选 live_status == 'is_live' 的条目。
    返回 video id 列表。
    """
    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "--dump-json",
        "--flat-playlist",
        "--no-check-certificates",
        streams_url
    ]
    print(f"   执行: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0 and r.stderr:
            print(f"   ⚠️ yt-dlp stderr: {r.stderr.strip()[:300]}")

        live_ids = []
        for line in (r.stdout or "").strip().splitlines():
            if not line.strip():
                continue
            try:
                info = json.loads(line)
            except json.JSONDecodeError:
                continue

            live_status = info.get("live_status")
            vid = info.get("id") or ""

            # 只保留正在直播、且 id 像正常 YouTube video id
            if live_status == "is_live" and len(vid) >= 10:
                live_ids.append(vid)
                print(f"   🎥 直播: {vid} | {info.get('title', '')[:60]}")
        return live_ids
    except subprocess.TimeoutExpired:
        print(f"   ⏱ 超时({timeout}s): {streams_url}")
        return []
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return []


def is_channel_home(url):
    markers = ["/@", "/channel/", "/c/", "/user/"]
    return any(m in url for m in markers)


def get_video_ids(url):
    """
    返回该频道下所有正在直播的 video id 列表。
    """
    if "v=" in url:
        vid = url.split("v=")[1].split("&")[0]
        return [vid] if vid else []

    if is_channel_home(url):
        base = url.rstrip("/")
        if base.endswith("/streams"):
            streams_url = base
        elif base.endswith("/live"):
            streams_url = base[:-len("/live")] + "/streams"
        else:
            streams_url = base + "/streams"
        return get_live_ids_from_streams(streams_url)

    return get_live_ids_from_streams(url)


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
            vids = get_video_ids(url)
        except Exception as e:
            print(f"   ❌ 处理异常: {e}")
            vids = []

        if not vids:
            print("   ⚠️ 未直播 / 无效")
            time.sleep(1.5)
            continue

        for vid in vids:
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
