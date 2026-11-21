import json,unittest
from pathlib import Path
class DualRecipientCaseTests(unittest.TestCase):
 def setUp(self):self.d=json.loads(Path("config/grant_candidate_cdss_swar_sadhana.json").read_text())
 def test_different_legal_bns(self):
  a,b=self.d["organizations"]
  self.assertNotEqual(a["federal_business_number"],b["federal_business_number"])
  self.assertFalse(b["legal_incorporation_number_verified"])
 def test_city_award_sum_and_stream(self):
  self.assertEqual(sum(x["amount_cad"] for r in self.d["organizations"] for x in r["awards"]),107500)
  self.assertEqual(len([x for r in self.d["organizations"] for x in r["awards"] if x["year"]==2024]),2)
 def test_no_duplicate_claim_inference(self):
  self.assertEqual(self.d["confirmed_duplicate_expense_claims"],0)
  self.assertEqual(self.d["confirmed_fraud"],0)
  self.assertEqual(self.d["original_invoices_obtained"],0)
  self.assertFalse(self.d["external_communications_permitted"])
