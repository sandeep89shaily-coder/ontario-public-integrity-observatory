"""Grant-only Brampton Advance Brampton Fund research, NOT a misconduct scoring model."""
from __future__ import annotations
import argparse,datetime as dt,hashlib,io,json,re
from collections import defaultdict,Counter
from decimal import Decimal,InvalidOperation
from pathlib import Path

SOURCES={
 "2024":"https://www.brampton.ca/EN/City-Hall/grants/Documents/2024%20Approved%20ABF%20Applicants%20%28For%20Web%29%20V.2.pdf",
 "2025":"https://www.brampton.ca/EN/City-Hall/grants/Documents/2025%20Advance%20Brampton%20Fund/2025%20Advance%20Brampton%20Fund%20Approved%20Applicants%20%28For%20Web%20V.%201%29.pdf",
 "2026":"https://www.brampton.ca/EN/City-Hall/grants/Documents/2026%20Advance%20Brampton%20Fund/2026-Advance-Brampton-Fund-Approved-Recipients.pdf",
}
HEADINGS=re.compile(r"(New\s+and\s+Small|Developing|Amplifying)\s+(?:Projects?\s+)?(?:Approved\s+Applicants|Recipients)",re.I)
AREAS={"Arts and Culture","Community Safety","Recreation"}
MONEY=re.compile(r"^\s*\$\s*\d[\d,]*(?:\.\d{1,2})?\s*$")

def stream_label(text):
    hits=list(HEADINGS.finditer(" ".join(str(text or "").split())))
    if not hits:return None
    word=hits[-1].group(1).casefold()
    return "New and Small" if "small" in word else "Developing" if "developing" in word else "Amplifying"

def key_for(name):
    # Exact normalized-name candidate only. Never infer shared legal identity.
    return " ".join(re.sub(r"[^a-z0-9]+"," ",str(name).casefold()).split())

def parse_money(s):
    if not MONEY.fullmatch(str(s)):return None
    try:return Decimal(str(s).replace("$","").replace(",","").strip())
    except InvalidOperation:return None

def parse_pdf(raw,year,url):
    import pdfplumber
    records=[];held=[];pages=[]
    digest=hashlib.sha256(raw).hexdigest()
    current=None
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page_index,page in enumerate(pdf.pages,1):
            tables=sorted(page.find_tables(),key=lambda t:t.bbox[1])
            count=0
            for t in tables:
                before=page.crop((0,0,page.width,max(0,t.bbox[1]))).extract_text() or ""
                current=stream_label(before) or current
                for row_index,cells in enumerate(t.extract()):
                    if not cells:continue
                    cols=[" ".join(str(x or "").split()) for x in cells]
                    h=stream_label(" ".join(cols))
                    if h:current=h;continue
                    if len(cols)<3:continue
                    name,area,printed_amount=cols[:3]
                    amount=parse_money(printed_amount)
                    if amount is None:continue
                    if not name or len(name)>350 or area not in AREAS:
                        held.append({"year":year,"page":page_index,"row":row_index,
                                     "status":"UNRECOGNIZED_TABLE_FORMAT","cells":cols[:3]})
                        continue
                    records.append({"year":year,"organization_as_published":name,
                        "program_area":area,"grant_stream":current or "UNKNOWN",
                        "approved_amount_cad":str(amount),
                        "source_url":url,"source_page":page_index,
                        "source_pdf_sha256":digest,"table_row":row_index,
                        "source_type":"APPROVED_AWARD_NOT_DISBURSEMENT",
                        "legal_identity_verified":False,"payment_verified":False,
                        "evaluation_scores_verified":False,"closeout_verified":False})
                    count+=1
            pages.append({"page":page_index,"tables":len(tables),"award_entries":count})
    return records,held,pages

