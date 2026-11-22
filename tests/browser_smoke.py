"""Exercise the built FraudPulse explorer at a GitHub Pages project subpath."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import tempfile
import threading
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    screenshots = ROOT / "browser-checks"
    screenshots.mkdir(exist_ok=True)
    data = json.loads((ROOT / "dist/data/cafc.json").read_text())
    cols = {name: i for i, name in enumerate(data["columns"])}
    dictionaries = data["dictionaries"]
    canada = dictionaries["country"].index("Canada")
    bc = dictionaries["province"].index("British Columbia")
    investment = dictionaries["category"].index("Investments")
    expected_canada = sum(r[cols["country"]] == canada for r in data["rows"])
    expected_bc = sum(r[cols["country"]] == canada and r[cols["province"]] == bc for r in data["rows"])
    expected_investment = sum(r[cols["country"]] == canada and r[cols["province"]] == bc and r[cols["category"]] == investment for r in data["rows"])
    threats = json.loads((ROOT / "dist/data/threats.json").read_text())
    cve = threats["records"][0]["cve"]
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT / "dist", Path(temporary) / "fraudpulse")
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=temporary))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
                page.set_default_timeout(30000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                base = f"http://127.0.0.1:{server.server_port}/fraudpulse/"
                page.goto(base)
                expect(page.locator(".metric-value").first).to_have_text(f"{expected_canada:,}")
                expect(page.locator("#country")).to_have_value("Canada")
                expect(page.locator(".week-comparison")).to_be_visible()
                expect(page.get_by_role("heading", name="Seasonality across the selected dates")).to_be_visible()
                page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
                page.locator("#province").select_option("British Columbia")
                expect(page.locator(".metric-value").first).to_have_text(f"{expected_bc:,}")
                page.locator("#category").select_option("Investments")
                expect(page.locator(".metric-value").first).to_have_text(f"{expected_investment:,}")
                page.locator("#interval").select_option("week")
                expect(page.locator("#interval")).to_have_value("week")
                page.wait_for_function("location.search.includes('interval=week')")
                assert "province=British+Columbia" in page.url
                page.reload()
                expect(page.locator(".metric-value").first).to_have_text(f"{expected_investment:,}")
                expect(page.locator("#interval")).to_have_value("week")
                with page.expect_download() as download_info:
                    page.locator("#export").click()
                download = download_info.value
                assert download.suggested_filename.startswith("fraudpulse-fraud-")
                exported = Path(download.path()).read_text(encoding="utf-8-sig")
                assert "date,province,category,method" in exported
                assert "British Columbia,Investments" in exported
                page.locator("nav [data-view='summaries']").click()
                expect(page.locator("#summaryEdition")).to_have_value("2026-h1")
                expect(page.locator("#dashboard")).to_contain_text("About $351M")
                expect(page.locator("#province")).to_have_count(0)
                expect(page.locator("#summaryMetric option")).to_have_count(1)
                expect(page.locator("#dashboard")).to_contain_text("$37.4M")
                with page.expect_download() as summary_download:
                    page.locator("#export").click()
                summary_csv = Path(summary_download.value.path()).read_text(encoding="utf-8-sig")
                assert "source_date_modified" in summary_csv and "approximately" in summary_csv
                assert "prior period quoted in this publication" in summary_csv
                page.locator("#summaryEdition").select_option("2025")
                expect(page.locator("#dashboard")).to_contain_text("Over $704M")
                expect(page.locator("#summaryMetric option")).to_have_count(3)
                page.locator("#summaryMetric").select_option("reports")
                page.reload()
                expect(page.locator("#summaryEdition")).to_have_value("2025")
                expect(page.locator("#summaryMetric")).to_have_value("reports")
                page.get_by_role("link", name="Investments", exact=True).click()
                expect(page.locator("#category")).to_have_value("Investments")
                expect(page.locator("#province")).to_have_value("")
                expect(page.locator("#country")).to_have_value("Canada")
                expect(page.locator("#end")).to_have_value(data["coverageEnd"])
                page.locator("nav [data-view='police']").click()
                expect(page.locator("#policeSource")).to_have_value("police-annual")
                expect(page.locator("#dashboard svg").first).to_be_visible()
                page.locator("#policeSource").select_option("police-quarterly")
                expect(page.locator(".notice.warning")).to_contain_text("preliminary")
                page.locator("nav [data-view='business']").click()
                expect(page.locator("#industry")).to_have_value("Private sector")
                expect(page.locator("#dashboard svg").first).to_be_visible()
                expect(page.locator("#dashboard")).to_contain_text("All enterprises")
                page.locator("nav [data-view='threats']").click()
                expect(page.locator("#query")).to_be_visible()
                page.locator("#query").fill(cve)
                expect(page.locator(".threat-card")).to_have_count(1)
                expect(page.locator(".threat-card")).to_contain_text(cve)
                page.locator("#query").fill('<img src=x onerror="alert(1)">')
                expect(page.locator(".threat-card")).to_have_count(0)
                expect(page.locator("img")).to_have_count(0)
                page.locator("nav [data-view='sources']").click()
                expect(page.locator(".source-card")).to_have_count(len(json.loads((ROOT / "dist/data/manifest.json").read_text())["sources"]))
                expect(page.locator("#export")).to_be_enabled()
                expect(page.locator("#dashboard")).to_contain_text("Refresh history")
                # Mobile layout for every view, with long real source labels.
                for width in (320, 390, 768):
                    page.set_viewport_size({"width": width, "height": 844})
                    for view in ("fraud", "summaries", "police", "business", "threats", "sources"):
                        page.locator(f"nav [data-view='{view}']").click()
                        expect(page.locator("#export")).to_be_enabled()
                        dimensions = page.evaluate("({content:document.documentElement.scrollWidth, viewport:window.innerWidth})")
                        assert dimensions["content"] <= dimensions["viewport"], (view, width, dimensions)
                page.set_viewport_size({"width": 390, "height": 844})
                page.locator("nav [data-view='fraud']").click()
                expect(page.locator("#export")).to_be_enabled()
                page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                # Hostile and out-of-coverage query dates cannot crash or invent coverage.
                page.goto(base + "?" + urlencode({"start": "2025-99-99", "end": "2099-12-31", "interval": "week"}))
                expect(page.locator("#export")).to_be_enabled()
                expect(page.locator("#end")).to_have_value(data["coverageEnd"])
                assert not errors, errors
                browser.close()
            print("Browser checks passed: actual datasets, country/filter totals, weekly query state, CSV, all views, safe text, date bounds and mobile layout")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
