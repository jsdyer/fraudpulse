#!/usr/bin/env python3
"""Build validated, provenance-bearing public data snapshots using only the standard library."""
from __future__ import annotations
import argparse, calendar, concurrent.futures, csv, datetime as dt, hashlib, io, json, math, os, re, sys, tempfile, time, urllib.request, zipfile
from decimal import Decimal
from pathlib import Path
from cafc_summaries import load_summaries

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'web' / 'data'
SCHEMA = 1
# StatCan's edge returns error 1010 for the default Python urllib User-Agent.
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
CAFC_API = 'https://open.canada.ca/data/api/action/package_show?id=6a09c998-cddb-4a22-beff-4dca67ab892f'
CAFC_PAGE = 'https://open.canada.ca/data/en/dataset/6a09c998-cddb-4a22-beff-4dca67ab892f'
CAFC_DEFINITIONS = 'https://open.canada.ca/data/dataset/6a09c998-cddb-4a22-beff-4dca67ab892f/resource/ec49223e-d746-4171-a97b-12fcc79d360f/download/annex-e_open-government-statistics-description-and-associated-definitions.pdf'
TABLES = [
 ('35100002','police-annual','Police-reported cybercrime by geography'),
 ('35100153','police-quarterly','Preliminary quarterly police-reported cybercrime'),
 ('35100001','police-offences','Annual police-reported cybercrime by violation'),
 ('22100076','business-incidents','Business cyber security incidents'),
 ('22100078','business-reporting','Business reporting of cyber incidents to police'),
 ('22100131','business-prevention-cost','Business cyber prevention and detection costs'),
 ('22100132','business-recovery-cost','Business cyber recovery costs'),
 ('22100001','business-measures','Business cyber security measures'),
 ('22100133','business-impacts','Impacts of cyber incidents on business'),
]
FLAGS = {'':'Published','A':'Excellent / very reliable','B':'Very good / reliable','C':'Good','D':'Acceptable','E':'Use with caution','F':'Too unreliable to publish','x':'Suppressed for confidentiality','..':'Not available','...':'Not applicable','p':'Preliminary','r':'Revised','0s':'Rounded to zero','t':'Terminated'}
PROVINCES = {'Newfoundland and Labrador','Prince Edward Island','Nova Scotia','New Brunswick','Quebec','Ontario','Manitoba','Saskatchewan','Alberta','British Columbia','Yukon','Northwest Territories','Nunavut'}
CAFC_FIELDS = {
 'date':'Date Received / Date reçue','province':'Province/State','category':'Fraud and Cybercrime Thematic Categories','method':'Solicitation Method','complaint':'Complaint Type','age':"Victim Age Range / Tranche d'âge des victimes",'country':'Country','victims':'Number of Victims / Nombre de victimes','loss':'Dollar Loss /pertes financières',
}

def now():
 return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')

