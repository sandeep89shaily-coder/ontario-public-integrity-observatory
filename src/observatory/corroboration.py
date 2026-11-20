"""Corroborate three municipal decisions against official primary sources.

A missing record means NOT_OBSERVED, not that the record does not exist.
No named individual or recipient is accused of wrongdoing in these outputs.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, io, json, re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .municipal_live import get

MISS_INDEX = "https://www.mississauga.ca/services-and-programs/business/doing-business-with-the-city/purchasing-reports/"
MISS_BYLAW = "https://www.mississauga.ca/wp-content/uploads/2025/10/01081514/Procurement-By-law-0013-2022.pdf"
TORONTO_REPORT = "https://www.toronto.ca/legdocs/mmis/2026/gg/bgrd/backgroundfile-285460.pdf"
TORONTO_DECISION = "https://secure.toronto.ca/council/agenda-item.do?item=2026.GG28.2"
BRAMPTON_2025_GUIDE = "https://www.brampton.ca/EN/City-Hall/grants/Documents/2025%20Advance%20Brampton%20Fund/2025%20Advance%20Brampton%20Fund%20Guidelines%20V1.0.pdf"
BRAMPTON_2025_NEWS = "https://www.brampton.ca/EN/City-Hall/News/Pages/News-Release.aspx/1483"
BRAMPTON_ARTS_DASHBOARD = "https://performancedashboard.brampton.ca/culture-community-well-being/grant-funding-directed-to-arts-and-culture-programs/"
MAX_PDF = 17_000_000
MAX_HTML = 800_000
REQUIRED = ("brampton_grants.json", "mississauga_noncompetitive.json", "toronto_decision_excerpts.json", "publication_threshold_review.json")

def normalize(text):
    return " ".join(str(text or "").split())

def source_text_pdf(raw):
    import pdfplumber
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        return normalize(" ".join(p.extract_text() or "" for p in pdf.pages))

def fetch_verified_source(url,fetch=get):
    from urllib.parse import urlsplit
    host=urlsplit(url).hostname
    if host not in ("www.mississauga.ca","www.toronto.ca","www.brampton.ca","secure.toronto.ca","performancedashboard.brampton.ca"):
        raise ValueError("Unapproved source host")
    is_pdf=url.lower().split("?")[0].endswith(".pdf")
    raw=fetch(url,MAX_PDF if is_pdf else MAX_HTML,expected_host=host,
              **({"expected_type":"pdf"} if is_pdf else {}))
    text=source_text_pdf(raw) if is_pdf else normalize(
        re.sub(r"<[^>]+>"," ",raw.decode("utf-8","replace")))
    return {"source_url":url,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),
            "text":text}

def validate_toronto_report(text):
    required=("6051950","3,180,416","1,764,477","4,944,893","1,514,477",
              "250,000","4,382,645","2,618,168","2022","2025")
    missing=[x for x in required if x not in text]
    if missing:return {"status":"HOLD_SOURCE_TEXT_MISSING_REQUIRED_VALUES","missing":missing}
    calculations={
      "old_plus_2026_increase_equals_revised":3180416+1764477==4944893,
      "2026_services_plus_allowance_equals_increase":1514477+250000==1764477,
      "initial_2026_request_less_removed_contract3_equals_approved_increase":4382645-2618168==1764477,
      "2022_and_2025_amendments_explain_current_order":2680611+300000+199805==3180416,
      "capital_plan_total_matches_reported_net_HST_amount":759927+781205+254400==1795532,
    }
    return {"status":"PUBLISHED_AMOUNTS_RECONCILED_NOT_ACTUAL_PAYMENTS" if all(calculations.values()) else "HOLD_ARITHMETIC",
            "calculations":calculations,
            "original_po_transfer_warning":"Original 2018 PO 6047779 and replacement 6051950 must not be added; the latter excluded earlier expenditures.",
            "scope_caveat":"Revised work removed Contracts 3/4; comparison is not like-for-like project cost.",
            "delivery_caveat":"City report attributes Islington delay partly to TTC conflicts; no contractor fault inferred.",
            "actual_expenditure_verified":False,"completion_verified":False}

def check_mississauga_threshold(rows,policy_text,document_texts):
    results=[]
    policy_present=all(term in policy_text for term in
        ("SECTION 13","SECTION 27","Single Source","Information Reports"))
    for row in rows:
        pid=row["procurement_id"];amt=row["reported_amount"]
        url=row["source_url"]
        source=document_texts.get(url)
        present=bool(source and pid in source and amt in source)
        results.append({
          "procurement_id":pid,"displayed_amount":amt,"source_pdf_url":url,
          "published_pdf_amount_and_id_confirmed":present,
          "published_by_law_context_verified":policy_present,
          "basis_status":"PUBLICATION_COVERAGE_QUESTION_NOT_PROCUREMENT_NONCOMPLIANCE",
          "missing_documents":[
             "Applicable procurement request form and original contract ceiling",
             "Schedule A single-source criterion/exception rationale, if required by classification",
             "Approval delegation and award authorization",
             "Whether published figure is initial award, amendment, purchase order or line item",
             "Actual payments and deliverables by contract (not in monthly report)"],
          "determination":"UNRESOLVED_ROUTINE_DISCLOSURE_REQUEST",
        })
    return results

def summarize_grants(grants,matches,news_text,guide_text):
    years=defaultdict(lambda:{"count":0,"approved_total":Decimal("0"),"source_urls":set()})
    for g in grants:
        year=g["year"]
        raw=g["approved_amount_as_reported"].replace("$","").replace(",","")
        try:amount=Decimal(raw)
        except InvalidOperation:raise ValueError("Invalid grant amount")
        years[year]["count"]+=1;years[year]["approved_total"]+=amount
        years[year]["source_urls"].add(g["source_url"])
    result={}
    for year,x in sorted(years.items()):
        result[year]={"award_entries":x["count"],"approved_total_cad":str(x["approved_total"]),
                      "recipient_list_urls":sorted(x["source_urls"]),
                      "individual_payments_verified":False,"deliverables_verified":False}
    announcement_confirmed=("1.75 million" in news_text.lower() and "159" in news_text)
    policy_confirmed=("Project Close Out Report" in guide_text and
                      "ineligible for future funding" in guide_text)
    return {"by_year":result,"year_2025_official_announcement_cross_check":
          ("EXACT_AGGREGATE_MATCH" if announcement_confirmed and
           result.get("2025",{}).get("approved_total_cad")=="1750000" and
           result["2025"]["award_entries"]==159 else "NOT_VERIFIED"),
         "2025_program_closeout_obligations_verified":policy_confirmed,
         "cross_year_name_matches_not_legal_identity":len(matches),
         "ineligible_grants_proven":0,
         "status":"APPROVED_VALUES_NOT_PAYMENTS_OR_PERFORMANCE",
         "missing_documents":[
            "2025 grant agreements, stream and project end-date list",
            "Approved close-out submissions and City acceptance status (redacted as required)",
            "2025 actual grant payments, holdbacks and any repayments",
            "2026 eligibility check including 2025 close-out compliance",
            "Annual grant outcomes / expenditures and any public aggregate impact report",
         ]}

def compare_brampton_arts_dashboard(grants,dashboard_text):
    """Different populations: award approvals vs dashboard estimated disbursements.

    This comparison must NOT be represented as unspent money or a fraud discrepancy.
    """
    rows=[r for r in grants if r.get("year")=="2025" and
          r.get("program_area_as_reported")=="Arts and Culture"]
    approved=sum((Decimal(r["approved_amount_as_reported"].replace("$","").replace(",",""))
                    for r in rows),Decimal("0"))
    dashboard_confirmed=all(s in dashboard_text for s in
        ("646,244","2025 Estimate","51 community-led projects"))
    base={
        "2025_recipient_list_arts_entries":len(rows),
        "2025_approved_arts_list_total_cad":str(approved),
        "dashboard_url":BRAMPTON_ARTS_DASHBOARD,
        "2025_dashboard_population_and_scope_verified":dashboard_confirmed,
        "comparison_status":"NOT_LIKE_FOR_LIKE_ESTIMATE_DISBURSEMENT_VS_APPROVALS",
        "actual_grant_level_payments_verified":False,
        "questions":[
          "Does the dashboard's 51-project count refer to the same population as the 53 approved Arts and Culture recipient entries?",
          "Does the dashboard's funding definition include a separate Creative Space Improvement stream or exclude any approved projects?",
          "Which awards were actually disbursed, withheld, cancelled, carried forward or still subject to reporting at the dashboard cut-off?",
          "Was the 2025 dashboard estimate subsequently revised, and what is the final reconciled program statement?"
        ],
        "no_misuse_inferred":True,
    }
    if dashboard_confirmed:
        base.update({"dashboard_2025_estimated_disbursed_cad":"646244",
                     "dashboard_2025_reported_project_count":51,
                     "nominal_difference_approved_vs_estimate_cad":str(approved-Decimal("646244")),
                     "difference_is_not_verified_unpaid_funds":True})
    return base

def request_drafts(thresholds,toronto,grants):
    ids=", ".join(r["procurement_id"] for r in thresholds)
    return f"""# Draft routine-disclosure enquiries — NOT SENT

