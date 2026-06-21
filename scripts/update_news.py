#!/usr/bin/env python3
"""
Lokerse Status Data Updater
Haalt nieuws van lokale bronnen, weer van Open-Meteo en berekent activiteitsscore.
Met liefde voor Lokeren, Destelbergen, Laarne, Lochristi en alle wezens daar.
"""

import feedparser
import json
import requests
from datetime import datetime, timedelta, date
import os
import sys

# === CONFIG ===
DATA_DIR = "data"
NEWS_FILE = os.path.join(DATA_DIR, "news.json")
WEATHER_FILE = os.path.join(DATA_DIR, "weather.json")
HISTORY_FILE = os.path.join(DATA_DIR, "activity_history.json")

# Coördinaten Lokeren (ongeveer)
LAT = 51.103
LON = 3.993

# RSS bronnen (uitbreidbaar)
RSS_SOURCES = [
    {
        "name": "Laarne",
        "url": "https://laarne.be/nieuws/rss",
        "icon": "laarne"
    },
    # Lokeren en Lochristi hebben momenteel geen publieke RSS.
    # We houden ze als placeholder voor toekomstige uitbreiding of scraping.
    # Je kunt hier later extra bronnen toevoegen.
]

MAX_NEWS_ITEMS = 12


def fetch_rss(source):
    """Haalt en parsed een RSS feed veilig."""
    try:
        feed = feedparser.parse(source["url"])
        items = []
        for entry in feed.entries[:MAX_NEWS_ITEMS]:
            item = {
                "title": entry.get("title", "Geen titel").strip(),
                "link": entry.get("link", "#"),
                "description": entry.get("summary", entry.get("description", ""))[:220].strip(),
                "source": source["name"],
                "pubDate": entry.get("published", entry.get("updated", datetime.now().isoformat())),
            }
            items.append(item)
        return items
    except Exception as e:
        print(f"Fout bij ophalen {source['name']}: {e}")
        return []


def get_weather():
    """Haalt actueel weer op via Open-Meteo (gratis, geen key nodig)."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={LAT}&longitude={LON}&"
            f"current_weather=true&"
            f"daily=temperature_2m_max,temperature_2m_min,weathercode&"
            f"timezone=Europe/Brussels"
        )
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()

        current = data.get("current_weather", {})
        daily = data.get("daily", {})

        weather = {
            "temp": round(current.get("temperature", 18)),
            "windspeed": current.get("windspeed", 0),
            "weathercode": current.get("weathercode", 0),
            "description": get_weather_description(current.get("weathercode", 0)),
            "max": round(daily.get("temperature_2m_max", [22])[0]) if daily.get("temperature_2m_max") else 22,
            "min": round(daily.get("temperature_2m_min", [12])[0]) if daily.get("temperature_2m_min") else 12,
            "updated": datetime.now().isoformat(),
        }
        return weather
    except Exception as e:
        print(f"Weer ophalen mislukt: {e}")
        return {
            "temp": 19, "max": 22, "min": 12,
            "description": "Licht bewolkt",
            "windspeed": 8,
            "updated": datetime.now().isoformat()
        }


def get_weather_description(code):
    codes = {
        0: "Helder", 1: "Overwegend helder", 2: "Gedeeltelijk bewolkt", 3: "Bewolkt",
        45: "Mist", 48: "Mist", 51: "Lichte motregen", 53: "Motregen",
        61: "Lichte regen", 63: "Regen", 65: "Zware regen",
        71: "Lichte sneeuw", 80: "Lichte buien", 95: "Onweer"
    }
    return codes.get(code, "Licht bewolkt")


def calculate_activity_score(news_count, events_count=4):
    """Simpele maar eerlijke activiteitsscore (0-100)."""
    score = min(95, (news_count * 6) + (events_count * 8) + 15)
    return max(15, int(score))


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_activity_history(today_score):
    """Houdt laatste 14 dagen bij voor de grafiek."""
    history = load_json(HISTORY_FILE, [])
    today_str = date.today().isoformat()

    # Verwijder eventuele dubbele entry van vandaag
    history = [h for h in history if h.get("date") != today_str]

    history.append({
        "date": today_str,
        "score": today_score,
        "label": date.today().strftime("%d %b")
    })

    # Houd alleen laatste 14 dagen
    history = history[-14:]
    save_json(HISTORY_FILE, history)
    return history


def main():
    print("=== Lokerse Status Data Update gestart ===")

    # 1. Nieuws ophalen
    all_news = []
    for source in RSS_SOURCES:
        items = fetch_rss(source)
        all_news.extend(items)

    # Sorteer op datum (nieuwste eerst) en beperk
    all_news.sort(key=lambda x: x.get("pubDate", ""), reverse=True)
    all_news = all_news[:MAX_NEWS_ITEMS]

    # 2. Weer ophalen
    weather = get_weather()

    # 3. Activiteitsscore berekenen
    activity_score = calculate_activity_score(len(all_news))

    # 4. Geschiedenis updaten
    history = update_activity_history(activity_score)

    # 5. Opslaan
    save_json(NEWS_FILE, {
        "updated": datetime.now().isoformat(),
        "items": all_news,
        "count": len(all_news)
    })

    save_json(WEATHER_FILE, weather)

    print(f"\u2713 {len(all_news)} nieuwsberichten opgehaald")
    print(f"\u2713 Weer: {weather['temp']}°C - {weather['description']}")
    print(f"\u2713 Activiteitsscore: {activity_score}")
    print("Data succesvol bijgewerkt.")

if __name__ == "__main__":
    main()
