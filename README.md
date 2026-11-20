# Ontario Public Integrity Observatory

> **Current grant-only investigation:** Brampton Advance Brampton Fund recipient continuity, project purpose, and documented relationships (2024–2026). [Open current casebook](docs/GRANTS_RECIPIENT_CASEBOOK_20261120.md). Source-linked continuity is a research queue, **not** an allegation. No external correspondence without explicit user approval.


> **Current investigative focus (Nov 20, 2026):** GRANTS ONLY — Brampton Advance Brampton Fund 2024–2026. Other procurement and contractor software remains preserved but is not in the active research workflow. [First source-version reconciliation](docs/GRANTS_CASE_001_2024_PUBLIC_LIST_REVISIONS.md).


**Independent, nonprofit, AI-assisted investigations and investigative journalism about public accountability in Ontario.**

## Mission
Advance investigative journalism and public accountability by examining municipal, regional, and provincial public records for evidence-backed questions about procurement, contractor performance, public spending, conflicts of interest, and potential misconduct. Document findings accurately, test innocent explanations, and never treat AI-generated suspicion as proof.

## Initial scope
Pilot: **Mississauga, Toronto, Brampton**. Start with existing GTA Commercial Radar collectors, but keep source code, private working data, and operations separate. Focus on repeat contract winners and how earlier contracts performed before later awards.

## Status
First live bounded three-city source smoke executed on November 20, 2026: 25 Toronto solicitations with 31 raw supplier mentions (including one obvious test record quarantined in the subsequent code revision), 14 Mississauga City-report vendor entries, and 3 Brampton public tender pages. These remain unreviewed source observations, **not a complete contract-award inventory or AI investigation**. Synthetic test fixtures are clearly separate. See [the live checkpoint](docs/FIRST_LIVE_CHECKPOINT_20261120.md). No confidential investigations belong in public commits.

## First milestones
1. Audit and license-check Radar modules for read-only reuse; maintain source provenance.
2. Import a small batch of actual, source-linked procurement awards without modifying Radar.
3. Deduplicate named vendors cautiously, only using verified identifiers.
4. Identify repeat winners and link earlier documented contract outcomes.
5. Pilot human-reviewed investigative dossiers and right-of-reply workflow.

## Run
Python 3.11+ (stdlib only for the initial scaffold):

```bash
python -m unittest discover -s tests -v
python -m src.observatory.cli --input tests/fixtures/awards_example.csv
```

See `docs/ARCHITECTURE.md` and `docs/EDITORIAL_POLICY.md`. All scheduled collection is disabled until source access and publication rights are checked.

## Bounded live source test
Run after confirming source terms:
```bash
python -m pip install "pdfplumber==0.11.7"
python -m src.observatory.municipal_live --live --out local_results/pilot
```
GitHub Actions also has a restricted one-shot source smoke workflow; outputs are short-retention artifacts, not public accusations.

## Integrity investigations — priority revised November 20, 2026
The first substantive investigations now follow **municipal procurement exceptions, contract amendments, grants, declared-interest records, and public-funds reconciliation**; historical contractor performance remains supporting context. A first bounded source run reviewed Toronto council decisions, Mississauga non-competitive purchasing reports, Brampton published 2025–26 grants, and public declared-interest registry entry points. The system produces neutral source-linked review questions, **not fraud findings**. See [live integrity pilot findings](docs/FIRST_INTEGRITY_PILOT_20261120.md).
