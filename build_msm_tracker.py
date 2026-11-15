import os
import re
import json
import urllib.parse
import requests
from bs4 import BeautifulSoup

API_URL = "https://mysingingmonsters.fandom.com/api.php"
ASSETS_DIR = "msm_assets"
MONSTERS_DIR = os.path.join(ASSETS_DIR, "monsters")
EGGS_DIR = os.path.join(ASSETS_DIR, "eggs")

os.makedirs(MONSTERS_DIR, exist_ok=True)
os.makedirs(EGGS_DIR, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MSMTrackerBuilder/2.0"
})

ROSTERS = {
    "wublins": [
        "Pixolotl", "Bona-Petite", "Maulch", "Fleechwurm",
        "Brump", "Zynth", "Poewk", "Thwok", "Dwumrohl", "Zuuker",
        "Screemu", "Tympa", "Dermit", "Gheegur", "Whajje",
        "Creepuscule", "Blipsqueak", "Scargo", "Astropod", "Monculus"
    ],
    "celestials": [
        "Scaratar", "Loodvigg", "Torrt", "Plixie", "Attmoz", "Hornacle",
        "Furnoss", "Glaishur", "Blasoom", "Syncopite", "Vhamp", "Galvana"
    ],
    "adults": [
        "Adult Scaratar", "Adult Loodvigg", "Adult Torrt", "Adult Plixie",
        "Adult Attmoz", "Adult Hornacle", "Adult Furnoss", "Adult Glaishur",
        "Adult Blasoom", "Adult Syncopite", "Adult Vhamp", "Adult Galvana"
    ],
    "amber": [
        "Kayna", "Glowl", "Flowah", "Stogg", "Phangler", "Boskus",
        "Barrb", "Floogull", "Whaddle", "Woolabee", "Repatillo", "Rootitoot",
        "Sooza", "Thrumble", "Ziggurab", "Wynq", "Tring", "Sneyser",
        "Yelmut", "Flum Ox", "Krillby", "Edamimi", "PongPing", "Incisaur",
        "Tiawa", "Bisonorus", "Candelavra", "Drummidary", "Bowhead", "Tuskski", "Gnarls"
    ]
}


def safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name.strip())


def clean_wikia_url(url: str) -> str:
    if not url or url.startswith("data:"):
        return ""
    return url.split("/revision/")[0]


def download_image(url: str, dest_path: str) -> str:
    if not url:
        return ""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 200:
        return dest_path.replace("\\", "/")
    try:
        r = SESSION.get(clean_wikia_url(url), timeout=15)
        if r.status_code == 200 and len(r.content) > 200:
            with open(dest_path, "wb") as f:
                f.write(r.content)
            return dest_path.replace("\\", "/")
    except Exception as e:
        print(f"    [!] Download error for {url}: {e}")
    return ""


def resolve_wiki_files(file_titles: list) -> dict:
    """Batch resolves File:... titles to static.wikia.nocookie.net URLs."""
    result = {}
    unique = [f for f in set(file_titles) if f]
    for i in range(0, len(unique), 40):
        batch = unique[i:i + 40]
        titles_param = "|".join(f if f.startswith("File:") else f"File:{f}" for f in batch)
        params = {
            "action": "query",
            "redirects": "1",
            "titles": titles_param,
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json"
        }
        try:
            data = SESSION.get(API_URL, params=params, timeout=15).json()
            q = data.get("query", {})
            rev = {}
            for n in q.get("normalized", []):
                rev.setdefault(n["to"], set()).add(n["from"])
            for rd in q.get("redirects", []):
                rev.setdefault(rd["to"], set()).add(rd["from"])
                for orig in list(rev.get(rd["from"], [])):
                    rev[rd["to"]].add(orig)

            for page in q.get("pages", {}).values():
                ii = page.get("imageinfo")
                if ii and ii[0].get("url"):
                    url = clean_wikia_url(ii[0]["url"])
                    names = {page.get("title", "")} | rev.get(page.get("title", ""), set())
                    for nm in names:
                        clean = nm.replace("File:", "")
                        result[clean] = url
                        result[clean.replace(" ", "_")] = url
                        result[clean.replace("_", " ")] = url
        except Exception as e:
            print(f"  [!] Batch resolve error: {e}")
    return result


def parse_page_api(page_title: str) -> dict:
    """Fetches both rendered HTML and raw Wikitext for a Wiki page."""
    params = {
        "action": "parse",
        "page": page_title,
        "redirects": "1",
        "prop": "text|wikitext",
        "format": "json"
    }
    try:
        r = SESSION.get(API_URL, params=params, timeout=20)
        data = r.json()
        parse_obj = data.get("parse", {})
        return {
            "html": parse_obj.get("text", {}).get("*", ""),
            "wikitext": parse_obj.get("wikitext", {}).get("*", "")
        }
    except Exception as e:
        print(f"  [!] API error on {page_title}: {e}")
        return {"html": "", "wikitext": ""}


