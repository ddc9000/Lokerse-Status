"""Tests voor regiofilter, activiteitsscore en DATEX-parser. Geen netwerk."""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.regions import (  # noqa: E402
    LOCAL_FOCUS,
    PlaceMatcher,
    activity_score,
    classify_item,
    items_for_region,
)
from scripts.traffic import lambert72_to_wgs84, parse_datex  # noqa: E402
from scripts.update_news import RSS_SOURCES, _select_news, strip_html, title_key  # noqa: E402


class PlaceTests(unittest.TestCase):
    def setUp(self):
        self.matcher = PlaceMatcher()

    def test_local_focus_and_aliases(self):
        found = [place["name"] for place in self.matcher.match("Brand in Kalken en Zaffelare")]
        self.assertIn("Laarne", found)
        self.assertIn("Lochristi", found)
        lokerse = [place["name"] for place in self.matcher.match("De Lokerse feesten")]
        self.assertEqual(lokerse, ["Lokeren"])

    def test_ambiguous_names_need_a_title_case_word(self):
        self.assertEqual(self.matcher.match("Een molen in een geel huis"), [])
        self.assertEqual(self.matcher.match("Assenede start werken"), [])
        self.assertEqual([p["name"] for p in self.matcher.match("Ongeval in Geel")], ["Geel"])
        self.assertEqual(self.matcher.match("", "ongeval in Geel-centrum"), [])

    def test_sint_niklaas_alias(self):
        found = [p["name"] for p in self.matcher.match("Markt in St-Niklaas")]
        self.assertEqual(found, ["Sint-Niklaas"])

    def test_gent_does_not_swallow_gentbrugge_twice(self):
        found = [p["name"] for p in self.matcher.match("Werken in Gentbrugge")]
        self.assertEqual(found, ["Gent"])

    def test_classify_keeps_municipal_default(self):
        item = classify_item("Chrysanten op de begraafplaats", "", "oost-vlaanderen", ["Laarne"], self.matcher)
        self.assertEqual(item["places"], ["Laarne"])
        self.assertEqual(item["province"], "oost-vlaanderen")

    def test_football_club_does_not_count_as_municipality(self):
        item = classify_item(
            "Anderlecht krijgt een 4-0-nederlaag van AA Gent",
            "",
            "vlaanderen",
            [],
            self.matcher,
        )
        self.assertEqual(item["places"], [])
        self.assertEqual(item["province"], "vlaanderen")
        civic = classify_item("Gemeenteraad van Gent keurt het plan goed", "", "vlaanderen", [], self.matcher)
        self.assertEqual(civic["places"], ["Gent"])
        anderlecht = classify_item("Brand in Anderlecht", "", "brussel", [], self.matcher)
        self.assertEqual(anderlecht["places"], ["Anderlecht"])
        club = classify_item("Anderlecht wint de titelstrijd", "", "vlaanderen", [], self.matcher)
        self.assertEqual(club["places"], [])

    def test_classify_overrides_when_one_city_is_clear(self):
        item = classify_item("Grote brand in Hasselt", "", "vlaanderen", [], self.matcher)
        self.assertEqual(item["province"], "limburg")
        self.assertEqual(item["places"], ["Hasselt"])

    def test_region_filter_keeps_lokerse_streek(self):
        items = [
            {"title": "a", "province": "oost-vlaanderen", "provinces": ["oost-vlaanderen"], "places": ["Lokeren"]},
            {"title": "b", "province": "limburg", "provinces": ["limburg"], "places": ["Hasselt"]},
            {"title": "c", "province": "vlaanderen", "provinces": [], "places": []},
        ]
        local = items_for_region(items, "lokerse-streek")
        self.assertEqual([item["title"] for item in local], ["a"])
        limburg = items_for_region(items, "limburg")
        self.assertEqual([item["title"] for item in limburg], ["b"])
        self.assertEqual(len(items_for_region(items, "alles")), 3)
        for name in LOCAL_FOCUS:
            self.assertIn(name, ("Lokeren", "Destelbergen", "Laarne", "Lochristi"))


class ScoreTests(unittest.TestCase):
    def test_empty_and_busy_bounds(self):
        self.assertEqual(activity_score([]), 15)
        now = datetime(2026, 10, 26, tzinfo=timezone.utc)
        fresh = [
            {"source": f"s{i}", "published": (now - timedelta(hours=2)).isoformat()}
            for i in range(8)
        ]
        quiet = [
            {"source": "s", "published": (now - timedelta(days=10)).isoformat()}
            for _ in range(4)
        ]
        self.assertGreater(activity_score(fresh, now=now), activity_score(quiet, now=now))
        self.assertLessEqual(activity_score(fresh, now=now), 95)
        self.assertGreaterEqual(activity_score(quiet, now=now), 15)

    def test_html_and_title_key(self):
        self.assertEqual(strip_html("<p>Dag &amp; nacht</p>"), "Dag & nacht")
        self.assertEqual(title_key("Brand in Lokeren - HLN"), title_key("Brand in Lokeren"))


class TrafficTests(unittest.TestCase):
    def test_lambert_gent(self):
        lat, lon = lambert72_to_wgs84(104000, 194000)
        self.assertAlmostEqual(lat, 51.05, delta=0.02)
        self.assertAlmostEqual(lon, 3.72, delta=0.02)

    def test_parse_datex_fixture(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <payload xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <situation id="EVT1">
            <situationRecord xsi:type="AbnormalTraffic">
              <validity><validityStatus>active</validityStatus></validity>
              <abnormalTrafficType>unspecifiedAbnormalTraffic</abnormalTrafficType>
              <gmlLineString><posList>104000 194000 104010 194010</posList></gmlLineString>
            </situationRecord>
          </situation>
          <situation id="EVT2">
            <situationRecord xsi:type="RoadOrCarriagewayOrLaneManagement">
              <validityStatus>definedByValidityTimeSpec</validityStatus>
              <roadOrCarriagewayOrLaneManagementType>narrowLanes</roadOrCarriagewayOrLaneManagementType>
              <posList>104000 194000</posList>
            </situationRecord>
          </situation>
        </payload>
        """
        items = parse_datex(xml)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["label"], "Verstoord verkeer")
        self.assertEqual(items[0]["severity"], "warning")
        self.assertEqual(items[0]["province"], "oost-vlaanderen")
        self.assertEqual(items[0]["place"], "Gent")


class SourceTests(unittest.TestCase):
    def test_local_items_survive_a_busy_national_feed(self):
        items = [
            {
                "title": f"nationaal {index}",
                "source": "VRT NWS",
                "province": "vlaanderen",
                "places": [],
                "published": f"2026-10-26T12:{index:02d}:00+00:00",
            }
            for index in range(40)
        ]
        items.append(
            {
                "title": "Raad in Lokeren",
                "source": "Nieuwsblad Lokeren",
                "province": "oost-vlaanderen",
                "places": ["Lokeren"],
                "published": "2026-10-02T10:00:00+00:00",
            }
        )
        selected = _select_news(items)
        self.assertTrue(any(item["title"] == "Raad in Lokeren" for item in selected))

    def test_laarne_feed_is_kept_and_sources_are_public(self):
        urls = [source["url"] for source in RSS_SOURCES]
        self.assertIn("https://laarne.be/nieuws/rss", urls)
        for source in RSS_SOURCES:
            self.assertTrue(source["url"].startswith("https://"), source["name"])
            self.assertNotIn("api_key", source["url"].lower())


if __name__ == "__main__":
    unittest.main()
