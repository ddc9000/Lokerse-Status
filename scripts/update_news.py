#!/usr/bin/env python3
"""Vlaamse Status data-updater.

Haalt nieuws van publieke RSS-feeds, weer van Open-Meteo en verkeersmeldingen
van het Verkeerscentrum (DATEX II). Geen betaalde API-sleutel nodig.
"""

import html
import os
import re
import sys
from datetime import datetime, timezone

import feedparser
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.regions import (  # noqa: E402
    LOCAL_FOCUS,
    WEATHER_LOCATIONS,
    PlaceMatcher,
    activity_score,
    classify_item,
    format_dutch,
    is_sport_text,
    municipalities,
    parse_datetime,
    region_scores,
    weather_description,
    write_regions_file,
)
from scripts.traffic import parse_datex  # noqa: E402

DATA_DIR = os.path.join(ROOT, "data")
NEWS_FILE = os.path.join(DATA_DIR, "news.json")
WEATHER_FILE = os.path.join(DATA_DIR, "weather.json")
HISTORY_FILE = os.path.join(DATA_DIR, "activity_history.json")
TRAFFIC_FILE = os.path.join(DATA_DIR, "traffic.json")
REGIONS_FILE = os.path.join(DATA_DIR, "regions.json")

USER_AGENT = "VlaamseStatus/3.0 (+https://github.com/ddc9000/Lokerse-Status)"
HEADERS = {"User-Agent": USER_AGENT}
DATEX_URL = "https://www.verkeerscentrum.be/uitwisseling/datex2v3full"
MAX_TOTAL = 64
LOCAL_KEEP = 12
PER_PROVINCE = 6
PROVINCE_ORDER = [
    "west-vlaanderen",
    "oost-vlaanderen",
    "antwerpen",
    "limburg",
    "vlaams-brabant",
    "brussel",
    "vlaanderen",
]

