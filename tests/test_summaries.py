"""Guard summary semantics, revisions and fail-closed source parsing."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import cafc_summaries as summaries
import refresh_data as pipeline


class SummaryPublications(unittest.TestCase):
    def raw(self, edition):
        return (ROOT / 'tests/fixtures' / f'cafc-summary-{edition}.html').read_bytes()

    def parse(self, index, raw=None):
        entry = summaries.PUBLICATIONS[index]
        return summaries.parse_publication(raw or self.raw(entry[0]), entry, '2026-11-22T00:00:00Z')

    def test_annual_deduplicates_lists_without_inventing_totals(self):
        edition, source = self.parse(0)
        self.assertEqual(len(edition['categories']), 13)
        investment = next(r for r in edition['categories'] if r['label'] == 'Investments')
        self.assertEqual(investment['reports'], 4409)
        self.assertEqual(investment['reportRank'], 2)
        self.assertEqual(investment['lossRank'], 1)
        self.assertEqual(edition['totals']['reports'], {'value': 112000, 'qualifier': 'over'})
        self.assertNotEqual(sum(r['reports'] for r in edition['categories']), 112000)
        self.assertIsNone(next(r for r in edition['categories'] if r['label'] == 'Phishing')['loss'])
        self.assertEqual(source['publishedAt'], '2026-02-25')
        self.assertEqual(source['coverageEnd'], '2025-12-31')

    def test_half_year_keeps_unpublished_counts_and_prior_period_separate(self):
        edition, _ = self.parse(1)
        self.assertNotIn('reports', edition['totals'])
        self.assertTrue(all(r['reports'] is None and r['victims'] is None for r in edition['categories']))
        self.assertEqual(edition['totals']['loss']['qualifier'], 'approximately')
        bank = next(r for r in edition['categories'] if r['label'] == 'Bank investigator fraud')
        self.assertEqual(bank['loss'], 28600000)
        prior = next(r for r in edition['comparisons'] if r['label'] == bank['label'])
        self.assertEqual(prior['loss'], 37400000)
        self.assertEqual(prior['periodEnd'], '2025-12-31')

    def test_missing_category_column_date_or_changed_label_requires_review(self):
        mutations = [self.raw('2025').replace(b'<td>Prize</td>', b'<td>New category</td>'),
                     self.raw('2025').replace(b'Dollar loss', b'Amount'),
                     self.raw('2025').replace(b'2026-02-25', b'2024-02-25'),
                     self.raw('2025').replace(b'$351 M', b'$-351 M')]
        for raw in mutations:
            with self.subTest(raw=raw[-80:]), self.assertRaises(ValueError):
                self.parse(0, raw)
        with self.assertRaises(ValueError):
            self.parse(1, self.raw('2026-h1').replace(b'<h3>Extortion', b'<h2>Extortion').replace(b'$25.5 million reported lost</h3>', b'$25.5 million reported lost</h2>'))

    def test_changed_amounts_are_reparsed_and_hashed(self):
        original, source = self.parse(0)
        revised, revision = self.parse(0, self.raw('2025').replace(b'$351 M', b'$352 M'))
        self.assertNotEqual(source['sha256'], revision['sha256'])
        self.assertEqual(next(r for r in revised['categories'] if r['label'] == 'Investments')['loss'], 352000000)
        self.assertEqual(original['totals'], revised['totals'])
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            self.parse(0, self.raw('2025').replace(b'$351 M', b'$352 M', 1))

    def test_failed_publication_preserves_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            (data/'manifest.json').write_text('{"sources":[]}')
            (data/'summaries.json').write_text('last good summaries')
            cafc = {'rows': [0] * 100000, 'coverageStart': '2021-01-01', 'coverageEnd': '2025-09-30',
                    'recordDateStart': '2021-01-01', 'recordDateEnd': '2025-09-30', 'coverageBasis': 'test',
                    'totals': {'canada': {'reports': 1}}}
            package = json.dumps({'result': {'resources': [{'format': 'CSV', 'url': 'https://example.test/cafc.csv'}]}}).encode()
            with patch.object(pipeline, 'DATA', data), patch.object(pipeline, 'TABLES', []), \
                 patch.object(pipeline, 'fetch', return_value=package), patch.object(pipeline, 'parse_cafc', return_value=cafc), \
                 patch.object(pipeline, 'load_summaries', side_effect=ValueError('Publication changed')):
                self.assertEqual(pipeline.run(data/'cache'), 1)
            self.assertEqual((data/'summaries.json').read_text(), 'last good summaries')
            self.assertEqual(json.loads((data/'manifest.json').read_text()), {'sources': []})
            self.assertEqual(json.loads((data/'refresh-status.json').read_text())['errors'][0]['source'], 'cafc-summaries')


if __name__ == '__main__':
    unittest.main()