These are records requests, not allegations. No private financial identifiers or personal records are requested.

## Mississauga Procurement Services
To: purchasing@mississauga.ca
Subject: Clarification of published non-competitive acquisition values and procurement authorizations

I am reviewing the City's public monthly purchasing reports and Procurement By-law 0013-2022 for a nonprofit public accountability project.
Could you clarify why procurement IDs {ids} appear in the May/July 2026 non-competitive information reports at reported amounts below the public $125,000 threshold? In particular, does the threshold apply to the entire contract/ceiling, cumulative orders, or individual printed lines?
For each procurement ID, please identify any routinely releasable Procurement Request Form, the approval/exception authority, the Schedule A justification where applicable, the original contract amount and any amendments, and any releasable record of payments to date. Redacted records or aggregate totals are welcome.
Please advise whether a formal MFIPPA request is needed, and quote any fees before processing.

## Toronto Water / Procurement
Subject: Public records supporting WSP PO 6051950 amendment and delivered costs

In connection with council item GG28.2 (April 8, 2026) and the March 23 staff report, please identify records showing the 2022 and 2025 PO amendments, the January 2026 request and resulting $1,764,477 approved amendment, contract 2 service schedule, actual payments to date, accepted deliverables, and any subsequent change orders.
Please clarify the treatment of the 2018 original PO 6047779 and the 2026 revised scope so expenditures are not counted twice. Please identify any later records for contracting work removed from the 2026 amendment. We are not alleging wrongdoing.

