"""Bounded, source-preserving Toronto procurement importer. No allegations or private data.
Adapted independently from GTA Radar's toronto_procurement_odata.py (source audit Nov 2026).
Source: City of Toronto published procurement OData feed.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://secure.toronto.ca/c3api_data/v2/DataAccess.svc/pmmd_solicitations/"
ENTITY = "feis_solicitation_published"
PORTAL = "https://www.toronto.ca/business-economy/doing-business-with-the-city/searching-bidding-on-city-contracts/toronto-bids-portal/"
MAX_BYTES = 1_500_000
AWARD_FIELDS = (
    "municipality", "contract_id", "vendor_name", "award_date",
    "award_amount_cad", "source_url", "source_record_id", "source_page_url",
    "raw_status", "contract_title", "client_division", "currency_verified",
    "amount_verified", "identity_verified", "performance_verified",
    "evidence_status", "observed_at_utc",
)


def endpoint(skip: int, top: int) -> str:
    if skip < 0 or not 1 <= top <= 200:
        raise ValueError("Bounds exceeded")
    return BASE + ENTITY + "?" + urlencode({
        "$skip": skip, "$top": top,
        "$format": "application/json;odata.metadata=none",
    })


def fetch_page(url: str) -> dict:
    if not url.startswith(BASE + ENTITY + "?"):
        raise ValueError("Unapproved source URL")
    req = Request(url, headers={"User-Agent": "OntarioPublicIntegrityObservatory/0.1",
                                 "Accept": "application/json"})
    with urlopen(req, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError("Unexpected HTTP response")
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("Oversized source response")
    return json.loads(payload)


def _text(value, maximum=400):
    return " ".join(str(value or "").split())[:maximum]


def _date(value):
    if not value:
        return ""
    value = str(value)
    # Keep original uncommon source date formats in raw data; don't fabricate conversion.
    if re.match(r"^\d{4}-\d{2}-\d{2}", value):
        try:
            return dt.date.fromisoformat(value[:10]).isoformat()
        except ValueError:
            return ""
    return ""


def _money(value):
    # Not all raw OData amounts have an established currency/tax basis.
    # Preserve original value in source JSON; never assert CAD unless verified.
    if isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)) and value >= 0:
        return str(value)
    if isinstance(value, str) and re.fullmatch(r"\d+(?:\.\d{1,2})?", value.strip()):
        return value.strip()
    return ""


def extract(page: dict, page_url: str, observed: str):
    if not isinstance(page, dict) or not isinstance(page.get("value"), list):
        raise ValueError("OData response missing value list")
    records, awards, holds = [], [], []
    for index, raw in enumerate(page["value"]):
        if not isinstance(raw, dict):
            holds.append({"row": index, "reason": "NOT_OBJECT"})
            continue
        doc_id = _text(raw.get("Solicitation_Document_Number"), 32)
        if not re.fullmatch(r"\d{8,12}", doc_id):
            holds.append({"row": index, "reason": "INVALID_SOLICITATION_ID"})
            continue
        status = _text(raw.get("Status"), 100)
        record = {
            "solicitation_id": doc_id, "raw_status": status,
            "title": _text(raw.get("Posting_Title")), "client_division": _text(raw.get("Client_Division")),
            "issue_date_raw": raw.get("Issue_Date"), "closing_date_raw": raw.get("Closing_Date"),
            "source_page_url": page_url, "source_dataset_url": BASE + ENTITY,
            "source_row_sha256": hashlib.sha256(json.dumps(raw, sort_keys=True, default=str).encode()).hexdigest(),
            "observed_at_utc": observed,
            "awarded_suppliers_raw": raw.get("Awarded_Suppliers"),
        }
        records.append(record)
        suppliers = raw.get("Awarded_Suppliers")
        if not isinstance(suppliers, list) or not suppliers:
            continue
        for supplier_index, supplier in enumerate(suppliers):
            if not isinstance(supplier, dict):
                holds.append({"solicitation_id": doc_id, "supplier_index": supplier_index,
                              "reason": "INVALID_SUPPLIER_OBJECT"})
                continue
            name = _text(supplier.get("Successful_Bidder"), 250)
            if not name:
                holds.append({"solicitation_id": doc_id, "supplier_index": supplier_index,
                              "reason": "MISSING_SUPPLIER_NAME"})
                continue
            amount = _money(supplier.get("Award_Amount"))
            awards.append({
                "municipality": "Toronto", "contract_id": doc_id,
                "vendor_name": name, "award_date": _date(supplier.get("Date_Awarded")),
                "award_amount_cad": "",  # source currency/basis needs independent checking
                "source_url": BASE + ENTITY, "source_record_id": doc_id,
                "source_page_url": page_url, "raw_status": status,
                "contract_title": record["title"], "client_division": record["client_division"],
                "currency_verified": "false", "amount_verified": "false",
                "identity_verified": "false", "performance_verified": "false",
                "evidence_status": "SOURCE_REPORTED_AWARDED_SUPPLIER_REVIEW_REQUIRED",
                "observed_at_utc": observed,
                "raw_amount_unverified": supplier.get("Award_Amount"),
                "parsed_raw_amount_unverified": amount,
                "raw_award_date": supplier.get("Date_Awarded"),
                "source_row_sha256": record["source_row_sha256"],
                "supplier_index": supplier_index,
            })
    return records, awards, holds


def collect(out_dir: str | Path, *, fetch=fetch_page, pages=2, page_size=50,
            observed=None):
    if not 1 <= pages <= 10 or not 1 <= page_size <= 200:
        raise ValueError("Collection limits exceeded")
    observed = observed or dt.datetime.now(dt.timezone.utc).isoformat()
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    records, awards, holds, audit = [], [], [], []
    seen = set()
    for n in range(pages):
        url = endpoint(n * page_size, page_size)
        try:
            data = fetch(url)
            recs, extracted, held = extract(data, url, observed)
            records.extend(recs)
            holds.extend(held)
            for item in extracted:
                # Vendor names alone never establish a legal-entity match.
                key = (item["contract_id"], item["vendor_name"].casefold(), item["supplier_index"])
                if key in seen:
                    holds.append({"solicitation_id": item["contract_id"], "reason": "DUPLICATE_AWARD_CANDIDATE"})
                    continue
                seen.add(key)
                awards.append(item)
            audit.append({"page": n + 1, "source": url, "status": "FETCHED",
                          "solicitations": len(recs), "awards": len(extracted)})
            if len(data["value"]) < page_size:
                break
        except Exception as exc:
            audit.append({"page": n + 1, "source": url, "status": "FAILED",
                          "error": type(exc).__name__, "detail": str(exc)[:240]})
            break
    report = {
        "status": "PARTIAL_FAILURE" if any(x["status"] == "FAILED" for x in audit)
                  else "SOURCE_BATCH_CAPTURED_NOT_FULL_HISTORICAL_COVERAGE",
        "source": BASE + ENTITY, "observed_at_utc": observed,
        "pages_requested": pages, "solicitations_seen": len(records),
        "supplier_award_mentions": len(awards), "held_records": len(holds),
        "page_audit": audit,
        "limitations": [
            "A solicitation is not automatically a completed contract.",
            "Awarded supplier names do not establish verified legal identity.",
            "Source-reported award amounts lack verified CAD and tax basis.",
            "No contractor performance or final contract cost evidence has been collected.",
            "Only bounded fetched OData pages were observed, not the entire history.",
        ],
    }
    (root / "toronto_status.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (root / "toronto_source_records.json").write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")
    (root / "toronto_supplier_mentions.json").write_text(json.dumps(awards, indent=2, default=str), encoding="utf-8")
    (root / "toronto_holds.json").write_text(json.dumps(holds, indent=2), encoding="utf-8")
    with (root / "toronto_award_candidates.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AWARD_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(awards)
    return report


def main():
    parser = argparse.ArgumentParser(description="Explicitly run bounded official Toronto OData collection")
    parser.add_argument("--out", default="local_results/toronto")
    parser.add_argument("--pages", type=int, default=2)
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--live", action="store_true", help="Required: make network requests")
    args = parser.parse_args()
    if not args.live:
        parser.error("No network fetch without --live")
    print(json.dumps(collect(args.out, pages=args.pages, page_size=args.page_size), indent=2))


if __name__ == "__main__":
    main()
