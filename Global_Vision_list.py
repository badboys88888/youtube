import json
import os

INPUT_FILE = "Global_Vision_list.json"
OUTPUT_FILE = "live.m3u"
ICON_MAP_FILE = "icons_map.json"

BASE_URL = "http://www.diffn.xyz:28000/live/"
URL_SUFFIX = "/index.m3u8"

# EPG地址
EPG_URL = "http://192.168.6.15:5678/t.xml.gz"

# 图标前缀
BASE_ICON_URL = "https://raw.githubusercontent.com/badboys88888/youtube/main/icons/"

def load_icon_map():
    if not os.path.exists(ICON_MAP_FILE):
        print("⚠️ icons_map.json 不存在，将仅使用网页抓取Logo")
        return {}
    try:
        with open(ICON_MAP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("❌ icons_map.json 读取失败:", e)
        return {}

def get_live_list(data):
    if isinstance(data.get("直播"), dict):
        return data["直播"].get("所有直播", [])
    if isinstance(data.get("data"), list):
        return data["data"]
    if isinstance(data, list):
        return data
    return []

def get_display_name(item):
    # 优先使用网页抓取的真实标题，没有再用频道名
    return item.get("title") or item.get("name") or "NO_TITLE"

def get_channel_id(item):
    # 必须用频道名，这样 EPG (t.xml.gz) 才能对应上
    return item.get("name") or "NO_ID"

def resolve_icon(item, icon_map):
    """
    图标优先级：
    1. icons_map.json 强制指定的
    2. Global_Vision_list.json 里的 logo（本地匹配或网页缩略图）
    """
    name = item.get("name") or ""
    
    # 优先查 icons_map
    icon = icon_map.get(name, "")
    if icon:
        if icon.startswith("http"):
            return icon
        return BASE_ICON_URL + icon
        
    # 如果没有，就用 JSON 里带过来的
    return item.get("logo", "") or ""

def main():
    if not os.path.exists(INPUT_FILE):
        print("❌ 找不到文件:", INPUT_FILE)
        return
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("❌ JSON解析失败:", e)
        return

    ICON_MAP = load_icon_map()
    live_list = get_live_list(data)
    if not live_list:
        print("⚠️ 没有直播数据")
        return

    lines = [f'#EXTM3U x-tvg-url="{EPG_URL}"']
    count = 0

    for item in live_list:
        vid = item.get("id")
        if not vid:
            continue

        channel_id = get_channel_id(item)      # tvg-id
        display_name = get_display_name(item)  # 逗号后显示名
        group = item.get("group") or "LIVE"
        url = f"{BASE_URL}{vid}{URL_SUFFIX}"
        icon = resolve_icon(item, ICON_MAP)

        if icon:
            lines.append(
                f'#EXTINF:-1 tvg-id="{channel_id}" tvg-logo="{icon}" group-title="{group}",{display_name}'
            )
        else:
            lines.append(
                f'#EXTINF:-1 tvg-id="{channel_id}" group-title="{group}",{display_name}'
            )
        lines.append(url)
        count += 1

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ M3U生成完成，共 {count} 条")

if __name__ == "__main__":
    main()
