#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import time
import os
import re
from urllib.parse import quote
from datetime import datetime

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


def resolve_logo(ch, icon_files):
    """
    logo 优先级：
    1. channels.json 的 icon 文件名
    2. channels.json 的 logo 完整 URL
    3. icons/ 按 name 自动匹配
    4. 空（后面由网页 thumbnail 兜底）
    """
    icon_file = (ch.get("icon") or "").strip()
    if icon_file:
        return RAW_BASE + quote(icon_file)
    preset_logo = (ch.get("logo") or "").strip()
    if preset_logo:
        return preset_logo
    matched = match_icon_by_name(ch.get("name", ""), icon_files)
    if matched:
        return RAW_BASE + quote(matched)
    return ""


def get_live_items_from_streams(streams_url, timeout=120, playlist_end=15):
    """
    解析 /streams 前 playlist_end 条，返回正在直播的 [{id, title, thumbnail}]
    """
    cmd = [
        "yt-dlp",
        "--quiet",
        "--no-warnings",
        "--dump-json",
        "--playlist-end", str(playlist_end),
        "--no-check-certificates",
        streams_url
    ]
    print(f"   执行: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0 and r.stderr:
            print(f"   ⚠️ yt-dlp stderr: {r.stderr.strip()[:300]}")

        items = []
        for line in (r.stdout or "").strip().splitlines():
            if not line.strip():
                continue
            try:
                info = json.loads(line)
            except json.JSONDecodeError:
                continue
            if info.get("live_status") != "is_live":
                continue
            vid = info.get("id") or ""
            if len(vid) < 10:
                continue
            items.append({
                "id": vid,
                "title": info.get("title", ""),
                "thumbnail": info.get("thumbnail", ""),
            })
            print(f"   🎥 直播: {vid} | {info.get('title','')[:60]}")
        return items
    except subprocess.TimeoutExpired:
        print(f"   ⏱ 超时({timeout}s): {streams_url}")
        return []
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return []


def is_channel_home(url):
    return any(m in url for m in ["/@", "/channel/", "/c/", "/user/"])


def get_live_items(url):
    if "v=" in url:
        vid = url.split("v=")[1].split("&")[0]
        return [{"id": vid, "title": "", "thumbnail": ""}] if vid else []

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


def run():
    CHANNELS = load_channels()
    output = []
    if not CHANNELS:
        print("⚠️ 没有加载到频道数据")
        return

    icon_files = list_icon_files()
    print(f"📁 icons/ 下找到 {len(icon_files)} 个图片文件")

    total = len(CHANNELS)
    for idx, ch in enumerate(CHANNELS, 1):
        name = ch.get("name", "unknown")
        print(f"🔍 [{idx}/{total}] 检测: {name}")

        url = ch.get("url")
        if not url:
            print("   ⚠️ 缺少 url，跳过")
            continue

        try:
            items = get_live_items(url)
        except Exception as e:
            print(f"   ❌ 处理异常: {e}")
            items = []

        if not items:
            print("   ⚠️ 未直播 / 无效")
            time.sleep(1.5)
            continue

        preset_logo = resolve_logo(ch, icon_files)

        for item in items:
            # logo 优先 preset/icons，其次网页缩略图
            logo = preset_logo or item.get("thumbnail", "")
            output.append({
                "name": name,                       # tvg-id、EPG 用
                "title": item.get("title", ""),     # 逗号后显示名用
                "group": ch.get("group", "LIVE"),
                "id": item["id"],
                "logo": logo,
                "url": f"https://www.youtube.com/watch?v={item['id']}"
            })
            print(f"   ✅ 成功: {item['id']} | 标题: {item.get('title','')[:50]}")

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