def analyze(records):
    by_year=defaultdict(list);by_name=defaultdict(list);same=defaultdict(list)
    for r in records:
        by_year[r["year"]].append(r)
        by_name[key_for(r["organization_as_published"])].append(r)
        same[(r["year"],key_for(r["organization_as_published"]))].append(r)
    summaries={}
    for year,rows in sorted(by_year.items()):
        streams=defaultdict(list)
        for row in rows:streams[row["grant_stream"]].append(row)
        def total(rs):return str(sum((Decimal(x["approved_amount_cad"]) for x in rs),Decimal("0")))
        summaries[year]={"approved_entries":len(rows),"approved_sum_cad":total(rows),
          "stream_breakdown":{s:{"count":len(v),"approved_sum_cad":total(v)}
                              for s,v in sorted(streams.items())},
          "actual_payments_obtained":False,"closeout_records_obtained":False}
    continuities=[]
    for key,rows in sorted(by_name.items()):
        years=sorted({r["year"] for r in rows})
        if len(years)<2:continue
        continuities.append({"case_id":"name-only-"+hashlib.sha256(key.encode()).hexdigest()[:14],
          "name_as_reported_example":rows[0]["organization_as_published"],
          "years":years,"matching_rule":"EXACT_NAME_NORMALIZED_NOT_LEGAL_IDENTITY",
          "source_awards":[{"year":r["year"],"stream":r["grant_stream"],
             "amount_cad":r["approved_amount_cad"],"page":r["source_page"],
             "source_url":r["source_url"]} for r in rows],
          "status":"NON_ADVERSE_CONTINUITY_REVIEW_ONLY",
          "unverified_controls":["Actual eligibility at decision date",
                                 "Three evaluator scores and final approval",
                                 "Grant agreement and actual payment dates",
                                 "Project end date, close-out acceptance and outcomes"]})
    same_year=[{"year":y,"name_as_reported":rows[0]["organization_as_published"],
                 "streams":sorted({r["grant_stream"] for r in rows}),
                 "status":"MULTIPLE_ENTRIES_TO_RECONCILE_NOT_WRONGDOING"}
               for (y,k),rows in sorted(same.items()) if len(rows)>1]
    return summaries,continuities,same_year

def run(out,fetch=None):
    if fetch is None:
        from .municipal_live import get
        fetch=get
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    records=[];holds=[];checks=[]
    for year,url in SOURCES.items():
        try:
            raw=fetch(url,4_000_000,expected_host="www.brampton.ca",expected_type="pdf")
            if not raw.startswith(b"%PDF-"):raise ValueError("Invalid PDF signature")
            entries,held,pages=parse_pdf(raw,year,url)
            records+=entries;holds+=held
            checks.append({"year":year,"status":"PDF_PARSED","awards_extracted":len(entries),
              "unknown_stream":sum(r["grant_stream"]=="UNKNOWN" for r in entries),
              "pdf_sha256":hashlib.sha256(raw).hexdigest(),"page_checks":pages})
        except Exception as exc:
            checks.append({"year":year,"status":"FAILED","type":type(exc).__name__,
                           "detail":str(exc)[:180],"url":url})
    summaries,continuities,multi=analyze(records)
    result={"date_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "scope":"Brampton Advance Brampton Fund only — 2024 through 2026",
      "source_checks":checks,"years_parsed":sum(x["status"]=="PDF_PARSED" for x in checks),
      "approved_entries":len(records),"repeat_name_candidates":len(continuities),
      "same_year_multiple_entries":len(multi),"confirmed_grant_noncompliance":0,
      "confirmed_fraud":0,"status":"APPROVED_AWARDS_SOURCE_RESEARCH_NOT_FINDINGS",
      "unknown":["actual payment tranches","eligibility score sheets",
                 "signed grant agreements","accepted close-out reports","project outcomes"]}
    for name,obj in (("status.json",result),("grants_approved.json",records),
        ("held_pdf_rows.json",holds),("year_summary.json",summaries),
        ("cross_year_continuity.json",continuities),("same_year_entries.json",multi)):
        (out/name).write_text(json.dumps(obj,indent=2),encoding="utf-8")
    (out/"RECORDS_REQUEST_DRAFT_NOT_SENT.md").write_text(
      "# Draft — Brampton Advance Brampton Fund records enquiry (NOT SENT)\n\n"
      "To: abf@brampton.ca\n\n"
      "Please identify existing public or routinely disclosable 2024–2026 records for: "
      "(1) application eligibility and three-reviewer scoring aggregates by year/stream, "
      "(2) approvals and funding agreements, (3) aggregate approved-versus-actually-paid "
      "tranches, holdbacks, cancellations and recovery, (4) close-out reports due/submitted/"
      "accepted by applicable program deadlines, (5) program-wide delivered project outcomes, "
      "and (6) documented conflicts-management procedures. "
      "A 2025 New and Small project could have a close-out deadline in March 2026, "
      "after 2026 applications were submitted. Please clarify how the City evaluated compliance "
      "at each decision date. We seek no unnecessary personal details or bank records. "
      "Please identify MFIPPA fees in advance. This enquiry makes no allegation.\n",
      encoding="utf-8")
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--live",action="store_true")
    ap.add_argument("--out",default="local_results/grants")
    a=ap.parse_args()
    if not a.live:ap.error("--live required to fetch official grants")
    print(json.dumps(run(a.out),indent=2))
if __name__=="__main__":main()
