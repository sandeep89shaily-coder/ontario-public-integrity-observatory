"""Evidence-first grant decision and receipt audit.

Consumes official, publicly listed grant awards and optionally *redacted* case
metadata stored in a restricted workspace. NEVER copies raw invoices, banking,
private evaluation sheets, personal addresses or photos to public GitHub.

A value not obtained is UNKNOWN, not proof of noncompliance. This module cannot
establish invoice authenticity by appearance; independent vendor/payment evidence
is required for any stronger description.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

POLICY = {
    "2025": {
        "url": "https://www.brampton.ca/EN/City-Hall/grants/Documents/2025%20Advance%20Brampton%20Fund/2025%20Advance%20Brampton%20Fund%20Guidelines%20V1.0.pdf",
        "threshold": {"New and Small": Decimal(50), "Developing": Decimal(60), "Amplifying": Decimal(70)},
    },
    "2026": {
        "url": "https://www.brampton.ca/EN/City-Hall/grants/Documents/2026%20Advance%20Brampton%20Fund/2026%20Advance%20Brampton%20Fund%20Guidelines%20Web%20V.1pdf.pdf",
        "threshold": {"New and Small": Decimal(50), "Developing": Decimal(60), "Amplifying": Decimal(70)},
    },
}
STAGES = ("applicant_identity", "eligibility", "selection", "approval", "agreement_and_payment", "expense_authenticity", "delivery_and_closeout")
SOURCE_SHA = re.compile(r"^[0-9a-f]{64}$")


def dec(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value).replace(",", "").replace("$", ""))
    except InvalidOperation:
        return None
    return number if number.is_finite() and number >= 0 else None


def reviewed(source_id, sources):
    """Documented existence and human inspection, not independent authenticity."""
    if not source_id or source_id not in sources:
        return False
    source = sources[source_id]
    return (isinstance(source, dict) and bool(source.get("reviewed_by_human"))
            and isinstance(source.get("sha256"), str)
            and bool(SOURCE_SHA.fullmatch(source["sha256"]))
            and bool(source.get("custody_reference")))


def check(status, message, sources=(), note=None):
    return {"status": status, "question": message,
            "supporting_source_ids": list(sources), "qualification": note or ""}


def inspect(award, case=None):
    """One grant case. `case` is redacted metadata, never raw private exhibits."""
    case = case or {}
    sources = case.get("evidence_register", {})
    year = str(award.get("year", ""))
    stream = award.get("grant_stream", "UNKNOWN")
    amount = dec(award.get("approved_amount_cad"))
    if not amount or not award.get("source_url") or not award.get("organization_as_published"):
        raise ValueError("Only complete public award entries may be evaluated")

    checks = {}
    org = case.get("organization", {})
    kind = org.get("type", "UNKNOWN")
    allowed = ("registered_charity", "incorporated_nonprofit", "unincorporated_nonprofit")
    if kind not in allowed:
        checks["applicant_identity"] = check("NOT_OBTAINED",
            "Determine the organization's eligible legal form and confirm the required documents as of application date.",
            note="No CRA charity listing is not proof of a fictitious nonprofit: an eligible unincorporated nonprofit may qualify.")
    elif reviewed(org.get("identity_source_id"), sources):
        checks["applicant_identity"] = check("DOCUMENT_AVAILABLE_REVIEW_REQUIRED",
            "Confirm the record refers to this recipient at the relevant decision date and matches application signatories and Brampton address.",
            [org["identity_source_id"]])
    else:
        checks["applicant_identity"] = check("NOT_OBTAINED",
            f"Obtain the 2025/2026 eligibility documents appropriate to {kind}.")

    elig = case.get("eligibility", {})
    if reviewed(elig.get("city_admin_review_source_id"), sources):
        checks["eligibility"] = check("DOCUMENT_AVAILABLE_REVIEW_REQUIRED",
            "Reconcile signed eligibility and complete-on-time records, category, budget template and insurance, without treating absence from public files as ineligibility.",
            [elig["city_admin_review_source_id"]])
    else:
        checks["eligibility"] = check("NOT_OBTAINED",
            "Obtain application submission timestamp, completeness decision, organization-status documents, insurance and applicable stream eligibility determination.")

    sel = case.get("selection", {})
    scores = sel.get("reviewer_scores", [])
    policy = POLICY.get(year)
    if not policy or stream not in policy["threshold"]:
        checks["selection"] = check("YEAR_POLICY_NOT_CALIBRATED",
            "Check the precise applicable year's rules; do not apply 2025 scoring thresholds to 2024 automatically.")
    elif len(scores) == 3 and all(isinstance(x, dict) and dec(x.get("score")) is not None
          and dec(x.get("score")) <= 100 and reviewed(x.get("source_id"), sources) for x in scores):
        avg = sum((dec(x["score"]) for x in scores), Decimal(0))/3
        threshold = policy["threshold"][stream]
        status = "DOCUMENTED_SCORING_RECONCILIATION_QUESTION" if avg < threshold else "SCORE_THRESHOLD_DOCUMENTED_NOT_APPROVAL_VERIFIED"
        checks["selection"] = check(status,
            f"Three source-backed scores average {avg.quantize(Decimal('0.01'))}% against the {threshold}% published threshold. Reconcile ranking, reviewer independence, declared conflicts and any award decision.",
            [x["source_id"] for x in scores],
            note="Scores alone never prove a conflict or determine funding; threshold is only one condition.")
    else:
        checks["selection"] = check("NOT_OBTAINED",
            "Obtain all three individual evaluation score sheets, criteria and weighting, overall average, reviewer recusal/conflict control, ranking and recommendation.",
            note="No review score, reviewer identity or conflict inference is supplied by published recipient PDFs.")

    approval = case.get("approval", {})
    if reviewed(approval.get("delegated_authority_source_id"), sources):
        checks["approval"] = check("DOCUMENT_AVAILABLE_REVIEW_REQUIRED",
            "Compare grant recommendation with Commissioner's signed final authorization, approved value and decision chronology.",
            [approval["delegated_authority_source_id"]])
    else:
        checks["approval"] = check("NOT_OBTAINED",
            "Obtain funding recommendation, dated delegated approval, any amount change, rationale and conflict declarations.")

    agreement = case.get("agreement", {})
    payment = case.get("payments", [])
    agreement_ok = reviewed(agreement.get("source_id"), sources)
    documented_payments = [x for x in payment if isinstance(x, dict) and reviewed(x.get("source_id"), sources)
                           and dec(x.get("amount_cad")) is not None]
    if not agreement_ok or not documented_payments:
        checks["agreement_and_payment"] = check("NOT_OBTAINED" if not documented_payments else "PARTIAL_PAYMENT_DOCUMENTATION",
            "Obtain executed grant agreement, authorized payment schedule, redacted City payment ledger, actual transfer dates and holdback/recovery decisions.",
            [x["source_id"] for x in documented_payments],
            note="2025/2026 policy specifies 100% New and Small and initial 90% for the larger streams; policy is not proof that any payment happened.")
    else:
        paid = sum((dec(x["amount_cad"]) for x in documented_payments), Decimal(0))
        checks["agreement_and_payment"] = check(
            "PAYMENT_AMOUNT_RECONCILIATION" if paid > amount else "PAYMENTS_RECORDED_SCOPE_REVIEW",
            f"Source-backed entries total CAD {paid} versus published grant approval CAD {amount}. Verify duplicates, tax basis, cancelled transfers, amendments and grant-agreement dates before interpreting.",
            [agreement["source_id"]] + [x["source_id"] for x in documented_payments],
            note="No entry here independently confirms recipient bank ownership; no bank identifiers should be published.")

    expenses = case.get("expenses", [])
    if not expenses:
        checks["expense_authenticity"] = check("NOT_OBTAINED",
            "Obtain redacted final expense worksheet, invoices/receipts, proof each payment cleared, grant-versus-match allocations, original records and independent supplier confirmation as appropriate.",
            note="An invoice image or point-of-sale receipt alone does not verify genuine delivery, authorized billing, or paid costs.")
    else:
        evidence_ids = [x.get("invoice_source_id") for x in expenses if isinstance(x,dict) and reviewed(x.get("invoice_source_id"),sources)]
        independently_supported = [x for x in expenses if isinstance(x,dict)
            and reviewed(x.get("invoice_source_id"), sources)
            and reviewed(x.get("payment_proof_source_id"), sources)
            and reviewed(x.get("independent_supplier_confirmation_source_id"),sources)]
        checks["expense_authenticity"] = check("PARTIAL_SOURCE_EVIDENCE_NEEDS_AUTHENTICITY_REVIEW",
            f"{len(evidence_ids)} itemized invoice documents available; {len(independently_supported)} have source-backed payment proof and an independent supplier confirmation. Check invoice IDs, dates, duplicates, seller and any applicable CRA GST/HST registration on the transaction date.",
            evidence_ids,
            note="Even with independent confirmation, authenticity and grant eligibility require a human assessment; no automatic 'genuine' verdict.")

    delivery = case.get("delivery", {})
    closeout = reviewed(delivery.get("city_accepted_closeout_source_id"),sources)
    third_party = reviewed(delivery.get("independent_output_source_id"),sources)
    if closeout and third_party:
        checks["delivery_and_closeout"] = check("TWO_SOURCE_DELIVERY_REVIEW_REQUIRED",
            "Reconcile accepted close-out outcomes with independently corroborated attendance, project activity, venue and budget; confirm the reported work matches the funded scope.",
            [delivery["city_accepted_closeout_source_id"],delivery["independent_output_source_id"]])
    elif closeout:
        checks["delivery_and_closeout"] = check("CITY_CLOSEOUT_PRESENT_NO_INDEPENDENT_CORROBORATION",
            "City acceptance is documented; obtain independently checkable project outputs and reconcile deliverables to the application.",
            [delivery["city_accepted_closeout_source_id"]])
    else:
        checks["delivery_and_closeout"] = check("NOT_OBTAINED",
            "Obtain project end date, report due date, submitted and accepted close-out, deliverables, actual participation and outcome evidence.",
            note="Do not treat an active project as late; due dates depend on stream, year and the agreement.")

    if stream in ("Developing","Amplifying"):
        question="Independently reconcile matching contributions (including permitted volunteer hours or gifts-in-kind) and avoid treating non-cash match as an unpaid invoice."
    else:
        question="No automatic 50% matching contribution requirement applies to the New and Small stream."
    return {"case_id":"public-award-"+hashlib.sha256((year+"|"+award["organization_as_published"]+"|"+str(award.get("table_row"))+"|"+stream).encode()).hexdigest()[:16],
        "award": {"year":year,"organization_as_published":award["organization_as_published"],
            "stream":stream,"approved_amount_cad":str(amount),"source_url":award["source_url"],
            "source_page":award.get("source_page")},
        "evidence_stage_checks":checks,"matching_funds_note":question,
        "public_conclusion":"NO_MISCONDUCT_DETERMINATION; DOCUMENTS_AND_HUMAN_REVIEW_REQUIRED"}


def overlapping_invoices(cases):
    """Cross-grant duplicate invoice IDs require reconciliation, not an allegation."""
    index = defaultdict(set)
    for case in cases:
        case_id=case.get("case_id", "")
        for x in case.get("expenses", []):
            vendor=" ".join(str(x.get("supplier", "")).casefold().split())
            inv=" ".join(str(x.get("invoice_number", "")).casefold().split())
            if vendor and inv and case_id:
                index[(vendor,inv)].add(case_id)
    return [{"supplier_name_normalized":vendor,"invoice_number":inv,
        "case_ids": sorted(ids),"status":"POSSIBLE_SHARED_INVOICE_ALLOCATION_NEEDS_DOCUMENT_REVIEW_NOT_FRAUD"}
        for (vendor,inv),ids in sorted(index.items()) if len(ids)>1]


def pilot_sample(grants,year="2025",per_stream=2):
    """Representative by source order, NOT target selection by suspicion."""
    if per_stream not in (1,2,3):raise ValueError("Use a bounded 1–3 per-stream sample")
    selected=[]
    for stream in ("New and Small","Developing","Amplifying"):
        valid=[x for x in grants if x.get("year")==year and x.get("grant_stream")==stream]
        valid.sort(key=lambda r:(str(r.get("organization_as_published", "")).casefold(),str(r.get("source_page",0))))
        selected.extend(valid[:per_stream])
    return selected


def run(input_path,output,year="2025",per_stream=2):
    grants=json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(grants,list):raise ValueError("Expected published awards JSON array")
    selection=pilot_sample(grants,year,per_stream)
    if len(selection)!=per_stream*3:raise ValueError("One or more required public source streams missing")
    cases=[inspect(x) for x in selection]
    count=Counter(check["status"] for case in cases for check in case["evidence_stage_checks"].values())
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    summary={"run_date_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "study":"Brampton Advance Brampton Fund, process controls and receipts; selected public awards only",
        "pilot_year":year,"sample_selection":"FIRST_ALPHABETICAL_2_PER_STREAM_NOT_AN_ALLEGATION_OR_RISK_RANKING",
        "sample_size":len(cases),"stage_status_counts":dict(count),
        "actual_original_applications_received":0,"original_score_sheets_received":0,
        "signed_grant_agreements_received":0,"actual_city_payment_ledgers_received":0,
        "original_invoice_and_proof_of_payment_pairs_received":0,
        "independently_verified_project_outcomes":0,
        "confirmed_fraud_or_recipient_ineligibility":0,
        "constraint":"Public award lists alone cannot establish selection compliance, receipt authenticity or delivery.",
        "no_external_messages_sent":True}
    (root/"CASE_STAGE_AUDITS_PUBLIC_SOURCE_ONLY.json").write_text(json.dumps(cases,indent=2),encoding="utf-8")
    (root/"AUDIT_STATUS.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    (root/"EVIDENCE_REGISTER_EXAMPLE_SYNTHETIC.json").write_text(json.dumps({
      "example_only":"SYNTHETIC_METADATA_STRUCTURE_NOT_A_REAL_GRANTEE",
      "organization":{"type":"registered_charity","identity_source_id":"doc1"},
      "evidence_register":{"doc1":{"sha256":"0"*64,"reviewed_by_human":False,
         "custody_reference":"PRIVATE_STORE_REFERENCE_NO_BANK_DETAILS"}},
      "selection":{"reviewer_scores":[]},"payments":[],"expenses":[],"delivery":{}},indent=2),encoding="utf-8")
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--grants",default="local_results/grants/grants_approved.json")
    p.add_argument("--out",default="local_results/process_audit")
    p.add_argument("--year",default="2025",choices=["2025","2026"])
    p.add_argument("--per-stream",type=int,default=2)
    a=p.parse_args()
    print(json.dumps(run(a.grants,a.out,a.year,a.per_stream),indent=2))

if __name__=="__main__":
    main()
