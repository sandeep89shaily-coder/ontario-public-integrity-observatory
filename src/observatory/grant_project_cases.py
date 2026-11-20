"""Evidence-constrained grant purposes and multi-funder casebook; no automated adverse verdicts."""
from __future__ import annotations
import argparse,csv,json,hashlib,re
from decimal import Decimal,InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit
from collections import defaultdict

ACTIVITY_TYPES={"RECIPIENT_PROMOTION","RECIPIENT_PROGRAM_PAGE","ORGANIZER_DELIVERY_REPORT"}
ACTIVITY_STATUSES={"PLANNED_OR_PROMOTED","SELF_REPORTED_DELIVERED"}

def key(s):
 return " ".join(re.sub(r"[^a-z0-9]+"," ",str(s or "").casefold()).split())

def valid_url(u):
 p=urlsplit(str(u or ""))
 return p.scheme=="https" and bool(p.hostname) and not p.username and not p.password

def amount(s):
 try:
  v=Decimal(str(s))
  if not v.is_finite() or v<0:return None
  return v
 except (InvalidOperation,ValueError):return None

def prepare(awards,evidence):
 byname=defaultdict(list);held=[];year_keys=set()
 for award in awards:
  name=key(award["organization_as_published"])
  byname[name].append(award)
  year_keys.add((award["year"],name))
 cases=[]
 for target in evidence["focus"]:
  name=key(target["recipient"])
  if not name or name not in byname:
   held.append({"type":"TARGET_NOT_IN_CITY_AWARDS","name":target.get("recipient")})
   continue
  group=sorted(byname[name],key=lambda a:a["year"])
  cases.append({"case_id":"grant-project-"+hashlib.sha256(name.encode()).hexdigest()[:12],
   "published_recipient_name":group[0]["organization_as_published"],
   "legal_identity_status":"NAME_ONLY_NOT_REGISTRY_VERIFIED",
   "city_approved_awards":[{"year":r["year"],"approved_cad":r["approved_amount_cad"],
      "grant_stream":r["grant_stream"],"priority_area":r["program_area"],
      "source_url":r["source_url"],"source_page":r["source_page"]} for r in group],
   "city_approved_total_cad":str(sum((Decimal(r["approved_amount_cad"]) for r in group),Decimal(0))),
   "activities":[],"other_funders":[],"reported_collaborations":[],
   "city_grant_contract_scope_verified":False,"actual_expense_invoices_verified":False,
   "grant_payment_ledger_verified":False,"city_closeout_approval_verified":False,
   "record_status":"RESEARCH_CASE_NO_ADVERSE_FINDING"})
 indexed={key(c["published_recipient_name"]):c for c in cases}
 for item in evidence.get("activities",[]):
  who=key(item.get("recipient"));yr=item.get("year")
  good=(who in indexed and (yr,who) in year_keys and
        item.get("evidence_type") in ACTIVITY_TYPES and
        item.get("activity_status") in ACTIVITY_STATUSES and
        item.get("scope_verified_by_city") is False and
        valid_url(item.get("source_url")) and
        len(item.get("description","").strip())>=30 and
        len(item.get("project","").strip())>=6)
  if not good:
   held.append({"type":"ACTIVITY_NOT_SUPPORTED","recipient":item.get("recipient"),"year":yr})
   continue
  indexed[who]["activities"].append({
   "year":yr,"project_as_publicly_described":item["project"],
   "description":item["description"],"status":item["activity_status"],
   "source_url":item["source_url"],"source_publisher":item["source_publisher"],
   "source_kind":item["evidence_type"],
   "city_contract_scope_verified":False,"full_delivery_verified":False,
   "spending_or_invoice_verification":"NOT_AVAILABLE"})
 for item in evidence.get("external_funding",[]):
  who=key(item.get("recipient"));yr=item.get("year")
  money=amount(item.get("reported_award_amount_cad"))
  good=(who in indexed and (yr,who) in year_keys and
   item.get("same_project_as_city_grant_verified") is False and
   item.get("amount_basis")=="FUNDER_PUBLISHED_FUNDING_NOT_RECONCILED_PAYMENTS" and
   money is not None and valid_url(item.get("source_url")) and
   len(item.get("program",""))>=5 and item.get("funder")!="City of Brampton")
  if not good:
   held.append({"type":"EXTERNAL_FUNDING_NOT_SUPPORTED","recipient":item.get("recipient"),"year":yr})
   continue
  indexed[who]["other_funders"].append({
   "year":yr,"funder":item["funder"],"funder_program":item["program"],
   "other_funder_reported_amount_cad":str(money),
   "funder_reported_purpose":item.get("stated_public_purpose"),
   "source_url":item["source_url"],"funder_published_not_paid":True,
   "same_costs_or_project_as_city_award_verified":False,
   "do_not_add_to_city_award_total":True})
 for item in evidence.get("relationships",[]):
  who=key(item.get("recipient"))
  good=(who in indexed and valid_url(item.get("source_url")) and
     item.get("evidence_type")=="RECIPIENT_REPORTED_COLLABORATION" and
     item.get("financial_relationship_verified") is False and
     item.get("related_entity_is_an_abf_recipient_verified") is False and
     len(item.get("description",""))>=30)
  if not good:
   held.append({"type":"RELATIONSHIP_NOT_SUPPORTED","recipient":item.get("recipient")})
   continue
  indexed[who]["reported_collaborations"].append({
   "other_entity_as_reported":item["related_entity"],"public_description":item["description"],
   "source_url":item["source_url"],"classification":"PUBLICLY_REPORTED_PARTNERSHIP_NOT_FINANCIAL_LINK",
   "financial_transfer_or_conflict_verified":False})
 summary={
   "city_award_cases":len(cases),
   "city_approved_award_records":sum(len(c["city_approved_awards"]) for c in cases),
   "self_described_activities":sum(len(c["activities"]) for c in cases),
   "separate_funder_published_awards":sum(len(c["other_funders"]) for c in cases),
   "reported_partner_associations":sum(len(c["reported_collaborations"]) for c in cases),
   "held_unverified_records":len(held),
   "city_grant_agreement_scopes_verified":0,
   "original_invoices_or_recipient_payments_verified":0,
   "confirmed_duplicate_funding":0,"confirmed_fraud":0,
   "important_limitations":[
    "Two funders supporting the same organization or general mission does not establish duplicate reimbursement.",
    "A publicly advertised activity is not necessarily the activity described in the city's grant agreement.",
    "A participant or organizer claiming delivery does not establish complete project close-out or receipts.",
    "Partnerships with external institutions are not proof of improper interest or financial transactions."]}
 return summary,cases,held

