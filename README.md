# Vlaamse Status

**Real-time nieuws- en statusdashboard voor heel Vlaanderen** — West-Vlaanderen, Oost-Vlaanderen, Antwerpen, Limburg en Vlaams-Brabant, plus Brussel waar dat zinvol is.

De Lokerse streek (Lokeren, Destelbergen, Laarne, Lochristi) blijft één klik verwijderd. Met liefde gemaakt voor de mensen, paarden, tuinen, poelen en alle wezens, van de Lokerse streek tot de kust, de Kempen en Limburg.

## Live

https://ddc9000.github.io/Lokerse-Status/

De site gebruikt relatieve paden (`./`, `data/…`, `manifest.json`). Ze werkt daardoor op GitHub Pages los van de reponaam. Na een hernoeming van de repository wijzigt enkel de URL hierboven.

## Wat je ziet

- Nieuws uit Vlaamse en regionale feeds, filterbaar per provincie, per gemeente en via **Lokerse streek**
- Kaart van Vlaanderen (OpenStreetMap via CARTO), gecentreerd op het gewest
- Weer per provincie via Open-Meteo, met Lokeren als station voor de Lokerse streek
- Verkeersmeldingen van het Vlaams Verkeerscentrum (DATEX II)
- Vlaamse rustindex en de bestaande 14-dagen grafiek
- PWA, installeerbaar op een telefoon

## Bronnen

Alles hieronder is publiek en werkt zonder API-sleutel.

| Bron | Dekking |
| --- | --- |
| [VRT NWS](https://www.vrt.be/vrtnws/nl.rss.headlines.xml) | Vlaanderen |
| [HLN](https://www.hln.be/home/rss.xml) en [HLN Regio](https://www.hln.be/regio/rss.xml) | Vlaanderen, plus Antwerpen, Brussel en Lokeren |
| [De Standaard](https://www.standaard.be/rss) | Vlaanderen |
| [Nieuwsblad](https://www.nieuwsblad.be/) per provincie | Vijf provincies, Brussel en Lokeren |
| [KW.be](https://kw.be/feed/) | West-Vlaanderen |
| [Gazet van Antwerpen](https://www.gva.be/regio/rss) en [ATV](https://www.atv.be/rss) | Antwerpen |
| [Het Belang van Limburg](https://www.hbvl.be/regio/rss) en [TVL](https://www.tvl.be/rss) | Limburg |
| [ROBtv](https://www.robtv.be/rss) | Vlaams-Brabant |
| [BRUZZ](https://www.bruzz.be/rss.xml) | Brussel |
| [Gemeente Laarne](https://laarne.be/nieuws/rss), [Sint-Niklaas](https://www.sint-niklaas.be/rss), [Mechelen](https://www.mechelen.be/rss) | Officieel gemeente- of stadsnieuws |
| Google Nieuws (publieke RSS-zoekfeed) | Lokerse streek, enkel berichten waarin een plaatsnaam voorkomt |
| [Open-Meteo](https://open-meteo.com/) | Weer, geen sleutel |
| [Verkeerscentrum Vlaanderen](https://www.verkeerscentrum.be/uitwisseling/datex2v3full) | DATEX II, licentie CC BY, geen sleutel |

Lokeren, Destelbergen en Lochristi publiceren momenteel geen bruikbare eigen RSS-feed (de feeds van Lokeren en Destelbergen zijn leeg). Hun nieuws komt via Nieuwsblad, HLN en de Google-zoekfeed. De feed van Laarne blijft rechtstreeks aangesloten, zoals voorheen.

Er is geen bron met een verplichte API-sleutel. Een betaalde verkeers-API is niet nodig: de DATEX II-feed van het Verkeerscentrum dekt het Vlaamse snelwegennet.

## Hoe werkt de data pipeline?

`.github/workflows/update-data.yml` draait elke 30 minuten `scripts/update_news.py`. Dat script:

1. haalt de RSS-feeds op en duidt provincie en gemeente aan
2. haalt het weer op voor de vijf provincies, Brussel en Lokeren
3. haalt verkeersmeldingen op en zet Lambert 72 om naar lengte- en breedtegraad
4. berekent de activiteitsscore en werkt de 14-dagen grafiek bij
5. schrijft `data/*.json` en commit die bestanden

Je kunt de workflow ook handmatig starten via het tabblad Actions.

Lokaal:

```bash
pip install -r requirements.txt
python scripts/update_news.py
python -m unittest tests.test_regions
```

## Een bron toevoegen

Zet een extra object in `RSS_SOURCES` in `scripts/update_news.py`:

```python
{
    "name": "Voorbeeld",
    "url": "https://example.be/rss",
    "province": "oost-vlaanderen",  # of vlaanderen, brussel, …
    "places": ["Lokeren"],          # leeg laten als de feed niet aan één gemeente hangt
    "limit": 5,
}
```

Gemeenten en aliassen (deelgemeenten zoals Kalken en Beervelde) staan in `scripts/regions.py`.

## Als de repository hernoemd wordt naar Vlaamse-Status

De code hoeft daarvoor niet aangepast te worden.

- GitHub Pages verhuist van `https://ddc9000.github.io/Lokerse-Status/` naar `https://ddc9000.github.io/Vlaamse-Status/`. Pas de live-link in deze README aan.
- De link naar de repository in de footer (`https://github.com/ddc9000/Lokerse-Status`) mag mee wijzigen. GitHub leidt de oude repo-URL doorgaans om.
- Manifest, service worker en datafetches zijn relatief (`./`, `data/news.json`) en bevatten de reponaam niet.
- Wie de PWA al geïnstalleerd had, installeert best opnieuw. De cache heet nu `vlaamse-status-v3`.

## Met dank

Gebouwd met zorg door ddc9000. Weer: Open-Meteo. Verkeer: Verkeerscentrum Vlaanderen (CC BY). Kaart: OpenStreetMap-bijdragers en CARTO.
