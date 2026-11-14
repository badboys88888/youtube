#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import time
import os
import re
import urllib.request
import html
from urllib.parse import quote
from datetime import datetime, timezone

# ===================== 配置 ===================== #
RAW_BASE = "https://raw.githubusercontent.com/badboys88888/youtube/main/icons/"
ICONS_DIR = "icons"
OUTPUT_FILE = "Global_Vision_list.json"

# 只保留已持续开播至少这么久的直播（小时）。临时/事件型直播一般几小时就结束，
# 常驻台的流动辄几周；定 48 小时是怕误杀隔几天重启一次的常驻流。
MIN_LIVE_HOURS = 48

# 覆盖保底：新列表条数低于旧文件的这个比例时，判定本次抓取异常，
# 不覆盖旧文件，改写到 .new.json 供人工检查。
MIN_KEEP_RATIO = 0.7


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


def parse_iso_ts(s):
    """解析 YouTube 页面里的时间戳（ISO 8601），失败返回 None。"""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def parse_live_details(page):
    """从视频页 HTML 里提取 liveBroadcastDetails。

    YouTube 的 microformat 里带这段:
      "liveBroadcastDetails":{"isLiveNow":true,
                              "startTimestamp":"2026-11-09T03:41:56+00:00",
                              "endTimestamp":"..."}   # 仅已结束的流才有
    提取不到（页面变体/被拦）时返回 None —— 调用方按"无法验证"处理，不误杀。
    """
    best = None
    for m in re.finditer(r'"liveBroadcastDetails"\s*:\s*\{', page):
        chunk = page[m.end():m.end() + 600]
        d = {}
        mm = re.search(r'"isLiveNow"\s*:\s*(true|false)', chunk)
        if mm:
            d["is_live_now"] = (mm.group(1) == "true")
        mm = re.search(r'"startTimestamp"\s*:\s*"([^"]+)"', chunk)
        if mm:
            d["start"] = parse_iso_ts(mm.group(1))
        mm = re.search(r'"endTimestamp"\s*:\s*"([^"]+)"', chunk)
        if mm:
            d["end"] = parse_iso_ts(mm.group(1))
        if d:
            # 优先带开播时间的那一段（页面里可能出现多段）
            if best is None or ("start" in d and "start" not in best):
                best = d
            if "start" in d and "is_live_now" in d:
                break
    return best


def judge_live(live):
    """判断一条流是否收录。返回 (是否保留, 原因)。

    原则: 能证明是"已结束/临时/未开播"的才剔除; 验证不到的一律放行, 怕误杀。
    """
    if not live:
        return True, "页面无直播信息, 无法验证, 放行"
    if live.get("end"):
        return False, "已结束的直播(已变录播)"
    if live.get("is_live_now"):
        start = live.get("start")
        if start:
            age_h = (datetime.now(timezone.utc) - start).total_seconds() / 3600
            if age_h >= MIN_LIVE_HOURS:
                return True, f"已开播 {age_h:.0f} 小时"
            return False, f"临时直播(仅开播 {age_h:.1f} 小时, 不满 {MIN_LIVE_HOURS} 小时)"
        return True, "直播中但页面无开播时间, 放行"
    if live.get("start"):
        return False, "未开播(预约流)"
    return True, "无法判定状态, 放行"


def _json_str(page, key, scope=None):
    """提取页面 JSON 里的字符串字段 (带转义处理), 失败返回空串。"""
    text = scope if scope is not None else page
    m = re.search(r'"%s":"((?:[^"\\]|\\.)*)"' % key, text)
    if not m:
        return ""
    try:
        return json.loads('"' + m.group(1) + '"')
    except Exception:
        return ""


def fetch_video_page_metadata(vid):
    """从 YouTube 视频页面读取标题、缩略图 URL、直播状态和详情。
    返回 (title, logo, live, author, desc): author 是频道名, desc 是视频简介,
    供下游 (盒子上的 Emby 库生成器) 写带详情的 nfo, 同一页顺带取, 不多发请求。"""
    url = f"https://www.youtube.com/watch?v={vid}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            page = response.read().decode("utf-8", errors="ignore")

        def get_meta(property_name):
            patterns = [
                rf'<meta[^>]+property=["\']{re.escape(property_name)}["\'][^>]+content=["\']([^"\']*)["\']',
                rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']{re.escape(property_name)}["\']',
                rf'<meta[^>]+name=["\']{re.escape(property_name)}["\'][^>]+content=["\']([^"\']*)["\']',
                rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']{re.escape(property_name)}["\']',
            ]
            for pattern in patterns:
                match = re.search(pattern, page, flags=re.IGNORECASE)
                if match:
                    return html.unescape(match.group(1)).strip()
            return ""

        title = get_meta("og:title")
        if not title:
            match = re.search(r"<title[^>]*>(.*?)</title>", page, flags=re.IGNORECASE | re.DOTALL)
            if match:
                title = html.unescape(match.group(1)).strip()
        title = re.sub(r"\s*-\s*YouTube$", "", title).strip()

        logo = get_meta("og:image") or get_meta("twitter:image")
        live = parse_live_details(page)

        # 详情: 在 videoDetails 附近找频道名和简介 (整页找兜底), 简介截断防 JSON 膨胀
        vd = page.find('"videoDetails"')
        scope = page[vd:vd + 25000] if vd >= 0 else page
        author = _json_str(page, "author", scope) or _json_str(page, "author")
        desc = _json_str(page, "shortDescription", scope) or \
            _json_str(page, "shortDescription") or get_meta("og:description")
        desc = re.sub(r"\n{3,}", "\n\n", desc.strip())[:1000]
        return title, logo, live, author, desc
    except Exception as e:
        print(f"   ⚠️ 网页信息获取失败: {e}")
        return "", "", None, "", ""


