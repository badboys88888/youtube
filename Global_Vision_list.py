#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import time
import os
import re
from urllib.parse import quote
from datetime import datetime

# ===================== 配置 ===================== #
RAW_BASE = "https://raw.githubusercontent.com/badboys88888/youtube/main/icons/"
ICONS_DIR = "icons"

def load_channels():
    try:
        with open("channels.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ channels.json 读取失败: {e}")
        return []

def list_icon_files():
    if not os.path.isdir(ICONS_DIR):
        print(f"⚠️ 未找到 {ICONS_DIR}/ 目录")
        return []
    exts = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")
    return [f for f in os.listdir(ICONS_DIR) if f.lower().endswith(exts)]

def norm_text(s):
    s = s.lower()
    s = re.sub(r"[_\-\s]+", "", s)
    for w in ["logo", "icon", "台标", "图标"]:
        s = s.replace(w, "")
    return s

def match_icon_by_name(name, icon_files):
    if not name:
        return None
    n = norm_text(name)
    if not n:
        return None
    for f in icon_files:
        if norm_text(os.path.splitext(f)[0]) == n:
            return f
    for f in icon_files:
        base = norm_text(os.path.splitext(f)[0])
        if n in base or (base and base in n):
            return f
    return None

def resolve_logo(ch, icon_files, web_thumbnail):
    """
    Logo 优先级：
    1. icons/ 里匹配到的图
    2. channels.json 里指定的 icon 或 logo
    3. 网页抓取的真实缩略图
    """
    # 1. 优先匹配本地 icons 文件夹
    matched = match_icon_by_name(ch.get("name", ""), icon_files)
    if matched:
        return RAW_BASE + quote(matched)

    # 2. 检查 channels.json 是否手动指定
    icon_file = (ch.get("icon") or "").strip()
    if icon_file:
        return RAW_BASE + quote(icon_file)
    preset_logo = (ch.get("logo") or "").strip()
    if preset_logo:
        return preset_logo

    # 3. 用网页缩略图兜底
    return web_thumbnail or ""

# ===================== 核心抓取逻辑 ===================== #

def get_video_real_metadata(vid):
    """
    针对具体的视频 ID 发起请求，抓取真实的网页标题和缩略图
    """
    url = f"https://www.youtube.com/watch?v={vid}"
    cmd = [
        "yt-dlp", "--quiet", "--no-warnings",
        "--print", "%(title)s",
        "--print", "%(thumbnail)s",
        "--no-check-certificates", url
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        lines = (r.stdout or "").strip().splitlines()
        if len(lines) >= 2:
            return lines[0].strip(), lines[1].strip()
    except Exception:
        pass
    return "", f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

def get_live_items_from_streams(streams_url, timeout=60):
    """
    第一步：拉取前 10 条，快速找出哪些是直播 ID
    """
    cmd = [
        "yt-dlp", "--quiet", "--no-warnings", "--dump-json",
        "--flat-playlist", "--playlist-end", "10",
        "--no-check-certificates", streams_url
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

            vid = info.get("id") or ""
            if info.get("live_status") == "is_live" and len(vid) >= 10:
                live_ids.append(vid)
        return live_ids
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return []

def is_channel_home(url):
    return any(m in url for m in ["/@", "/channel/", "/c/", "/user/"])

def get_live_ids(url):
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
        return get_live_items_from_streams(streams_url)

    return get_live_items_from_streams(url)

# ===================== 主流程 ===================== #

def run():
    CHANNELS = load_channels()
    output = []
    if not CHANNELS:
        return

    icon_files = list_icon_files()

    total = len(CHANNELS)
    for idx, ch in enumerate(CHANNELS, 1):
        name = ch.get("name", "unknown")
        print(f"🔍 [{idx}/{total}] 检测: {name}")

        url = ch.get("url")
        if not url:
            continue

        try:
            vids = get_live_ids(url)
        except Exception:
            vids = []

        if not vids:
            print("   ⚠️ 未直播 / 无效")
            time.sleep(1.5)
            continue

        for vid in vids:
            # 关键点：拿到直播 ID 后，单独请求一次去抓真实页面信息
            print(f"   🔄 获取详情: {vid} ...")
            real_title, web_thumbnail = get_video_real_metadata(vid)
            
            logo_url = resolve_logo(ch, icon_files, web_thumbnail)

            output.append({
                "name": name,
                "title": real_title,       # 网页真实标题
                "group": ch.get("group", "LIVE"),
                "id": vid,
                "logo": logo_url,          # 匹配的台标
                "url": f"https://www.youtube.com/watch?v={vid}"
            })
            print(f"   ✅ 成功: {vid} | 标题: {real_title[:30]}...")
            time.sleep(1) # 防止短时间内请求太密集

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
