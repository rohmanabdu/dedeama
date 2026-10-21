import requests, re, os, json, time, random, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_config():
    with open("candak.json", "r", encoding="utf-8") as f:
        content = f.read().strip()
    
    # FIX OTOMATIS kalau ada extra data / double JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print("WARNING: config.json rusak (Extra data), coba auto-fix...")
        # ambil JSON pertama yang valid saja
        decoder = json.JSONDecoder()
        obj, idx = decoder.raw_decode(content)
        print(f"Auto-fix berhasil, ambil data sampai char {idx}")
        return obj

def fetch(url):
    headers = {"User-Agent": "Mozilla/5.0 Chrome/126.0", "Referer": "https://bandeltv.xyz/"}
    for i in range(3):
        try:
            print(f"Fetch {url} attempt {i+1}")
            r = requests.get(url, headers=headers, timeout=60, verify=False)
            if len(r.text) > 30:
                return r.text
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(random.randint(2,5))
    return ""

def parse(content):
    entries=[]; cur=None
    for line in content.splitlines():
        line=line.strip()
        if line.startswith("#EXTINF"): cur=line
        elif line and not line.startswith("#") and cur:
            entries.append({"extinf":cur, "url":line}); cur=None
    return entries

def get_info(extinf):
    g=re.search(r'group-title="([^"]*)"', extinf, re.I)
    t=re.search(r',([^,]*)$', extinf)
    return (g.group(1) if g else ""), (t.group(1).strip() if t else "")

def classify(group, title, cfg):
    txt=f"{group} {title}".lower()
    for k in cfg["kategori_deteksi"]["upcoming_keywords"]:
        if k.lower() in txt: return "upcoming"
    return "live"

def set_group(extinf, new_group):
    if 'group-title="' in extinf:
        return re.sub(r'group-title="[^"]*"', f'group-title="{new_group}"', extinf)
    return extinf.replace("#EXTINF:", f'#EXTINF: group-title="{new_group}" ')

def main():
    cfg=load_config()
    live_list, up_list = [], []
    seen=set()
    for url in cfg["sources"]:
        data=fetch(url)
        items=parse(data)
        print(f"Dapat {len(items)} dari {url}")
        time.sleep(1)
        for e in items:
            if e["url"] in seen: continue
            seen.add(e["url"])
            group,title=get_info(e["extinf"])
            cat=classify(group,title,cfg)
            if cat=="live":
                e["extinf"]=set_group(e["extinf"], cfg["kategori_output"]["live"])
                live_list.append(e)
            else:
                if cfg["upcoming_edit"]["enabled"]:
                    custom_map=cfg["upcoming_edit"]["video_custom_per_judul"]
                    replaced=False
                    for key, vid in custom_map.items():
                        if key.lower() in title.lower():
                            e["url"]=vid; replaced=True; break
                    if not replaced:
                        e["url"]=cfg["upcoming_edit"]["default_video"]
                e["extinf"]=set_group(e["extinf"], cfg["kategori_output"]["upcoming"])
                up_list.append(e)
    out=cfg["output_file"]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for e in live_list: f.write(f"{e['extinf']}\n{e['url']}\n")
        for e in up_list: f.write(f"{e['extinf']}\n{e['url']}\n")
    print(f"SELESAI -> LIVE: {len(live_list)} | UPCOMING: {len(up_list)}")

if __name__=="__main__":
    main()
