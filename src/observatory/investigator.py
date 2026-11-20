"""AI-assisted, citation-constrained procurement review. No automatic publication."""
from __future__ import annotations
import argparse,json,os,urllib.request
from pathlib import Path

RULES="""You are a public-interest investigative research assistant, not a fraud adjudicator.
Use ONLY the supplied official-source observations and dated public evidence.
Create neutral questions for verifying prior contractor performance and later awards.
Test innocent explanations including specialization, lowest compliant bids, missing
records, scope changes, and projects not yet due for completion.
Never assert concealment, corruption, fraud, collusion or poor performance from
repeat awards, name matches, missing disclosures or cost increases alone.
Reported procurement amounts are NOT final project costs. Reporting months are not award dates.
Do not treat general project-level completion as proof of contractor performance.
Every factual claim must cite a supplied source_id. Return JSON with keys:
evidence_facts (array of objects with source_id and statement), missing_evidence
(array of strings), alternative_explanations (array), follow_up_documents (array),
publication_status (always HUMAN_REVIEW_REQUIRED).
No personal risk scores or unreviewed adverse conclusions."""

SKEPTIC="""Independently challenge the investigator: time-order ambiguity, name-only matching,
missing contractor evaluations, city-caused vs contractor-caused delays, supplier competition.
Never invent sources. JSON keys: unsupported_claims, competing_explanations,
required_corrobation, publication_status (HUMAN_REVIEW_REQUIRED)."""

def prepare_case(case,extra=None):
 evidence=[{
  "source_id":"procurement:"+x["procurement_id"]+":"+x["report_month"],
  "source_url":x["source_url"],"page":x.get("source_page"),
  "vendor_name_as_published":x["vendor_as_published"],
  "procurement_id":x["procurement_id"],"report_month":x["report_month"],
  "project":x["project_description"],"reported_acquisition_value":x["reported_amount"],
  "verified_final_cost":None,"verified_performance":None
 } for x in case["contracts"]]
 evidence.extend(extra or [])
 return {"investigator_system":RULES,"skeptic_system":SKEPTIC,
   "investigator_input":{"subject":case["candidate_name"],"match_status":case["match_basis"],
     "source_evidence":evidence,"limitations":[case["sum_disclaimer"],case["performance_status"],
       "Available reports are a partial historical sample; no full vendor register available."]}}

def validate_review(review,allowed):
 if not isinstance(review,dict) or review.get("publication_status")!="HUMAN_REVIEW_REQUIRED":
  raise ValueError("AI publication gate not satisfied")
 facts=review.get("evidence_facts",[])
 if not isinstance(facts,list):raise ValueError("Model facts must be an array")
 for f in facts:
  if not isinstance(f,dict) or f.get("source_id") not in allowed or not f.get("statement"):
   raise ValueError("Unsupported model claim or invented citation")
 return review

def call_model(messages,api_key,*,transport=None):
 if not api_key:raise ValueError("DEEPSEEK_API_KEY_REQUIRED")
 request={"model":"deepseek-chat","temperature":0,"max_tokens":900,
   "response_format":{"type":"json_object"},"messages":messages}
 if transport:
  response=transport(request)
 else:
  req=urllib.request.Request("https://api.deepseek.com/chat/completions",
    data=json.dumps(request).encode(),method="POST",
    headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"})
  with urllib.request.urlopen(req,timeout=35) as res:
   raw=res.read(200001)
   if len(raw)>200000:raise ValueError("MODEL_RESPONSE_TOO_LARGE")
   response=json.loads(raw)
 return json.loads(response["choices"][0]["message"]["content"])

def run(cases_path,out,*,ai=False,key=None,limit=2,transport=None):
 if not 1<=limit<=3:raise ValueError("Limit must be 1..3")
 cases=json.loads(Path(cases_path).read_text(encoding="utf-8"))["repeat_name_candidates"][:limit]
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 prepared=[prepare_case(c) for c in cases]
 (out/"ai_review_prompts.json").write_text(json.dumps(prepared,indent=2),encoding="utf-8")
 result={"status":"PROMPTS_ONLY_NO_MODEL_CALLED","review_candidates":len(prepared),
  "model_calls":0,"publication_status":"HUMAN_REVIEW_REQUIRED"}
 if ai:
  if not key:raise ValueError("DEEPSEEK_API_KEY_REQUIRED; no model calls executed")
  reports=[]
  for p in prepared:
   first=call_model([{"role":"system","content":p["investigator_system"]},
       {"role":"user","content":json.dumps(p["investigator_input"])}],key,transport=transport)
   allowed={x["source_id"] for x in p["investigator_input"]["source_evidence"]}
   validate_review(first,allowed)
   second=call_model([{"role":"system","content":p["skeptic_system"]},
      {"role":"user","content":json.dumps({"evidence":p["investigator_input"],
                                           "initial_review":first})}],key,transport=transport)
   if second.get("publication_status")!="HUMAN_REVIEW_REQUIRED":
    raise ValueError("Skeptic review cannot be automatically published")
   reports.append({"subject":p["investigator_input"]["subject"],
                   "investigator":first,"skeptic":second})
  (out/"PRIVATE_UNVERIFIED_MODEL_REVIEW.json").write_text(json.dumps(reports,indent=2),encoding="utf-8")
  result.update(status="PRIVATE_UNVERIFIED_MODEL_REVIEW",model_calls=len(reports)*2)
 (out/"ai_review_status.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
 return result

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--cases",default="local_results/history/candidate_histories.json")
 p.add_argument("--out",default="local_results/ai_review")
 p.add_argument("--ai",action="store_true",help="Opt in to paid AI using a separate DEEPSEEK_API_KEY")
 p.add_argument("--limit",type=int,default=2)
 args=p.parse_args()
 print(json.dumps(run(args.cases,args.out,ai=args.ai,key=os.getenv("DEEPSEEK_API_KEY"),
                     limit=args.limit),indent=2))
if __name__=="__main__":main()
