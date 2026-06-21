# Lokerse Status

**Real-time nieuws- en statusdashboard voor Lokeren en de regio** (Destelbergen, Laarne, Lochristi, Oost-Vlaanderen).

Met liefde gemaakt voor de mensen, paarden, tuinen, poelen en alle wezens van de Lokerse streek.

## Live
https://ddc9000.github.io/Lokerse-Status/

## v2.0 Highlights
- Automatische data pipeline via GitHub Actions (elke 30 min)
- Echte RSS feeds (start met Laarne)
- Weer via Open-Meteo
- Activiteit Index + 14-dagen geschiedenis grafiek
- PWA-ondersteuning (installeerbaar op telefoon)
- Volledig data-driven frontend

## Hoe werkt de data pipeline?
`.github/workflows/update-data.yml` draait elke 30 minuten een Python script dat:
1. RSS feeds ophaalt
2. Weer ophaalt
3. Activiteitsscore berekent
4. `data/*.json` bestanden updatet
5. Commit & push

Je kunt de workflow ook handmatig triggeren via de Actions tab.

## Lokale bronnen toevoegen
Bewerk `scripts/update_news.py` en voeg extra entries toe aan `RSS_SOURCES`.

## Met dank
Gebouwd met zorg voor de buurt door ddc9000.