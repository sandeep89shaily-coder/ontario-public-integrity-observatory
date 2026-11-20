# Toronto OData acceptance

## Current state
Bounded adapter implemented, with mocked automated tests. Live OData download not verified in this release. GitHub Actions runs offline tests only. No recurring collection or paid AI is enabled.

## Source
- Official OData base: https://secure.toronto.ca/c3api_data/v2/DataAccess.svc/pmmd_solicitations/feis_solicitation_published
- Official portal: https://www.toronto.ca/business-economy/doing-business-with-the-city/searching-bidding-on-city-contracts/toronto-bids-portal/
- Previous code reference: GTA Radar `toronto_procurement_odata.py`, assessed for design and fields, not copied as a dependency.

## Manual live test, after reviewing source policies

```powershell
python -m src.observatory.toronto --live --out local_results/toronto --pages 2 --page-size 50
```

Outputs include full source records, extracted supplier mentions, held records, page diagnostics and CSV candidates. The directory is intentionally ignored by Git.

## Gates before an investigation
1. Verify access and licensing for exact source, and check at least 20 records manually.
2. Confirm actual award status and source record identity on the official portal.
3. Resolve legal vendor identity across spelling variations.
4. Obtain original contract terms, change orders, actual final cost, completion reports and contractor evaluations separately.
5. Never infer poor performance or impropriety from repeated awards or missing public documents.
