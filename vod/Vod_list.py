#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""点播清单生成器 (在 GitHub Actions 里跑)。

读同仓库的 vod_urls.txt (一行一个地址, # 开头是注释), 地址可以是:
  - 单个视频页  https://www.youtube.com/watch?v=xxxx
  - 播放列表    https://www.youtube.com/playlist?list=xxxx
  - 频道视频页  https://www.youtube.com/@xxx/videos
用 yt-dlp 把地址展开成视频, 再逐个取详情 (标题/封面/频道/简介/时长/发布日期),
生成 Vod_list.json 给甲骨文盒子上的生成器消费 (它只读 JSON 套 vod 地址生成 strm)。

增量: 已在旧 Vod_list.json 里、且这次展开还存在的视频, 详情直接沿用旧的,
只有新视频才发详情请求, 日常跑很快。正在直播/预约的条目跳过 (那是直播那边的)。
覆盖保底: 新条数低于旧文件的 70% 时不覆盖, 写 .new.json 供检查。
"""

import subprocess
import json
import time
import os
import re
import urllib.request
from datetime import datetime

URLS_FILE = "vod_urls.txt"
OUTPUT_FILE = "Vod_list.json"
MIN_KEEP_RATIO = 0.7
MAX_VIDEOS = 2000  # 全清单上限, 防某个超大播放列表把任务跑爆


def load_urls():
    """读地址清单, 返回 [(url, start, end, group), ...]。
    行格式: 地址, 或 地址 | 数量 (只取前 N 个), 或 地址 | 起-止 (取区间)。
    分组: 单独一行 "# @分组名" 后, 下面所有条目都归到该分组 (下游生成到
    同名文件夹下); 再写一行 "# @" (后面不带名字) 就退出分组, 回到根目录。
    例: https://www.youtube.com/@GMMTV/videos | 200"""
    urls = []
    group = ""
    try:
        with open(URLS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    m = re.match(r"#\s*@\s*(.*)$", line)
                    if m:
                        group = m.group(1).strip()
                    continue
                start = end = None
                if "|" in line:
                    line, _, rng = line.partition("|")
                    line = line.strip()
                    rng = rng.strip()
                    try:
                        if "-" in rng:
                            a, b = rng.split("-", 1)
                            start, end = int(a), int(b)
                        elif rng:
                            end = int(rng)
                    except ValueError:
                        print(f"⚠️ 数量格式不对, 忽略数量: {rng}")
                urls.append((line, start, end, group))
    except Exception as e:
        print(f"❌ {URLS_FILE} 读取失败: {e}")
    return urls


def ytdlp_json(cmd, timeout):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = []
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def expand_url(url, start=None, end=None):
    """把一个地址展开成 [(vid, series, episode), ...] (播放列表/频道页/单视频通用)。
    地址本身是播放列表时, 顺带记下列表名和第几集, 下游按剧集建库 (连续剧/BL剧用);
    其他地址 series/episode 为空, 下游当单片处理。
    start/end 来自 txt 里的数量设置 (取第 start~end 个), 没设就全取。"""
    is_playlist = ("list=" in url) or ("/playlist" in url)
    cmd = ["yt-dlp", "--quiet", "--no-warnings", "--dump-json",
           "--flat-playlist", "--no-check-certificates"]
    if start:
        cmd += ["--playlist-start", str(start)]
    if end:
        cmd += ["--playlist-end", str(end)]
    cmd.append(url)
    print(f"   展开: {url}" + (f" (取 {start or 1}~{end or '末尾'})" if (start or end) else ""))
    try:
        infos = ytdlp_json(cmd, timeout=300)
    except subprocess.TimeoutExpired:
        print("   ⏱ 展开超时, 跳过这个地址")
        return []
    out, seen = [], set()
    for info in infos:
        vid = info.get("id") or ""
        if len(vid) < 10 or vid in seen:
            continue
        seen.add(vid)
        series = episode = None
        if is_playlist:
            series = (info.get("playlist_title") or "").strip() or None
            idx = info.get("playlist_index")
            episode = int(idx) if isinstance(idx, int) and idx > 0 else None
        out.append((vid, series, episode))
    print(f"   -> {len(out)} 个视频")
    return out


def fetch_details_ytdlp(vid):
    url = f"https://www.youtube.com/watch?v={vid}"
    cmd = ["yt-dlp", "--quiet", "--no-warnings", "--dump-json",
           "--no-playlist", "--no-check-certificates", url]
    try:
        infos = ytdlp_json(cmd, timeout=90)
    except Exception as e:
        print(f"   ⚠️ yt-dlp 异常: {e}")
        return None
    if not infos:
        return None
    info = infos[0]
    if (info.get("live_status") or "") in ("is_live", "is_upcoming"):
        return "skip-live"
    cover = (info.get("thumbnail") or "").strip()
    if not cover and info.get("thumbnails"):
        cover = (info["thumbnails"][-1].get("url") or "").strip()
    desc = re.sub(r"\n{3,}", "\n\n", (info.get("description") or "").strip())[:1000]
    return {
        "title": (info.get("title") or "").strip(),
        "cover": cover,
        "author": (info.get("uploader") or info.get("channel") or "").strip(),
        "desc": desc,
        "duration": int(info.get("duration") or 0),
        "upload_date": (info.get("upload_date") or "").strip(),
    }


def fetch_details_oembed(vid):
    """yt-dlp 拿不到时的兜底: oEmbed 有标题/频道/封面, 没有简介和时长。"""
    try:
        req = urllib.request.Request(
            "https://www.youtube.com/oembed?url="
            f"https://www.youtube.com/watch?v={vid}&format=json",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            oe = json.loads(r.read().decode("utf-8", "replace"))
        return {
            "title": oe.get("title", ""),
            "cover": oe.get("thumbnail_url", ""),
            "author": oe.get("author_name", ""),
            "desc": "",
            "duration": 0,
            "upload_date": "",
        }
    except Exception:
        return None


def load_old():
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data["data"] if isinstance(data, dict) else data
        return {e["id"]: e for e in items if e.get("id")}
    except Exception:
        return {}


def run():
    urls = load_urls()
    if not urls:
        print(f"⚠️ {URLS_FILE} 里没有地址, 结束")
        return
    old = load_old()
    print(f"旧清单 {len(old)} 条")

    # 1) 展开所有地址, 收集视频 ID (记住来源地址、剧集信息和分组)
    order, source, series_of, group_of = [], {}, {}, {}
    for url, start, end, grp in urls:
        for vid, series, episode in expand_url(url, start, end):
            if vid not in source:
                source[vid] = url
                series_of[vid] = (series, episode)
                group_of[vid] = grp
                order.append(vid)
        time.sleep(1)
    print(f"\n共展开 {len(order)} 个不重复视频")
    if len(order) > MAX_VIDEOS:
        print(f"⚠️ 超过上限 {MAX_VIDEOS}, 只取前 {MAX_VIDEOS} 个")
        order = order[:MAX_VIDEOS]

    # 2) 组装输出: 老视频沿用旧详情, 新视频现取
    output, n_new, n_skip = [], 0, 0
    for idx, vid in enumerate(order, 1):
        series, episode = series_of.get(vid, (None, None))
        if vid in old:
            e = dict(old[vid])
            e["source"] = source[vid]
            e["series"] = series
            e["episode"] = episode
            e["group"] = group_of.get(vid, "")
            output.append(e)
            continue
        print(f"🔍 [{idx}/{len(order)}] 新视频取详情: {vid}")
        det = fetch_details_ytdlp(vid)
        if det == "skip-live":
            n_skip += 1
            print("   🚫 直播/预约流, 跳过")
            continue
        if not det:
            det = fetch_details_oembed(vid)
        if not det:
            n_skip += 1
            print("   ⚠️ 详情取不到, 跳过")
            continue
        n_new += 1
        output.append({
            "id": vid,
            "title": det["title"] or vid,
            "cover": det["cover"],
            "author": det["author"],
            "desc": det["desc"],
            "duration": det["duration"],
            "upload_date": det["upload_date"],
            "series": series,
            "episode": episode,
            "group": group_of.get(vid, ""),
            "source": source[vid],
            "url": f"https://www.youtube.com/watch?v={vid}",
        })
        print(f"   ✅ {det['title'][:40]}")
        time.sleep(0.5)

    result = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(output),
        "data": output,
    }
    if old and len(output) < len(old) * MIN_KEEP_RATIO:
        alt = OUTPUT_FILE.replace(".json", ".new.json")
        with open(alt, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n⚠️ 新清单仅 {len(output)} 条, 低于旧清单 {len(old)} 条的 "
              f"{MIN_KEEP_RATIO:.0%}, 未覆盖, 写到 {alt} 供检查")
        return
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n🎉 点播清单生成完成: 共 {len(output)} 条 (新增 {n_new}, 跳过 {n_skip})")


if __name__ == "__main__":
    run()