def run(award_path,evidence_path,out):
 awards=json.loads(Path(award_path).read_text(encoding="utf-8"))
 evidence=json.loads(Path(evidence_path).read_text(encoding="utf-8"))
 summary,cases,held=prepare(awards,evidence)
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 for name,item in (("summary.json",summary),("grant_project_cases.json",cases),
                   ("held_evidence.json",held)):
  (out/name).write_text(json.dumps(item,indent=2,ensure_ascii=False),encoding="utf-8")
 with (out/"focused_grant_cases.csv").open("w",newline="",encoding="utf-8") as f:
  cols=["recipient","years","city_approved_total_cad","project_evidence_items","other_funder_entries",
        "published_partnerships","grant_agreement_verified","payments_verified"]
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
  for c in cases:
   w.writerow({"recipient":c["published_recipient_name"],
    "years":",".join(sorted({a["year"] for a in c["city_approved_awards"]})),
    "city_approved_total_cad":c["city_approved_total_cad"],
    "project_evidence_items":len(c["activities"]),
    "other_funder_entries":len(c["other_funders"]),
    "published_partnerships":len(c["reported_collaborations"]),
    "grant_agreement_verified":False,"payments_verified":False})
 return summary

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--awards",required=True)
 p.add_argument("--evidence",default="config/grant_specific_project_evidence.json")
 p.add_argument("--out",default="local_results/grant_project_cases")
 a=p.parse_args()
 print(json.dumps(run(a.awards,a.evidence,a.out),indent=2))
if __name__=="__main__":
 main()
