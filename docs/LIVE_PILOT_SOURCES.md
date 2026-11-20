# Official source acceptance and limitations (November 20, 2026)

**No published adverse claims.** This is one bounded public-source acquisition pilot.

### Toronto
- OData: https://secure.toronto.ca/c3api_data/v2/DataAccess.svc/pmmd_solicitations/feis_solicitation_published
- Reads at most 25 solicitation objects per trial.
- Source-reported suppliers are not independently confirmed completed contracts; neither delivery performance nor final cost are available in this feed.
- Check official open-data terms before scaling and reverify statuses.

### Mississauga
- Official index: https://www.mississauga.ca/services-and-programs/business/doing-business-with-the-city/purchasing-reports/
- October 2026 competitive/noncompetitive City-PDF reports are used as a fixed, bounded first sample, not a claim of historical completeness.
- Tabular extraction is held for manual verification of procurement ID, vendor, amount and amount basis; multi-vendor awards are separate rows. No contractor evaluation is inferred.
- Only official PDFs, no vendor login, no subscription, no scraping of protected third-party portal APIs.

### Brampton
- Three exact, publicly linked bid-detail page URLs are tested subject to robots and access checks.
- This pilot DOES NOT infer an award recipient from tender bid status; a separate award notice or City procurement appendix is required.
- City council report appendices identified separately: https://pub-brampton.escribemeetings.com/filestream.ashx?DocumentId=165031 (some clients receive HTTP 403).
- No workaround of 403, login gate or robots restrictions is permitted.
- The restricted 2026 council appendix may be accessed legitimately through municipal records or a publisher-approved retrieval route.

### Evidence firewall
- Documents are not committed to the public repository.
- Normalized source-observation artifacts are produced by GitHub Actions and expire after seven days.
- Even a parsed City report is a research candidate until page/award/vendor fields are independently reviewed.
- No AI-based fraud allegations, contractor quality scores or findings are generated.
