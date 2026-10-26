"""Regio's, plaatsherkenning en activiteitsscore voor Vlaamse Status.

Dekking: de vijf Vlaamse provincies plus Brussel, met de Lokerse streek
(Lokeren, Destelbergen, Laarne, Lochristi) als lokale focus.
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

PROVINCES = [
    {
        "id": "west-vlaanderen",
        "name": "West-Vlaanderen",
        "lat": 51.05,
        "lon": 3.05,
        "zoom": 9,
    },
    {
        "id": "oost-vlaanderen",
        "name": "Oost-Vlaanderen",
        "lat": 51.02,
        "lon": 3.90,
        "zoom": 9,
    },
    {
        "id": "antwerpen",
        "name": "Antwerpen",
        "lat": 51.25,
        "lon": 4.70,
        "zoom": 9,
    },
    {
        "id": "limburg",
        "name": "Limburg",
        "lat": 50.95,
        "lon": 5.45,
        "zoom": 9,
    },
    {
        "id": "vlaams-brabant",
        "name": "Vlaams-Brabant",
        "lat": 50.88,
        "lon": 4.55,
        "zoom": 9,
    },
    {
        "id": "brussel",
        "name": "Brussel",
        "lat": 50.846,
        "lon": 4.352,
        "zoom": 12,
    },
]

# id -> naam, ook voor items die niet aan één provincie hangen
REGION_NAMES = {p["id"]: p["name"] for p in PROVINCES}
REGION_NAMES["vlaanderen"] = "Vlaanderen"
REGION_NAMES["lokerse-streek"] = "Lokerse streek"
REGION_NAMES["alles"] = "Vlaanderen"

LOCAL_FOCUS = ["Lokeren", "Destelbergen", "Laarne", "Lochristi"]

# Korte of dubbelzinnige namen enkel matchen als ze zo in de titel staan.
AMBIGUOUS = {"Mol", "Geel", "Lier", "Boom", "Asse", "Halle", "Peer", "Bree"}

# (naam, provincie, lat, lon, marker, aliases)
# marker=True: stip op de kaart. aliases: deelgemeenten of gangbare vormen.
_PLACES = [
    # West-Vlaanderen
    ("Brugge", "west-vlaanderen", 51.209, 3.224, True, ["Brugse"]),
    ("Oostende", "west-vlaanderen", 51.216, 2.928, True, ["Oostendse"]),
    ("Kortrijk", "west-vlaanderen", 50.828, 3.265, True, ["Kortrijkse"]),
    ("Roeselare", "west-vlaanderen", 50.945, 3.123, True, []),
    ("Ieper", "west-vlaanderen", 50.851, 2.885, False, ["Ieperse"]),
    ("Knokke-Heist", "west-vlaanderen", 51.349, 3.287, False, ["Knokke"]),
    ("Veurne", "west-vlaanderen", 51.072, 2.662, False, []),
    ("Diksmuide", "west-vlaanderen", 51.033, 2.864, False, []),
    ("Tielt", "west-vlaanderen", 50.999, 3.327, False, []),
    ("Waregem", "west-vlaanderen", 50.887, 3.428, False, []),
    ("Torhout", "west-vlaanderen", 51.066, 3.100, False, []),
    ("Izegem", "west-vlaanderen", 50.920, 3.213, False, []),
    ("Blankenberge", "west-vlaanderen", 51.313, 3.132, False, []),
    # Oost-Vlaanderen
    ("Gent", "oost-vlaanderen", 51.054, 3.722, True, ["Gentse", "Gentbrugge"]),
    ("Aalst", "oost-vlaanderen", 50.937, 4.040, True, ["Aalsterse"]),
    ("Sint-Niklaas", "oost-vlaanderen", 51.164, 4.139, True, ["St-Niklaas", "St.-Niklaas", "Sint Niklaas"]),
    ("Lokeren", "oost-vlaanderen", 51.103, 3.993, True, ["Lokerse", "Daknam", "Eksaarde"]),
    ("Destelbergen", "oost-vlaanderen", 51.059, 3.799, True, []),
    ("Laarne", "oost-vlaanderen", 51.029, 3.853, True, ["Beervelde", "Kalken"]),
    ("Lochristi", "oost-vlaanderen", 51.096, 3.833, True, ["Zeveneken", "Zaffelare"]),
    ("Dendermonde", "oost-vlaanderen", 51.028, 4.101, True, []),
    ("Oudenaarde", "oost-vlaanderen", 50.845, 3.608, False, []),
    ("Eeklo", "oost-vlaanderen", 51.187, 3.566, False, []),
    ("Deinze", "oost-vlaanderen", 50.983, 3.530, False, []),
    ("Ninove", "oost-vlaanderen", 50.835, 4.025, False, []),
    ("Geraardsbergen", "oost-vlaanderen", 50.772, 3.882, False, []),
    ("Wetteren", "oost-vlaanderen", 51.006, 3.883, False, []),
    ("Zele", "oost-vlaanderen", 51.066, 4.041, False, []),
    ("Hamme", "oost-vlaanderen", 51.098, 4.137, False, []),
    ("Temse", "oost-vlaanderen", 51.127, 4.213, False, []),
    ("Beveren", "oost-vlaanderen", 51.213, 4.257, False, []),
    ("Zelzate", "oost-vlaanderen", 51.200, 3.807, False, []),
    # Antwerpen
    ("Antwerpen", "antwerpen", 51.221, 4.399, True, ["Antwerpse"]),
    ("Mechelen", "antwerpen", 51.025, 4.477, True, ["Mechelse"]),
    ("Turnhout", "antwerpen", 51.323, 4.949, True, []),
    ("Geel", "antwerpen", 51.161, 4.990, False, []),
    ("Lier", "antwerpen", 51.131, 4.570, False, []),
    ("Herentals", "antwerpen", 51.177, 4.836, False, []),
    ("Mol", "antwerpen", 51.184, 5.116, False, []),
    ("Hoogstraten", "antwerpen", 51.400, 4.761, False, []),
    ("Heist-op-den-Berg", "antwerpen", 51.075, 4.728, False, []),
    ("Brasschaat", "antwerpen", 51.291, 4.494, False, []),
    ("Mortsel", "antwerpen", 51.170, 4.451, False, []),
    ("Boom", "antwerpen", 51.087, 4.366, False, []),
    ("Willebroek", "antwerpen", 51.060, 4.361, False, []),
    # Limburg
    ("Hasselt", "limburg", 50.931, 5.337, True, ["Hasseltse"]),
    ("Genk", "limburg", 50.965, 5.500, True, ["Genkse"]),
    ("Sint-Truiden", "limburg", 50.816, 5.186, True, ["St-Truiden", "Sint Truiden"]),
    ("Tongeren", "limburg", 50.781, 5.464, False, ["Tongerse"]),
    ("Beringen", "limburg", 51.049, 5.226, False, []),
    ("Lommel", "limburg", 51.230, 5.313, False, []),
    ("Maaseik", "limburg", 51.095, 5.783, False, []),
    ("Maasmechelen", "limburg", 50.965, 5.694, False, []),
    ("Leopoldsburg", "limburg", 51.117, 5.258, False, []),
    ("Heusden-Zolder", "limburg", 51.033, 5.278, False, []),
    ("Bilzen", "limburg", 50.873, 5.518, False, []),
    ("Peer", "limburg", 51.130, 5.458, False, []),
    ("Bree", "limburg", 51.141, 5.597, False, []),
    # Vlaams-Brabant
    ("Leuven", "vlaams-brabant", 50.879, 4.701, True, ["Leuvense"]),
    ("Vilvoorde", "vlaams-brabant", 50.928, 4.425, True, []),
    ("Halle", "vlaams-brabant", 50.734, 4.234, True, []),
    ("Tienen", "vlaams-brabant", 50.807, 4.938, False, []),
    ("Diest", "vlaams-brabant", 50.985, 5.050, False, []),
    ("Aarschot", "vlaams-brabant", 50.984, 4.837, False, []),
    ("Zaventem", "vlaams-brabant", 50.885, 4.473, False, []),
    ("Asse", "vlaams-brabant", 50.909, 4.199, False, []),
    ("Dilbeek", "vlaams-brabant", 50.848, 4.263, False, []),
    ("Overijse", "vlaams-brabant", 50.774, 4.537, False, []),
    ("Tervuren", "vlaams-brabant", 50.824, 4.514, False, []),
    ("Rotselaar", "vlaams-brabant", 50.953, 4.717, False, ["Werchter"]),
    # Brussel
    ("Brussel", "brussel", 50.847, 4.352, True, ["Brusselse"]),
    ("Elsene", "brussel", 50.827, 4.372, False, []),
    ("Schaarbeek", "brussel", 50.868, 4.373, False, []),
    ("Anderlecht", "brussel", 50.836, 4.308, False, []),
    ("Ukkel", "brussel", 50.803, 4.337, False, []),
    ("Sint-Jans-Molenbeek", "brussel", 50.855, 4.338, False, ["Molenbeek"]),
]

# Plaatsen die ook een voetbalclub zijn. Sportkoppen horen niet in het gemeente-filter.
CLUB_PLACES = {"Anderlecht", "Genk", "Gent", "Brugge", "Antwerpen", "Mechelen"}
CLUB_PHRASES = re.compile(
    r"\b(AA Gent|Club Brugge|RSC Anderlecht|Antwerp FC|KV Mechelen|KRC Genk|paars-wit)\b",
    re.IGNORECASE,
)
ANDERLECHT_AS_PLACE = re.compile(r"\b(in Anderlecht|Anderlechtse|gemeente Anderlecht)\b")
SPORT_WORDS = re.compile(
    r"\b(voetbal|eredivisie|jupiler|coach|speler|nederlaag|gelijkspel|doelpunt|scheids|transfer|trainer|doelman|match|ploeg|competitie|uitslag|degradatie|titelstrijd)\b",
    re.IGNORECASE,
)
CIVIC_WORDS = re.compile(
    r"\b(gemeente|schepen|burgemeester|politie|station|wegenwerken|school|ziekenhuis|gemeenteraad)\b",
    re.IGNORECASE,
)

PROVINCE_HINTS = [
    ("west-vlaanderen", ["West-Vlaanderen", "West Vlaanderen"]),
    ("oost-vlaanderen", ["Oost-Vlaanderen", "Oost Vlaanderen", "Waasland"]),
    ("vlaams-brabant", ["Vlaams-Brabant", "Vlaams Brabant"]),
    ("antwerpen", ["provincie Antwerpen"]),
    ("limburg", ["Belgisch Limburg", "provincie Limburg"]),
    ("brussel", ["Brussels Hoofdstedelijk", "Brussel-Hoofdstad"]),
]

WEATHER_LOCATIONS = [
    {"id": "west-vlaanderen", "name": "Brugge", "lat": 51.2093, "lon": 3.2247},
    {"id": "oost-vlaanderen", "name": "Gent", "lat": 51.0543, "lon": 3.7174},
    {"id": "antwerpen", "name": "Antwerpen", "lat": 51.2194, "lon": 4.4025},
    {"id": "limburg", "name": "Hasselt", "lat": 50.9307, "lon": 5.3325},
    {"id": "vlaams-brabant", "name": "Leuven", "lat": 50.8798, "lon": 4.7005},
    {"id": "brussel", "name": "Brussel", "lat": 50.8503, "lon": 4.3517},
    {"id": "lokerse-streek", "name": "Lokeren", "lat": 51.1033, "lon": 3.9931},
]

MONTHS_NL = ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]
BRUSSELS = ZoneInfo("Europe/Brussels")

WMO_CODES = {
    0: "Helder",
    1: "Overwegend helder",
    2: "Gedeeltelijk bewolkt",
    3: "Bewolkt",
    45: "Mist",
    48: "Rijpmist",
    51: "Lichte motregen",
    53: "Motregen",
    55: "Dichte motregen",
    61: "Lichte regen",
    63: "Regen",
    65: "Zware regen",
    71: "Lichte sneeuw",
    73: "Sneeuw",
    75: "Zware sneeuw",
    80: "Lichte buien",
    81: "Buien",
    82: "Zware buien",
    95: "Onweer",
    96: "Onweer met hagel",
    99: "Zwaar onweer",
}


def municipalities():
    """Gemeenten als dicts, langste naam eerst zodat aliases niet worden afgekapt."""
    items = []
    for name, province, lat, lon, marker, aliases in _PLACES:
        items.append(
            {
                "name": name,
                "province": province,
                "lat": lat,
                "lon": lon,
                "marker": marker,
                "local": name in LOCAL_FOCUS,
                "ambiguous": name in AMBIGUOUS,
                "aliases": list(aliases),
            }
        )
    return items


def _compile_patterns(name, aliases, ambiguous):
    variants = [name, *aliases]
    compiled = []
    for variant in variants:
        flags = 0
        if ambiguous or len(variant) <= 5:
            flags = 0
        else:
            flags = re.IGNORECASE
        compiled.append((variant, re.compile(rf"(?<![\w]){re.escape(variant)}(?![\w])", flags)))
    return compiled


class PlaceMatcher:
    def __init__(self, places=None):
        places = places if places is not None else municipalities()
        decorated = []
        for place in places:
            patterns = _compile_patterns(place["name"], place.get("aliases") or [], place.get("ambiguous"))
            decorated.append((place, patterns))
        decorated.sort(key=lambda pair: len(pair[0]["name"]), reverse=True)
        self._places = decorated
        self._hints = [
            (province, [re.compile(rf"(?<![\w]){re.escape(hint)}(?![\w])") for hint in hints])
            for province, hints in PROVINCE_HINTS
        ]

    def match(self, title, description=""):
        """Geeft unieke gemeenten terug. Dubbelzinnige namen enkel in de titel."""
        found = []
        seen = set()
        title = title or ""
        description = description or ""
        for place, patterns in self._places:
            hit = False
            for _variant, pattern in patterns:
                if pattern.search(title):
                    hit = True
                    break
                if place.get("ambiguous"):
                    continue
                if pattern.search(description):
                    hit = True
                    break
            if hit and place["name"] not in seen:
                seen.add(place["name"])
                found.append(place)
        return found

    def hint_provinces(self, text):
        text = text or ""
        found = []
        for province, patterns in self._hints:
            if any(pattern.search(text) for pattern in patterns):
                found.append(province)
        return found


def is_sport_text(title, description=""):
    text = f"{title or ''} {description or ''}"
    return bool(SPORT_WORDS.search(text) or CLUB_PHRASES.search(text))


def without_club_noise(places, title, description):
    """Haal clubnamen uit sportkoppen, behalve als het bericht ook bestuurlijk is.

    'Anderlecht' zonder plaatsbepaling ('in Anderlecht') is bijna altijd de club.
    """
    if not places:
        return places
    text = f"{title or ''} {description or ''}"
    civic = bool(CIVIC_WORDS.search(text))
    sporty = is_sport_text(title, description)
    kept = []
    for place in places:
        if place["name"] == "Anderlecht" and not civic and not ANDERLECHT_AS_PLACE.search(text):
            continue
        if sporty and not civic and place["name"] in CLUB_PLACES:
            continue
        kept.append(place)
    return kept


def classify_item(title, description, default_province, default_places, matcher):
    """Bepaal provincies en plaatsen voor een bericht.

    default_places worden altijd meegenomen (officiële gemeentefeed).
    Een eenduidige plaatsherkenning overschrijft de standaardprovincie.
    """
    places = without_club_noise(matcher.match(title, description), title, description)
    names = []
    seen = set()
    for name in list(default_places or []) + [place["name"] for place in places]:
        if name and name not in seen:
            seen.add(name)
            names.append(name)

    catalog = {place["name"]: place for place in municipalities()}
    provinces = []
    for name in names:
        province = catalog.get(name, {}).get("province")
        if province and province not in provinces:
            provinces.append(province)

    if not provinces:
        hinted = matcher.hint_provinces(f"{title or ''} {description or ''}")
        for province in hinted:
            if province not in provinces:
                provinces.append(province)

    if not provinces and default_province and default_province != "vlaanderen":
        provinces.append(default_province)

    if len(provinces) == 1:
        primary = provinces[0]
    elif default_province:
        primary = default_province
    else:
        primary = "vlaanderen"

    return {"province": primary, "provinces": provinces, "places": names}


def nearest_municipality(lat, lon, places=None, max_deg=0.45):
    places = places if places is not None else municipalities()
    best = None
    best_d = max_deg * max_deg
    for place in places:
        dlat = place["lat"] - lat
        dlon = place["lon"] - lon
        dist = dlat * dlat + dlon * dlon
        if dist < best_d:
            best_d = dist
            best = place
    return best


def parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    try:
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(text)
        if dt is not None:
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def format_dutch(dt):
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(BRUSSELS)
    return f"{local.day} {MONTHS_NL[local.month - 1]} {local.strftime('%H:%M')}"


def activity_score(items, now=None):
    """0-100, hoger betekent drukker. Leeg blijft laag, een gewone dag zit rond 50-70."""
    if not items:
        return 15
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    cutoff = moment - timedelta(hours=36)
    sources = set()
    recent = 0
    dated = 0
    for item in items:
        sources.add(item.get("source") or "")
        dt = parse_datetime(item.get("published") or item.get("pubDate"))
        if dt is None:
            continue
        dated += 1
        if dt >= cutoff:
            recent += 1
    if dated == 0:
        ratio = 0.35
    else:
        ratio = recent / dated
    score = round(18 + ratio * 55 + min(10, len([s for s in sources if s])) * 2.5)
    return max(15, min(95, int(score)))


def items_for_region(items, region):
    if not region or region in ("alles", "vlaanderen"):
        return list(items)
    if region == "lokerse-streek":
        local = set(LOCAL_FOCUS)
        return [item for item in items if any(place in local for place in item.get("places") or [])]
    selected = []
    for item in items:
        provinces = item.get("provinces") or ([item["province"]] if item.get("province") else [])
        if region in provinces or item.get("province") == region:
            selected.append(item)
    return selected


def region_scores(items, now=None):
    keys = ["alles", "lokerse-streek", *[province["id"] for province in PROVINCES]]
    return {key: activity_score(items_for_region(items, key), now=now) for key in keys}


def weather_description(code):
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "Licht bewolkt"
    return WMO_CODES.get(code, "Licht bewolkt")


def regions_payload():
    return {
        "provinces": PROVINCES,
        "municipalities": [
            {
                "name": place["name"],
                "province": place["province"],
                "lat": place["lat"],
                "lon": place["lon"],
                "marker": place["marker"],
                "local": place["local"],
            }
            for place in municipalities()
        ],
        "localFocus": LOCAL_FOCUS,
        "map": {"south": 50.67, "west": 2.54, "north": 51.51, "east": 5.92},
    }


def write_regions_file(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(regions_payload(), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
