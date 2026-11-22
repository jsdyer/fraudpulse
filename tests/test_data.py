"""Semantic safeguards for public statistical sources and failure handling."""
import csv
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('refresh_data',ROOT/'scripts'/'refresh_data.py')
pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)

class DataSemantics(unittest.TestCase):
 def sample(self, entries):
  fields=["Numéro d'identification / Number ID",*pipeline.CAFC_FIELDS.values()]
  f=io.StringIO();writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
  for i,entry in enumerate(entries):
   row={k:'' for k in fields};row.update({fields[0]:str(i+1),pipeline.CAFC_FIELDS['date']:'2025-01-01',pipeline.CAFC_FIELDS['country']:'Canada',pipeline.CAFC_FIELDS['province']:'Ontario',pipeline.CAFC_FIELDS['victims']:'1',pipeline.CAFC_FIELDS['loss']:'$1,234.56'});row.update(entry);writer.writerow(row)
  return f.getvalue().encode()

 def test_country_scope_and_cents(self):
  data=pipeline.parse_cafc(self.sample([{}, {pipeline.CAFC_FIELDS['country']:'Not Specified',pipeline.CAFC_FIELDS['victims']:'0',pipeline.CAFC_FIELDS['loss']:'$0.00'}]))
  self.assertEqual(data['totals']['canada'],{'reports':1,'victims':1,'loss':1234.56})
  self.assertEqual(data['totals']['allReports']['reports'],2)
  self.assertNotIn('id',data['columns'])

 def test_extract_window_includes_days_without_reports(self):
  data={'coverageStart':'2025-01-02','coverageEnd':'2025-09-29'}
  result=pipeline.cafc_coverage(data,{}, {'url':'https://example.test/data-2025-01-01-to-2025-09-30-extracted.csv'})
  self.assertEqual(result['coverageStart'],'2025-01-01');self.assertEqual(result['coverageEnd'],'2025-09-30')
  self.assertEqual(result['recordDateEnd'],'2025-09-29')

 def test_duplicate_report_is_failure_not_double_count(self):
  with self.assertRaisesRegex(ValueError,'duplicate'):
   pipeline.parse_cafc(self.sample([{}, {"Numéro d'identification / Number ID":'1'}]))

 def test_blank_loss_is_not_assumed_zero(self):
  with self.assertRaises(Exception):pipeline.parse_cafc(self.sample([{pipeline.CAFC_FIELDS['loss']:''}]))

 def test_suppressed_unavailable_unreliable_remain_null(self):
  for flag in ['x','F','..','...']:
   self.assertIsNone(pipeline.number({'VALUE':'','STATUS':flag,'SCALAR_FACTOR':'units'}))
  self.assertEqual(pipeline.number({'VALUE':'0','STATUS':'','SCALAR_FACTOR':'units'}),0)
  self.assertEqual(pipeline.number({'VALUE':'3.4','STATUS':'E','SCALAR_FACTOR':'units'}),3.4)

 def test_quarter_is_not_ytd_and_coverage_is_quarter_end(self):
  base={'REF_DATE':'2026','GEO':'Canada','Calendar quarter':'Q2','VALUE':'123','STATUS':'','SCALAR_FACTOR':'units','Cyber-related violation':'Fraud'}
  rows=pipeline.police_rows([{**base,'Statistics':'Quarterly data'},{**base,'Statistics':'Year to date data'}],'police-quarterly')
  self.assertEqual([r['measure'] for r in rows],['Incidents','Year to date incidents'])
  self.assertEqual(pipeline.period_end(rows[0]['period']),'2026-06-30')

 def test_reporting_denominator_is_impacted_businesses(self):
  source={'REF_DATE':'2025','GEO':'Canada','Cyber security incidents reported to a police service':'Business reported cyber security incidents to a police service','North American Industry Classification System (NAICS)':'Private sector','Size of enterprise':'Total, all enterprises','UOM':'Percent','VALUE':'11','STATUS':'A','SCALAR_FACTOR':'units'}
  self.assertEqual(pipeline.business_rows([source],'business-reporting')[0]['denominator'],'Impacted enterprises')

 def test_unrecognized_statistic_or_geography_is_rejected(self):
  row={'REF_DATE':'2025','GEO':'Canada','Statistics':'Unfounded incidents','VALUE':'1','STATUS':'','SCALAR_FACTOR':'units'}
  with self.assertRaisesRegex(ValueError,'annual statistic'):pipeline.police_rows([row],'police-annual')
  self.assertEqual(pipeline.annual_geo('Canada'),('Canada','country'))
  row={'REF_DATE':'2025','GEO':'Ontario','Metric':'Reported','North American Industry Classification System (NAICS)':'Private sector','Size of enterprise':'Total, all enterprises','UOM':'Percent','VALUE':'1','STATUS':'A','SCALAR_FACTOR':'units'}
  with self.assertRaisesRegex(ValueError,'geography'):pipeline.business_rows([row],'business-reporting')
  with self.assertRaisesRegex(ValueError,'Duplicate'):pipeline.unique_coordinates([{'period':'2025'},{'period':'2025'}],['period'])

 def test_source_regression_is_rejected(self):
  old={'sources':[{'id':'cafc','coverageEnd':'2025-09-30','recordCount':100}]}
  with self.assertRaises(ValueError):pipeline.check_regression(old,[{'id':'cafc','coverageEnd':'2025-06-30','recordCount':90}])
  with self.assertRaises(ValueError):pipeline.check_regression(old,[{'id':'cafc','coverageEnd':'2025-09-30','recordCount':20}])

 def test_failed_refresh_preserves_last_good_data(self):
  with tempfile.TemporaryDirectory() as folder:
   data=Path(folder);original={'sources':[],'generatedAt':'yesterday'}
   (data/'manifest.json').write_text(json.dumps(original));(data/'cafc.json').write_text('last good')
   with patch.object(pipeline,'DATA',data),patch.object(pipeline,'TABLES',[]),patch.object(pipeline,'fetch',side_effect=RuntimeError('test unavailable')):
    self.assertEqual(pipeline.run(data/'cache'),1)
   self.assertEqual(json.loads((data/'manifest.json').read_text()),original)
   self.assertEqual((data/'cafc.json').read_text(),'last good')
   self.assertFalse(json.loads((data/'refresh-status.json').read_text())['success'])

