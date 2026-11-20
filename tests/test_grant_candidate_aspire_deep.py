import json,unittest
from decimal import Decimal
from pathlib import Path

class AspireDeepSourceIntegrityTests(unittest.TestCase):
 def setUp(self):
  self.rows=json.loads(Path("config/grant_candidate_aspire_deep_evidence.json").read_text(encoding="utf-8"))
 def test_sources_use_https_and_have_distinct_ids(self):
  self.assertEqual(len(self.rows),len({r["id"] for r in self.rows}))
  self.assertTrue(all(r["source_url"].startswith("https://") for r in self.rows))
  self.assertTrue(all(r["adverse_finding"] is False for r in self.rows))
 def test_2021_and_2022_feddev_listings_are_one_agreement(self):
  versions=[r for r in self.rows if r.get("canonical_agreement_id")=="1000102"]
  self.assertEqual(len(versions),2)
  self.assertEqual({v["amount_cad"] for v in versions},{"977070"})
  # Counting agreement IDs, not record versions, avoids a misleading $1.95414m sum.
  self.assertEqual(len({r["canonical_agreement_id"] for r in versions}),1)
 def test_no_adding_payment_to_award_without_matching_period(self):
  ont=next(r for r in self.rows if r["id"]=="ON_FY_24_25_TRANSFER")
  sdf=next(r for r in self.rows if r["id"]=="ON_SDF_REPORTED_4_5M")
  uw=next(r for r in self.rows if r["id"]=="UW_2025_26_GRANT")
  self.assertEqual(ont["type"],"PUBLIC_ACCOUNTS_FISCAL_TRANSFER_PAYMENT")
  self.assertEqual(sdf["type"],"PRESS_REPORTED_FUNDING_AWARD")
  self.assertEqual(uw["type"],"OTHER_FUNDER_PUBLISHED_ALLOCATION")
 def test_trust_is_never_classed_as_municipal_payment(self):
  trust=next(r for r in self.rows if r["id"]=="SFL_TRUST_2025")
  self.assertEqual(trust["type"],"THIRD_PARTY_INDEPENDENTLY_AUDITED_LIABILITY")
  self.assertFalse(trust["adverse_finding"])

 def test_public_accounts_federal_payments_not_duplicated_as_award_commitments(self):
  items=[r for r in self.rows if r["type"]=="FEDERAL_PUBLIC_ACCOUNTS_AGGREGATE_PAYMENTS"]
  self.assertEqual(len(items),2)
  self.assertEqual(sum(int(r["amount_cad"]) for r in items),490618)
  self.assertTrue(all("AGGREGATE_PAYMENTS" in r["type"] for r in items))
  self.assertTrue(all(r["adverse_finding"] is False for r in items))
