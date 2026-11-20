# Ontario Public Integrity Observatory

**Independent, nonprofit, AI-assisted investigations and investigative journalism about public accountability in Ontario.**

## Mission
Advance investigative journalism and public accountability by examining municipal, regional, and provincial public records for evidence-backed questions about procurement, contractor performance, public spending, conflicts of interest, and potential misconduct. Document findings accurately, test innocent explanations, and never treat AI-generated suspicion as proof.

## Initial scope
Pilot: **Mississauga, Toronto, Brampton**. Start with existing GTA Commercial Radar collectors, but keep source code, private working data, and operations separate. Focus on repeat contract winners and how earlier contracts performed before later awards.

## Status
Repository scaffold only. **No live collection, complete contract-award inventory, or AI investigation is claimed.** All sample data are synthetic. No confidential investigations belong in public commits.

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
