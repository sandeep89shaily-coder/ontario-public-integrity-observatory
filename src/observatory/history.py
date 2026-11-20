"""Conservative municipal contractor-history research, not a fraud detection verdict."""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,re
from collections import defaultdict
from decimal import Decimal,InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

CITIES=("Gormley","Mississauga","Toronto","Vaughan","Markham","Kitchener",
"Brampton","Stouffville","Newmarket","Hamilton","Whitby","Ottawa","Richmond Hill",
"Schomberg","Bradford","Concord","Milgrove","Milton","King City","Acton",
"Barrie","Etobicoke","Oakville","Burlington","North York","Kleinburg","Waterloo",
"Woodbridge","Scarborough","Brantford","Caledon","Aurora","Pickering","Vancouver","Guelph")

def split_city(raw):
 s=" ".join(str(raw or "").split())
 for city in sorted(CITIES,key=len,reverse=True):
  m=re.search(r"\s+"+re.escape(city)+r"\s*$",s,re.I)
  if m:return s[:m.start()].strip(),city
 return s,""

def normalize_name(raw):
 company,_=split_city(raw)
 return " ".join(re.sub(r"[^0-9a-z]+"," ",company.casefold()).split())

def amount(raw):
 s=str(raw or "").strip().replace("$","").replace(",","")
 if not re.fullmatch(r"\d+(?:\.\d{2})?",s):return None
 try:return Decimal(s)
 except InvalidOperation:return None

def read_sources(path):
 with Path(path).open(encoding="utf-8-sig",newline="") as f:
  rows=list(csv.DictReader(f))
 if not 1<=len(rows)<=18:raise ValueError("Bounded 1..18 official reports required")
 seen=set()
 for row in rows:
  label=row.get("report_id","");p=urlparse(row.get("source_url",""))
  if (not label or label in seen or p.scheme!="https" or
   p.hostname!="www.mississauga.ca" or not p.path.startswith("/wp-content/uploads/") or
   not p.path.lower().endswith(".pdf") or not re.fullmatch(r"202\d-(0[1-9]|1[0-2])",row.get("report_month",""))):
   raise ValueError("Invalid or duplicate official source")
  seen.add(label)
 return rows

def collect_report_rows(sources,fetch_pdf,parse_pdf):
 observations=[];report_audit=[]
 for spec in sources:
  url=spec["source_url"]
  try:
   content=fetch_pdf(url,4_000_000,expected_host="www.mississauga.ca",expected_type="pdf")
   rows,pages=parse_pdf(content,url=url,report_name=spec["report_id"])
   for row in rows:
    observations.append({**row,"report_month":spec["report_month"],"competition":spec["competition"]})
   report_audit.append({"report_id":spec["report_id"],"source_url":url,"status":"PARSED",
    "candidate_rows":len(rows),"pages":len(pages),"sha256":hashlib.sha256(content).hexdigest()})
  except Exception as e:
   report_audit.append({"report_id":spec["report_id"],"source_url":url,"status":"FAILED",
    "error_type":type(e).__name__,"error":str(e)[:180]})
 return observations,report_audit

def analyze(observations):
 groups=defaultdict(list);held=[];seen=set()
 for row in observations:
  raw=row.get("vendor_raw","");vendor,city=split_city(raw);key=normalize_name(raw)
  pid=str(row.get("procurement_id") or "").upper();money=amount(row.get("award_amount_displayed"))
  url=str(row.get("source_url") or "")
  if not key or not pid or money is None or not url.startswith("https://"):
   held.append({"reason":"MISSING_VENDOR_PROCUREMENT_AMOUNT_OR_SOURCE","source_row":row});continue
  identity=(pid,key,str(money))
  record={"procurement_id":pid,"vendor_as_published":raw,"vendor_name_candidate":vendor,
    "vendor_location_in_report":city,"reported_amount":str(money),
    "reported_amount_basis":"PUBLISHED_ACQUISITION_VALUE_NOT_FINAL_COST",
    "report_month":row.get("report_month","UNKNOWN"),"competition":row.get("competition","UNKNOWN"),
    "project_description":row.get("description_raw",""),"source_url":url,
    "source_page":row.get("source_page"),"source_pdf_sha256":row.get("source_pdf_sha256",""),
    "legal_identity_verified":False,"performance_verified":False}
  if identity in seen:
   held.append({"reason":"SAME_VENDOR_PROCUREMENT_VALUE_REAPPEARS","record":record});continue
  seen.add(identity);groups[key].append(record)
 cases=[]
 for key,records in sorted(groups.items()):
  records.sort(key=lambda r:(r["report_month"],r["procurement_id"]))
  unique={r["procurement_id"] for r in records}
  if len(unique)<2:continue
  total=sum((Decimal(r["reported_amount"]) for r in records),Decimal("0"))
  cases.append({"case_id":"name-match-"+hashlib.sha256(key.encode()).hexdigest()[:16],
    "candidate_name":records[0]["vendor_name_candidate"],
    "match_basis":"NORMALIZED_NAME_ONLY_NOT_VERIFIED_LEGAL_ENTITY",
    "distinct_procurements":len(unique),"reported_amount_sum":str(total),
    "sum_disclaimer":"Sum of listed acquisition values only; not payments, final cost, overrun or wrongdoing",
    "contracts":records,"performance_status":"NOT_YET_ESTABLISHED",
    "investigation_questions":[
      "Were any previous contracts completed before later awards?",
      "What delivery schedule, change-order, final-cost and acceptance evidence exists?",
      "Did the City complete supplier evaluations and consider them in later awards?",
      "Are repeated awards explained by competitive bids, qualified suppliers and project scope?"]})
 return {"source_observations":len(observations),"unique_vendor_candidates":len(groups),
    "repeat_name_candidates":sorted(cases,key=lambda c:(-c["distinct_procurements"],c["candidate_name"])),
    "held":held,"non_findings":"Name-only cases cannot establish legal identity, poor performance or misconduct."}

def run(sources,destination,*,fetch_pdf=None,parse_pdf=None):
 if fetch_pdf is None or parse_pdf is None:
  from .municipal_live import get,parse_mississauga_pdf
  fetch_pdf=fetch_pdf or get;parse_pdf=parse_pdf or parse_mississauga_pdf
 observations,audit=collect_report_rows(read_sources(sources),fetch_pdf,parse_pdf)
 research=analyze(observations);out=Path(destination);out.mkdir(parents=True,exist_ok=True)
 status={"status":"PARTIAL_FETCH_FAILURE" if any(a["status"]!="PARSED" for a in audit)
     else "SOURCE_SAMPLE_CAPTURED_NOT_COMPLETE_COVERAGE",
     "observed_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
     "reports_total":len(audit),"reports_parsed":sum(a["status"]=="PARSED" for a in audit),
     "source_observations":research["source_observations"],
     "repeat_name_candidates":len(research["repeat_name_candidates"]),
     "historical_performance_verified":0,"report_audit":audit}
 for name,data in [("history_source_status",status),("source_observations",observations),
                   ("candidate_histories",research)]:
  (out/(name+".json")).write_text(json.dumps(data,indent=2),encoding="utf-8")
 return status

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--sources",default="config/mississauga_historical_reports.csv")
 p.add_argument("--out",default="local_results/history")
 p.add_argument("--live",action="store_true")
 args=p.parse_args()
 if not args.live:p.error("--live required to fetch official reports")
 print(json.dumps(run(args.sources,args.out),indent=2))
if __name__=="__main__":main()
