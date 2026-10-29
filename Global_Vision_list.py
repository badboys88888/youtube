#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import time
import os
import re
import urllib.request
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
    if not name: return None
    n = norm_text(name)
    if not n: return None
    for f in icon_files:
        if norm_text(os.path.splitext(f)[0]) == n: return f
    for f in icon_files:
        base = norm_text(os.path.splitext(f)[0])
        if n in base or (base and base in n): return f
    return None

def resolve_logo(ch, icon_files, vid):
    """优先本地匹配 -> 指定文件 -> 网页标准缩略图"""
    matched = match_icon_by_name(ch.get("name", ""), icon_files)
    if matched:
        return RAW_BASE + quote(matched)
    
    icon_file = (ch.get("icon") or "").strip()
    if icon_file:
        return RAW_BASE + quote(icon_file)
        
    preset_logo = (ch.get("logo") or "").strip()
    if preset_logo:
        return preset_logo
        
    # 直接拼 YouTube 官方固定图床
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

# ===================== 网页爬取标题 ===================== #

def fetch_title_from_web(vid):
    """
    直接请求网页 HTML，用正则抓 <title>。完全不用 yt-dlp。
    """
    url = f"https://www.youtube.com/watch?v={vid}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8', errors='ignore')
            match = re.search(r'<title>(.*?)</title>', html)
            if match:
                title = match.group(1).strip()
                # 去掉 YouTube 后缀
                title = re.sub(r'\s*-\s*YouTube$', '', title)
                return title
    except Exception as e:
        print(f"   ⚠️ 网页标题获取失败: {e}")
    return ""

# ===================== ID 提取 ===================== #

def get_live_ids_from_streams(streams_url, timeout=60):
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
            if not line.strip(): continue
            try:
                info = json.loads(line)
            except json.JSONDecodeError: continue

            vid = info.get("id") or ""
            if info.get("live_status") == "is_live" and len(vid) >= 10:
                live_ids.append(vid)
                print(f"   🎥 直播: {vid}")
        return live_ids
    except subprocess.TimeoutExpired:
        print(f"   ⏱ 超时({timeout}s): {streams_url}")
        return []
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return []

def is_channel_home(url):
    return any(m in url for m in ["/@", "/channel/", "/c/", "/user/"])

def get_video_ids(url):
    if "v=" in url:
        vid = url.split("v=")[1].split("&")[0]
        return [vid] if vid else []

    if is_channel_home(url):
        base = url.rstrip("/")
        if base.endswith("/streams"): streams_url = base
        elif base.endswith("/live"): streams_url = base[:-len("/live")] + "/streams"
        else: streams_url = base + "/streams"
        return get_live_ids_from_streams(streams_url)

    return get_live_ids_from_streams(url)

# ===================== 主流程 ===================== #

def run():
    CHANNELS = load_channels()
    output = []
    if not CHANNELS: return

    icon_files = list_icon_files()
    total = len(CHANNELS)

    for idx, ch in enumerate(CHANNELS, 1):
        name = ch.get("name", "unknown")
        print(f"🔍 [{idx}/{total}] 检测: {name}")

        url = ch.get("url")
        if not url: continue

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
            print(f"   🔄 获取详情: {vid} ...")
            
            # 用 Python 原生爬 HTML 获取真实网页标题
            real_title = fetch_title_from_web(vid)
            if not real_title:
                real_title = name
                
            # 匹配台标（本地图优先，最后强拼官方缩略图）
            logo_url = resolve_logo(ch, icon_files, vid)

            output.append({
                "name": name,
                "title": real_title,
                "group": ch.get("group", "LIVE"),
                "id": vid,
                "logo": logo_url,
                "url": f"https://www.youtube.com/watch?v={vid}"
            })
            print(f"   ✅ 成功: {vid} | 标题: {real_title[:30]} | Logo: {'有' if logo_url else '无'}")
            time.sleep(1) # 控制抓取网页频率

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
