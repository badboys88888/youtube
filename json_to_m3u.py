import json
import os

INPUT_FILE = "Global_Vision_list.json"
OUTPUT_FILE = "live.m3u"
ICON_MAP_FILE = "icons_map.json"

BASE_URL = "http://192.168.6.16:8080/play?id="

# =========================
# 🟢 EPG地址（新增）
# =========================
EPG_URL = "http://192.168.6.15:5678/t.xml.gz"


# =========================
# 🟢 加载图标映射
# =========================
def load_icon_map():
    if not os.path.exists(ICON_MAP_FILE):
        print("⚠️ icons_map.json 不存在，将不加载图标")
        return {}

    try:
        with open(ICON_MAP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("❌ icons_map.json 读取失败:", e)
        return {}


# =========================
# 🟢 读取直播列表
# =========================
def get_live_list(data):

    if isinstance(data.get("直播"), dict):
        return data["直播"].get("所有直播", [])

    if isinstance(data.get("data"), list):
        return data["data"]

    if isinstance(data, list):
        return data

    return []


# =========================
# 🟢 获取名称
# =========================
def get_name(item):
    return (
        item.get("title")
        or item.get("name")
        or item.get("channel")
        or "NO_TITLE"
    )


# =========================
# 🧠 图标匹配（支持URL/文件名）
# =========================
def resolve_icon(name, icon_map):

    icon = icon_map.get(name, "")

    if not icon:
        return ""

    if icon.startswith("http"):
        return icon

    BASE_ICON_URL = "https://raw.githubusercontent.com/badboys88888/youtube/main/icons/"
    return BASE_ICON_URL + icon


# =========================
# 🚀 主程序
# =========================
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

    lines = []

    # =========================
    # 🟢 M3U头（新增EPG）
    # =========================
    lines.append(f'#EXTM3U x-tvg-url="{EPG_URL}"')

    count = 0

    for item in live_list:

        vid = item.get("id")
        if not vid:
            continue

        name = get_name(item)
        group = item.get("group") or "LIVE"

        url = BASE_URL + str(vid)

        icon = resolve_icon(name, ICON_MAP)

        # =========================
        # 🟢 EXTINF
        # =========================
        if icon:
            lines.append(
                f'#EXTINF:-1 tvg-id="{name}" tvg-logo="{icon}" group-title="{group}",{name}'
            )
        else:
            lines.append(
                f'#EXTINF:-1 tvg-id="{name}" group-title="{group}",{name}'
            )

        lines.append(url)

        count += 1

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ M3U生成完成，共 {count} 条")


if __name__ == "__main__":
    main()
