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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MSMTrackerBuilder/3.0"
})

ROSTERS = {
    "wublins": [
        "Brump", "Zynth", "Poewk", "Thwok", "Dwumrohl", "Zuuker",
        "Screemu", "Tympa", "Dermit", "Gheegur", "Whajje",
        "Creepuscule", "Blipsqueak", "Scargo", "Astropod",
        "Pixolotl", "Bona-Petite", "Maulch", "Fleechwurm", "Monculus"
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

# Verified fallback for Adult Celestials in case any Wiki sub-template is missing
ADULT_FALLBACK_RECIPES = {
    "Adult Scaratar": {"time": "31 days", "eggs": [["Floot Fly",3], ["Shrubb",3], ["Fwog",3], ["Drumpler",3], ["HippityHop",2], ["Squot",2], ["Wimmzies",2], ["Ziggurab",2], ["Cantorell",2], ["Bridg-it",2], ["Clavi Gnat",2], ["Reedling",2], ["Pladdie",2], ["Quarrister",2], ["Boo'qwurm",1], ["Rare 2E Faerie Flex",2], ["Rare 3E Fire Flex",1]]},
    "Adult Loodvigg": {"time": "30 days", "eggs": [["Pango",3], ["Maw",3], ["Gob",3], ["Bulbo",3], ["Spytrap",3], ["TooToo",3], ["Fiddlement",2], ["Bowgart",2], ["Spunge",2], ["Thumpies",2], ["Congle",1], ["Deedge",1], ["Blow't",1], ["Pluckbill",1], ["Whisp",1], ["Nebulob",1], ["Arackulele",1], ["Rare 2E Light Flex",1], ["Rare 3E Psychic Flex",1], ["Rare 3E Faerie Flex",1], ["Rare 3E Bone Flex",1]]},
    "Adult Torrt": {"time": "31 days", "eggs": [["Drumpler",3], ["Fwog",3], ["Shrubb",3], ["Cybop",3], ["T-Rox",2], ["Clamble",2], ["PomPom",2], ["Thumpies",2], ["Reedling",2], ["Quarrister",2], ["Entbrat",2], ["Deedge",2], ["Riff",2], ["Shellbeat",2], ["Punkleton",1], ["Rare 2E Earth Flex",2], ["Rare 3E Earth Flex",1], ["Rare 4E Earth Flex",1]]},
    "Adult Plixie": {"time": "30 days", "eggs": [["Theremind",3], ["Fwog",3], ["Maw",3], ["Drumpler",3], ["Bonkers",2], ["Oaktopus",2], ["Poppette",2], ["Yuggler",2], ["Tapricorn",2], ["Rooba",2], ["Periscorp",2], ["Furcorn",2], ["Gloptic",2], ["Entbrat",2], ["Gobbleygourd",1], ["Rare 2E Psychic Flex",2], ["Rare 3E Fire Flex",1]]},
    "Adult Attmoz": {"time": "31 days", "eggs": [["Dandidoo",3], ["Cybop",3], ["Quibble",3], ["Pango",3], ["T-Rox",2], ["Congle",2], ["PomPom",2], ["Scups",2], ["Reedling",2], ["Spunge",2], ["Thumpies",2], ["Bowgart",2], ["Riff",2], ["Deedge",2], ["Schmoochle",1], ["Yool",2], ["Rare 2E Air Flex",2], ["Rare 3E Air Flex",1], ["Rare 4E Air Flex",1]]},
    "Adult Hornacle": {"time": "31 days", "eggs": [["Fwog",3], ["Maw",3], ["Oaktopus",3], ["Quibble",3], ["T-Rox",2], ["Bowgart",2], ["Pummel",2], ["Spunge",2], ["Scups",2], ["Congle",2], ["Shellbeat",2], ["Deedge",2], ["Riff",2], ["Entbrat",2], ["Carillong",1], ["Rare 2E Water Flex",2], ["Rare 3E Water Flex",1], ["Rare 4E Water Flex",1]]},
    "Adult Furnoss": {"time": "28 days", "eggs": [["Glowl",3], ["Flowah",3], ["Stogg",3], ["Phangler",3], ["Boskus",3], ["Barrb",2], ["Floogull",2], ["Whaddle",2], ["Woolabee",2], ["Repatillo",2], ["Reedling",2], ["Tring",2], ["Sneyser",2], ["Schmoochle",1], ["Rare 2E Fire Flex",2], ["Rare 3E Fire Flex",1]]},
    "Adult Glaishur": {"time": "31 days", "eggs": [["Pango",3], ["Furcorn",3], ["Drumpler",3], ["Maw",3], ["Thumpies",2], ["PomPom",2], ["Congle",2], ["Clamble",2], ["Bowgart",2], ["T-Rox",2], ["Deedge",2], ["Entbrat",2], ["Riff",2], ["Quarrister",2], ["Ffidyll",1], ["Rare 2E Cold Flex",2], ["Rare 3E Cold Flex",1], ["Rare 4E Cold Flex",1]]},
    "Adult Blasoom": {"time": "30 days", "eggs": [["Furcorn",3], ["Shrubb",3], ["Oaktopus",3], ["Dandidoo",3], ["Bowgart",2], ["Clamble",2], ["Pummel",2], ["Reedling",2], ["Spunge",2], ["Thumpies",2], ["Entbrat",2], ["Deedge",2], ["Shellbeat",2], ["Quarrister",2], ["Blabbit",1], ["Viveine",1], ["Rare 2E Plant Flex",2], ["Rare 3E Plant Flex",1], ["Rare 4E Plant Flex",1]]},
    "Adult Syncopite": {"time": "31 days", "eggs": [["Clackula",3], ["Fwog",3], ["Maw",3], ["Oaktopus",3], ["Denchuhs",2], ["Hawlo",2], ["Peckidna",2], ["Thrumble",2], ["Withur",2], ["Uuduk",2], ["Banjaw",2], ["T-Rox",2], ["Plinkajou",2], ["Shellbeat",2], ["Spurrit",1], ["Rare 2E Bone Flex",2], ["Rare 3E Fire Flex",1]]},
    "Adult Vhamp": {"time": "30 days", "eggs": [["Cybop",3], ["Quibble",3], ["Pango",3], ["Drumpler",3], ["T-Rox",2], ["PomPom",2], ["Scups",2], ["Reedling",2], ["Riff",2], ["Reebro",1], ["Jeeode",1], ["Humbug",1], ["Monculus",1], ["Mythical Flex",3], ["Rare 4E Fire Flex",2]]},
    "Adult Galvana": {"time": "31 days", "eggs": [["Kayna",3], ["Glowl",2], ["Flowah",2], ["Stogg",2], ["Phangler",2], ["Boskus",2], ["Barrb",1], ["Floogull",1], ["Whaddle",2], ["Woolabee",1], ["Repatillo",1], ["Rootitoot",1], ["Sooza",1], ["Thrumble",1], ["Ziggurab",1], ["Wynq",1], ["Tring",1], ["Sneyser",1], ["Hoola",1], ["Rare 4E Plant Flex",1], ["Rare 4E Cold Flex",1], ["Rare 4E Air Flex",1], ["Rare 4E Water Flex",1], ["Rare 4E Earth Flex",1]]}
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


def parse_eggs_from_dom_element(elem, egg_url_map: dict, allow_single: bool = False) -> list:
    """Extracts [egg_name, count] from any HTML element containing egg/flex images."""
    pairs = []
    for img in elem.find_all("img"):
        raw_key = urllib.parse.unquote(
            img.get("data-image-name")
            or img.get("data-image-key")
            or img.get("alt")
            or img.get("src")
            or ""
        )
        if "egg" not in raw_key.lower() and "flex" not in raw_key.lower():
            continue
        if any(bad in raw_key.lower() for bad in ["statue", "vessel", "trophy", "costume", "button"]):
            continue

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

        count = None
        # Method A: walk next siblings for "x3" or "×3"
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

        # Method B: check parent container if it wraps a single egg (supports "x2" or leading "2 Rare ... Flex Egg")
        if count is None:
            for parent_tag in ["span", "li", "td", "div"]:
                p = img.find_parent(parent_tag)
                if p and len(p.find_all("img")) == 1:
                    ptxt = p.get_text(" ", strip=True)
                    m = re.search(r"[x×]\s*(\d+)", ptxt, re.I) or re.search(r"^(\d+)\s+", ptxt)
                    if m:
                        count = int(m.group(1))
                        break

        if egg_name and count and 0 < count <= 200:
            pairs.append([egg_name, count])

    if not allow_single and len(pairs) < 2:
        return []
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

        # Collect ALL egg cells in the row (merges 'Required Inventory' + 'Required Flex Eggs' columns if split)
        egg_tds = []
        row_eggs = []
        for td in tds:
            cand = parse_eggs_from_dom_element(td, egg_url_map, allow_single=(category == "adults"))
            if len(cand) >= 1 and (len(cand) >= 2 or egg_tds):
                egg_tds.append(td)
                row_eggs.extend(cand)

        if len(row_eggs) < 2:
            continue

        m_name = ""
        m_img = ""
        for td in tds:
            if td in egg_tds:
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

        combined_html_low = " ".join(td.decode_contents().lower() for td in egg_tds)
        is_rare = m_name.lower().startswith("rare ") or all(e[0].lower().startswith("rare ") for e in row_eggs)
        is_epic = m_name.lower().startswith("epic ") or all(e[0].lower().startswith("epic ") for e in row_eggs)
        has_flex = "flex" in combined_html_low or m_name.lower().startswith("adult ")

        if category in ("wublins", "amber") and (is_rare or is_epic):
            continue
        if category == "celestials" and (has_flex or is_rare or is_epic):
            continue
        if category == "adults" and not has_flex:
            continue

        key_name = re.sub(r"^Adult\s+", "", m_name, flags=re.I).strip()
        if category == "adults":
            key_name = f"Adult {key_name}"

        time_str = "-"
        for td in tds:
            if td in egg_tds:
                continue
            txt = " ".join(td.get_text(" ", strip=True).split())
            if re.match(r"^\d+\s*x\s*\d+$", txt, re.I) or txt == m_name:
                continue
            if re.search(r"\b\d+\s*(d|days|h|hours)\b", txt, re.I) or re.search(
                r"(January|February|March|April|May|June|July|August|September|October|November|December)", txt, re.I
            ):
                if time_str == "-":
                    time_str = txt

        if key_name.lower() not in results:
            results[key_name.lower()] = {
                "name": key_name,
                "img_url": m_img,
                "time": time_str,
                "eggs": row_eggs
            }
            print(f"  [+] Parsed {key_name} from {page_title}: {len(row_eggs)} egg types")

    return results


def scrape_individual_monster(monster_name: str, category: str, egg_url_map: dict) -> dict:
    """Scrapes an individual monster's Wiki page (keeps 'Adult ' prefix for Adult Celestials!)."""
    # FIX #1: Do NOT strip 'Adult ' — each Adult Celestial has its own dedicated Wiki page (e.g. Adult_Scaratar)
    page_target = monster_name
    print(f"  -> Scraping individual page: {page_target}...")
    parsed = parse_page_api(page_target)
    soup = BeautifulSoup(parsed["html"], "html.parser")

    # 1. Portrait image from portable infobox
    m_img = ""
    pi_img = soup.select_one(".portable-infobox .pi-image img, .infobox img")
    if pi_img:
        m_img = clean_wikia_url(pi_img.get("data-src") or pi_img.get("src") or "")

    # 2. Extract eggs directly from Portable Infobox 'Required Inventory' + 'Required Flex Eggs' rows first
    infobox_eggs = []
    seen_infobox = set()
    for item in soup.select(".portable-infobox .pi-data"):
        header_el = item.select_one(".pi-data-label")
        val_el = item.select_one(".pi-data-value")
        if not val_el:
            continue
        header_txt = (header_el.get_text(" ", strip=True) if header_el else "").lower()
        if "inventory" in header_txt or "flex" in header_txt:
            pairs = parse_eggs_from_dom_element(val_el, egg_url_map, allow_single=True)
            for e_n, c in pairs:
                if e_n not in seen_infobox:
                    seen_infobox.add(e_n)
                    infobox_eggs.append([e_n, c])

            # Also check for text-formatted Flex Eggs (e.g. "2 Rare Faerie Double Flex Egg")
            if "flex" in header_txt and not pairs:
                for line in val_el.stripped_strings:
                    m_fl = re.match(r"^(?:[x×]?\s*(\d+)\s+)(.+?Flex\s*Egg.*)$", line, re.I)
                    if m_fl:
                        cnt = int(m_fl.group(1))
                        f_name = m_fl.group(2).strip()
                        if f_name not in seen_infobox:
                            seen_infobox.add(f_name)
                            infobox_eggs.append([f_name, cnt])

    # 3. If Portable Infobox didn't yield the list, scan page tables/containers without the broken has_flex block
    eggs = infobox_eggs
    if len(eggs) < 2:
        for block in soup.select(".pi-data-value, table, td"):
            pairs = parse_eggs_from_dom_element(block, egg_url_map, allow_single=False)
            if len(pairs) >= 2:
                dedup = []
                seen = set()
                for e_n, c in pairs:
                    if e_n not in seen:
                        seen.add(e_n)
                        dedup.append([e_n, c])
                is_rare = all(e[0].lower().startswith("rare ") for e in dedup)
                is_epic = all(e[0].lower().startswith("epic ") for e in dedup)
                if not is_rare and not is_epic:
                    eggs = dedup
                    break

    # 4. Clean Time Limit extraction
    time_str = "-"
    for item in soup.select(".pi-data"):
        raw_txt = item.get_text(" ", strip=True)
        m_time = re.search(r"Time\s*limit\s*:\s*([0-9]+\s*(?:days?|hours?|d|h)|No\s*limit)", raw_txt, re.I)
        if m_time:
            time_str = m_time.group(1).strip()
            break

    # Ensure Adult Celestials always include their Required Flex Eggs at the end of the recipe
    if category == "adults" and monster_name in ADULT_FALLBACK_RECIPES:
        fb = ADULT_FALLBACK_RECIPES[monster_name]
        if len(eggs) < 2:
            eggs = fb["eggs"]
        elif not any("flex" in e[0].lower() for e in eggs):
            flex_only = [pair for pair in fb["eggs"] if "flex" in pair[0].lower()]
            eggs.extend(flex_only)
        if time_str == "-":
            time_str = fb["time"]

    print(f"     Found {len(eggs)} egg types for {monster_name} (Time: {time_str})")
    return {
        "name": monster_name,
        "img_url": m_img,
        "time": time_str,
        "eggs": eggs
    }


def get_flex_fallback_monster(egg_name: str) -> str:
    if "Mythical" in egg_name: return "G'joob"
    if "Faerie" in egg_name: return "Bridg-it"
    if "Light" in egg_name: return "Gob"
    if "Psychic" in egg_name: return "Periscorp"
    if "Bone" in egg_name: return "Withur"
    if "Fire" in egg_name: return "Ziggurab"
    if "Plant" in egg_name: return "Entbrat"
    if "Cold" in egg_name: return "Deedge"
    if "Air" in egg_name: return "Riff"
    if "Water" in egg_name: return "Shellbeat"
    if "Earth" in egg_name: return "Quarrister"
    return "Kayna"


def main():
    egg_url_map = {}

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

    for cat in ["wublins", "celestials", "adults", "amber"]:
        ov = overview_by_cat[cat]
        for name in ROSTERS[cat]:
            entry = ov.get(name.lower())
            if not entry or len(entry.get("eggs", [])) < 2:
                entry = scrape_individual_monster(name, cat, egg_url_map)

            m_id = f"{cat}-{safe_filename(name).lower()}" if cat in ("adults", "amber") else safe_filename(name).lower()
            if cat == "wublins" and name.lower() == "bona-petite":
                m_id = "bona-petite"

            disp_name = f"{name} Vessel" if cat == "amber" else name
            final_db[cat].append({
                "id": m_id,
                "base_name": name,
                "name": disp_name,
                "img_url": entry.get("img_url", ""),
                "time": entry.get("time", "-"),
                "eggs": entry.get("eggs", [])
            })

    # Resolve any missing monster or egg image URLs via MediaWiki API
    files_to_resolve = []
    for cat in final_db:
        for m in final_db[cat]:
            if not m["img_url"]:
                files_to_resolve.append(f"{m['base_name'].replace(' ', '_')}.png")
            for e_name, _ in m["eggs"]:
                if e_name not in egg_url_map:
                    cl = get_flex_fallback_monster(e_name).replace(" ", "_") if "flex" in e_name.lower() else e_name.replace(" ", "_")
                    files_to_resolve.extend([f"{cl}-egg.png", f"{cl}_Egg.png", f"{cl}-Egg.png"])

    resolved_files = resolve_wiki_files(files_to_resolve)

    for cat in final_db:
        for m in final_db[cat]:
            fn = f"{m['base_name'].replace(' ', '_')}.png"
            if not m["img_url"] and resolved_files.get(fn):
                m["img_url"] = resolved_files[fn]
            for e_name, _ in m["eggs"]:
                if e_name not in egg_url_map:
                    cl = get_flex_fallback_monster(e_name).replace(" ", "_") if "flex" in e_name.lower() else e_name.replace(" ", "_")
                    for cand in [f"{cl}-egg.png", f"{cl}_Egg.png", f"{cl}-Egg.png"]:
                        if resolved_files.get(cand):
                            egg_url_map[e_name] = resolved_files[cand]
                            break

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

    print(f"\nSaved msm_recipes.json & msm_recipes.js with {sum(len(v) for v in final_db.values())} monsters!")


if __name__ == "__main__":
    main()