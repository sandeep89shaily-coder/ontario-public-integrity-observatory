import json,tempfile,unittest
from pathlib import Path
from src.observatory.investigator import prepare_case,validate_review,run,call_model

CASE={"candidate_name":"Example Works Ltd","match_basis":"NAME_ONLY",
 "sum_disclaimer":"Acquisition amounts are not final cost","performance_status":"NOT_ESTABLISHED",
 "contracts":[{"procurement_id":"PRC0051","report_month":"2026-09",
   "source_url":"https://www.mississauga.ca/x.pdf","source_page":1,
   "vendor_as_published":"Example Works Ltd","project_description":"Road works",
   "reported_amount":"200000.00"}]}
class InvestigatorTests(unittest.TestCase):
 def test_citation_validation(self):
  p=prepare_case(CASE)
  good={"evidence_facts":[{"source_id":"procurement:PRC0051:2026-09",
                          "statement":"Procurement report entry"}],
        "publication_status":"HUMAN_REVIEW_REQUIRED"}
  self.assertEqual(validate_review(good,{"procurement:PRC0051:2026-09"}),good)
  with self.assertRaises(ValueError):
   validate_review({"evidence_facts":[{"source_id":"INVENTED","statement":"x"}],
                    "publication_status":"HUMAN_REVIEW_REQUIRED"},{"procurement:PRC0051:2026-09"})
 def test_no_key_no_cost(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"cases.json";p.write_text(json.dumps({"repeat_name_candidates":[CASE]}))
   result=run(p,Path(d)/"out")
   self.assertEqual(result["model_calls"],0)
   self.assertTrue((Path(d)/"out/ai_review_prompts.json").exists())
   self.assertFalse((Path(d)/"out/PRIVATE_UNVERIFIED_MODEL_REVIEW.json").exists())
 def test_key_required(self):
  with self.assertRaises(ValueError):call_model([],None)
