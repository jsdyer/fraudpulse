"""Parse reviewed CAFC publications. Never infer individual reports from summaries."""
import datetime as dt
from decimal import Decimal
import hashlib
from html.parser import HTMLParser
import re

PUBLICATIONS = [
    ('2025', '2025 · full year', '2025-01-01', '2025-12-31',
     'https://antifraudcentre-centreantifraude.ca/features-vedette/2026/02/top-fraud-2025-fraudes-plus-courantes-eng.htm'),
    ('2026-h1', '2026 · January–June', '2026-01-01', '2026-06-30',
     'https://antifraudcentre-centreantifraude.ca/features-vedette/2026/08/fraud-trends-tendances-matiere-fraude-eng.htm'),
]
# Navigation aids only: these do not assert identical definitions or populations.
CATEGORY_LINKS = {
    'Identity fraud': 'Identity Fraud', 'Investments': 'Investments',
    'Investment fraud': 'Investments', 'Service': 'Service',
    'Personal information': 'Personal Info', 'Phishing': 'Phishing',
    'Extortion': 'Extortion', 'Merchandise': 'Merchandise',
    'Fraud investigator': 'Bank Investigator', 'Bank investigator fraud': 'Bank Investigator',
    'Job': 'Job', 'Relationship': 'Romance', 'Spear phishing': 'Spear Phishing',
    'Recovery pitch': 'Recovery Pitch', 'Recovery fraud': 'Recovery Pitch', 'Prize': 'Prize',
}


def clean(value):
    return ' '.join(value.split())


