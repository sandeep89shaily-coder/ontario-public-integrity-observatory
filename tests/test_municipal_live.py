import unittest
from src.observatory.municipal_live import TextCollector, robots_permission, REPORTS, BRAMPTON
class LivePilotOfflineTests(unittest.TestCase):
    def test_fixed_official_sources(self):
        self.assertEqual(len(REPORTS),2)
        self.assertTrue(all(u.startswith("https://www.mississauga.ca/") for u in REPORTS.values()))
        self.assertTrue(all(u.startswith("https://brampton.bidsandtenders.ca/") for u in BRAMPTON.values()))
    def test_html_reading_is_not_evidence_of_awarded_vendor(self):
        parser=TextCollector()
        parser.feed("<html><body><p>Bid Status: Awarded</p></body></html>")
        self.assertIn("Awarded", " ".join(parser.parts))
    def test_scripts_are_not_presented_as_tender_evidence(self):
        parser=TextCollector()
        parser.feed("<script>Ext.net.ResourceMgr.init({});</script><p>Bid Number: T2026-161</p>")
        self.assertNotIn("Ext.net", " ".join(parser.parts))
        self.assertIn("T2026-161", " ".join(parser.parts))