class ShippedSnapshot(unittest.TestCase):
 def test_cafc_snapshot_is_consistent(self):
  p=ROOT/'web/data/cafc.json'
  if not p.exists():self.skipTest('Initial refresh has not finished')
  data=json.loads(p.read_text());rows=data['rows'];self.assertGreater(len(rows),100000)
  ci=data['dictionaries']['country'].index('Canada');canada=[r for r in rows if r[6]==ci]
  self.assertEqual(len(canada),data['totals']['canada']['reports'])
  self.assertEqual(sum(r[7] for r in canada),data['totals']['canada']['victims'])
  self.assertEqual(min(r[0] for r in rows),data.get('recordDateStart',data['coverageStart']))
  self.assertEqual(max(r[0] for r in rows),data.get('recordDateEnd',data['coverageEnd']))
  for index,name in enumerate(data['columns'][1:7],1):
   self.assertTrue(all(0<=r[index]<len(data['dictionaries'][name]) for r in rows))

 def test_statcan_snapshot_preserves_quality(self):
  for name in ['police','business']:
   p=ROOT/f'web/data/{name}.json'
   if not p.exists():self.skipTest('Initial refresh has not finished')
   data=json.loads(p.read_text());self.assertGreater(len(data['rows']),100)
   self.assertTrue(any(r['value'] is None for r in data['rows']))
   for row in data['rows']:
    if row['status'] in {'x','F','..','...'}:self.assertIsNone(row['value'])
    if row['value'] is not None:self.assertGreaterEqual(row['value'],0)

if __name__=='__main__':unittest.main()