def resolve_logo(ch, icon_files, page_logo):
    """优先使用网页获取的缩略图；网页没有时回退至本地/JSON配置。"""
    if page_logo:
        return page_logo

    matched = match_icon_by_name(ch.get("name", ""), icon_files)
    if matched:
        return RAW_BASE + quote(matched)

    icon_file = (ch.get("icon") or "").strip()
    if icon_file:
        return RAW_BASE + quote(icon_file)

    preset_logo = (ch.get("logo") or ch.get("tvg-logo") or "").strip()
    return preset_logo


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
            if not line.strip():
                continue
            try:
                info = json.loads(line)
            except json.JSONDecodeError:
                continue

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
        if base.endswith("/streams"):
            streams_url = base
        elif base.endswith("/live"):
            streams_url = base[:-len("/live")] + "/streams"
        else:
            streams_url = base + "/streams"
        return get_live_ids_from_streams(streams_url)

    return get_live_ids_from_streams(url)


def old_output_count():
    """读现有输出文件的条数, 用于覆盖保底比较。没有/损坏返回 0。"""
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            old = json.load(f)
        if isinstance(old, dict) and isinstance(old.get("data"), list):
            return len(old["data"])
        if isinstance(old, list):
            return len(old)
    except Exception:
        pass
    return 0


# ===================== 主流程 ===================== #
def run():
    CHANNELS = load_channels()
    output = []
    if not CHANNELS:
        return

    icon_files = list_icon_files()
    total = len(CHANNELS)
    dropped = {"ended": 0, "temp": 0, "upcoming": 0}

    for idx, ch in enumerate(CHANNELS, 1):
        name = ch.get("name", "unknown")
        print(f"🔍 [{idx}/{total}] 检测: {name}")

        url = ch.get("url")
        if not url:
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

        # 兼容 JSON 中 tvg-id 或误写的 tiv-id；没有配置时留空，不使用视频 ID 代替。
        channel_tvg_id = ch.get("tvg-id") or ch.get("tiv-id") or ""

        for vid in vids:
            print(f"   🔄 获取详情: {vid} ...")

            # 标题和 tvg-logo 均优先从视频网页读取；同一页顺带验直播状态、取详情。
            real_title, page_logo, live, author, desc = fetch_video_page_metadata(vid)
            keep, reason = judge_live(live)
            if not keep:
                if "已结束" in reason:
                    dropped["ended"] += 1
                elif "未开播" in reason:
                    dropped["upcoming"] += 1
                else:
                    dropped["temp"] += 1
                print(f"   🚫 跳过: {vid} | {reason}")
                time.sleep(1)
                continue
            print(f"   ⏱ 状态: {reason}")

            if not real_title:
                real_title = name

            logo_url = resolve_logo(ch, icon_files, page_logo)

            output.append({
                "name": name,
                "title": real_title,
                "group": ch.get("group", "LIVE"),
                "tvg-id": channel_tvg_id,
                "tvg-logo": logo_url,
                # 网页详情: 频道名 + 简介, 下游写 nfo 用 (老读取程序忽略即可)。
                "author": author,
                "desc": desc,
                # 保留原有字段，方便兼容现有读取程序。
                "id": vid,
                "logo": logo_url,
                "url": f"https://www.youtube.com/watch?v={vid}"
            })
            print(f"   ✅ 成功: {vid} | 标题: {real_title[:30]} | Logo: {'有' if logo_url else '无'}")
            time.sleep(1)  # 控制抓取网页频率

        time.sleep(1.5)

    result = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(output),
        "data": output
    }

    # 覆盖保底: 新条数骤降说明这次抓取大概率出问题了, 保留旧文件。
    old_n = old_output_count()
    if old_n and len(output) < old_n * MIN_KEEP_RATIO:
        alt = OUTPUT_FILE.replace(".json", ".new.json")
        with open(alt, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n⚠️ 新列表仅 {len(output)} 条, 低于旧文件 {old_n} 条的 {MIN_KEEP_RATIO:.0%}, "
              f"疑似抓取异常 — 未覆盖 {OUTPUT_FILE}, 新结果写到 {alt} 供检查")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n🎉 JSON生成完成，共 {len(output)} 条直播"
          f"（剔除: 已结束 {dropped['ended']} / 临时 {dropped['temp']} / 未开播 {dropped['upcoming']}）")


if __name__ == "__main__":
    run()
