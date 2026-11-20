# First live procurement-source checkpoint — November 20, 2026

**Status:** Real official-source retrieval confirmed in GitHub Actions. This is an investigative-data intake pilot, **not** a fraud finding and not an exhaustive municipal coverage claim.

- [Source-smoke GitHub Actions run](https://github.com/sandeep89shaily-coder/ontario-public-integrity-observatory/actions/runs/44813843742) — successful.
- [Offline tests](https://github.com/sandeep89shaily-coder/ontario-public-integrity-observatory/actions/runs/44813843718) — successful.
- Real collection timestamp: November 20, 2026, 20:43 UTC.

## Measured source intake

| Municipality | Directly acquired | Important limitation |
| --- | ---: | --- |
| Toronto | 25 official solicitation rows; 31 initial supplier mentions on 10 solicitations | One source record (`1111111111`, title `DELETE - Testing 99`) was clearly a test row and is now held by a quality gate; award counts are not a count of distinct completed contracts |
| Mississauga | 14 vendor/acquisition candidates from October 2026 City PDF reports (13 competitive, 1 noncompetitive) | PDF-extracted values require manual review; report is high-value acquisitions only |
| Brampton | 3 public tender-detail pages | Awarded-supplier identity and actual performance NOT determined |

Historical contract performance documents verified: **0**. Confirmed misconduct: **0**. Public allegations: **0**.

## Initial review leads (public records only)

1. Mississauga's [October 2026 competitive acquisitions report](https://www.mississauga.ca/wp-content/uploads/2026/11/11081727/October-2026-Competitive-Acquisitions-Report.pdf) lists **Mopal Construction Limited** for `PRC005342` (multiple community gardens, **$585,396.00**) and `PRC005414` (mountain bike course, **$343,750.00**). This is an exact-name repeat award lead, not an irregularity. Before any adverse suggestion, collect each contract's scope, delivery timetable, actual cost, completion reports and evaluation.
2. The same Mississauga report lists **1338568 Ontario Inc. o/a Winsom Landscaping** under `PRC005229` (**$2,443,563.04**). Brampton's [official procurement appendix](https://pub-brampton.escribemeetings.com/filestream.ashx?DocumentId=165031) identifies **1338568 Ontario Inc o/a Winsom Landscape Contractors**, `T2024-183`, with **$528,219.72 contract amount as of the appendix date**. Exact numbered-company wording suggests a cross-municipality link for verification. The Brampton PDF returned HTTP 403 in some independent access attempts; do not claim independently re-fetched or performance-verified evidence. Verify legal-entity identity, original versus amended amounts and service delivery before concluding anything.
3. Brampton public bids `T2026-161`, `T2026-136`, `T2026-230` were accessible as pages, but neither award recipients nor actual completed project outcomes were established from those pages.

## Evidence quality rules

- The official feed can contain placeholder/test solicitations; quarantine recognized examples and preserve raw source evidence rather than inventing an award.
- One procurement with multiple suppliers is not necessarily multiple separately awarded contracts.
- Raw City-source amounts are not independently audited final costs, and do not establish delivery performance.
- Cross-city name matches are a research queue, never automatic proof of common beneficial ownership or misconduct.

## Next acceptance gates

1. Recheck **at least 20** City procurement rows against exact official public pages/PDF tables.
2. Develop repeat-award matching with verified company identifiers and procurement IDs.
3. Retrieve actual project completion, cost-amendment, and supplier-evaluation reports for at least two vendors.
4. Produce two source-linked, human-reviewed contractor histories before enabling automated investigative claims.