# Eerst lokale en officiële feeds, zodat die bij een dubbel bericht de bron blijven.
RSS_SOURCES = [
    {
        "name": "Gemeente Laarne",
        "url": "https://laarne.be/nieuws/rss",
        "province": "oost-vlaanderen",
        "places": ["Laarne"],
        "limit": 8,
    },
    {
        "name": "Stad Sint-Niklaas",
        "url": "https://www.sint-niklaas.be/rss",
        "province": "oost-vlaanderen",
        "places": ["Sint-Niklaas"],
        "limit": 4,
    },
    {
        "name": "Stad Mechelen",
        "url": "https://www.mechelen.be/rss",
        "province": "antwerpen",
        "places": ["Mechelen"],
        "limit": 4,
    },
    {
        "name": "Nieuwsblad Lokeren",
        "url": "https://www.nieuwsblad.be/regio/oost-vlaanderen/waasland/lokeren/rss",
        "province": "oost-vlaanderen",
        "places": ["Lokeren"],
        "limit": 8,
    },
    {
        "name": "HLN Lokeren",
        "url": "https://www.hln.be/regio/lokeren/rss.xml",
        "province": "oost-vlaanderen",
        "places": ["Lokeren"],
        "limit": 6,
    },
    {
        "name": "Google Nieuws",
        "url": "https://news.google.com/rss/search?q=%28Lokeren+OR+Lochristi+OR+Destelbergen+OR+Laarne+OR+Beervelde+OR+Kalken%29+when%3A14d&hl=nl&gl=BE&ceid=BE:nl",
        "province": "oost-vlaanderen",
        "places": [],
        "limit": 8,
        "scan": 40,
        "require_local": True,
    },
    {
        "name": "Nieuwsblad West-Vlaanderen",
        "url": "https://www.nieuwsblad.be/regio/west-vlaanderen/rss",
        "province": "west-vlaanderen",
        "places": [],
        "limit": 6,
    },
    {
        "name": "Nieuwsblad Oost-Vlaanderen",
        "url": "https://www.nieuwsblad.be/regio/oost-vlaanderen/rss",
        "province": "oost-vlaanderen",
        "places": [],
        "limit": 6,
    },
    {
        "name": "Nieuwsblad Antwerpen",
        "url": "https://www.nieuwsblad.be/regio/antwerpen/rss",
        "province": "antwerpen",
        "places": [],
        "limit": 6,
    },
    {
        "name": "Nieuwsblad Limburg",
        "url": "https://www.nieuwsblad.be/regio/limburg/rss",
        "province": "limburg",
        "places": [],
        "limit": 6,
    },
    {
        "name": "Nieuwsblad Vlaams-Brabant",
        "url": "https://www.nieuwsblad.be/regio/vlaams-brabant/rss",
        "province": "vlaams-brabant",
        "places": [],
        "limit": 6,
    },
    {
        "name": "Nieuwsblad Brussel",
        "url": "https://www.nieuwsblad.be/regio/brussel/rss",
        "province": "brussel",
        "places": [],
        "limit": 5,
    },
    {
        "name": "KW",
        "url": "https://kw.be/feed/",
        "province": "west-vlaanderen",
        "places": [],
        "limit": 5,
    },
    {
        "name": "GVA",
        "url": "https://www.gva.be/regio/rss",
        "province": "antwerpen",
        "places": [],
        "limit": 5,
    },
    {
        "name": "HBVL",
        "url": "https://www.hbvl.be/regio/rss",
        "province": "limburg",
        "places": [],
        "limit": 5,
    },
    {
        "name": "TVL",
        "url": "https://www.tvl.be/rss",
        "province": "limburg",
        "places": [],
        "limit": 4,
    },
    {
        "name": "ROBtv",
        "url": "https://www.robtv.be/rss",
        "province": "vlaams-brabant",
        "places": [],
        "limit": 4,
    },
    {
        "name": "ATV",
        "url": "https://www.atv.be/rss",
        "province": "antwerpen",
        "places": [],
        "limit": 4,
    },
    {
        "name": "BRUZZ",
        "url": "https://www.bruzz.be/rss.xml",
        "province": "brussel",
        "places": [],
        "limit": 5,
    },
    {
        "name": "HLN Regio",
        "url": "https://www.hln.be/regio/rss.xml",
        "province": "vlaanderen",
        "places": [],
        "limit": 5,
    },
    {
        "name": "HLN Antwerpen",
        "url": "https://www.hln.be/regio/antwerpen/rss.xml",
        "province": "antwerpen",
        "places": [],
        "limit": 4,
    },
    {
        "name": "HLN Brussel",
        "url": "https://www.hln.be/regio/brussel/rss.xml",
        "province": "brussel",
        "places": [],
        "limit": 4,
    },
    {
        "name": "VRT NWS",
        "url": "https://www.vrt.be/vrtnws/nl.rss.headlines.xml",
        "province": "vlaanderen",
        "places": [],
        "limit": 8,
    },
    {
        "name": "HLN",
        "url": "https://www.hln.be/home/rss.xml",
        "province": "vlaanderen",
        "places": [],
        "limit": 5,
    },
    {
        "name": "De Standaard",
        "url": "https://www.standaard.be/rss",
        "province": "vlaanderen",
        "places": [],
        "limit": 5,
    },
]

TAG_RE = re.compile(r"<[^>]+>")
TITLE_SOURCE_RE = re.compile(r"\s+-\s+[^-]+$")


def strip_html(value):
    text = TAG_RE.sub(" ", value or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def title_key(title):
    text = strip_html(title).lower()
    text = TITLE_SOURCE_RE.sub("", text)
    text = re.sub(r"[^0-9a-zà-ÿ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:90]


def load_json(path, default):
    if os.path.exists(path):
        try:
            import json

            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError):
            pass
    return default


def save_json(path, data):
    import json

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def fetch_rss(source, matcher):
    try:
        response = requests.get(source["url"], timeout=15, headers=HEADERS)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as exc:
        print(f"Fout bij ophalen {source['name']}: {exc}")
        return []

    items = []
    local = set(LOCAL_FOCUS)
    limit = source.get("limit", 6)
    scan = source.get("scan", limit)
    for entry in feed.entries:
        title = strip_html(entry.get("title") or "")
        if not title:
            continue
        description = strip_html(entry.get("summary") or entry.get("description") or "")[:220]
        link = entry.get("link") or "#"
        published_raw = entry.get("published") or entry.get("updated") or ""
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        published_dt = None
        if parsed:
            try:
                published_dt = datetime(*parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                published_dt = None
        if published_dt is None:
            published_dt = parse_datetime(published_raw)
        classified = classify_item(
            title,
            description,
            source.get("province") or "vlaanderen",
            source.get("places") or [],
            matcher,
        )
        if source.get("require_local") and not any(place in local for place in classified["places"]):
            continue
        iso = ""
        if published_dt is not None:
            if published_dt.tzinfo is None:
                iso = published_dt.isoformat()
            else:
                iso = published_dt.isoformat()
        items.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "source": source["name"],
                "province": classified["province"],
                "provinces": classified["provinces"],
                "places": classified["places"],
                "pubDate": format_dutch(published_dt) if published_dt else "",
                "published": iso,
            }
        )
        if len(items) >= scan:
            break
    if len(items) > limit:
        items = _prefer_local_mix(items, limit) if source.get("require_local") else items[:limit]
    return items


