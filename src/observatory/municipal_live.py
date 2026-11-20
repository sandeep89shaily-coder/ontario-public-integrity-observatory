"""One-shot, source-bounded public municipal procurement intake.

Toronto: official OData supplier mentions.
Mississauga: exact City-published October 2026 purchasing-report PDFs.
Brampton: public bid-detail metadata, subject to robots and access checks.

Everything is a research candidate, not a published adverse finding.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from pathlib import Path

from . import toronto

REPORTS = {
    "mississauga_oct2026_competitive":
      "https://www.mississauga.ca/wp-content/uploads/2026/11/11081727/October-2026-Competitive-Acquisitions-Report.pdf",
    "mississauga_oct2026_noncompetitive":
      "https://www.mississauga.ca/wp-content/uploads/2026/11/11081727/October-2026-Non-Competitive-Acquisitions-Report.pdf",
}
BRAMPTON = {
    "T2026-161": "https://brampton.bidsandtenders.ca/Module/Tenders/en/Tender/Detail/1b55cbdd-b299-45a6-90fc-3130a2f4aaec",
    "T2026-136": "https://brampton.bidsandtenders.ca/Module/Tenders/en/Tender/Detail/3ebf9115-dcdc-4302-9cb4-6ec0a8beadc2/",
    "T2026-230": "https://brampton.bidsandtenders.ca/Module/Tenders/en/Tender/Detail/786c354d-8ee7-421f-8a6c-422629e426d9/",
}
USER_AGENT = "OntarioPublicIntegrityObservatory/0.1 (+source-check; no-login)"
MAX_PDF = 4_000_000
MAX_HTML = 800_000


def get(url, max_bytes, *, expected_host, expected_type=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != expected_host:
        raise ValueError("SOURCE_NOT_APPROVED")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        final = urllib.parse.urlsplit(resp.url)
        if final.scheme != "https" or final.hostname != expected_host:
            raise ValueError("UNAPPROVED_REDIRECT")
        if resp.status != 200:
            raise ValueError("HTTP_NOT_200")
        media = resp.headers.get_content_type()
        if expected_type == "pdf" and media not in ("application/pdf", "application/octet-stream"):
            raise ValueError("NOT_PDF_CONTENT_TYPE")
        raw = resp.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError("RESPONSE_TOO_LARGE")
    if expected_type == "pdf" and not raw.startswith(b"%PDF-"):
        raise ValueError("NOT_PDF_SIGNATURE")
    return raw


def parse_mississauga_pdf(data: bytes, *, url, report_name):
    """Use the visibly ruled official report tables; retain unparsed cells."""
    import pdfplumber
    import io
    records = []
    page_checks = []
    with pdfplumber.open(io.BytesIO(data)) as doc:
        for page_index, page in enumerate(doc.pages, 1):
            tables = page.extract_tables()
            page_count = 0
            for table in tables:
                current = ""
                for raw in table:
                    cells = [" ".join(str(x or "").split()) for x in raw]
                    if len(cells) < 4:
                        continue
                    match = re.search(r"\bPRC\d{5,8}\b", cells[0], flags=re.I)
                    if match and not cells[0].upper().startswith("TOTAL"):
                        current = match.group(0).upper()
                    if not current or any("TOTAL PRC" in s.upper() for s in cells):
                        continue
                    vendor_raw = cells[2].strip()
                    amount = cells[3].strip()
                    if not vendor_raw or not re.fullmatch(r"\$[\d,]+\.\d{2}", amount):
                        continue
                    if "VENDOR" == vendor_raw.upper() or "DEPARTMENT" in vendor_raw.upper():
                        continue
                    records.append({
                        "municipality": "Mississauga",
                        "procurement_id": current,
                        "source_report": report_name,
                        "competition_class": ("noncompetitive" if "noncompetitive" in report_name else "competitive"),
                        "description_raw": cells[1],
                        "vendor_raw": vendor_raw,
                        "award_amount_displayed": amount,
                        "amount_verified": False,
                        "contractor_identity_verified": False,
                        "performance_verified": False,
                        "source_url": url,
                        "source_page": page_index,
                        "source_pdf_sha256": hashlib.sha256(data).hexdigest(),
                        "record_status": "PDF_TABLE_CANDIDATE_NEEDS_MANUAL_REVIEW",
                    })
                    page_count += 1
            page_checks.append({"page":page_index, "tables_detected":len(tables), "award_candidates":page_count})
    return records, page_checks


class TextCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self._suppressed = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._suppressed += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._suppressed:
            self._suppressed -= 1
    def handle_data(self, text):
        if self._suppressed:
            return
        value = " ".join(text.split())
        if value: self.parts.append(value)


def robots_permission(host, url):
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url("https://" + host + "/robots.txt")
    try:
        parser.read()
        if parser.disallow_all:
            return False, "ROBOTS_DISALLOW_ALL"
        if not parser.allow_all and not parser.can_fetch(USER_AGENT, url):
            return False, "ROBOTS_DISALLOW"
        return True, "ROBOTS_ALLOWS"
    except Exception as exc:
        return False, "ROBOTS_FETCH_UNVERIFIED_" + type(exc).__name__


def fetch_brampton_metadata():
    outcome = []
    for bid, url in BRAMPTON.items():
        permitted, reason = robots_permission("brampton.bidsandtenders.ca", url)
        if not permitted:
            outcome.append({"bid_id":bid, "url":url, "status":"BLOCKED", "reason":reason})
            continue
        try:
            raw = get(url, MAX_HTML, expected_host="brampton.bidsandtenders.ca")
            parser = TextCollector()
            parser.feed(raw.decode("utf-8", errors="replace"))
            text = " | ".join(parser.parts)
            # Labels are not robust structured data. Do not manufacture award evidence.
            outcome.append({
                "bid_id":bid, "url":url, "status":"PUBLIC_PAGE_RETRIEVED_REVIEW_ONLY",
                "sha256":hashlib.sha256(raw).hexdigest(),
                "has_awarded_word": bool(re.search(r"\bAwarded\b", text, re.I)),
                "has_award_date_label":"Bid Awarded Date" in text,
                "verified_awarded_supplier": False,
                "text_excerpt": text[:1500],
            })
        except Exception as exc:
            outcome.append({"bid_id":bid,"url":url,"status":"FAILED",
                            "reason":type(exc).__name__, "detail":str(exc)[:180]})
    return outcome


def run(out: Path, *, pdf_fetch=get, toronto_fetch=None, brampton_fetch=fetch_brampton_metadata):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    observed = dt.datetime.now(dt.timezone.utc).isoformat()
    toronto_status = toronto.collect(out / "toronto", fetch=toronto_fetch or toronto.fetch_page,
                                    pages=1, page_size=25, observed=observed)
    miss_records, miss_reports = [], []
    for label, url in REPORTS.items():
        try:
            data = pdf_fetch(url, MAX_PDF, expected_host="www.mississauga.ca", expected_type="pdf")
            rows, pages = parse_mississauga_pdf(data, url=url, report_name=label)
            miss_records.extend(rows)
            miss_reports.append({"report":label,"status":"PARSED_CANDIDATES","pages":pages,
                                 "bytes":len(data),"candidates":len(rows)})
        except Exception as exc:
            miss_reports.append({"report":label,"status":"FAILED",
                                 "reason":type(exc).__name__,"detail":str(exc)[:200]})
    (out / "mississauga_candidates.json").write_text(json.dumps(miss_records, indent=2),encoding="utf-8")
    (out / "mississauga_report_status.json").write_text(json.dumps(miss_reports, indent=2),encoding="utf-8")
    brampton = brampton_fetch()
    (out / "brampton_status.json").write_text(json.dumps(brampton,indent=2),encoding="utf-8")
    summary = {
        "status": "BOUNDED_PILOT_COMPLETED_WITH_SOURCE_ERRORS_VISIBLE",
        "observed_at_utc": observed,
        "toronto_supplier_mentions": toronto_status["supplier_award_mentions"],
        "toronto_fetch_status": toronto_status["status"],
        "mississauga_report_candidates": len(miss_records),
        "mississauga_reports": miss_reports,
        "brampton_pages_retrieved": sum(r["status"]=="PUBLIC_PAGE_RETRIEVED_REVIEW_ONLY" for r in brampton),
        "brampton_sources": brampton,
        "historical_contract_performance_verified": 0,
        "legal_entity_links_verified": 0,
        "note": "Source observations are not misconduct findings. Bounded source batch, not exhaustive municipal history.",
    }
    (out / "LIVE_INTAKE_STATUS.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--live",action="store_true", help="Required to make external source requests")
    p.add_argument("--out", default="local_results/pilot")
    a = p.parse_args()
    if not a.live: p.error("--live required")
    print(json.dumps(run(Path(a.out)), indent=2))


if __name__=="__main__":
    main()