class Publication(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.tables = []
        self.active = []
        self.table = None
        self.row = None
        self.modified = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.table = {'caption': '', 'rows': []}
        if tag == 'tr':
            self.row = []
        if tag in ('h1', 'h2', 'h3', 'p', 'caption', 'th', 'td') or (tag == 'time' and dict(attrs).get('property') == 'dateModified'):
            self.active.append([tag, []])

    def handle_data(self, data):
        for _, chunks in self.active:
            chunks.append(data)

    def handle_endtag(self, tag):
        if self.active and self.active[-1][0] == tag:
            _, chunks = self.active.pop()
            value = clean(''.join(chunks))
            if tag == 'time':
                self.modified = dt.date.fromisoformat(value).isoformat()
            elif tag == 'caption' and self.table is not None:
                self.table['caption'] = value
            elif tag in ('th', 'td') and self.row is not None:
                self.row.append(value)
            else:
                self.blocks.append((tag, value))
        if tag == 'tr' and self.row is not None:
            if self.table is not None:
                self.table['rows'].append(self.row)
            self.row = None
        if tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def required(pattern, text):
    match = re.search(pattern, text, re.I)
    if not match:
        raise ValueError('CAFC publication structure changed: ' + pattern)
    return match


def millions(value):
    return int(Decimal(value.replace(',', '')) * 1_000_000)


def count(value):
    if not re.fullmatch(r'\d[\d,]*', value):
        raise ValueError('Invalid published count: ' + value)
    return int(value.replace(',', ''))


def category(label, reports=None, victims=None, loss=None, qualifier='approximately'):
    if label not in CATEGORY_LINKS:
        raise ValueError('Review new CAFC category before linking: ' + label)
    return {'label': label, 'reportCategory': CATEGORY_LINKS[label], 'reports': reports,
            'victims': victims, 'loss': loss, 'lossQualifier': qualifier if loss is not None else 'not applicable',
            'reportRank': None, 'lossRank': None}


def parse_annual(page):
    text = ' '.join(value for _, value in page.blocks)
    headline = required(r'In 2025,.*?received over ([\d,]+) fraud reports involving more than \$([\d.]+) million', text)
    totals = {'reports': {'value': count(headline[1]), 'qualifier': 'over'},
              'loss': {'value': millions(headline[2]), 'qualifier': 'over'}}
    categories = {}
    for phrase, rank in [('frequency of reporting', 'reportRank'), ('reported dollar loss', 'lossRank')]:
        tables = [t for t in page.tables if phrase in t['caption'] and '2025' in t['caption']]
        if len(tables) != 1:
            raise ValueError('Expected one complete top-ten CAFC table: ' + phrase)
        table_rows = [r for r in tables[0]['rows'] if not (len(r) == 1 and r[0].startswith('*'))]
        if len(table_rows) != 11:
            raise ValueError('Expected ten category rows: ' + phrase)
        if table_rows[0] != ['Fraud type', 'Reports', 'Victims', 'Dollar loss']:
            raise ValueError('CAFC table columns changed')
        seen = set()
        for position, cells in enumerate(table_rows[1:], 1):
            if len(cells) != 4:
                raise ValueError('Incomplete CAFC category row')
            label, reports, victims, loss_text = cells
            label = label.rstrip('*').strip()
            if label in seen:
                raise ValueError('Duplicate category in top-ten table')
            seen.add(label)
            loss = None if loss_text == 'N/A' else millions(required(r'^\$([\d.]+)\s*M$', loss_text)[1])
            item = category(label, count(reports), count(victims), loss, 'rounded')
            if label in categories:
                if any(categories[label][k] != item[k] for k in ('reports', 'victims', 'loss')):
                    raise ValueError('Conflicting duplicated CAFC category')
            else:
                categories[label] = item
            categories[label][rank] = position
    return totals, list(categories.values()), []


def parse_half_year(page):
    text = ' '.join(value for _, value in page.blocks)
    required(r'First 6 Months of 2026', text)
    headline = required(r'first six months of the year, Canadians reported approximately \$([\d.]+) million', text)
    totals = {'loss': {'value': millions(headline[1]), 'qualifier': 'approximately'}}
    rows = []
    paragraphs = {}
    current = None
    for tag, value in page.blocks:
        if tag == 'h3':
            match = re.fullmatch(r'(.+?)\s*[-–]\s*approximately \$([\d.]+) million reported lost', value)
            current = match[1] if match else None
            if match:
                rows.append(category(current, loss=millions(match[2])))
                paragraphs[current] = ''
        elif tag == 'p' and current:
            paragraphs[current] += ' ' + value
    expected = {'Investment fraud', 'Spear phishing', 'Bank investigator fraud', 'Extortion', 'Recovery fraud'}
    if len(rows) != 5 or {r['label'] for r in rows} != expected:
        raise ValueError('CAFC half-year categories changed; review publication')
    comparisons = []
    for label, pattern, qualifier in [
        ('Spear phishing', r'In all of 2025, reported losses exceeded \$([\d.]+) million', 'over'),
        ('Bank investigator fraud', r'losses were approximately \$([\d.]+) million in 2025', 'approximately'),
        ('Extortion', r'approximately \$([\d.]+) million reported during all of 2025', 'approximately'),
        ('Recovery fraud', r'approximately \$([\d.]+) million during all of 2025', 'approximately'),
    ]:
        value = millions(required(pattern, paragraphs[label])[1])
        comparisons.append({'label': label, 'periodStart': '2025-01-01', 'periodEnd': '2025-12-31',
                            'loss': value, 'lossQualifier': qualifier})
    return totals, rows, comparisons


def parse_publication(raw, entry, checked):
    identifier, label, start, end, url = entry
    page = Publication(raw.decode('utf-8-sig'))
    if not page.modified or page.modified < end:
        raise ValueError('Missing or invalid CAFC publication modification date')
    totals, categories, comparisons = parse_annual(page) if identifier == '2025' else parse_half_year(page)
    source_id = 'cafc-summary-' + identifier
    edition = {'id': identifier, 'label': label, 'sourceId': source_id,
               'periodStart': start, 'periodEnd': end, 'totals': totals,
               'categories': categories, 'comparisons': comparisons}
    source = {'id': source_id, 'title': 'CAFC published summary · ' + label,
              'publisher': 'Canadian Anti-Fraud Centre', 'url': url, 'downloadUrl': url,
              'license': 'Government of Canada terms and conditions', 'checkedAt': checked,
              'publishedAt': page.modified, 'publicationDateMeaning': 'Source page date modified',
              'coverageStart': start, 'coverageEnd': end, 'recordCount': len(categories),
              'status': 'ok', 'sha256': hashlib.sha256(raw).hexdigest(),
              'note': 'National publication summary, not individual records. Category rows are a selected subset; dollar values are rounded. Publication date is the source page date modified.'}
    return edition, source


def load_summaries(cache, offline, checked, fetch):
    editions, sources = [], []
    for entry in PUBLICATIONS:
        raw = fetch(entry[-1], cache / ('cafc-summary-' + entry[0] + '.html'), offline)
        edition, source = parse_publication(raw, entry, checked)
        editions.append(edition)
        sources.append(source)
    return {'schemaVersion': 1, 'editions': editions}, sources
