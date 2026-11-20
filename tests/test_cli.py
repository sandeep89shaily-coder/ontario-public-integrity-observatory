import tempfile
import unittest
from pathlib import Path
from src.observatory.cli import investigate

FIXTURE=Path(__file__).parent/'fixtures'/'awards_example.csv'
class InvestigationTests(unittest.TestCase):
    def test_repeat_awards_are_only_candidates(self):
        result=investigate(FIXTURE)
        self.assertEqual(result['record_count'],3)
        self.assertEqual(len(result['repeat_vendor_candidates']),1)
        self.assertIn('NOT_FINDINGS',result['status'])
    def test_missing_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.csv'
            p.write_text('municipality,contract_id,vendor_name,award_date,award_amount_cad,source_url\nTown,1,Example,2026-01-01,5,http://example.com\n')
            with self.assertRaises(ValueError):investigate(p)
