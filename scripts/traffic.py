"""Verkeersmeldingen uit de publieke DATEX II-feed van het Verkeerscentrum.

Geen API-sleutel. Coördinaten in de feed zijn Lambert 72 (EPSG:31370).
"""

from xml.etree import ElementTree as ET

from pyproj import Transformer

from scripts.regions import nearest_municipality

_TRANSFORMER = Transformer.from_crs("EPSG:31370", "EPSG:4326", always_xy=True)

MGMT_NL = {
    "newRoadworksLayout": "Nieuwe wegenwerken",
    "narrowLanes": "Versmalde rijstroken",
    "roadClosed": "Weg afgesloten",
    "singleAlternateLineTraffic": "Beurtelings verkeer",
}

MAINT_NL = {
    "roadsideWork": "Werken langs de weg",
    "roadworks": "Wegenwerken",
}

RECORD_NL = {
    "AbnormalTraffic": "Verstoord verkeer",
    "GeneralObstruction": "Hindernis op de weg",
    "MaintenanceWorks": "Onderhoudswerken",
    "RoadOrCarriagewayOrLaneManagement": "Verkeersmaatregel",
}

RECORD_RANK = {
    "AbnormalTraffic": 50,
    "GeneralObstruction": 40,
    "MaintenanceWorks": 20,
    "RoadOrCarriagewayOrLaneManagement": 10,
}


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _xsi_type(element):
    for key, value in element.attrib.items():
        if key.endswith("type"):
            return value.rsplit(":", 1)[-1]
    return ""


def lambert72_to_wgs84(x, y):
    lon, lat = _TRANSFORMER.transform(float(x), float(y))
    return lat, lon


def _midpoint(pos_list):
    nums = []
    for chunk in (pos_list or "").split():
        try:
            nums.append(float(chunk))
        except ValueError:
            continue
    if len(nums) < 2:
        return None
    mid = (len(nums) // 4) * 2
    if mid + 1 >= len(nums):
        mid = 0
    lat, lon = lambert72_to_wgs84(nums[mid], nums[mid + 1])
    if not (49.4 <= lat <= 52.0 and 2.3 <= lon <= 6.5):
        return None
    return lat, lon


def _record_summary(record):
    status = ""
    label = ""
    rank = 0
    pos = None
    until = ""
    flow = ""
    rtype = _xsi_type(record)
    if rtype in RECORD_NL:
        label = RECORD_NL[rtype]
        rank = RECORD_RANK.get(rtype, 10)
    for el in record.iter():
        name = _local(el.tag)
        text = (el.text or "").strip()
        if name == "validityStatus" and text:
            status = text
        elif name == "posList" and pos is None:
            pos = _midpoint(text)
        elif name == "roadOrCarriagewayOrLaneManagementType" and text in MGMT_NL:
            label = MGMT_NL[text]
            if text == "roadClosed":
                rank = max(rank, 30)
            else:
                rank = max(rank, 12)
        elif name == "roadMaintenanceType" and text in MAINT_NL:
            label = MAINT_NL[text]
            rank = max(rank, 18)
        elif name == "overallEndTime" and text:
            until = text[:10]
        elif name == "trafficFlowCharacteristics" and text:
            flow = text
            if text in {"trafficBlocked", "stationary"}:
                rank = max(rank, 45)
                label = "Verkeer geblokkeerd"
    if status and status != "active":
        return None
    if pos is None or not label:
        return None
    # Wegafsluitingen en gewone werken blijven info. Enkel echte hinder
    # (file, blokkade, obstructie) trekt het alertniveau omhoog.
    severity = "warning" if rank >= 40 else "info"
    return {
        "label": label,
        "rank": rank,
        "severity": severity,
        "lat": round(pos[0], 5),
        "lon": round(pos[1], 5),
        "until": until,
        "flow": flow,
    }


def parse_datex(xml_bytes, places=None, limit=40):
    """Zet een DATEX II-payload om naar compacte meldingen met provincie."""
    if isinstance(xml_bytes, str):
        xml_bytes = xml_bytes.encode("utf-8")
    root = ET.fromstring(xml_bytes)
    items = []
    seen = set()
    for situation in root.iter():
        if _local(situation.tag) != "situation":
            continue
        sid = situation.attrib.get("id") or ""
        best = None
        for record in situation.iter():
            if _local(record.tag) != "situationRecord":
                continue
            summary = _record_summary(record)
            if summary and (best is None or summary["rank"] > best["rank"]):
                best = summary
        if not best:
            continue
        key = (best["label"], round(best["lat"], 2), round(best["lon"], 2))
        if key in seen:
            continue
        seen.add(key)
        place = nearest_municipality(best["lat"], best["lon"], places)
        items.append(
            {
                "id": sid,
                "label": best["label"],
                "severity": best["severity"],
                "rank": best["rank"],
                "lat": best["lat"],
                "lon": best["lon"],
                "until": best["until"],
                "province": place["province"] if place else "vlaanderen",
                "place": place["name"] if place else "",
            }
        )
    items.sort(key=lambda item: (-item["rank"], item["label"]))
    trimmed = items[:limit]
    for item in trimmed:
        item.pop("rank", None)
    return trimmed
