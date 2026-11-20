import json,unittest
from pathlib import Path
class AspireCaseEvidenceTests(unittest.TestCase):
 def setUp(self):
  self.data=json.loads(Path("config/grant_candidate_aspire_evidence.json").read_text())
 def test_not_an_adverse_finding(self):
  self.assertEqual(self.data["verified_fraud"],0)
  self.assertEqual(self.data["verified_improper_public_funds_use"],0)
  self.assertEqual(self.data["communication_permissions"],"NO_OUTREACH_WITHOUT_EXPLICIT_USER_APPROVAL")
 def test_never_merge_funding_bases(self):
  a=self.data["other_public_funding"]
  types={r["accounting_basis"] for r in a}
  self.assertIn("PROVINCIAL_PUBLIC_ACCOUNTS_TRANSFER_PAYMENT_NOT_A_NEW_AGREEMENT_FACE_VALUE",types)
  self.assertIn("FEDERAL_CONTRIBUTION_AGREEMENT_FACE_VALUE_NOT_PAYMENT_TOTAL",types)
  self.assertEqual(self.data["municipal_sum_cad_if_same_entity"],sum(r["approved_cad"] for r in self.data["municipal_awards"]))
  self.assertFalse(self.data["legal_identity"]["local_award_named_entities_reconciled_to_federal_number"])
 def test_trust_is_not_verified_city_grant(self):
  x=self.data["third_party_audited_accounting_disclosure"]
  self.assertFalse(x["grant_source_or_payment_path_verified"])
  self.assertFalse(x["same_legal_entity_as_municipal_award_recipient_verified"])
 def test_sources_have_https(self):
  from urllib.parse import urlsplit
  entries=self.data["other_public_funding"]+self.data["municipal_awards"]
  self.assertTrue(all(urlsplit(r["source_url"]).scheme=="https" for r in entries))
