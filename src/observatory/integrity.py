"""Public-interest source intake: procurement exceptions, amendments, grants and registers.

A screening queue is NOT a fraud finding. Automated output consists of public
source observations and specific questions for corroboration.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .municipal_live import get, parse_mississauga_pdf

MISSISSAUGA_REPORTS = (
    "https://www.mississauga.ca/services-and-programs/business/doing-business-with-the-city/purchasing-reports/"
)
TORONTO_COUNCIL = (
    "https://secure.toronto.ca/council/report.do?meeting=2026.GG28&type=decisions"
)
GRANT_PDFS = {
    "2026": "https://www.brampton.ca/EN/City-Hall/grants/Documents/2026%20Advance%20Brampton%20Fund/2026-Advance-Brampton-Fund-Approved-Recipients.pdf",
    "2025": "https://www.brampton.ca/EN/City-Hall/grants/Documents/2025%20Advance%20Brampton%20Fund/2025%20Advance%20Brampton%20Fund%20Approved%20Applicants%20%28For%20Web%20V.%201%29.pdf",
}
REGISTRIES = {
    "brampton_interest_declarations": "https://www.brampton.ca/EN/City-Hall/Council-Committees/Pages/Term-of-Council-Declarations-of-Interest.aspx",
    "toronto_interest_declarations": "https://www.toronto.ca/city-government/accountability-operations-customer-service/access-city-information-or-records/declared-interests-registry/",
}
INDEX_MAX_BYTES = 1_000_000
MAX_PDF = 5_000_000
AMOUNT_RE = re.compile(r"^\s*\$\s*\d[\d,]*(?:\.\d{1,2})?\s*$")

class LinkExtractor(HTMLParser):
    """Extract visible anchor label and target. Never follow extracted links automatically."""
    def __init__(self):
        super().__init__()
        self.links=[]
        self.href=None
        self.labels=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.href=dict(attrs).get("href")
            self.labels=[]
    def handle_endtag(self,tag):
        if tag=="a" and self.href:
            self.links.append((" ".join(" ".join(self.labels).split()),self.href))
            self.href=None
            self.labels=[]
    def handle_data(self,data):
        if self.href:self.labels.append(data)

class CouncilSections(HTMLParser):
    """Preserve council-item headings and their visible text, excluding scripts."""
    def __init__(self):
        super().__init__()
        self.current_heading=None
        self.current_text=[]
        self.sections=[]
        self._heading_depth=0
        self._heading_chunks=[]
        self._suppress=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):
            self._suppress+=1
        if tag in ("h2","h3","h4"):
            self._heading_depth+=1
            if self._heading_depth==1:self._heading_chunks=[]
        if tag in ("p","div","li","br","section"):
            self.current_text.append(" ")
    def handle_endtag(self,tag):
        if tag in ("h2","h3","h4") and self._heading_depth:
            self._heading_depth-=1
            if self._heading_depth==0:
                heading=" ".join(" ".join(self._heading_chunks).split())
                if re.match(r"^(?:GG|CC|EX|AU)\d{1,3}\.\d+\s*-\s*",heading):
                    if self.current_heading:
                        self.sections.append((self.current_heading," ".join(" ".join(self.current_text).split())))
                    self.current_heading=heading
                    self.current_text=[]
        if tag in ("script","style","noscript") and self._suppress:
            self._suppress-=1
    def handle_data(self,data):
        if self._suppress:return
        if self._heading_depth:
            self._heading_chunks.append(data)
        elif self.current_heading:
            self.current_text.append(data)
    def finish(self):
        if self.current_heading:
            self.sections.append((self.current_heading," ".join(" ".join(self.current_text).split())))
        return self.sections

def report_pdf_links(html, *,maximum=6):
    extractor=LinkExtractor()
    extractor.feed(html)
    selected=[]
    for label,href in extractor.links:
        if not re.search(r"\b2026\b",label) or "non-competitive" not in label.casefold():
            continue
        url=urljoin(MISSISSAUGA_REPORTS,href)
        parsed=urlsplit(url)
        if (parsed.scheme=="https" and parsed.hostname=="www.mississauga.ca" and
                parsed.path.startswith("/wp-content/uploads/") and parsed.path.lower().endswith(".pdf") and
                url not in selected):
            selected.append(url)
        if len(selected)>=maximum:break
    return selected

def council_items(html,url=TORONTO_COUNCIL):
    parser=CouncilSections()
    parser.feed(html)
    result=[]
    for title,body in parser.finish():
        title_l=title.casefold()
        if "non-competitive" in title_l:
            category="NONCOMPETITIVE_DECISION_FOR_REVIEW"
        elif "amendment" in title_l or "increase to" in title_l:
            category="CONTRACT_AMENDMENT_FOR_REVIEW"
        else:
            continue
        result.append({"municipality":"Toronto","source_url":url,"source_heading":title,
            "source_text_excerpt":body[:4500],"category":category,
            "source_sha256":hashlib.sha256(body.encode()).hexdigest(),
            "factual_basis":"CITY_PUBLISHED_COUNCIL_ITEM_NOT_ADVERSE_FINDING"})
    return result

def grants_from_pdf(payload,*,year,source_url):
    import pdfplumber
    entries=[];holds=[];page_audit=[]
    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        for page_idx,page in enumerate(pdf.pages,1):
            count=0
            for table in page.extract_tables():
                for cells in table:
                    if len(cells)<3:continue
                    name=" ".join(str(cells[0] or "").split())
                    area=" ".join(str(cells[1] or "").split())
                    value=" ".join(str(cells[2] or "").split())
                    if not name or not AMOUNT_RE.fullmatch(value) or len(name)>300:
                        continue
                    if "organization name" in name.casefold() or "approved applicant" in name.casefold():
                        continue
                    if not area or len(area)>120:
                        holds.append({"year":year,"page":page_idx,"reason":"MISSING_CATEGORY"})
                        continue
                    entries.append({
                        "year":year,"municipality":"Brampton",
                        "organization_name_as_reported":name,
                        "program_area_as_reported":area,
                        "approved_amount_as_reported":value,
                        "source_url":source_url,"source_page":page_idx,
                        "source_sha256":hashlib.sha256(payload).hexdigest(),
                        "record_status":"PUBLIC_PDF_TABLE_CANDIDATE_NEEDS_VALIDATION",
                        "funds_disbursed_verified":False,
                        "grant_deliverables_verified":False,
                        "organization_identity_verified":False,
                    })
                    count+=1
            page_audit.append({"page":page_idx,"table_rows_extracted":count})
    return entries,holds,page_audit

def research_questions(category):
    if category=="NONCOMPETITIVE_PURCHASE":
        return [
            "Which legally applicable procurement exception and delegated authority justified the purchase?",
            "Were competition alternatives or market assessments documented?",
            "Is the listed amount a one-time award, amendment, renewal or cumulative purchase?",
            "Did subsequent invoices and deliverables align with approved scope and policy?",
        ]
    if category=="CONTRACT_AMENDMENT_FOR_REVIEW":
        return [
            "What was the original approved scope, amount and schedule?",
            "What documented event justified the amendment and who approved it?",
            "Are previous and revised amounts on the same tax, scope and currency basis?",
            "Do change orders and actual paid amounts corroborate the public explanation?",
        ]
    if category=="NONCOMPETITIVE_DECISION_FOR_REVIEW":
        return [
            "What legal exemption or procurement policy clause was invoked?",
            "Is there supporting exclusivity, urgency, compatibility or market evidence?",
            "What approvals and financial limits applied, and were they observed?",
        ]
    if category=="GRANT_RECIPIENT_FOR_REVIEW":
        return [
            "Did the applicant satisfy published program criteria at the decision date?",
            "What assessment and conflict-management records support the decision?",
            "Are grant agreement, deliverables, actual payment and reporting records available?",
            "Were later renewals or awards made following documented prior results?",
        ]
    return ["What primary documentary evidence would verify this decision and its chronology?"]

def neutral_queue(council,noncompetitive,grants):
    queue=[]
    for rec in council:
        queue.append({"category":rec["category"],"source_url":rec["source_url"],
            "source_title":rec["source_heading"],"evidence_excerpt":rec["source_text_excerpt"],
            "questions":research_questions(rec["category"]),
            "status":"RESEARCH_ONLY_NOT_ALLEGATION"})
    for rec in noncompetitive:
        queue.append({"category":"NONCOMPETITIVE_PURCHASE","source_url":rec["source_url"],
            "source_title":rec["procurement_id"],"evidence_excerpt":
              {"vendor":rec["vendor_raw"],"amount":rec["award_amount_displayed"],
               "description":rec["description_raw"],"source_page":rec["source_page"]},
            "questions":research_questions("NONCOMPETITIVE_PURCHASE"),
            "status":"RESEARCH_ONLY_NOT_ALLEGATION"})
    # Repeat grant recipients are neutral continuity checks, never allegations.
    groups=defaultdict(list)
    for g in grants:
        key=" ".join(re.sub(r"[^a-z0-9]+"," ",g["organization_name_as_reported"].casefold()).split())
        if key:groups[key].append(g)
    repeats=[{"name_example":rows[0]["organization_name_as_reported"],
               "years":sorted({r["year"] for r in rows}),
               "source_urls":sorted({r["source_url"] for r in rows}),
               "identity_verified":False,"status":"NAME_MATCH_ONLY_NOT_AN_ALLEGATION"}
             for rows in groups.values() if len({r["year"] for r in rows})>1]
    for g in grants:
        queue.append({"category":"GRANT_RECIPIENT_FOR_REVIEW","source_url":g["source_url"],
            "source_title":g["organization_name_as_reported"],
            "evidence_excerpt":{"year":g["year"],"amount":g["approved_amount_as_reported"],
               "priority_area":g["program_area_as_reported"],"page":g["source_page"]},
            "questions":research_questions("GRANT_RECIPIENT_FOR_REVIEW"),
            "status":"RESEARCH_ONLY_NOT_ALLEGATION"})
    return queue,repeats

def run(out,*,fetch=get):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    audit=[]; council=[]; purchases=[]; grants=[]
    def html(url):
        p=urlsplit(url)
        return fetch(url,INDEX_MAX_BYTES,expected_host=p.hostname).decode("utf-8","replace")
    try:
        doc=html(MISSISSAUGA_REPORTS)
        urls=report_pdf_links(doc,maximum=6)
        audit.append({"source":MISSISSAUGA_REPORTS,"status":"INDEX_FETCHED",
                      "matching_2026_report_links":len(urls)})
    except Exception as e:
        urls=[]
        audit.append({"source":MISSISSAUGA_REPORTS,"status":"FAILED",
                      "error_type":type(e).__name__,"detail":str(e)[:180]})
    for url in urls:
        try:
            data=fetch(url,MAX_PDF,expected_host="www.mississauga.ca",expected_type="pdf")
            records,pages=parse_mississauga_pdf(data,url=url,report_name="noncompetitive_2026")
            for x in records:
                purchases.append({**x,"review_kind":"NONCOMPETITIVE_PURCHASE"})
            audit.append({"source":url,"status":"PDF_PARSED","candidate_rows":len(records),
                          "pdf_sha256":hashlib.sha256(data).hexdigest(),"pages":len(pages)})
        except Exception as e:
            audit.append({"source":url,"status":"FAILED","error_type":type(e).__name__,
                          "detail":str(e)[:180]})
    try:
        c=html(TORONTO_COUNCIL)
        council=council_items(c)
        audit.append({"source":TORONTO_COUNCIL,"status":"HTML_PARSED",
                      "candidate_items":len(council)})
    except Exception as e:
        audit.append({"source":TORONTO_COUNCIL,"status":"FAILED",
                      "error_type":type(e).__name__,"detail":str(e)[:180]})
    for year,url in GRANT_PDFS.items():
        try:
            payload=fetch(url,MAX_PDF,expected_host="www.brampton.ca",expected_type="pdf")
            records,holds,pages=grants_from_pdf(payload,year=year,source_url=url)
            grants.extend(records)
            audit.append({"source":url,"status":"PDF_PARSED","year":year,
                          "candidate_rows":len(records),"holds":len(holds),"pages":len(pages),
                          "pdf_sha256":hashlib.sha256(payload).hexdigest()})
        except Exception as e:
            audit.append({"source":url,"status":"FAILED","year":year,
                          "error_type":type(e).__name__,"detail":str(e)[:180]})
    for name,url in REGISTRIES.items():
        try:
            data=html(url)
            audit.append({"source":url,"registry":name,"status":"PUBLIC_INDEX_RETRIEVED",
                          "byte_count":len(data.encode()),"sha256":hashlib.sha256(data.encode()).hexdigest(),
                          "declaration_entries_parsed":0,
                          "note":"Index access does NOT verify absence or presence of conflicts."})
        except Exception as e:
            audit.append({"source":url,"registry":name,"status":"FAILED",
                          "error_type":type(e).__name__,"detail":str(e)[:180]})
    queue,repeats=neutral_queue(council,purchases,grants)
    status={"observed_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "classification":"PUBLIC_SOURCE_REVIEW_ONLY_NOT_FRAUD_FINDINGS",
        "toronto_council_items":len(council),
        "mississauga_noncompetitive_entries":len(purchases),
        "brampton_grant_recipient_entries":len(grants),
        "cross_year_grant_name_matches":len(repeats),
        "review_questions_generated":len(queue),
        "actual_fraud_findings":0,
        "verified_legal_conflicts_of_interest":0,
        "verified_misuse_of_funds":0,
        "audit":audit,
        "limitations":"Uneven coverage. Missing records are unknown, never violations. Public recipients and lawful exceptions do not imply wrongdoing."}
    for name,obj in (
        ("source_status.json",status),("toronto_decision_excerpts.json",council),
        ("mississauga_noncompetitive.json",purchases),
        ("brampton_grants.json",grants),("cross_year_grant_name_matches.json",repeats),
        ("research_question_queue.json",queue)):
        (out/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")
    return status

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="local_results/integrity")
    p.add_argument("--live",action="store_true")
    a=p.parse_args()
    if not a.live:p.error("--live required to fetch official records")
    print(json.dumps(run(a.out),indent=2))
if __name__=="__main__":
    main()
