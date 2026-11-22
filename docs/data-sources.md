# Official sources and statistical meaning

FraudPulse downloads primary-source files, never estimates records from charts, and never substitutes simulated or third-party incident counts. Original sources remain authoritative. The initial snapshot was checked on 22 November 2026 UTC.

## CAFC public reporting records

- Catalogue: <https://open.canada.ca/data/en/dataset/6a09c998-cddb-4a22-beff-4dca67ab892f>
- Machine-readable discovery: <https://open.canada.ca/data/api/action/package_show?id=6a09c998-cddb-4a22-beff-4dca67ab892f>
- Definitions: [CAFC definitions PDF](https://open.canada.ca/data/dataset/6a09c998-cddb-4a22-beff-4dca67ab892f/resource/ec49223e-d746-4171-a97b-12fcc79d360f/download/annex-e_open-government-statistics-description-and-associated-definitions.pdf)
- Licence: Open Government Licence – Canada.

The current 75,503,029-byte CSV advertises an extract window of **2021-01-01 through 2025-09-30** and was published on 2025-10-02. Its 350,361 unique public record IDs include 266,553 records whose Country is Canada. Foreign and unspecified-country reports are retained as distinct filter options. The catalogue explicitly says that the Q4 2025 update is delayed by a system changeover; a recent successful check does not resolve that delay.

The observed non-empty report dates in this extract are 2021-01-02 through 2025-09-29. Those extrema are `recordDateStart/End`, separate from the advertised `coverageStart/End`. Empty dates inside the extract window can appear as zero reported records, while dates outside it must not be presented as zero crime. The publisher's extract filename supplies the complete window; any new extract must encompass every observed date.

`Date Received` is a receipt date, not necessarily the occurrence date. One row is one unique public report record; original IDs are validated for uniqueness and then omitted. `Number of Victims` is summed as recorded and is **not a deduplicated people count**. Current complaint types include Victim, Attempt, Other, Unknown and Incomplete. Each presently published Victim row has one recorded victim, while other complaint types have zero.

Dollar losses are CAD, using the publisher's conversion. Amounts are retained to the cent. The CAFC explains that identity fraud, personal-information theft and phishing may record zero because loss is absorbed elsewhere or occurs subsequently. Zero loss is therefore not “no harm.” Median and percentile loss statistics are conditional on **positive recorded loss per report**, not per victim. No extrapolated national fraud prevalence or unreported losses are calculated.

Public row output contains receipt date, province/state, category, contact method, complaint type, age band, country, victim count and recorded loss. No report IDs, names, addresses, narrative reports or target URLs are exposed.

## Statistics Canada

Each downloadable ZIP contains the observation CSV and source metadata/footnotes. Download URLs follow `https://www150.statcan.gc.ca/n1/tbl/csv/TABLE-eng.zip`; the table web page supplies the current release date. Every ingest retains the published `STATUS` flag, uses the stated unit and rejects unsupported scalar factors. Suppressed (`x`), unreliable (`F`), unavailable (`..`) and inapplicable (`...`) cells remain null, never zero. A–D quality flags remain attached, and E is explicitly cautionary.

| Table | Coverage at launch | Meaning |
| --- | --- | --- |
| [35-10-0002-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3510000201) | 2014–2025 | Annual police-reported incident counts and published population rates, by country, province and policing-based CMA |
| [35-10-0153-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3510015301) | 2024 Q1–2026 Q2 | Preliminary regional quarterly and cumulative year-to-date counts, separately labelled |
| [35-10-0001-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3510000101) | 2014–2025 | Annual cyber-related violation counts for reporting police services |
| [22-10-0076-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210007601) | 2017, 2019, 2021, 2023, 2025 | Business incident types; percentage of in-scope enterprises |
| [22-10-0078-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210007801) | 2017–2025 survey cycles | Reporting to police; percentage of enterprises impacted by incidents |
| [22-10-0131-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210013101) | 2019–2025 survey cycles | Average prevention/detection spending in dollars |
| [22-10-0132-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210013201) | 2019–2025 survey cycles | Average recovery spending among impacted enterprises |
| [22-10-0001-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210000101) | 2017–2025 survey cycles | Adoption of cyber security measures |
| [22-10-0133-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210013301) | 2017–2025 survey cycles | Consequences of incidents among impacted enterprises |

Annual police tables were released 2026-07-22; quarterly data on 2026-10-08; business tables on 2026-10-21. These are publication dates, not downloader timestamps.

### Police comparisons

A cyber-related violation identifies the particular violation in an incident involving a computer/internet as instrument or target. CAFC reports and police incidents cannot be added together or treated as a clean report-to-investigation funnel.

Annual 2025 cybercrime coverage is 99.6% of Canada's population; New Brunswick coverage is 90.9%. Coverage and recording practices vary over time. Prior to 2020, some services could not report the indicator in all years. Toronto annual results can increase on later revision; Calgary data since 2017 are suspected cybercrimes. London experienced a reporting-process break in 2023. Detailed official caveats are retained in `police.json`.

Use the source's population rate rather than deriving a rate from a separate population table whose geography may not align with police boundaries. Toronto and Hamilton CMA coverage is incomplete, and policing-based CMA boundaries differ from standard census boundaries. Province, CMA, aggregate and national rows overlap and must never be summed. Military-police inclusion differs by year and source.

Quarterly population coverage varies from 91% to 99%; annual and quarterly values are not interchangeable. Quarterly releases are not retroactively revised, while year-to-date data reflect the later submission cutoff. Consequently, published YTD may not equal the sum of published quarters. StatCan explicitly avoids quarterly percentage-change calculations because changing reporting coverage could create misleading comparisons. FraudPulse follows that restriction.

### Business comparisons

The survey covers enterprises with Canadian operations and 10+ employees in most sectors, excluding public administration. Small means 10–49 employees, medium 50–249, large 250+. It is not a survey of every sole proprietor or microbusiness. Measures relate to incidents businesses considered impactful. Industries can be parents or components, so percentages and averages must not be summed across them.

The 2025 estimate is 16.4% impacted, versus 11.0% of **impacted enterprises** reporting to police. Different denominators prevent direct comparison as if both were shares of all businesses. Recovery costs and business-impact percentages also use impacted enterprises. Prevention/detection costs and security-measure uptake have the wider in-scope enterprise denominator. Response quality flags accompany each observation. 2017 cost estimates are not included because later cost methodology is not comparable.

## Snapshot contract

`web/data/manifest.json` contains `schemaVersion`, `checkedAt`, `generatedAt`, `sources`, `files` and `qualityFlags`. Every source has an ID, title, publisher, source/download URL, licence, check date, publication date, observation coverage, status, source-row count, SHA-256 and a caveat. Source counts are source observations and are not combined into a national statistic.

`cafc.json` is dictionary encoded. Columns are `[date, province, category, method, complaint, age, country, victims, loss]`. Six categorical fields are integer indices into the corresponding dictionary. Each row contributes one record. Dates are ISO strings and monetary values are CAD. Totals include separate all-record and Canada-only checks.

`police.json` rows have `source, period, geo, geoLevel, offence, measure, value, status`. Quarterly periods use `YYYY-QN`; manifest coverage uses ISO dates. Measures distinguish Incidents, Rate per 100,000 population and Year to date incidents. `business.json` rows have `source, period, industry, size, metric, unit, value, status, denominator`. Both files retain source footnotes and quality legends.

The CISA snapshot is documented in [threat-sources.md](threat-sources.md). It supplies global defensive context, not Canadian incident statistics.

## Refresh safety and reproducibility

The standard-library collector downloads with the normal browser User-Agent `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36`; StatCan's edge rejected the default Python urllib signature with error 1010. No authentication is used.

The collector validates source schemas, unique CAFC IDs, numeric ranges, exact statistical coordinate uniqueness, country dimensions, supported measure labels and source coverage. A coverage regression or row-count fall over 20% requires review. Failed required sources produce `refresh-status.json` and a nonzero exit without replacing last-good datasets or manifest. The workflow only commits and deploys after validation. Refresh history keeps 60 successful attempts, changed source hashes, counts and coverage before/after. The original 75MB source is cached locally, not committed.

Ordinary builds use committed snapshots without network access. `python3 scripts/refresh_data.py --cache-dir /path` chooses a cache; `--offline-cache` explicitly rebuilds from previously downloaded source files. The cache must contain the source ZIPs, CAFC CSV/catalogue and table HTML pages. Source `publishedAt` is never inferred from cache mtime or build time. An offline rebuild preserves the last remote `checkedAt` (or uses the oldest cache timestamp if no manifest exists), sets `offlineRebuild: true`, and advances only `generatedAt`.

## Newer CAFC publication summaries

`summaries.json` stores independent editions, each with an ID, coverage window, headline totals, selected categories and any older-period figures quoted in that edition. Original labels and qualifiers (`over`, `approximately`, `rounded`, `not applicable`) are retained. Counts missing from a publication remain null; identity/phishing N/A losses remain null. The 2025 edition merges its two top-ten lists by category and rejects conflicting duplicate values, without adding their counts. The 2026 half-year edition contains only the five highlighted categories. Their sum is not a new national total.

Source IDs are `cafc-summary-2025` and `cafc-summary-2026-h1`. The manifest's publication date is the page's explicit `dateModified`, labelled as such, separate from observation coverage and download time. Source-row counts mean displayed category rows, not fraud reports. The SHA-256 covers downloaded HTML.

The standard weekly collector retrieves these reviewed URLs before publishing any candidate data. The parser validates headings, dates, expected columns, categories, counts and monetary qualifiers; changed structure or ambiguous categories fail closed. Tests include revisions, missing values, duplicate conflicts and preservation of the last good snapshot on publication failure. HTML responses are cached as `cafc-summary-2025.html` and `cafc-summary-2026-h1.html`, required for offline refresh. Additional publication URLs and category associations require review rather than automatic inference.

Category navigation does not assert equivalence across editions or with the detailed CSV. It resets all detailed filters except category and defaults country to Canada. The summary view and its CSV clearly separate headline rows, selected category rows and prior-period figures quoted in the publication. No series is joined, no partial-year figure is annualized, no missing months are inferred, and no publication headline is recalculated from selected categories.
