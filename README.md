# FraudPulse Canada

A public Canadian fraud and cybercrime explorer for [CoolCode](https://coolcode.ca/), at [coolcode.ca/fraudpulse/](https://coolcode.ca/fraudpulse/). Static HTML, CSS and JavaScript; Python's standard library prepares the official-source snapshots. There are no runtime API keys, database requirements or npm dependencies.

<!-- coolcode:guide -->
Start with Canadian Anti-Fraud Centre reports and filter by receipt date, province, category or contact method; compare reporting frequency with reported dollar losses. Newer national CAFC summaries have a separate view: for example, open the 2026 half-year investment loss and follow its topic link to older detailed Investment records, without splicing the figures into one time series. Police incidents, business survey estimates and global exploited vulnerabilities have separate views and denominators. Source-check dates mean that publication was checked, not that new incidents were published; the Sources view records coverage, limitations and snapshot changes.
<!-- /coolcode:guide -->

## Explore

- **Fraud reports:** daily, weekly and monthly reporting trends; country, province, category and contact-method filters; losses, victims and fraud-category comparisons; calendar patterns and filtered CSV export.
- **Recent CAFC summaries:** full-year 2025 headline reports/losses and the union of its two top-ten lists, plus January–June 2026 headline losses and five highlighted categories. Select a publication, rank categories, follow related historical category links, or export with source dates and value qualifiers.
- **Police cybercrime:** annual counts and published population rates, plus separately labelled preliminary quarterly incidents. Select a geography, offence and measure; do not add parent totals to their component offences or geographic regions.
- **Business cyber security:** incidence, reporting and cost measures by industry and business size. These are weighted survey estimates with quality flags, not individual police reports.
- **Exploited vulnerabilities:** search official CISA KEV entries by CVE, vendor, product and known ransomware use. These are global defensive-security context, not Canadian crime totals.
- **Sources:** original dataset links, coverage periods, download hashes, check dates, limitations and the bounded refresh journal. Related CoolCode tools link to deeper vulnerability analysis and access-to-information exploration.

## Sources and interpretation

The [CAFC reporting dataset](https://open.canada.ca/data/en/dataset/6a09c998-cddb-4a22-beff-4dca67ab892f) contains public records received from January 2021 through September 2025 in the initial snapshot. The portal says Q4 2025 is delayed by a reporting-system changeover. Country defaults to Canada; the underlying extract also contains foreign and unspecified-country reports. A record is a report, not a proven criminal incident or a unique person. Reported victims are not deduplicated people. Values are as reported, include missing/unspecified categories and can be revised. Calendar dates refer to report receipt, not necessarily when fraud occurred. No individual URLs, domains, names or narrative complaints are exposed by this tool.

Newer CAFC summary publications are available even though the detailed CSV is delayed. The [2025 top-ten release](https://antifraudcentre-centreantifraude.ca/features-vedette/2026/02/top-fraud-2025-fraudes-plus-courantes-eng.htm) reports **over** 112,000 reports and **over** $704 million in losses; the [January–June 2026 publication](https://antifraudcentre-centreantifraude.ca/features-vedette/2026/08/fraud-trends-tendances-matiere-fraude-eng.htm) reports **approximately** $351 million in losses. These are national publication summaries, not additional report records. They have no province, daily, age or solicitation dimensions. Selected categories are incomplete, rounded amounts retain their qualifiers, and unpublished values remain null. Do not add these headlines to the CSV, subtract its partial totals to estimate missing months, or calculate growth between a full year and a half year.

Category links are editorial topic associations, not a verified statistical crosswalk: Relationship → Romance, Personal information → Personal Info, Fraud investigator → Bank Investigator, Recovery fraud → Recovery Pitch. Opening one resets to all Canadian detailed records for that category. Original publication labels remain visible. The August article's 2025 reference figures are retained separately: its bank-investigator figure differs from February's fraud-investigator figure, and the publisher does not reconcile the difference. The app does not silently overwrite either edition.

Loss quantiles describe positive recorded loss per report. A zero recorded loss does not establish absence of harm, especially for identity fraud, phishing or losses absorbed elsewhere.

Statistics Canada tables are ingested separately:

| Table | Subject |
| --- | --- |
| [35-10-0002-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3510000201) | Annual police-reported cybercrime, counts and rates |
| [35-10-0153-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3510015301) | Preliminary quarterly police-reported cybercrime |
| [35-10-0001-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3510000101) | Annual police-reported cybercrime by violation |
| [22-10-0076-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210007601) | Business cyber security incidents |
| [22-10-0078-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210007801) | Business reporting of cyber security incidents |
| [22-10-0131-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210013101) | Cyber security prevention and detection spending |
| [22-10-0132-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210013201) | Recovery spending after cyber security incidents |
| [22-10-0001-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210000101) | Business cyber security measures |
| [22-10-0133-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2210013301) | Impacts of cyber incidents on businesses |

Use the exact units and dimensions displayed for each table. Population coverage and reporting practices change. Quarterly police figures are preliminary and are not interchangeable with annual final figures. Published suppression and quality flags are retained; unavailable cells are never converted to zero. Business survey estimates describe the survey's in-scope enterprises (generally 10 or more employees), not all Canadian businesses or all victims. Crime reports, police incidents, victims, percentages and dollars are never added together.

The [CISA Known Exploited Vulnerabilities catalogue](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) provides international vulnerability context. A listing indicates exploitation in the wild; it is not evidence that a particular Canadian organisation was compromised. CISA due dates apply to the relevant US federal directive, not a Canadian legal deadline. A value other than “Known” does not establish absence of ransomware use.

Detailed source and pipeline notes live in [`docs/`](docs/). Government datasets remain subject to their source licences: [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada) and the [Statistics Canada Open Licence](https://www.statcan.gc.ca/en/reference/licence). FraudPulse is an independent tool and is not endorsed by the source organisations.

## Refresh and deployment

```sh
python3 scripts/refresh_threats.py
python3 scripts/refresh_data.py
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

`scripts/refresh_data.py --cache-dir /path/to/cache` changes the download cache location. Committed snapshots make the ordinary build offline and reproducible. The default `.cache/` directory and generated `dist/` are ignored.

**FraudPulse · Refresh official data** checks the sources each Monday at 13:23 UTC and can also be run manually. This includes re-fetching both reviewed CAFC publication pages, parsing their current values and detecting source revisions. New publications at other URLs require review and addition to `scripts/cafc_summaries.py`; this is not automatic discovery of every new CAFC article. New source content is validated before replacing the previous snapshot; check dates and change summaries are recorded even when published content is unchanged. Failed required-source downloads or validation leave the previous good data in place and fail the job. Diagnostics are attached to the Actions run. After successful validation, the workflow commits the data and explicitly starts the Pages workflow, since commits made with `GITHUB_TOKEN` do not trigger an ordinary push workflow.

**Browser tool · Check and publish** runs model tests, Python tests, an offline build and a Chromium browser check at a project subpath. Pull requests only check and package a preview. Successful `main` builds publish `dist/` through GitHub Pages. Configure the repository's **Settings → Pages → Source** as **GitHub Actions**; do not set a CNAME on this repository. The account site supplies the CoolCode domain.

The CoolCode catalogue registers discovery, search, sitemap, issue reporting, GitHub workflow history and source metadata monitoring. Its six-hour metadata check is separate from this tool's weekly source download. The shared Cloudflare collector must include `fraudpulse` in its accepted tool IDs for aggregate opens and private issue reports.

Public-repository GitHub schedules may be disabled after 60 days without repository activity. Workflow history is the authoritative record of refresh/deployment failures; a source's latest published period can lag well behind a successful download check.

## Privacy

All filters, chart calculations and CSV exports run in the browser against the bundled public snapshots. The tool does not request uploads, store visitor input or send filter selections to an analysis service. A share link includes its visible filter parameters in the URL, so they are shared with anyone receiving that link and with ordinary hosting requests. CoolCode's existing aggregate page-open counter receives the public tool ID; it excludes chart inputs and URL parameters. Source and related-tool links open the respective external sites.

## Development

App source is in `web/`, transformation logic is in `web/model.mjs`, collectors are in `scripts/`, and meaningful validation tests are in `tests/`. `tool.json` is the reviewed catalogue record; `scripts/build.py` fills metadata and shared reporting placeholders without fetching anything. Preserve relative paths so the application works at `/fraudpulse/`.

The browser check is a CI-only test dependency (`tests/browser-requirements.txt`), not an application dependency. It exercises loaded real snapshots, filters, tabs, exports and a mobile viewport. A preview should serve the built `dist/` directory.