def parse_eggs_from_dom_element(elem, egg_url_map: dict) -> list:
    """Extracts (egg_name, count) from any HTML element containing egg images and x<number>."""
    pairs = []
    # Find all images inside this element
    for img in elem.find_all("img"):
        raw_key = urllib.parse.unquote(
            img.get("data-image-name")
            or img.get("data-image-key")
            or img.get("alt")
            or img.get("src")
            or ""
        )
        if "egg" not in raw_key.lower():
            continue
        if any(bad in raw_key.lower() for bad in ["statue", "vessel", "trophy", "costume", "button"]):
            continue

        # Clean egg name
        egg_name = re.sub(r"\.(png|webp|jpg|gif)$", "", raw_key, flags=re.I)
        egg_name = egg_name.replace("_", " ")
        egg_name = re.sub(r"\s*(-egg|-Egg| Egg)\b.*$", "", egg_name).strip()
        if not egg_name or "File:" in egg_name:
            a_parent = img.find_parent("a")
            if a_parent and a_parent.get("title"):
                egg_name = a_parent["title"].strip()

        img_url = clean_wikia_url(img.get("data-src") or img.get("src") or "")
        if egg_name and img_url:
            egg_url_map[egg_name] = img_url

        # Look for the "x6" or "×6" right after this image
        count = None
        # Method A: walk next siblings in the DOM
        node = img.find_parent("a") or img
        curr = node.next_sibling
        acc = ""
        hops = 0
        while curr is not None and hops < 6:
            if getattr(curr, "name", None) == "img":
                break
            if hasattr(curr, "find") and curr.find("img"):
                break
            txt = curr.get_text(" ", strip=True) if hasattr(curr, "get_text") else str(curr)
            acc += " " + txt
            m = re.search(r"[x×]\s*(\d+)", acc, re.I)
            if m:
                count = int(m.group(1))
                break
            curr = curr.next_sibling
            hops += 1

        # Method B: if inside an <li> or <span> with a single img
        if count is None:
            for parent_tag in ["span", "li", "td"]:
                p = img.find_parent(parent_tag)
                if p and len(p.find_all("img")) == 1:
                    m = re.search(r"[x×]\s*(\d+)", p.get_text(" ", strip=True), re.I)
                    if m:
                        count = int(m.group(1))
                        break

        if egg_name and count and 0 < count <= 200:
            pairs.append([egg_name, count])

    return pairs


def parse_eggs_from_wikitext(wikitext: str, category: str) -> list:
    """Fallback parser that reads raw MediaWiki wikitext for egg templates or File:*-egg.png."""
    if not wikitext:
        return []

    section = wikitext
    if category == "amber":
        m = re.search(r"==\s*Amber Island.*?(?===[^=]|$)", wikitext, re.S | re.I)
        if m:
            section = m.group(0)
    elif category in ("wublins", "celestials"):
        # Stop before Rare / Epic / Adult subsections
        m = re.split(r"===\s*(?:Rare|Epic|Adult)", wikitext, flags=re.I)
        if m:
            section = m[0]

    pairs = []
    seen = set()

    # Pattern 1: [[File:Entbrat-egg.png|...]] x6 or ×6
    for m in re.finditer(r"File:([A-Za-z0-9_' -]+?)(?:-egg|_Egg)\.(?:png|webp)[^\n\r]{0,120}?[x×]\s*(\d+)", section, re.I):
        e_name = m.group(1).replace("_", " ").strip()
        cnt = int(m.group(2))
        if e_name not in seen and 0 < cnt <= 200:
            seen.add(e_name)
            pairs.append([e_name, cnt])

    # Pattern 2: {{Inventory/Egg|Entbrat|6}} or {{Egg|Entbrat|6}} or |inventory = ...
    if len(pairs) < 2:
        for m in re.finditer(r"\{\{(?:Inventory/Egg|Egg|MonsterEgg)\|([^|}]+)\|(\d+)", section, re.I):
            e_name = m.group(1).replace("_", " ").strip()
            cnt = int(m.group(2))
            if e_name not in seen and 0 < cnt <= 200:
                seen.add(e_name)
                pairs.append([e_name, cnt])

    return pairs


