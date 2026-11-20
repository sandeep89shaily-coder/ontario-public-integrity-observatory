import tempfile,unittest,json
from pathlib import Path
from src.observatory.grant_process_audit import inspect,reviewed,overlapping_invoices,pilot_sample,run

BASE={"year":"2025","grant_stream":"Developing","organization_as_published":"Synthetic Test Group",
 "source_url":"https://www.brampton.ca/example.pdf","approved_amount_cad":"10000",
 "table_row":1,"source_page":2}

def cite(id):
 return {"sha256":(id[0].encode().hex()[:1] or "a")*64,"reviewed_by_human":True,"custody_reference":"private/"+id}

class ProcessAuditTests(unittest.TestCase):
 def test_missing_real_documents_are_unknown_not_fraud(self):
  res=inspect(BASE)
  self.assertTrue(all(v["status"] in ("NOT_OBTAINED","YEAR_POLICY_NOT_CALIBRATED") for v in res["evidence_stage_checks"].values()))
  self.assertIn("NO_MISCONDUCT",res["public_conclusion"])
 def test_unincorporated_not_auto_rejected(self):
  c=inspect(BASE,{"organization":{"type":"unincorporated_nonprofit"}})
  self.assertEqual(c["evidence_stage_checks"]["applicant_identity"]["status"],"NOT_OBTAINED")
 def test_scorer_three_documented_below_threshold_is_question(self):
  x={"evidence_register":{f"s{i}":cite(f"s{i}") for i in range(3)},
     "selection":{"reviewer_scores":[{"score":30,"source_id":f"s{i}"} for i in range(3)]}}
  c=inspect(BASE,x)
  self.assertEqual(c["evidence_stage_checks"]["selection"]["status"],"DOCUMENTED_SCORING_RECONCILIATION_QUESTION")
 def test_missing_one_score_is_unknown(self):
  x={"evidence_register":{"s1":cite("s1")},"selection":{"reviewer_scores":[{"score":90,"source_id":"s1"}]}}
  self.assertEqual(inspect(BASE,x)["evidence_stage_checks"]["selection"]["status"],"NOT_OBTAINED")
 def test_invoice_not_automatically_authenticated(self):
  x={"evidence_register":{"i1":cite("i1")},"expenses":[{"invoice_number":"5","invoice_source_id":"i1"}]}
  c=inspect(BASE,x)
  self.assertIn("NEEDS_AUTHENTICITY",c["evidence_stage_checks"]["expense_authenticity"]["status"])
 def test_shared_invoice_reconciliation_not_fraud(self):
  x=[{"case_id":"a","expenses":[{"supplier":"Test Inc","invoice_number":"001"}]},
     {"case_id":"b","expenses":[{"supplier":"test inc","invoice_number":"001"}]}]
  result=overlapping_invoices(x)
  self.assertEqual(len(result),1)
  self.assertIn("NOT_FRAUD",result[0]["status"])
 def test_approval_not_a_payment(self):
  c=inspect(BASE,{"payments":[]})
  self.assertEqual(c["evidence_stage_checks"]["agreement_and_payment"]["status"],"NOT_OBTAINED")
 def test_cannot_use_unreviewed_hash(self):
  self.assertFalse(reviewed("x",{"x":{"sha256":"a"*64,"reviewed_by_human":False,"custody_reference":"r"}}))
 def test_report_real_published_sample_not_fraud(self):
  sample=[]
  for stream in ("New and Small","Developing","Amplifying"):
   for i in range(3):sample.append({**BASE,"grant_stream":stream,"organization_as_published":f"Synthetic {stream} {i}"})
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"grants.json";path.write_text(json.dumps(sample))
   report=run(path,Path(d)/"out",per_stream=2)
   self.assertEqual(report["sample_size"],6)
   self.assertEqual(report["original_score_sheets_received"],0)
   self.assertEqual(report["confirmed_fraud_or_recipient_ineligibility"],0)
