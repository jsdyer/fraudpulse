import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from refresh_threats import normalize, refresh, MIRROR_URL


def fixture(count=1):
    return {
        "catalogVersion": "2026.11.20", "dateReleased": "2026-11-20T17:00:00Z", "count": count,
        "vulnerabilities": [{
            "cveID": f"CVE-2026-{10000 + i}", "vendorProject": "Example vendor", "product": "Example product",
            "vulnerabilityName": "Example vulnerability", "dateAdded": "2026-11-20", "dueDate": "2026-12-01",
            "knownRansomwareCampaignUse": "Unknown", "shortDescription": "Fixture only.",
            "requiredAction": "Apply the vendor update.",
        } for i in range(count)],
    }


class ThreatTests(unittest.TestCase):
    def test_unknown_is_preserved_and_dates_are_source_dates(self):
        data = fixture()
        result = normalize(json.dumps(data).encode(), "2026-11-22T01:00:00Z", MIRROR_URL)
        self.assertFalse(result["records"][0]["ransomware_known"])
        self.assertEqual(result["records"][0]["ransomware_status"], "Unknown")
        self.assertEqual(result["source"]["coverageEnd"], "2026-11-20")
        self.assertEqual(result["source"]["scope"], "global")
        self.assertEqual(result["source"]["downloadUrl"], MIRROR_URL)

    def test_rejects_duplicate_cve_missing_values_count_and_unknown_schema(self):
        cases = []
        data = fixture(2)
        data["vulnerabilities"][1]["cveID"] = data["vulnerabilities"][0]["cveID"]
        cases.append(data)
        data = fixture()
        data["count"] = 10
        cases.append(data)
        data = fixture()
        data["vulnerabilities"][0]["dateAdded"] = "2026-02-30"
        cases.append(data)
        data = fixture()
        data["vulnerabilities"][0]["knownRansomwareCampaignUse"] = "No"
        cases.append(data)
        data = fixture()
        del data["vulnerabilities"][0]["vendorProject"]
        cases.append(data)
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValueError):
                normalize(json.dumps(data).encode(), "2026-11-22T01:00:00Z")

    def test_failed_refresh_preserves_last_good_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "threats.json"
            fetch = lambda: (json.dumps(fixture(120)).encode(), MIRROR_URL)
            refresh(target, fetch=fetch)
            original = target.read_bytes()
            def fail():
                raise RuntimeError("upstream unavailable")
            with self.assertRaises(RuntimeError):
                refresh(target, fetch=fail)
            self.assertEqual(target.read_bytes(), original)
            with self.assertRaisesRegex(ValueError, "shrank"):
                refresh(target, fetch=lambda: (json.dumps(fixture(100)).encode(), MIRROR_URL))
            self.assertEqual(target.read_bytes(), original)
            old = fixture(120)
            old["dateReleased"] = "2026-10-01T00:00:00Z"
            with self.assertRaisesRegex(ValueError, "backwards"):
                refresh(target, fetch=lambda: (json.dumps(old).encode(), MIRROR_URL))
            self.assertEqual(target.read_bytes(), original)

    def test_source_count_and_valid_cves_in_committed_catalogue(self):
        path = Path(__file__).resolve().parents[1] / "web/data/threats.json"
        if not path.exists():
            self.skipTest("Initial data download has not run")
        data = json.loads(path.read_text())
        self.assertEqual(len(data["records"]), data["source"]["recordCount"])
        self.assertEqual(len({row["cve"] for row in data["records"]}), len(data["records"]))
        self.assertGreater(len(data["records"]), 100)


if __name__ == "__main__":
    unittest.main()