def scrape_overview_table(page_title: str, category: str, egg_url_map: dict) -> dict:
    """Scrapes bulk inventory tables from Wublins, Celestials, or Amber_Island."""
    print(f"Scraping overview page: {page_title} ({category})...")
    parsed = parse_page_api(page_title)
    soup = BeautifulSoup(parsed["html"], "html.parser")
    results = {}

    for tr in soup.find_all("tr"):
        tds = tr.find_all(["td", "th"])
        if len(tds) < 2:
            continue

        egg_td = None
        eggs = []
        for td in tds:
            cand = parse_eggs_from_dom_element(td, egg_url_map)
            if len(cand) >= 2:
                egg_td = td
                eggs = cand
                break

        if not egg_td:
            continue

        # Find monster name and portrait in cells before egg_td
        m_name = ""
        m_img = ""
        for td in tds:
            if td == egg_td:
                break
            for img in td.find_all("img"):
                u = clean_wikia_url(img.get("data-src") or img.get("src") or "")
                k = urllib.parse.unquote(img.get("data-image-name") or img.get("alt") or "")
                if u and not any(x in k.lower() for x in ["statue", "vessel", "inactive", "grid", "coin", "key", "relic"]):
                    if not m_img:
                        m_img = u
            links = [a.get_text(" ", strip=True) for a in td.find_all("a") if a.get_text(" ", strip=True)]
            if links and not m_name:
                m_name = links[-1]

        if not m_name:
            continue

        # Filter Rare / Epic / Adult vs Common
        row_html_low = egg_td.decode_contents().lower()
        is_rare = m_name.lower().startswith("rare ") or all(e[0].lower().startswith("rare ") for e in eggs)
        is_epic = m_name.lower().startswith("epic ") or all(e[0].lower().startswith("epic ") for e in eggs)
        has_flex = "flex" in row_html_low or m_name.lower().startswith("adult ")

        if category in ("wublins", "amber") and (is_rare or is_epic):
            continue
        if category == "celestials" and (has_flex or is_rare or is_epic):
            continue
        if category == "adults" and not has_flex:
            continue

        key_name = re.sub(r"^Adult\s+", "", m_name, flags=re.I).strip()
        if category == "adults":
            key_name = f"Adult {key_name}"

        # Extract cost & time from remaining cells
        cost, time_str = "-", "-"
        for td in tds:
            if td == egg_td:
                continue
            txt = " ".join(td.get_text(" ", strip=True).split())
            if re.match(r"^\d+\s*x\s*\d+$", txt, re.I) or txt == m_name:
                continue
            if re.search(r"\b\d+\s*(d|days|h|hours)\b", txt, re.I) or re.search(
                r"(January|February|March|April|May|June|July|August|September|October|November|December)", txt, re.I
            ):
                if time_str == "-":
                    time_str = txt
            elif re.search(r"\d", txt) and cost == "-":
                cost = txt

        if key_name.lower() not in results:
            results[key_name.lower()] = {
                "name": key_name,
                "img_url": m_img,
                "cost": cost,
                "time": time_str,
                "eggs": eggs
            }
            print(f"  [+] Parsed {key_name} from {page_title}: {len(eggs)} egg types ({sum(c for _, c in eggs)} total)")

    return results


def scrape_individual_monster(monster_name: str, category: str, egg_url_map: dict) -> dict:
    """Scrapes an individual monster's Wiki page (Infobox 'Required Inventory' + tables + Wikitext)."""
    page_target = monster_name.replace("Adult ", "") if category == "adults" else monster_name
    print(f"  -> Scraping individual page: {page_target} (for {monster_name})...")
    parsed = parse_page_api(page_target)
    soup = BeautifulSoup(parsed["html"], "html.parser")

    # 1. Portrait image from portable infobox
    m_img = ""
    pi_img = soup.select_one(".portable-infobox .pi-image img, .infobox img")
    if pi_img:
        m_img = clean_wikia_url(pi_img.get("data-src") or pi_img.get("src") or "")

    # 2. Check Portable Infobox "Required Inventory" block first, plus all tables/divs
    candidate_lists = []
    for block in soup.select(".pi-item, .pi-data-value, table, td, div"):
        if block.name == "div" and block.find(["table", "div"]) and "pi-data-value" not in (block.get("class") or []):
            continue
        pairs = parse_eggs_from_dom_element(block, egg_url_map)
        if len(pairs) >= 2:
            # Deduplicate while preserving order
            dedup = []
            seen = set()
            for e_n, c in pairs:
                if e_n not in seen:
                    seen.add(e_n)
                    dedup.append([e_n, c])

            is_rare = all(e[0].lower().startswith("rare ") for e in dedup)
            is_epic = all(e[0].lower().startswith("epic ") for e in dedup)
            has_flex = any("flex" in e[0].lower() for e in dedup)

            if category == "adults" and has_flex:
                candidate_lists.append(dedup)
            elif category != "adults" and not is_rare and not is_epic and not has_flex:
                candidate_lists.append(dedup)

    # 3. Fallback to Wikitext if DOM didn't yield a clean list
    if not candidate_lists:
        wt_pairs = parse_eggs_from_wikitext(parsed["wikitext"], category)
        if len(wt_pairs) >= 2:
            candidate_lists.append(wt_pairs)

    eggs = candidate_lists[0] if candidate_lists else []
    print(f"     Found {len(eggs)} egg types for {monster_name}: {eggs}")

    # Extract time limit from infobox if present
    time_str = "-"
    for item in soup.select(".pi-data"):
        raw_txt = item.get_text(" ", strip=True)
        m_time = re.search(r"Time\s*limit\s*:\s*([0-9]+\s*(?:days?|hours?|d|h)|No\s*limit)", raw_txt, re.I)
        if m_time:
            time_str = m_time.group(1).strip()
            break

    return {
        "name": monster_name,
        "img_url": m_img,
        "cost": "10 Keys" if category == "adults" else "-",
        "time": time_str,
        "eggs": eggs
    }


