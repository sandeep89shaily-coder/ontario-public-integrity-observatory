# Architecture and integration boundaries

- **Separate project:** Observatory code, investigative outputs, budgets and editorial control remain independent of GTA Commercial Radar.
- **Read-only adapter first:** Do not modify Radar or import its historical SQLite database into a public repository.
- **Candidate modules to assess:** `municipal_document_capture.py`, `gta_council_document_delta.py`, `toronto_procurement_odata.py`, `mississauga_procurement.py`, `gta_cross_source_evidence_reconciliation.py`, `municipal_full_document_ai.py`.
- **Not verified reusable:** Small-municipality procurement collectors; full historical contract amendments and contractor evaluations.
- **Expected source fields:** municipality, contract ID, legal vendor identifier if verified, exact award notice URL, date, amount and tax basis, amendment IDs, final cost, completion and evaluation evidence, limitations.
- **Data classification:** PUBLIC_VERIFIED, PUBLIC_UNVERIFIED, REQUIRES_RECORD_REQUEST, RESTRICTED_PRIVATE. Only PUBLIC_VERIFIED, human-reviewed claims may be published.
- **No public case allegations:** GitHub Actions should run tests only until source rights and review governance exist.