def fetch(url, path, offline=False):
 if offline:
  if not path.exists(): raise ValueError(f'Missing offline source: {path.name}')
  return path.read_bytes()
 last = None
 for attempt in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':USER_AGENT,'Accept':'*/*'}), timeout=120) as response:
    value=response.read()
   if not value: raise ValueError('Empty response')
   path.parent.mkdir(parents=True,exist_ok=True)
   path.write_bytes(value)
   return value
  except Exception as exc:
   last=exc
   if attempt < 2: time.sleep(1+attempt)
 raise RuntimeError(f'Download failed: {url}: {last}')

def dump_json(path, value):
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix=path.name+'.',dir=path.parent)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:
   json.dump(value,f,ensure_ascii=False,separators=(',',':'),allow_nan=False)
   f.write('\n')
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp): os.unlink(tmp)

def money(value):
 result=Decimal(value.strip().replace('$','').replace(',',''))
 if not result.is_finite() or result < 0: raise ValueError(f'Invalid loss: {value!r}')
 return int(result) if result == result.to_integral() else float(result)

def parse_cafc(raw):
 reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
 missing=set(CAFC_FIELDS.values())-set(reader.fieldnames or [])
 if missing: raise ValueError(f'CAFC schema changed: missing {sorted(missing)}')
 id_field=next((x for x in reader.fieldnames if 'Number ID' in x),None)
 if not id_field: raise ValueError('CAFC missing unique public record ID')
 dictionaries={k:[] for k in ('province','category','method','complaint','age','country')}
 lookups={k:{} for k in dictionaries}
 rows=[]; seen=set(); totals={'reports':0,'victims':0,'lossCents':0};canadian={'reports':0,'victims':0,'lossCents':0}
 for item in reader:
  identifier=item[id_field]
  if not identifier or identifier in seen: raise ValueError('Missing or duplicate CAFC report ID')
  seen.add(identifier)
  date=dt.date.fromisoformat(item[CAFC_FIELDS['date']]).isoformat()
  values={k:item[v].strip() for k,v in CAFC_FIELDS.items()}
  values['age']=values['age'].lstrip("'")
  values['age']=values['age'].replace('Not Available / non disponible','Not available').replace('Deceased / Décédé','Deceased')
  if values['province']=='Newfoundland And Labrador': values['province']='Newfoundland and Labrador'
  encoded=[]
  for key in dictionaries:
   val=values[key] or 'Not specified'
   if val not in lookups[key]:
    lookups[key][val]=len(dictionaries[key]);dictionaries[key].append(val)
   encoded.append(lookups[key][val])
  victims=int(values['victims']); loss=money(values['loss'])
  if victims < 0: raise ValueError('Negative victim count')
  rows.append([date,*encoded,victims,loss])
  for total in ([totals,canadian] if values['country']=='Canada' else [totals]):
   total['reports']+=1;total['victims']+=victims;total['lossCents']+=int(Decimal(values['loss'].replace('$','').replace(',',''))*100)
 if not rows: raise ValueError('Empty CAFC extract')
 rows.sort(key=lambda r:r[0])
 for total in (totals,canadian): total['loss']=total.pop('lossCents')/100
 return {'schemaVersion':SCHEMA,'coverageStart':rows[0][0],'coverageEnd':rows[-1][0],'columns':['date',*dictionaries,'victims','loss'],'dictionaries':dictionaries,'rows':rows,'totals':{'allReports':totals,'canada':canadian},'notes':[
  'One row is one public CAFC report record. Counts are reports received, not incident dates, confirmed offences, or unique people. Public record IDs are omitted.',
  'Default Canadian view requires Country = Canada. Foreign and unspecified-country records remain separately selectable; Canadian connection does not establish Canadian residence.',
  'Victims are the sum of the published Number of Victims field; do not treat the total as unique individuals.',
  'Losses are reported Canadian dollars. A zero recorded loss is not proof of no harm: identity fraud, personal-information theft and phishing may record zero because losses are absorbed elsewhere or occur later.',
  'Loss quantiles describe positive recorded loss per report, not loss per victim. Do not infer unreported fraud or subtract these reports from police totals.',
 ]}

def cafc_coverage(data, package, resource):
 # Publisher's extract window includes days with no records. Observed extrema are separate.
 data['recordDateStart']=data['coverageStart'];data['recordDateEnd']=data['coverageEnd']
 match=re.search(r'(\d{4}-\d{2}-\d{2})-to-(\d{4}-\d{2}-\d{2})',resource['url'])
 if match:
  start,end=match.groups();dt.date.fromisoformat(start);dt.date.fromisoformat(end)
  if start>data['recordDateStart'] or end<data['recordDateEnd']:raise ValueError('CAFC extract dates exclude observed records')
  data['coverageStart']=start;data['coverageEnd']=end;data['coverageBasis']='Publisher extract filename'
 else:
  data['coverageBasis']='Observed record dates; no publisher extract window available'
 return data

def parse_zip(raw, table):
 with zipfile.ZipFile(io.BytesIO(raw)) as archive:
  body=archive.read(table+'.csv').decode('utf-8-sig')
  meta=archive.read(table+'_MetaData.csv').decode('utf-8-sig')
 rows=list(csv.DictReader(io.StringIO(body)))
 if not rows or not {'REF_DATE','GEO','VALUE','STATUS','UOM','SCALAR_FACTOR'}.issubset(rows[0]): raise ValueError(f'Invalid table schema {table}')
 return rows,meta

def number(row):
 value=row['VALUE'].strip();status=row['STATUS'].strip()
 if status in {'x','F','..','...'} or not value: return None
 result=float(value)
 if not math.isfinite(result) or result < 0: raise ValueError('Invalid or negative statistical value')
 if row['SCALAR_FACTOR'] != 'units': raise ValueError(f"Unsupported scalar factor: {row['SCALAR_FACTOR']}")
 return int(result) if result.is_integer() else result

def period_end(period):
 if '-Q' in period:
  year,q=period.split('-Q');month=int(q)*3
  return f'{year}-{month:02}-{calendar.monthrange(int(year),month)[1]:02}'
 return f'{period}-12-31'

def annual_geo(value):
 clean=re.sub(r' \[\d+\]$','',value)
 if clean in {'Canada','Total police-reported cybercrime','Canada, selected police services'}: return 'Canada','country'
 if clean in PROVINCES:return clean,'province'
 if clean.startswith('Total '):return clean,'aggregate'
 if 'Military' in clean:return clean,'military'
 return clean,'cma'

def police_rows(rows, source):
 result=[]
 for row in rows:
  period=row['REF_DATE'];geo,level=annual_geo(row['GEO'])
  measure='Incidents'
  if source=='police-quarterly':
   period+='-'+row['Calendar quarter'];geo=row['GEO'];level='country' if geo=='Canada' else 'region'
   if row['Statistics']=='Year to date data':measure='Year to date incidents'
   elif row['Statistics']!='Quarterly data': raise ValueError('Unrecognized quarterly statistic')
  elif source=='police-annual':
   if row.get('Statistics')=='Rate per 100,000 population':measure='Rate per 100,000 population'
   elif row.get('Statistics')!='Number of cybercrime incidents':raise ValueError('Unrecognized annual statistic')
  result.append({'source':source,'period':period,'geo':geo,'geoLevel':level,'offence':row.get('Cyber-related violation','Total, all violations'),'measure':measure,'value':number(row),'status':row['STATUS']})
 return result

def business_rows(rows, source):
 reserved={'REF_DATE','GEO','DGUID','North American Industry Classification System (NAICS)','Size of enterprise','UOM','UOM_ID','SCALAR_FACTOR','SCALAR_ID','VECTOR','COORDINATE','VALUE','STATUS','SYMBOL','TERMINATED','DECIMALS'}
 dimensions=[x for x in rows[0] if x not in reserved]
 if len(dimensions)!=1:raise ValueError(f'Unexpected business dimensions: {dimensions}')
 result=[]
 for row in rows:
  if row['GEO']!='Canada':raise ValueError('Unexpected business geography; regional dimensions require explicit support')
  value=number(row)
  if row['UOM']=='Percent' and value is not None and value > 100:raise ValueError('Percentage outside 0–100')
  result.append({'source':source,'period':row['REF_DATE'],'industry':row['North American Industry Classification System (NAICS)'],'size':row['Size of enterprise'],'metric':row[dimensions[0]],'unit':row['UOM'],'value':value,'status':row['STATUS'],'denominator':'Impacted enterprises' if source in {'business-reporting','business-recovery-cost','business-impacts'} else 'All enterprises'})
 return result

def unique_coordinates(rows, dimensions):
 seen=set()
 for row in rows:
  key=tuple(row[d] for d in dimensions)
  if key in seen:raise ValueError('Duplicate normalized statistical coordinate')
  seen.add(key)

def metadata_notes(meta):
 lines=list(csv.reader(io.StringIO(meta)))
 start=next((i+1 for i,r in enumerate(lines) if r[:2]==['Note ID','Note']),None)
 if start is None:return []
 notes=[]
 for r in lines[start:]:
  if len(r)<2 or not r[0].isdigit():break
  notes.append({'id':r[0],'text':r[1]})
 return notes

def table_load(entry, cache, offline, checked):
 table,source,title=entry;url=f'https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={table}01';download=f'https://www150.statcan.gc.ca/n1/tbl/csv/{table}-eng.zip'
 raw=fetch(download,cache/(table+'-eng.zip'),offline);rows,meta=parse_zip(raw,table)
 converted=police_rows(rows,source) if source.startswith('police-') else business_rows(rows,source)
 unique_coordinates(converted,['period','geo','offence','measure'] if source.startswith('police-') else ['period','industry','size','metric','unit'])
 periods=sorted({r['period'] for r in converted})
 # The publication date comes from the source page, not the downloader's clock.
 html=fetch(url,cache/(table+'.html'),offline).decode('utf-8',errors='replace')
 match=re.search(r'Release date:.*?(\d{4}-\d{2}-\d{2})',html,re.S)
 if not match: raise ValueError(f'Publication date missing from StatCan table {table}')
 info={'id':source,'title':title,'publisher':'Statistics Canada','url':url,'downloadUrl':download,'license':'Statistics Canada Open Licence','checkedAt':checked,'publishedAt':match.group(1),'coverageStart':periods[0][:4]+'-01-01','coverageEnd':period_end(periods[-1]),'status':'ok','recordCount':len(rows),'sha256':hashlib.sha256(raw).hexdigest(),'table':table,'note':'Preliminary quarterly observations; quarterly and cumulative year-to-date counts are separate.' if source=='police-quarterly' else 'Suppressed, unavailable and unpublished estimates remain null; source quality flags are retained.'}
 return converted,info,metadata_notes(meta)

def check_regression(old, current):
 for entry in current:
  previous=next((x for x in old.get('sources',[]) if x['id']==entry['id']),None)
  if previous:
   if entry['coverageEnd'] < previous['coverageEnd']:raise ValueError(f"Coverage regressed for {entry['id']}")
   if entry['recordCount'] < previous['recordCount']*0.8:raise ValueError(f"Record count fell by more than 20% for {entry['id']}; review the publisher's change before replacing")

def run(cache, offline=False):
 attempted=now();checked=attempted;DATA.mkdir(parents=True,exist_ok=True)
 old=json.loads((DATA/'manifest.json').read_text()) if (DATA/'manifest.json').exists() else {}
 if offline:
  cached_files=list(cache.glob('*'))
  if not cached_files:raise ValueError('Offline source cache is empty')
  checked=old.get('checkedAt') or dt.datetime.fromtimestamp(min(p.stat().st_mtime for p in cached_files),dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
 errors=[];police=[];business=[];notes={};sources=[]
 try:
  package=json.loads(fetch(CAFC_API,cache/'cafc-package.json',offline))['result']
  resource=next(r for r in package['resources'] if r['format'].upper()=='CSV')
  raw=fetch(resource['url'],cache/'cafc.csv',offline);cafc=cafc_coverage(parse_cafc(raw),package,resource)
  if len(cafc['rows']) < 100000:raise ValueError('CAFC extract unexpectedly small')
  warning=package.get('notes_translated',{}).get('en',package.get('notes',''))
  delayed='changeover' in warning.lower() or 'not yet ready' in warning.lower()
  sources.append({'id':'cafc','title':'Canadian Anti-Fraud Centre public fraud reports','publisher':'Royal Canadian Mounted Police / CAFC','url':CAFC_PAGE,'downloadUrl':resource['url'],'definitionsUrl':CAFC_DEFINITIONS,'license':'Open Government Licence – Canada','checkedAt':checked,'publishedAt':(resource.get('last_modified') or resource.get('created') or '')[:10],'catalogModifiedAt':package.get('metadata_modified',''),'coverageStart':cafc['coverageStart'],'coverageEnd':cafc['coverageEnd'],'recordDateStart':cafc['recordDateStart'],'recordDateEnd':cafc['recordDateEnd'],'coverageBasis':cafc['coverageBasis'],'status':'stale' if delayed else 'ok','recordCount':len(cafc['rows']),'canadaRecordCount':cafc['totals']['canada']['reports'],'sha256':hashlib.sha256(raw).hexdigest(),'note':'The publisher says the Q4 2025 update is delayed by a system changeover. Checking weekly does not create newer reports.' if delayed else 'Coverage describes report receipt dates in the published extract; latest check is not a new observation.'})
 except Exception as exc:errors.append({'source':'cafc','error':str(exc)})
 try:
  summaries,summary_sources=load_summaries(cache,offline,checked,fetch)
  sources.extend(summary_sources)
 except Exception as exc:errors.append({'source':'cafc-summaries','error':str(exc)})
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  futures={pool.submit(table_load,entry,cache,offline,checked):entry for entry in TABLES}
  for future in concurrent.futures.as_completed(futures):
   entry=futures[future]
   try:
    rows,info,source_notes=future.result();sources.append(info);notes[info['id']]=source_notes
    (police if info['id'].startswith('police-') else business).extend(rows)
   except Exception as exc:errors.append({'source':entry[1],'error':str(exc)})
 sources.sort(key=lambda s:next((i for i,t in enumerate(['cafc']+[e[1] for e in TABLES]) if t==s['id']),100))
 if not errors:
  try:check_regression(old,sources)
  except Exception as exc:errors.append({'source':'validation','error':str(exc)})
 if errors:
  dump_json(DATA/'refresh-status.json',{'schemaVersion':SCHEMA,'checkedAt':checked,'attemptedAt':attempted,'offlineRebuild':offline,'success':False,'errors':errors,'note':'Previous validated data files and manifest were preserved.'})
  for e in errors:print(f"ERROR {e['source']}: {e['error']}",file=sys.stderr)
  return 1
 police.sort(key=lambda r:(r['source'],r['period'],r['geo'],r['offence'],r['measure']))
 business.sort(key=lambda r:(r['source'],r['period'],r['industry'],r['size'],r['metric']))
 threat_path=DATA/'threats.json'
 if threat_path.exists():
  threat=json.loads(threat_path.read_text());source=threat.get('source')
  if source:sources.append(source)
 changes=[]
 for source in sources:
  prev=next((s for s in old.get('sources',[]) if s['id']==source['id']),{})
  if any(prev.get(k)!=source.get(k) for k in ['sha256','coverageStart','coverageEnd','publishedAt','status']):
   changes.append({'source':source['id'],'previousCount':prev.get('recordCount'),'recordCount':source.get('recordCount'),'previousCoverageEnd':prev.get('coverageEnd'),'coverageEnd':source.get('coverageEnd'),'previousHash':prev.get('sha256'),'sha256':source.get('sha256')})
 manifest={'schemaVersion':SCHEMA,'checkedAt':checked,'generatedAt':attempted,'offlineRebuild':offline,'sources':sources,'files':{name:f'data/{name}.json' for name in ['cafc','summaries','police','business','threats']},'notes':['These sources measure different populations and must not be added together.','Source release dates, observation coverage and our download/check dates are distinct.'],'qualityFlags':FLAGS}
 history_path=DATA/'refresh-history.json';history=json.loads(history_path.read_text()) if history_path.exists() else {'schemaVersion':SCHEMA,'runs':[]}
 history['runs'].insert(0,{'checkedAt':checked,'generatedAt':attempted,'offlineRebuild':offline,'success':True,'changedSources':len(changes),'changes':changes});history['runs']=history['runs'][:60]
 payloads={'cafc.json':cafc,'police.json':{'schemaVersion':SCHEMA,'rows':police,'notes':{k:v for k,v in notes.items() if k.startswith('police-')},'qualityFlags':FLAGS},'business.json':{'schemaVersion':SCHEMA,'rows':business,'notes':{k:v for k,v in notes.items() if k.startswith('business-')},'qualityFlags':FLAGS},'manifest.json':manifest,'refresh-history.json':history,'refresh-status.json':{'schemaVersion':SCHEMA,'checkedAt':checked,'attemptedAt':attempted,'offlineRebuild':offline,'success':True,'errors':[],'changedSources':len(changes)}}
 payloads['summaries.json']=summaries
 # Serialize and validate every output before publishing any files.
 for name,payload in payloads.items():json.dumps(payload,allow_nan=False)
 for name,payload in payloads.items():dump_json(DATA/name,payload)
 print(json.dumps({'success':True,'checkedAt':checked,'cafcReports':len(cafc['rows']),'policeObservations':len(police),'businessObservations':len(business),'sources':len(sources),'changedSources':len(changes)}))
 return 0

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cache-dir',type=Path,default=ROOT/'.cache'/'sources');parser.add_argument('--offline-cache',action='store_true',help='Rebuild from exact previously downloaded source files without network calls')
 args=parser.parse_args();return run(args.cache_dir,args.offline_cache)

if __name__=='__main__':raise SystemExit(main())
