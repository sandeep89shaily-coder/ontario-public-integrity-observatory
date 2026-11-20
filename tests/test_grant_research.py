import tempfile,unittest
from pathlib import Path
from src.observatory.grant_research import stream_label,key_for,parse_money,analyze,run
class GrantsTests(unittest.TestCase):
 def test_streams_not_inferred_from_amount(self):
  self.assertEqual(stream_label("2025 Advance Brampton Fund Developing Projects Approved Applicants"),"Developing")
  self.assertEqual(stream_label("2024 Advance Brampton Fund New and Small Project Approved Applicants"),"New and Small")
  self.assertIsNone(stream_label("Unknown"))
  self.assertNotEqual(key_for("Example Inc"),key_for("Example Ltd"))
 def test_money_is_approved_only(self):
  self.assertEqual(parse_money("$2,500.00"),2500)
  r=[dict(year=y,organization_as_published="Sample Group",grant_stream="UNKNOWN",
      approved_amount_cad="2500",source_url="https://www.brampton.ca/x.pdf",
      source_page=1) for y in ("2025","2026")]
  s,c,m=analyze(r)
  self.assertEqual(s["2025"]["approved_sum_cad"],"2500")
  self.assertFalse(s["2025"]["actual_payments_obtained"])
  self.assertEqual(len(c),1)
  self.assertIn("NOT_LEGAL_IDENTITY",c[0]["matching_rule"])
 def test_network_failure_is_not_zero_records(self):
  with tempfile.TemporaryDirectory() as d:
   def fail(*a,**kw):raise ConnectionError("Access denied")
   r=run(Path(d),fetch=fail)
   self.assertEqual(r["years_parsed"],0)
   self.assertTrue(all(x["status"]=="FAILED" for x in r["source_checks"]))