def main():
    egg_url_map = {}

    # 1. Scrape overview pages first
    wublin_ov = scrape_overview_table("Wublins", "wublins", egg_url_map)
    celestial_ov = scrape_overview_table("Celestials", "celestials", egg_url_map)
    adult_ov = scrape_overview_table("Celestials", "adults", egg_url_map)
    amber_ov = scrape_overview_table("Amber_Island", "amber", egg_url_map)

    overview_by_cat = {
        "wublins": wublin_ov,
        "celestials": celestial_ov,
        "adults": adult_ov,
        "amber": amber_ov
    }

    final_db = {"wublins": [], "celestials": [], "adults": [], "amber": []}

    # 2. Build complete roster for each tab, scraping individual monster pages for any missing entry
    for cat in ["wublins", "celestials", "adults", "amber"]:
        ov = overview_by_cat[cat]
        for name in ROSTERS[cat]:
            entry = ov.get(name.lower())
            if not entry or len(entry.get("eggs", [])) < 2:
                entry = scrape_individual_monster(name, cat, egg_url_map)

            m_id = f"{cat}-{safe_filename(name).lower()}" if cat in ("adults", "amber") else safe_filename(name).lower()
            # Keep original IDs for the 4 screenshot Wublins so tallies match
            if cat == "wublins" and name.lower() == "bona-petite":
                m_id = "bona-petite"

            disp_name = f"{name} Vessel" if cat == "amber" else name
            final_db[cat].append({
                "id": m_id,
                "base_name": name,
                "name": disp_name,
                "img_url": entry.get("img_url", ""),
                "cost": entry.get("cost", "-"),
                "time": entry.get("time", "-"),
                "eggs": entry.get("eggs", [])
            })

    # 3. Resolve any missing monster or egg image URLs in bulk via MediaWiki API
    files_to_resolve = []
    for cat in final_db:
        for m in final_db[cat]:
            if cat == "adults" or not m["img_url"]:
                files_to_resolve.append(f"{m['base_name'].replace(' ', '_')}.png")
            for e_name, _ in m["eggs"]:
                if e_name not in egg_url_map:
                    cl = e_name.replace(" ", "_")
                    files_to_resolve.extend([f"{cl}-egg.png", f"{cl}_Egg.png", f"{cl}-Egg.png"])

    resolved_files = resolve_wiki_files(files_to_resolve)

    for cat in final_db:
        for m in final_db[cat]:
            fn = f"{m['base_name'].replace(' ', '_')}.png"
            if (cat == "adults" or not m["img_url"]) and resolved_files.get(fn):
                m["img_url"] = resolved_files[fn]
            for e_name, _ in m["eggs"]:
                if e_name not in egg_url_map:
                    cl = e_name.replace(" ", "_")
                    for cand in [f"{cl}-egg.png", f"{cl}_Egg.png", f"{cl}-Egg.png"]:
                        if resolved_files.get(cand):
                            egg_url_map[e_name] = resolved_files[cand]
                            break

    # 4. Download all Monster & Egg PNGs into ./msm_assets/
    print("\n=== Downloading Monster & Egg Sprites to ./msm_assets/ ===")
    for cat in final_db:
        for m in final_db[cat]:
            dest = os.path.join(MONSTERS_DIR, f"{m['id']}.png")
            m["local_img"] = download_image(m["img_url"], dest)

    local_egg_map = {}
    for e_name, url in sorted(egg_url_map.items()):
        dest = os.path.join(EGGS_DIR, f"{safe_filename(e_name)}.png")
        local_egg_map[e_name] = download_image(url, dest)

    payload = {"monsters": final_db, "eggs": local_egg_map}

    with open("msm_recipes.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    with open("msm_recipes.js", "w", encoding="utf-8") as f:
        f.write("window.MSM_SCRAPED_DATA = " + json.dumps(payload, indent=2) + ";\n")

    print(f"\nSaved msm_recipes.json with {sum(len(v) for v in final_db.values())} monsters and {len(local_egg_map)} egg sprites!")


if __name__ == "__main__":
    main()