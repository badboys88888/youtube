#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

def json_to_m3u(json_path="Global_Vision_list.json", m3u_path="output/Global_Vision_list.m3u"):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(os.path.dirname(m3u_path), exist_ok=True)

    lines = ["#EXTM3U"]
    for item in data.get("data", []):
        name = item.get("name", "")
        display_name = item.get("display_name") or name
        group = item.get("group", "LIVE")
        vid = item.get("id", "")
        logo = item.get("logo", "")
        url = item.get("url", "")

        lines.append(
            f'#EXTINF:-1 tvg-id="{vid}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{display_name}'
        )
        lines.append(url)

    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"🎉 M3U 生成完成: {m3u_path}")


if __name__ == "__main__":
    json_to_m3u()
