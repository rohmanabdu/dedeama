import requests
import re
import os
import json

CONFIG_FILE = "config.json"

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def fetch_playlist(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Gagal fetch {url}: {e}")
        return ""

def parse_m3u(content):
    entries = []
    lines = content.strip().splitlines()
    current_extinf = None
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            current_extinf = line
        elif line and not line.startswith("#") and current_extinf:
            entries.append({
                "extinf": current_extinf,
                "url": line
            })
            current_extinf = None
    return entries

def get_group_and_title(extinf):
    group_match = re.search(r'group-title="([^"]*)"', extinf, re.IGNORECASE)
    title_match = re.search(r',([^,]*)$', extinf)
    group = group_match.group(1) if group_match else ""
    title = title_match.group(1).strip() if title_match else extinf
    return group, title

def classify(entry, config):
    group, title = get_group_and_title(entry["extinf"])
    text_check = f"{group} {title}".lower()
    
    for kw in config["categories"]["live_keywords"]:
        if kw.lower() in text_check:
            return "live"
    for kw in config["categories"]["upcoming_keywords"]:
        if kw.lower() in text_check:
            return "upcoming"
    # default anggap live kalau gak ada kategori
    return "live"

def rebuild_extinf(entry, new_group):
    # ganti group-title lama dengan baru
    if 'group-title="' in entry["extinf"]:
        new_extinf = re.sub(r'group-title="[^"]*"', f'group-title="{new_group}"', entry["extinf"])
    else:
        new_extinf = entry["extinf"].replace("#EXTINF:", f'#EXTINF: group-title="{new_group}" ')
    return new_extinf

def main():
    config = load_config()
    live_list = []
    upcoming_list = []
    seen_urls = set()

    for url in config["sources"]:
        print(f"Fetching: {url}")
        content = fetch_playlist(url)
        if not content:
            continue
        entries = parse_m3u(content)
        for e in entries:
            if e["url"] in seen_urls:
                continue
            seen_urls.add(e["url"])
            cat = classify(e, config)
            
            if cat == "live":
                e["extinf"] = rebuild_extinf(e, config["output_groups"]["live"])
                live_list.append(e)
            else:
                # handle custom video untuk upcoming
                if config["upcoming_custom"]["enabled"]:
                    if config["upcoming_custom"]["mode"] == "replace_all":
                        e["url"] = config["upcoming_custom"]["video_url"]
                e["extinf"] = rebuild_extinf(e, config["output_groups"]["upcoming"])
                upcoming_list.append(e)

    # Gabungkan
    output_path = config["output_file"]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as out:
        out.write("#EXTM3U\n")
        out.write(f"# Total LIVE: {len(live_list)} | UPCOMING: {len(upcoming_list)}\n\n")
        
        for e in live_list:
            out.write(e["extinf"] + "\n")
            out.write(e["url"] + "\n")
        
        out.write("\n")
        
        for e in upcoming_list:
            out.write(e["extinf"] + "\n")
            out.write(e["url"] + "\n")

    print(f"Sukses! File jadi: {output_path} - LIVE: {len(live_list)}, UPCOMING: {len(upcoming_list)}")

if __name__ == "__main__":
    main()
