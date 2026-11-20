# Brampton grant-recipient histories, purposes, patterns and relationships

This is the current primary OPIO analysis focus. It uses 2024–2026 Advance Brampton Fund approved-recipient PDFs. It generates an **investigation queue**, not fraud risk scores or findings.

## Four distinct evidence levels

1. **Published award:** recipient name, amount, year, grant stream and priority area with City PDF URL and page. These are *approved awards*, not payments.
2. **Same printed recipient across years:** normalized exact-name match only. A corporate registry identifier or separately verified identity is still required for legal continuity; name variants are held rather than automatically joined.
3. **Actual project purpose:** not derivable from 'Arts and Culture', 'Community Safety' or 'Recreation'. The City's [2025 grant guidelines](https://www.brampton.ca/EN/City-Hall/grants/Documents/2025%20Advance%20Brampton%20Fund/2025%20Advance%20Brampton%20Fund%20Guidelines%20V1.0.pdf) section 13 states activity name and description will be made public. Until an official description is retrieved and cited, mark exact project purpose **unknown**.
4. **Cross-recipient relationship:** requires a dated, specific public document directly evidencing a common registered entity, officer, director, partnership, or financial transfer. Shared surnames, organizational mission, area, addresses, cultural community, funding stream, event participation or proximity are **not** proof of common control or improper relationships.

## Working questions

- Does the recipient appear in 2 or 3 consecutive years, and are the year-by-year approved values and streams materially different?
- Are the *specific proposed projects* the same or substantially overlapping, and if so did the program allow renewal or multi-year funding?
- Do published incorporation identifiers and disclosed organizational leadership support a genuine relationship between two recipients? If names alone match, stop at unverified.
- Is there a direct, documented financial relationship between a grant recipient and a supplier or another grantee? Do not assume one.
- What actual activity, expenditure, City payment and accepted project closure records establish delivery?
- For a legally relevant decision, did a municipal decision-maker disclose a pertinent interest, and was any recusal required? Evaluate specific decisions, never assume wrongdoing from association.

## Source routes for enrichment

- [Brampton official grant program and PDFs](https://www.brampton.ca/EN/City-Hall/grants/pages/advance-brampton-fund.aspx)
- [CRA public charity information / filings](https://www.canada.ca/en/revenue-agency/services/charities-giving/charities/information-about-a-charity.html)
- [Ontario Business Registry](https://www.ontario.ca/page/ontario-business-registry)
- Federal Corporations Canada records where applicable
- Public audited financial statements, board rosters, relevant co-hosted events and primary City grant agreements, subject to permitted access

The CRA charity register does not cover all eligible unincorporated or non-charity nonprofit recipients. A missing charity registration is *not* proof of ineligibility.

## System output

The GitHub workflow refreshes the three annual PDF sources and writes `cross_year_recipient_histories.json`, `recipient_continuity.csv`, `specific_project_purposes.json`, `documented_cross_recipient_relationships.json`, `evidence_held.json`, and `summary.json`.

Two CSV evidence registers are intentionally blank until sourced review:
- `config/grant_project_purposes.csv`: attach an exact *grant-funded* project title and published description only.
- `config/grant_relationship_evidence.csv`: attach direct, dated relationship evidence. A human-reviewed evidence row is not, itself, evidence of misconduct.

**No emails, contact, filings, access-to-information submissions or fee commitments are authorized by this system.**