def _is_local(item):
    return any(place in LOCAL_FOCUS for place in item.get("places") or [])


def _sport_item(item):
    return is_sport_text(item.get("title") or "", item.get("description") or "")


def _prefer_local_mix(items, limit):
    """Zorg dat Lokeren, Destelbergen, Laarne en Lochristi niet wegvallen achter sportoverzichten."""
    ordered = sorted(
        items,
        key=lambda item: (0 if _sport_item(item) else 1, item.get("published") or ""),
        reverse=True,
    )
    picked = []
    seen = set()
    for name in LOCAL_FOCUS:
        for item in ordered:
            if name in (item.get("places") or []) and id(item) not in seen:
                picked.append(item)
                seen.add(id(item))
                break
        if len(picked) >= limit:
            return picked[:limit]
    for item in ordered:
        if len(picked) >= limit:
            break
        if id(item) not in seen:
            picked.append(item)
            seen.add(id(item))
    return picked[:limit]


def _diversify(items, limit):
    """Neem per bron om de beurt, nieuwste eerst, zodat één feed de emmer niet vult."""
    pools = {}
    for item in sorted(items, key=lambda entry: entry.get("published") or "", reverse=True):
        pools.setdefault(item.get("source") or "", []).append(item)
    picked = []
    names = list(pools)
    guard = 0
    while len(picked) < limit and names:
        progressed = False
        for name in names:
            pool = pools.get(name) or []
            if not pool:
                continue
            picked.append(pool.pop(0))
            progressed = True
            if len(picked) >= limit:
                break
        if not progressed:
            break
        guard += 1
        if guard > limit:
            break
    return picked


def _select_news(collected):
    local = [item for item in collected if _is_local(item)]
    picked = _prefer_local_mix(local, LOCAL_KEEP)
    chosen = {id(item) for item in picked}
    buckets = {province: [] for province in PROVINCE_ORDER}
    for item in collected:
        if id(item) in chosen:
            continue
        buckets.setdefault(item.get("province") or "vlaanderen", []).append(item)
    for province in PROVINCE_ORDER:
        picked.extend(_diversify(buckets.get(province) or [], PER_PROVINCE))
    if len(picked) > MAX_TOTAL:
        # Lokale berichten blijven vooraan staan; de rest wordt op datum begrensd.
        head = [item for item in picked if _is_local(item)][:LOCAL_KEEP]
        tail = [item for item in picked if item not in head]
        tail.sort(key=lambda item: item.get("published") or "", reverse=True)
        picked = head + tail[: MAX_TOTAL - len(head)]
    picked.sort(key=lambda item: item.get("published") or "", reverse=True)
    return picked[:MAX_TOTAL]


def collect_news(matcher):
    collected = []
    seen = set()
    report = []
    for source in RSS_SOURCES:
        items = fetch_rss(source, matcher)
        kept = 0
        for item in items:
            key = title_key(item["title"]) or item["link"]
            if key in seen:
                continue
            seen.add(key)
            collected.append(item)
            kept += 1
        report.append({"name": source["name"], "province": source.get("province"), "count": kept})
        print(f"  {source['name']}: {kept}")
    return _select_news(collected), report


