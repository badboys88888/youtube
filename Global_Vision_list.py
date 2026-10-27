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

def ytdlp_print_id(url, timeout=25):
    """
    用 yt-dlp 直接输出视频 id。
    成功返回 id 字符串，失败/无直播返回 None。
    """
    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "--print", "%(id)s",
        url
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        vid = (r.stdout or "").strip()
        # yt-dlp 有时会输出多行（例如 playlist），只取第一行有效 id
        if vid:
            vid = vid.splitlines()[0].strip()
        return vid if vid else None
    except Exception:
        return None


def is_channel_home(url):
    """
    判断是否为频道主页类链接（可自动补 /live）
    """
    markers = ["/@", "/channel/", "/c/", "/user/"]
    return any(m in url for m in markers)


def get_video_id(url):
    """
    获取 video id，兼容：
    - 普通视频 watch?v=
    - 频道主页 /@xxx、/channel/UCxxx、/c/xxx、/user/xxx（自动补 /live）
    - 频道 /live 页面
    - 已带 /live 或 /streams 的频道链接
    """

    # 1) 普通视频
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]

    # 2) 频道主页类链接
    if is_channel_home(url):
        # 已经是 /live 或 /streams 就直接用；否则补 /live
        if url.rstrip("/").endswith("/live") or url.rstrip("/").endswith("/streams"):
            live_url = url
        else:
            live_url = url.rstrip("/") + "/live"

        vid = ytdlp_print_id(live_url)
        if vid:
            return vid

        # /live 没取到，再尝试 /streams 取最近一条（可选兜底）
        if not live_url.rstrip("/").endswith("/streams"):
            streams_url = live_url.rstrip("/")[:-len("/live")] + "/streams"
            vid = ytdlp_print_id(streams_url)
            if vid:
                return vid
        return None

    # 3) 其他 /live 链接（非频道主页形式，比如直接直播间地址）
    if "/live" in url:
        return ytdlp_print_id(url)

    return None


# ===================== 主流程 ===================== #

def run():
    CHANNELS = load_channels()
    output = []

    if not CHANNELS:
        print("⚠️ 没有加载到频道数据")
        return

    for ch in CHANNELS:
        print(f"🔍 检测: {ch.get('name', 'unknown')}")

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
