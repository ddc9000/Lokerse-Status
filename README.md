# Lokerse Status

**Real-time nieuws- en statusdashboard voor Lokeren en de regio** (Destelbergen, Laarne, Lochristi, Oost-Vlaanderen).

Geïnspireerd op moderne OSINT-dashboards zoals pizzint.watch, maar volledig lokaal, nuttig en community-focused.

## 🚀 Live Demo

https://ddc9000.github.io/Lokerse-Status/  (activeer GitHub Pages in repo settings als het nog niet live is)

## Wat is Lokerse Status?

Een modern, minimalistisch dashboard dat:
- Lokale nieuwsberichten aggregeert
- Belangrijke evenementen en agenda toont
- Een "Lokerse Activiteit Index" geeft (fun proxy voor hoe druk het is in de regio)
- Praktische info (weer, verkeer, alerts)
- Snelle links naar officiële bronnen

Doel: Één centrale plek voor iedereen die wil weten "wat er speelt" in Lokeren en de directe omgeving, zonder 10 tabs open te hebben.

## Techniek (v1)

- Volledig statisch (HTML + Tailwind CSS via CDN + vanilla JavaScript)
- Geen build step nodig
- Werkt direct op GitHub Pages
- Klaar voor uitbreiding met GitHub Actions + echte data scraping (RSS + officiële sites)

## Roadmap

- [ ] GitHub Actions workflow voor automatische data-updates (elke 30-60 min)
- [ ] Echte RSS feeds van lokeren.be, laarne.be, lochristi.be, Nieuwsblad, etc.
- [ ] Weer API integratie (KMI)
- [ ] Event calendar parsing
- [ ] "Niets Gebeurt Vandaag" meter met historische data
- [ ] Mobile PWA
- [ ] Bijdragen van locals (PRs welkom!)

## Hoe bijdragen?

1. Fork de repo
2. Maak een branch
3. Voeg nieuwe nieuwsbronnen of UI-verbeteringen toe
4. Open een Pull Request

Of open een Issue met ideeën voor lokale data-bronnen.

## Licentie

MIT voor code. Data van officiële bronnen (respecteer hun voorwaarden).

Gebouwd met ❤️ voor de Lokerse regio door ddc9000.

---

*Demo data in v1. Echte live data volgt snel.*