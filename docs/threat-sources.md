# Exploited-vulnerability context

FraudPulse includes the complete [CISA Known Exploited Vulnerabilities (KEV)
catalogue](https://www.cisa.gov/known-exploited-vulnerabilities-catalog). This is
global technical context. It is **not** a measure of Canadian crime, attack
frequency, compromised devices or victims, and it must never be added to CAFC or
Statistics Canada totals.

The updater tries CISA's [canonical JSON
feed](https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json),
then CISA's own [official GitHub mirror](https://github.com/cisagov/kev-data).
The mirror is maintained by the publisher; it is not a third-party substitute.
`source.downloadUrl` records which transport succeeded. The source's CC0 licence
permits reuse, and attribution is retained in the app and data.

## Reading the fields

- A row is a CVE included in KEV because CISA has evidence of exploitation.
- `date_added` is the catalogue addition date, not the date of an attack.
- `ransomware_status` preserves `Known` or `Unknown`. The Boolean
  `ransomware_known` means confirmed use only. `false` means **unknown**, not no use.
- `due_date` is the date in CISA's record. Its federal remediation requirements
  apply to U.S. Federal Civilian Executive Branch agencies; these are not Canadian
  legal deadlines.
- A vendor's number of entries is not a vulnerability rate or a security ranking:
  vendors differ in installed base, product range and reporting visibility.
- KEV is selective. A product not listed here is not necessarily safe.

The app preserves CISA's description and required action and links each CVE to
its NIST record. Catalogue records can be revised; `source.publishedAt` retains
CISA's release timestamp, while `source.checkedAt` is the time the downloader
successfully verified this snapshot.

## Refresh and validation

Run `python3 scripts/refresh_threats.py` before `scripts/refresh_data.py` so the
shared manifest includes the latest KEV source summary. This needs no API key and
uses only Python's standard library. It validates the source count, unique CVE
identifiers, required fields, ISO dates and ransomware categories. The raw input
SHA-256 is recorded. Network errors, schema drift, publication-date rollback or a
count decrease greater than 10% leave the existing output unchanged and return a
failure. A genuine large catalogue correction needs review before relaxing that
guard.

`web/data/threats.json` is committed browser data. The offline app build never
downloads or rebuilds it. Browsers fetch this same-origin snapshot and make no
requests to CISA or NIST until a visitor follows an external source link.

## Data contract

The envelope is `{schemaVersion: 1, source: {...}, records: [...]}`. Source metadata
uses the shared camelCase manifest fields. Records retain these fields:

`cve`, `vendor`, `product`, `name`, `date_added`, `due_date`,
`ransomware_known`, `ransomware_status`, `description`, `action`, `url`.
