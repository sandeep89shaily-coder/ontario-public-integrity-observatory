import json,unittest
from pathlib import Path
class CollegeProviderCaseTests(unittest.TestCase):
 def setUp(self):
  self.d=json.loads(Path("config/grant_candidate_aspire_college_provider.json").read_text())
 def test_hours_reconcile_arithmetic_only(self):
  r=self.d["reported_2024"];s=self.d["current_schedule"]
  self.assertEqual(r["scholarship_instruction_total_hours"]//r["scholarship_instruction_adults"],480)
  self.assertEqual(s["gross_scheduled_clock_hours_per_participant"],390)
  self.assertFalse(s["historical_schedule_same_as_2024_verified"])
  self.assertFalse(s["program_academic_hours_definition_verified"])
 def test_no_current_retail_rate_imputed_to_past(self):
  self.assertIsNone(self.d["historical_contract_per_seat_cad"])
  self.assertFalse(self.d["current_retail_price_is_historical_contract"])
  self.assertFalse(self.d["office"]["aspire_cohort_confirmed"])
 def test_protect_privacy_and_evidence_gates(self):
  self.assertEqual(self.d["findings_of_fraud"],0)
  self.assertFalse(self.d["private_participant_data_requested"])
  self.assertEqual(self.d["contact_permission"],"NONE")