## Brampton Advance Brampton Fund
To: abf@brampton.ca
Subject: 2025 Advance Brampton Fund program-wide closeout and payment reconciliation

Please advise whether a public 2025 program closeout or outcomes report is available. If so, can it show, by grant stream, how many funded projects submitted approved close-out reports, how many required revisions, final amounts disbursed versus awarded, holdbacks not paid, and amounts recovered, if any?
Could you also identify any existing administrative record or published method for verifying compliance with prior-year close-out obligations when assessing a 2026 application, including any documented exception process?
We prefer anonymized program-level aggregates before considering specific redacted case records. We do not infer wrongdoing from repeat funding. Please flag whether these requests require MFIPPA processing and any costs.

All enquiries are drafts; human review and sending approval remain required.
"""

def run(source_dir,out,*,fetch=get):
    source_dir=Path(source_dir);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    data={}
    for name in REQUIRED+("cross_year_grant_name_matches.json",):
        p=source_dir/name
        if not p.exists():raise FileNotFoundError("Missing input from live collection: "+name)
        data[name]=json.loads(p.read_text(encoding="utf-8"))
    thresholds=data["publication_threshold_review.json"]
    urls=list(dict.fromkeys([r["source_url"] for r in thresholds]))
    source_urls=[MISS_BYLAW,MISS_INDEX,TORONTO_REPORT,TORONTO_DECISION,
                 BRAMPTON_2025_GUIDE,BRAMPTON_2025_NEWS,BRAMPTON_ARTS_DASHBOARD]+urls
    captures={};audit=[]
    for url in source_urls:
        try:
            item=fetch_verified_source(url,fetch=fetch)
            captures[url]=item["text"]
            audit.append({k:item[k] for k in ("source_url","sha256","bytes")} |
                        {"status":"SOURCE_RETRIEVED"})
        except Exception as exc:
            audit.append({"source_url":url,"status":"SOURCE_UNAVAILABLE",
                          "error":type(exc).__name__,"detail":str(exc)[:160]})
    toronto=validate_toronto_report(captures.get(TORONTO_REPORT,""))
    toronto["source_url"]=TORONTO_REPORT
    toronto["decision_url"]=TORONTO_DECISION
    toronto["decision_record_confirmed"]=("6051950" in captures.get(TORONTO_DECISION,"") and
        "1,764,477" in captures.get(TORONTO_DECISION,""))
    miss=check_mississauga_threshold(thresholds,captures.get(MISS_BYLAW,""),
             {url:captures[url] for url in urls if url in captures})
    brampton=summarize_grants(data["brampton_grants.json"],
              data["cross_year_grant_name_matches.json"],
              captures.get(BRAMPTON_2025_NEWS,""),captures.get(BRAMPTON_2025_GUIDE,""))
    arts_comparison=compare_brampton_arts_dashboard(
         data["brampton_grants.json"],captures.get(BRAMPTON_ARTS_DASHBOARD,""))
    brampton["guideline_source_url"]=BRAMPTON_2025_GUIDE
    brampton["official_announcement_url"]=BRAMPTON_2025_NEWS
    result={"run_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "status":"CORROBORATION_AUDIT_NO_ALLEGATIONS",
        "mississauga_source_rows_confirmed":sum(r["published_pdf_amount_and_id_confirmed"] for r in miss),
        "toronto_arithmetic_reconciled":toronto["status"]=="PUBLISHED_AMOUNTS_RECONCILED_NOT_ACTUAL_PAYMENTS",
        "brampton_2025_award_rollup_confirmed":brampton["year_2025_official_announcement_cross_check"]=="EXACT_AGGREGATE_MATCH",
        "brampton_arts_dashboard_scope_verified":arts_comparison["2025_dashboard_population_and_scope_verified"],
        "verified_actual_payments_by_contract":0,
        "verified_grant_project_closeouts":0,
        "verified_fraud_findings":0,
        "source_audit":audit,
        "caveat":"Official reported awards, approvals and public aggregate totals are not proof of disbursement, effective procurement controls or wrongdoing."}
    for name,obj in (("audit_status.json",result),("mississauga_control_review.json",miss),
         ("toronto_wsp_reconciliation.json",toronto),("brampton_grant_reconciliation.json",brampton),
         ("brampton_arts_dashboard_scope_review.json",arts_comparison)):
        (out/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")
    (out/"RECORD_REQUESTS_DRAFT_NOT_SENT.md").write_text(
         request_drafts(miss,toronto,brampton),encoding="utf-8")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",default="local_results/integrity")
    p.add_argument("--out",default="local_results/corroboration")
    p.add_argument("--live",action="store_true")
    args=p.parse_args()
    if not args.live:p.error("--live required for independent primary-source downloads")
    result=run(args.source_dir,args.out)
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
