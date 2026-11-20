import tempfile
import unittest
from pathlib import Path
from src.observatory.history import normalize_name,analyze,amount,split_city,read_sources,run

def row(num,name,money,report):
 return dict(procurement_id=num,vendor_raw=name,award_amount_displayed=money,
  description_raw="Official example",source_url="https://www.mississauga.ca/x.pdf",
  source_page=1,source_pdf_sha256="a",report_month=report,competition="competitive")

class HistoryTests(unittest.TestCase):
 def test_city_removed_only_with_known_suffix(self):
  self.assertEqual(split_city("Mopal Construction Limited Gormley"),("Mopal Construction Limited","Gormley"))
  self.assertEqual(normalize_name("Mopal Construction Limited Gormley"),normalize_name("Mopal Construction Limited"))
  self.assertEqual(split_city("New York Example"),("New York Example",""))
 def test_realistic_repeat_and_duplicate(self):
  r=[row("PRC005464","Mopal Construction Limited Gormley","$2,337,355.00","2026-08"),
     row("PRC005502","Mopal Construction Limited Gormley","$323,130.00","2026-09"),
     row("PRC005464","Mopal Construction Limited Gormley","$2,337,355.00","2026-08"),
     row("PRC005500","Other Vendor Toronto","$100.00","2026-09")]
  c=analyze(r)
  self.assertEqual(len(c["repeat_name_candidates"]),1)
  self.assertEqual(c["repeat_name_candidates"][0]["distinct_procurements"],2)
  self.assertEqual(c["repeat_name_candidates"][0]["reported_amount_sum"],"2660485.00")
  self.assertEqual(c["held"][0]["reason"],"SAME_VENDOR_PROCUREMENT_VALUE_REAPPEARS")
  self.assertEqual(c["repeat_name_candidates"][0]["performance_status"],"NOT_YET_ESTABLISHED")
 def test_bad_values_and_source(self):
  self.assertIsNone(amount("Private"))
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"bad.csv";p.write_text("report_id,report_month,competition,source_url\n1,2026-01,competitive,http://example.org/file.pdf\n")
   with self.assertRaises(ValueError):read_sources(p)
 def test_network_failure_honestly_recorded(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"one.csv";p.write_text("report_id,report_month,competition,source_url\nx,2026-01,competitive,https://www.mississauga.ca/wp-content/uploads/2026/a.pdf\n")
   def fail(*a,**k):raise OSError("network failure")
   x=run(p,Path(d)/"output",fetch_pdf=fail,parse_pdf=lambda *a,**k:([],[]))
   self.assertEqual(x["status"],"PARTIAL_FETCH_FAILURE")
   self.assertEqual(x["source_observations"],0)
