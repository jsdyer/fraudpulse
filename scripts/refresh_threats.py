#!/usr/bin/env python3
"""Download and validate CISA's public KEV catalogue; preserve the last good file."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE_URL = "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
DOWNLOAD_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
MIRROR_URL = "https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json"
MAX_BYTES = 20_000_000
CVE = re.compile(r"CVE-\d{4}-\d{4,}")
NOTE = (
    "Global technical context, not a count of Canadian crimes, attacks or victims. "
    "Each row is a vulnerability with evidence of exploitation. Date added is the "
    "catalogue addition date, not the date of an attack. Ransomware 'Unknown' means "
    "CISA has not confirmed ransomware use; it does not mean none. Due dates are "
    "CISA's U.S. federal agency deadlines, not Canadian legal requirements. "
    "Absence from the catalogue does not establish that a product is safe."
)


def iso_date(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{label} must be an ISO date")
    date.fromisoformat(value)
    return value


def timestamp(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed


def nonempty(item, field):
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing {field}")
    return value.strip()


def normalize(payload, checked_at, download_url=DOWNLOAD_URL):
    """Produce a small, explicit browser schema without guessing missing values."""
    data = json.loads(payload)
    if not isinstance(data, dict) or not isinstance(data.get("vulnerabilities"), list):
        raise ValueError("KEV response must contain a vulnerabilities array")
    rows = data["vulnerabilities"]
    if not rows or type(data.get("count")) is not int or data["count"] != len(rows):
        raise ValueError("KEV count does not match nonempty source rows")
    timestamp(checked_at, "checkedAt")
    published_at = nonempty(data, "dateReleased")
    timestamp(published_at, "dateReleased")
    version = nonempty(data, "catalogVersion")
    records, seen = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Every KEV row must be an object")
        cve = nonempty(row, "cveID")
        if not CVE.fullmatch(cve) or cve in seen:
            raise ValueError(f"Invalid or duplicated CVE: {cve}")
        seen.add(cve)
        ransomware = nonempty(row, "knownRansomwareCampaignUse")
        if ransomware not in {"Known", "Unknown"}:
            raise ValueError(f"Unrecognized ransomware status: {ransomware}")
        records.append({
            "cve": cve,
            "vendor": nonempty(row, "vendorProject"),
            "product": nonempty(row, "product"),
            "name": nonempty(row, "vulnerabilityName"),
            "date_added": iso_date(row.get("dateAdded"), "dateAdded"),
            "due_date": iso_date(row.get("dueDate"), "dueDate"),
            "ransomware_known": ransomware == "Known",
            "ransomware_status": ransomware,
            "description": nonempty(row, "shortDescription"),
            "action": nonempty(row, "requiredAction"),
            "url": f"https://nvd.nist.gov/vuln/detail/{cve}",
        })
    records.sort(key=lambda item: (item["date_added"], item["cve"]), reverse=True)
    return {
        "schemaVersion": 1,
        "source": {
            "id": "cisa-kev", "title": "Known Exploited Vulnerabilities",
            "publisher": "U.S. Cybersecurity and Infrastructure Security Agency",
            "url": CATALOGUE_URL, "downloadUrl": download_url,
            "license": "CC0 1.0", "licenseUrl": "https://github.com/cisagov/kev-data/blob/develop/LICENSE",
            "checkedAt": checked_at, "publishedAt": published_at,
            "coverageStart": min(item["date_added"] for item in records),
            "coverageEnd": max(item["date_added"] for item in records),
            "status": "ok", "recordCount": len(records),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "catalogVersion": version, "scope": "global", "note": NOTE,
        },
        "records": records,
    }


def download():
    errors = []
    for url in (DOWNLOAD_URL, MIRROR_URL):
        try:
            request = Request(url, headers={
                "User-Agent": "FraudPulse/1.0 (+https://github.com/jsdyer/fraudpulse)",
                "Accept": "application/json",
            })
            with urlopen(request, timeout=45) as response:
                payload = response.read(MAX_BYTES + 1)
            if len(payload) > MAX_BYTES:
                raise ValueError("KEV source exceeds download size limit")
            # Validate before selecting a transport. The official mirror may recover
            # from an unavailable or invalid canonical response.
            normalize(payload, datetime.now(timezone.utc).isoformat(), url)
            return payload, url
        except (OSError, URLError, ValueError, KeyError) as error:
            errors.append(f"{url}: {error}")
    raise RuntimeError("No validated official KEV download: " + "; ".join(errors))


def refresh(destination=ROOT / "web/data/threats.json", fetch=download, now=None):
    destination = Path(destination)
    previous = json.loads(destination.read_text()) if destination.exists() else None
    payload, url = fetch()
    checked_at = (now or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")
    result = normalize(payload, checked_at, url)
    if result["source"]["recordCount"] < 100:
        raise ValueError("KEV catalogue unexpectedly contains fewer than 100 records")
    if previous:
        before, after = previous["source"], result["source"]
        if after["recordCount"] < before["recordCount"] * 0.9:
            raise ValueError("KEV catalogue shrank by more than 10%; review source before replacing")
        if timestamp(after["publishedAt"], "publishedAt") < timestamp(before["publishedAt"], "publishedAt"):
            raise ValueError("KEV source publication date moved backwards")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                         prefix=".threats-", suffix=".json", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(result, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
        temporary.replace(destination)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "web/data/threats.json")
    args = parser.parse_args()
    try:
        result = refresh(args.output)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        raise SystemExit(f"Threat refresh failed; existing data preserved: {exc}")
    source = result["source"]
    print(f"Validated {source['recordCount']:,} KEV records; catalogue {source['catalogVersion']}; {source['downloadUrl']}")
