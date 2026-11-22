// Pure transforms. Source populations remain separate; totals are never combined.
export const VIEWS = ['fraud', 'police', 'business', 'threats', 'sources'];
export const DEFAULTS = {view:'fraud',country:'Canada',province:'',category:'',method:'',complaint:'',age:'',start:'',end:'',interval:'month',metric:'reports',policeSource:'police-annual',geo:'Canada',offence:'Total, all violations',measure:'Incidents',industry:'Private sector',size:'Total, all enterprises',businessSource:'business-incidents',businessMetric:'',query:'',ransomware:'all'};
export function validDate(value) { if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;const date=new Date(value+'T00:00:00Z');return Number.isFinite(date.valueOf())&&date.toISOString().slice(0,10)===value; }
export function stateFromSearch(search) {
  const params = new URLSearchParams(search);
  const state = {...DEFAULTS};
  for (const key of Object.keys(state)) if (params.has(key)) state[key] = params.get(key);
  if (!VIEWS.includes(state.view)) state.view = DEFAULTS.view;
  if (!['day','week','month','year'].includes(state.interval)) state.interval = DEFAULTS.interval;
  if (!['reports','victims','loss'].includes(state.metric)) state.metric = DEFAULTS.metric;
  if (!['all','known'].includes(state.ransomware)) state.ransomware = DEFAULTS.ransomware;
  for (const key of ['start','end']) if (!validDate(state[key])) state[key] = '';
  return state;
}
export function searchFromState(state) {const q=new URLSearchParams();for(const [k,v] of Object.entries(DEFAULTS)) if(state[k]!==v&&state[k]!==undefined&&state[k]!=='') q.set(k,state[k]);return q.toString();}
export function periodKey(date, interval='month') {
  if (interval==='day') return date;
  if (interval==='year') return date.slice(0,4);
  if (interval==='month') return date.slice(0,7);
  const d=new Date(date+'T00:00:00Z'); const offset=(d.getUTCDay()+6)%7;d.setUTCDate(d.getUTCDate()-offset);return d.toISOString().slice(0,10);
}
export function increment(map,key,victims,loss) {const row=map.get(key)||{key,reports:0,victims:0,loss:0};row.reports++;row.victims+=victims;row.loss+=loss;map.set(key,row);}
export function percentile(sorted,p){if(!sorted.length)return null;const pos=(sorted.length-1)*p,lo=Math.floor(pos),hi=Math.ceil(pos);return sorted[lo]+(sorted[hi]-sorted[lo])*(pos-lo);}
export function cafcSummary(data,filters={}) {
  const columns=Object.fromEntries(data.columns.map((name,i)=>[name,i]));
  const coded=[];
  for(const key of ['country','province','category','method','complaint','age']) {
    if(filters[key]) coded.push([columns[key],data.dictionaries[key].indexOf(filters[key])]);
  }
  const rows=[],timeline=new Map(),categories=new Map(),provinces=new Map(),methods=new Map(),daily=new Map();
  let victims=0,loss=0,first=null,last=null;const positives=[];
  for (const row of data.rows) {
    const date=row[columns.date];
    if(filters.start&&date<filters.start||filters.end&&date>filters.end||coded.some(([i,n])=>row[i]!==n)) continue;
    const v=Number(row[columns.victims])||0,l=Number(row[columns.loss])||0;
    rows.push(row);victims+=v;loss+=l;if(l>0)positives.push(l);first=first===null||date<first?date:first;last=last===null||date>last?date:last;
    increment(timeline,periodKey(date,filters.interval||'month'),v,l);
    increment(categories,data.dictionaries.category[row[columns.category]],v,l);
    increment(provinces,data.dictionaries.province[row[columns.province]],v,l);
    increment(methods,data.dictionaries.method[row[columns.method]],v,l);
    increment(daily,date,v,l);
  }
  positives.sort((a,b)=>a-b);const metric=filters.metric||'reports';
  const sort=map=>[...map.values()].sort((a,b)=>b[metric]-a[metric]||a.key.localeCompare(b.key));
  const bins=[{key:'No recorded loss',reports:rows.length-positives.length},{key:'Under $1,000',reports:0},{key:'$1,000–$9,999',reports:0},{key:'$10,000–$99,999',reports:0},{key:'$100,000+',reports:0}];
  for(const v of positives) bins[v<1000?1:v<10000?2:v<100000?3:4].reports++;
  return {rows,reports:rows.length,victims,loss,first,last,positiveCount:positives.length,median:percentile(positives,.5),p90:percentile(positives,.9),maximum:positives.at(-1)??null,timeline:[...timeline.values()].sort((a,b)=>a.key.localeCompare(b.key)),categories:sort(categories),provinces:sort(provinces),methods:sort(methods),daily:[...daily.values()].sort((a,b)=>a.key.localeCompare(b.key)),bins};
}
export function decodedCafcRows(data,rows){return rows.map(row=>Object.fromEntries(data.columns.map((key,i)=>[key,data.dictionaries[key]?data.dictionaries[key][row[i]]:row[i]])));}
export function policeSeries(rows,state){return rows.filter(r=>r.source===state.policeSource&&r.geo===state.geo&&r.offence===state.offence&&r.measure===state.measure).sort((a,b)=>a.period.localeCompare(b.period));}
export function businessSeries(rows,state){return rows.filter(r=>r.source===state.businessSource&&r.industry===state.industry&&r.size===state.size&&r.metric===state.businessMetric).sort((a,b)=>a.period.localeCompare(b.period));}
export function threatRecords(rows,{query='',ransomware='all'}={}) {const needle=query.trim().toLowerCase();return rows.filter(r=>(ransomware!=='known'||r.ransomware_known)&&(!needle||[r.cve,r.vendor,r.product,r.name,r.description].some(s=>String(s??'').toLowerCase().includes(needle))));}
export function csv(rows,columns=Object.keys(rows[0]||{})) {
  const cell=value=>{let s=String(value??'');if(typeof value!=='number'&&/^[\s\u0000-\u001f]*[=+@-]/.test(s))s="'"+s;return /[",\r\n]/.test(s)?'"'+s.replaceAll('"','""')+'"':s;};
  return '\uFEFF'+[columns.map(cell).join(','),...rows.map(row=>columns.map(k=>cell(row[k])).join(','))].join('\r\n');
}
export function unique(rows,key){return [...new Set(rows.map(r=>r[key]).filter(v=>v!==undefined&&v!==null))].sort((a,b)=>String(a).localeCompare(String(b)));}
export function completePeriods(points,interval,start,end) {
  if(!start||!end||start>end)return [];const byKey=new Map(points.map(p=>[p.key,p]));const result=[];
  let cursor=periodKey(start,interval),last=periodKey(end,interval);let safety=0;
  while(cursor<=last&&safety++<10000) {
    result.push(byKey.get(cursor)||{key:cursor,reports:0,victims:0,loss:0});
    const d=new Date(cursor+(cursor.length===4?'-01-01':cursor.length===7?'-01':'')+'T00:00:00Z');
    if(interval==='year')d.setUTCFullYear(d.getUTCFullYear()+1);else if(interval==='month')d.setUTCMonth(d.getUTCMonth()+1);else d.setUTCDate(d.getUTCDate()+(interval==='week'?7:1));
    cursor=periodKey(d.toISOString().slice(0,10),interval);
  }
  return result;
}
export function completeWeekComparison(daily,start,end,metric='reports') {
  if(!validDate(start)||!validDate(end)||start>end)return null;
  const last=new Date(end+'T00:00:00Z');last.setUTCDate(last.getUTCDate()-last.getUTCDay());
  const iso=d=>d.toISOString().slice(0,10),shift=(d,days)=>{const result=new Date(d);result.setUTCDate(result.getUTCDate()+days);return result;};
  const currentStart=iso(shift(last,-6)),currentEnd=iso(last),previousStart=iso(shift(last,-13)),previousEnd=iso(shift(last,-7));
  if(previousStart<start)return null;
  let current=0,previous=0;
  for(const row of daily){if(row.key>=currentStart&&row.key<=currentEnd)current+=row[metric]||0;if(row.key>=previousStart&&row.key<=previousEnd)previous+=row[metric]||0;}
  return {currentStart,currentEnd,previousStart,previousEnd,current,previous,difference:current-previous,percent:previous?(current-previous)/previous*100:null};
}
export function monthlySeasonality(daily,start,end,metric='reports') {
  if(!validDate(start)||!validDate(end)||start>end)return [];
  const months=Array.from({length:12},(_,i)=>({key:['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][i],days:0,total:0,average:null}));
  const byDate=new Map(daily.map(row=>[row.key,row[metric]||0]));
  for(let day=new Date(start+'T00:00:00Z'),last=new Date(end+'T00:00:00Z');day<=last;day.setUTCDate(day.getUTCDate()+1)){const m=months[day.getUTCMonth()];m.days++;m.total+=byDate.get(day.toISOString().slice(0,10))||0;}
  for(const month of months)if(month.days)month.average=month.total/month.days;
  return months;
}