def fetch_weather():
    lats = ",".join(str(loc["lat"]) for loc in WEATHER_LOCATIONS)
    lons = ",".join(str(loc["lon"]) for loc in WEATHER_LOCATIONS)
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={lats}&longitude={lons}&current_weather=true&"
        "daily=temperature_2m_max,temperature_2m_min,weathercode&"
        "timezone=Europe%2FBrussels&forecast_days=1"
    )
    response = requests.get(url, timeout=20, headers=HEADERS)
    response.raise_for_status()
    payload = response.json()
    blocks = payload if isinstance(payload, list) else [payload]
    locations = {}
    numeric = []
    for loc, block in zip(WEATHER_LOCATIONS, blocks):
        current = block.get("current_weather") or {}
        daily = block.get("daily") or {}
        code = current.get("weathercode", 0)
        entry = {
            "id": loc["id"],
            "name": loc["name"],
            "temp": round(current.get("temperature", 0)),
            "windspeed": current.get("windspeed", 0),
            "weathercode": code,
            "description": weather_description(code),
            "max": round((daily.get("temperature_2m_max") or [0])[0]),
            "min": round((daily.get("temperature_2m_min") or [0])[0]),
        }
        locations[loc["id"]] = entry
        if loc["id"] not in {"lokerse-streek", "brussel"}:
            numeric.append(entry)
    if numeric:
        descriptions = {}
        for entry in numeric:
            descriptions[entry["description"]] = descriptions.get(entry["description"], 0) + 1
        common = max(descriptions, key=descriptions.get)
        locations["vlaanderen"] = {
            "id": "vlaanderen",
            "name": "Vlaanderen",
            "temp": round(sum(entry["temp"] for entry in numeric) / len(numeric)),
            "windspeed": round(sum(float(entry["windspeed"] or 0) for entry in numeric) / len(numeric), 1),
            "weathercode": 0,
            "description": common,
            "max": round(sum(entry["max"] for entry in numeric) / len(numeric)),
            "min": round(sum(entry["min"] for entry in numeric) / len(numeric)),
        }
    return {
        "updated": datetime.now().isoformat(),
        "source": "Open-Meteo",
        "locations": locations,
    }


def fetch_traffic(places):
    response = requests.get(DATEX_URL, timeout=30, headers=HEADERS)
    response.raise_for_status()
    items = parse_datex(response.content, places)
    warnings = sum(1 for item in items if item.get("severity") == "warning")
    return {
        "updated": datetime.now().isoformat(),
        "source": "Verkeerscentrum Vlaanderen (DATEX II)",
        "license": "CC BY",
        "count": len(items),
        "warnings": warnings,
        "items": items,
    }


def update_activity_history(today_score):
    from datetime import date

    history = load_json(HISTORY_FILE, [])
    today_str = date.today().isoformat()
    history = [row for row in history if row.get("date") != today_str]
    history.append(
        {
            "date": today_str,
            "score": today_score,
            "label": date.today().strftime("%d %b"),
        }
    )
    history = history[-14:]
    save_json(HISTORY_FILE, history)
    return history


def main():
    print("=== Vlaamse Status data-update gestart ===")
    write_regions_file(REGIONS_FILE)
    matcher = PlaceMatcher()

    news, report = collect_news(matcher)
    if news:
        score = activity_score(news)
        save_json(
            NEWS_FILE,
            {
                "updated": datetime.now().isoformat(),
                "items": news,
                "count": len(news),
                "scores": region_scores(news),
                "sources": report,
            },
        )
        update_activity_history(score)
        print(f"✓ {len(news)} nieuwsberichten")
        print(f"✓ Activiteitsscore Vlaanderen: {score}")
    else:
        print("Geen nieuws opgehaald; bestaand nieuwsbestand blijft behouden.")

    try:
        weather = fetch_weather()
        save_json(WEATHER_FILE, weather)
        overview = weather["locations"].get("vlaanderen", {})
        print(f"✓ Weer Vlaanderen: {overview.get('temp')}°C - {overview.get('description')}")
    except Exception as exc:
        print(f"Weer ophalen mislukt, vorige data blijft behouden: {exc}")

    try:
        traffic = fetch_traffic(municipalities())
        save_json(TRAFFIC_FILE, traffic)
        print(f"✓ Verkeer: {traffic['count']} meldingen, {traffic['warnings']} met hinder")
    except Exception as exc:
        print(f"Verkeer ophalen mislukt, vorige data blijft behouden: {exc}")

    print("Data bijgewerkt.")


if __name__ == "__main__":
    main()
