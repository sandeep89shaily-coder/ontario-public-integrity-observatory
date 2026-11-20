import json
import tempfile
import unittest
from pathlib import Path

from src.observatory.toronto import collect, endpoint, extract

SAMPLE = {
    "value": [
        {
            "Solicitation_Document_Number": "1234567890",
            "Status": "Awarded",
            "Posting_Title": "Synthetic municipal works",
            "Client_Division": "Test division",
            "Awarded_Suppliers": [
                {"Successful_Bidder": "Example Civil Ltd",
                 "Date_Awarded": "2025-01-10T12:00:00", "Award_Amount": "$123,400"},
                {"Successful_Bidder": "Second Vendor Inc", "Date_Awarded": "2025-01-11",
                 "Award_Amount": 5000},
            ],
        },
        {"Solicitation_Document_Number": "1234567891", "Status": "Open",
         "Awarded_Suppliers": []},
    ]
}


class TorontoTests(unittest.TestCase):
    def test_endpoint_is_bounded(self):
        self.assertIn("%24top=50", endpoint(0, 50))
        with self.assertRaises(ValueError):
            endpoint(0, 201)

    def test_source_supplier_mentions_not_performance_or_verified_amount(self):
        records, awards, holds = extract(SAMPLE, endpoint(0, 2), "2026-11-20T00:00:00Z")
        self.assertEqual(len(records), 2)
        self.assertEqual(len(awards), 2)
        self.assertFalse(holds)
        self.assertEqual(awards[0]["award_amount_cad"], "")
        self.assertEqual(awards[1]["award_amount_cad"], "")
        self.assertEqual(awards[0]["performance_verified"], "false")
        self.assertEqual(awards[0]["source_record_id"], "1234567890")
        self.assertEqual(awards[0]["parsed_raw_amount_unverified"], "")

    def test_collect_mocked_with_status_files(self):
        with tempfile.TemporaryDirectory() as folder:
            result = collect(folder, fetch=lambda url: SAMPLE, pages=3,
                             page_size=3, observed="2026-11-20T00:00:00Z")
            self.assertEqual(result["supplier_award_mentions"], 2)
            self.assertEqual(result["page_audit"][0]["status"], "FETCHED")
            self.assertTrue((Path(folder) / "toronto_award_candidates.csv").exists())

    def test_failure_is_recorded_not_hidden(self):
        with tempfile.TemporaryDirectory() as folder:
            def fail(url):
                raise ConnectionError("source not available")
            result = collect(folder, fetch=fail)
            self.assertEqual(result["status"], "PARTIAL_FAILURE")
            self.assertEqual(result["page_audit"][0]["status"], "FAILED")
            self.assertEqual(result["supplier_award_mentions"], 0)

    def test_city_test_record_is_held(self):
        payload={"value":[{"Solicitation_Document_Number":"1111111111",
                            "Posting_Title":"DELETE - Testing 99",
                            "Status":"Awarded",
                            "Awarded_Suppliers":[{"Successful_Bidder":"Successful Bidde"}]}]}
        records, awards, holds = extract(payload, endpoint(0, 1), "2026-11-20")
        self.assertFalse(records)
        self.assertFalse(awards)
        self.assertEqual(holds[0]["reason"], "SOURCE_TEST_RECORD_NOT_AN_AWARD")

    def test_invalid_schema_fails(self):
        with self.assertRaises(ValueError):
            extract({"notvalue": []}, endpoint(0, 1), "2026-11-20")
