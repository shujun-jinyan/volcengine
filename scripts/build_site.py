#!/usr/bin/env python3
"""根据 data/ledger.json 生成静态台账网站 public/index.html。"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "ledger.json")
PUBLIC = os.path.join(ROOT, "public")

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>方舟项目账单台账</title>
<style>
:root{
  --bg:#f5f7fb; --card:#ffffff; --ink:#101828; --sub:#667085; --line:#e6eaf2;
  --brand:#2f6bff; --brand-2:#7aa2ff; --green:#0f9f6e; --red:#e0483d; --amber:#d98600;
  --shadow:0 1px 2px rgba(16,24,40,.04),0 8px 24px rgba(16,24,40,.06);
  --radius:16px;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing:antialiased;padding:28px 22px 60px;}
.wrap{max-width:1280px;margin:0 auto}
header.top{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:22px}
.brand{display:flex;align-items:center;gap:12px}
.logo{width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,#2f6bff,#78a4ff);
  display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:18px;box-shadow:var(--shadow)}
h1{font-size:22px;margin:0;letter-spacing:.2px}
.sub{color:var(--sub);font-size:13px;margin-top:4px}
.meta{text-align:right;font-size:12px;color:var(--sub);line-height:1.7}
.pill{display:inline-flex;align-items:center;gap:6px;background:#eef3ff;color:#2f5cd8;
  border-radius:999px;padding:4px 10px;font-size:12px;font-weight:600}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green)}
.grid-kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}
.kpi{padding:16px 18px}
.kpi .label{font-size:12px;color:var(--sub);display:flex;align-items:center;gap:6px}
.kpi .val{font-size:26px;font-weight:700;margin-top:8px;letter-spacing:-.3px;font-variant-numeric:tabular-nums}
.kpi .val small{font-size:13px;font-weight:500;color:var(--sub);margin-left:4px}
.kpi .hint{font-size:12px;color:var(--sub);margin-top:6px}
.section{margin-top:18px;padding:20px}
.section-head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px}
.section-title{font-size:15px;font-weight:700}
.section-title span{font-weight:500;color:var(--sub);font-size:12px;margin-left:8px}
select,input{font-family:inherit;font-size:13px;color:var(--ink);background:#fff;border:1px solid var(--line);
  border-radius:10px;padding:8px 10px;outline:none}
select:focus,input:focus{border-color:var(--brand);box-shadow:0 0 0 3px rgba(47,107,255,.12)}
.btn{font-family:inherit;font-size:13px;cursor:pointer;border:1px solid var(--line);background:#fff;
  color:var(--ink);border-radius:10px;padding:8px 12px;font-weight:600}
.btn:hover{border-color:#c9d4ea;background:#f8faff}
.btn.primary{background:var(--brand);border-color:var(--brand);color:#fff}
.btn.primary:hover{background:#255ce0}
.chart{width:100%;height:300px;overflow:visible}
.legend{display:flex;flex-wrap:wrap;gap:10px 16px;margin-top:10px;font-size:12px;color:var(--sub)}
.legend i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:6px;vertical-align:middle}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
th{font-size:12px;color:var(--sub);font-weight:600;background:#fafbfe;position:sticky;top:0;z-index:1}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tbody tr:hover{background:#f7f9ff}
.share{display:flex;align-items:center;gap:8px;min-width:130px}
.bar{height:6px;border-radius:99px;background:#eef1f7;flex:1;overflow:hidden}
.bar>i{display:block;height:100%;border-radius:99px;background:var(--brand)}
.tag{display:inline-block;padding:2px 8px;border-radius:999px;background:#f2f4f8;color:#475467;font-size:11px;font-weight:600}
.table-wrap{max-height:520px;overflow:auto;border:1px solid var(--line);border-radius:12px}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.toolbar label{font-size:12px;color:var(--sub)}
.note-input{width:100%;min-width:120px;border:1px dashed #d6dced;border-radius:8px;padding:5px 8px;font-size:12px;background:#fcfdff}
.note-input:focus{border-style:solid;border-color:var(--brand);background:#fff}
.matrix td.first{position:sticky;left:0;background:#fff;font-weight:600;z-index:1;box-shadow:1px 0 0 var(--line)}
.matrix tbody tr:hover td.first{background:#f7f9ff}
.matrix th.first{position:sticky;left:0;background:#fafbfe;z-index:2}
.heat{font-weight:600}
.empty{padding:26px;text-align:center;color:var(--sub);font-size:13px}
footer{margin-top:26px;color:#98a2b3;font-size:12px;line-height:1.8;text-align:center}
.tabs{display:flex;gap:6px;background:#f1f4fa;padding:4px;border-radius:12px}
.tab{border:0;background:transparent;font-family:inherit;font-size:13px;font-weight:600;color:var(--sub);
  padding:7px 14px;border-radius:9px;cursor:pointer}
.tab.active{background:#fff;color:var(--ink);box-shadow:0 1px 2px rgba(16,24,40,.08)}
.kpi .up{color:var(--red)} .kpi .down{color:var(--green)}
@media(max-width:960px){.grid-kpi{grid-template-columns:repeat(2,1fr)}}
@media(max-width:640px){body{padding:16px 12px 40px}.kpi .val{font-size:22px}.section{padding:14px}}
@media print{body{background:#fff;padding:0}.btn,.toolbar,.tabs{display:none}.card{box-shadow:none}}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div class="brand">
      <div class="logo">方</div>
      <div>
        <h1>方舟项目账单台账</h1>
        <div class="sub">按天 × 项目统计 · 数据来源：火山引擎账单中心分账明细</div>
      </div>
    </div>
    <div class="meta">
      <div class="pill"><span class="dot"></span>数据已更新</div>
      <div id="genAt" style="margin-top:6px"></div>
      <div>每日 10:00 / 14:00 自动更新</div>
    </div>
  </header>

  <div class="grid-kpi">
    <div class="card kpi">
      <div class="label">统计周期累计消费</div>
      <div class="val" id="kpiTotal">—<small>元</small></div>
      <div class="hint" id="kpiRange"></div>
    </div>
    <div class="card kpi">
      <div class="label">参与项目数</div>
      <div class="val" id="kpiProjects">—<small>个</small></div>
      <div class="hint">含未归属项目</div>
    </div>
    <div class="card kpi">
      <div class="label">日均消费</div>
      <div class="val" id="kpiAvg">—<small>元</small></div>
      <div class="hint">按有消费日期计算</div>
    </div>
    <div class="card kpi">
      <div class="label">最新一日消费</div>
      <div class="val" id="kpiLatest">—<small>元</small></div>
      <div class="hint" id="kpiLatestDate"></div>
    </div>
  </div>

  <div class="card section">
    <div class="section-head">
      <div class="section-title">每日消费趋势<span id="chartSub"></span></div>
      <div class="toolbar">
        <label>项目</label>
        <select id="fProject"></select>
        <label>口径</label>
        <select id="fMetric"><option value="pretax">税前应付</option><option value="payable">应付金额</option></select>
      </div>
    </div>
    <svg class="chart" id="chart" viewBox="0 0 1100 300" preserveAspectRatio="none"></svg>
    <div class="legend" id="legend"></div>
  </div>

  <div class="card section">
    <div class="section-head">
      <div class="section-title">项目消费汇总<span>点击表头可排序</span></div>
      <div class="toolbar">
        <label>月份</label>
        <select id="fMonth"></select>
      </div>
    </div>
    <div class="table-wrap">
      <table id="projTable">
        <thead><tr>
          <th data-k="name">项目名称</th><th data-k="id">项目标识</th>
          <th class="num" data-k="pretax">消费金额(元)</th>
          <th class="num" data-k="share">占比</th>
          <th class="num" data-k="days">消费天数</th>
          <th class="num" data-k="avg">日均(元)</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>

  <div class="card section">
    <div class="section-head">
      <div class="section-title">消费台账明细<span>可填写备注，备注保存在本机浏览器</span></div>
      <div class="toolbar">
        <input id="fSearch" placeholder="搜索项目 / 日期">
        <select id="fMonth2"></select>
        <button class="btn primary" id="btnCsv">导出 CSV</button>
        <button class="btn" id="btnPrint">打印</button>
      </div>
    </div>
    <div class="table-wrap">
      <table id="ledgerTable">
        <thead><tr>
          <th>日期</th><th>项目名称</th><th>项目标识</th>
          <th class="num">消费金额(元)</th><th class="num">应付金额(元)</th>
          <th>备注</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>

  <div class="card section">
    <div class="section-head">
      <div class="section-title">项目 × 日期 台账矩阵<span>颜色越深表示当日消费越高</span></div>
      <div class="toolbar">
        <select id="fMonth3"></select>
        <select id="fOrder"><option value="name">按项目名称</option><option value="total">按累计金额</option></select>
      </div>
    </div>
    <div class="table-wrap">
      <table class="matrix" id="matrixTable">
        <thead></thead><tbody></tbody>
      </table>
    </div>
  </div>

  <footer>
    数据口径：分账明细（ListSplitBillDetail，按天 × 项目），金额为税前应付（PretaxAmount）。<br>
    分账明细存在 T+2 延迟，当日及前一日数据可能仍在滚动更新；请以火山引擎账单中心最终账单为准。
  </footer>
</div>

<script id="ledger-data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('ledger-data').textContent);
const fmt = n => (n||0).toLocaleString('zh-CN',{minimumFractionDigits:2, maximumFractionDigits:2});
const fmtShort = n => Math.abs(n)>=10000 ? (n/10000).toFixed(2)+'万' : fmt(n);
const $ = s => document.querySelector(s);
const state = { month:'all', project:'all', metric:'pretax', order:'name', sortK:'pretax', sortDir:-1 };

document.getElementById('genAt').textContent = '最近更新：' + DATA.generatedAt;
document.getElementById('kpiRange').textContent = DATA.dateRange.start + ' 至 ' + DATA.dateRange.end;

const projById = {}; DATA.projects.forEach(p=>projById[p.id]=p);
const cellMap = {}; DATA.cells.forEach(c=>cellMap[c.date+'|'+c.project]=c);

function months(){ return [...new Set(DATA.cells.map(c=>c.date.slice(0,7)))].sort(); }
function monthCells(m){
  return m==='all'? DATA.cells : DATA.cells.filter(c=>c.date.startsWith(m));
}
function projectsIn(m){
  const mp = {}; monthCells(m).forEach(c=>{mp[c.project]=(mp[c.project]||0)+c.pretax;});
  return Object.entries(mp).sort((a,b)=>b[1]-a[1]).map(([id])=>projById[id]);
}

/* KPI */
(function(){
  const t = DATA.totalPretax;
  $('#kpiTotal').innerHTML = fmt(t)+'<small>元</small>';
  $('#kpiProjects').innerHTML = DATA.projects.length+'<small>个</small>';
  const days = DATA.dates.length;
  $('#kpiAvg').innerHTML = fmt(t/Math.max(days,1))+'<small>元</small>';
  const last = DATA.dates[DATA.dates.length-1];
  if(last){
    $('#kpiLatest').innerHTML = fmt(last.pretax)+'<small>元</small>';
    $('#kpiLatestDate').textContent = last.date + ' · ' + last.projects + ' 个项目';
  }
})();

/* filters */
const mSel = months();
['#fMonth','#fMonth2','#fMonth3'].forEach(sel=>{
  const el=$(sel); el.innerHTML='<option value="all">全部月份</option>'+mSel.map(m=>`<option value="${m}">${m}</option>`).join('');
  el.addEventListener('change',()=>{
    state.month=el.value;
    ['#fMonth','#fMonth2','#fMonth3'].forEach(s=>{ if($(s).value!==el.value) $(s).value=el.value; });
    renderAll();
  });
});
$('#fProject').innerHTML='<option value="all">全部项目</option>'+DATA.projects.map(p=>`<option value="${p.id}">${p.name}</option>`).join('');
$('#fProject').addEventListener('change',e=>{state.project=e.target.value;renderChart();});
$('#fMetric').addEventListener('change',e=>{state.metric=e.target.value;renderChart();});
$('#fSearch').addEventListener('input',renderLedger);
$('#fOrder').addEventListener('change',e=>{state.order=e.target.value;renderMatrix();});
document.querySelectorAll('#projTable th[data-k]').forEach(th=>{
  th.style.cursor='pointer';
  th.addEventListener('click',()=>{
    const k=th.dataset.k;
    if(state.sortK===k) state.sortDir*=-1; else {state.sortK=k;state.sortDir=-1;}
    renderProjects();
  });
});

const PALETTE=['#2f6bff','#0f9f6e','#d98600','#8e5cf7','#e0483d','#0e9aa7','#c026d3','#64748b','#f59e0b','#3b82f6','#10b981','#ef4444','#8b5cf6'];
const colorOf={};
function colorFor(id){
  if(!colorOf[id]){
    const idx=Object.keys(colorOf).length % PALETTE.length;
    colorOf[id]=PALETTE[idx];
  }
  return colorOf[id];
}

/* chart: stacked daily bars */
function renderChart(){
  const m = state.month;
  const cells = monthCells(m).filter(c=> state.project==='all' || c.project===state.project);
  const dates = [...new Set(cells.map(c=>c.date))].sort();
  const byDate={};
  cells.forEach(c=>{ (byDate[c.date]=byDate[c.date]||{})[c.project]=(byDate[c.date][c.project]||0)+c[state.metric]; });
  const totals = dates.map(d=>Object.values(byDate[d]).reduce((a,b)=>a+b,0));
  const max = Math.max(...totals,1);
  const projTotals={};
  cells.forEach(c=>projTotals[c.project]=(projTotals[c.project]||0)+c[state.metric]);
  let order=Object.entries(projTotals).sort((a,b)=>b[1]-a[1]).map(([id])=>id);
  if(order.length>8){ order=order.slice(0,7).concat(['__other']); }
  $('#chartSub').textContent = `${dates.length} 天 · ${state.project==='all'?'全部项目':projById[state.project].name}`;
  const W=1100,H=300,padL=54,padR=16,padT=16,padB=34;
  const plotW=W-padL-padR, plotH=H-padT-padB;
  const bw=plotW/Math.max(dates.length,1);
  const barW=Math.max(2,Math.min(26,bw*0.62));
  let svg=`<g class="axis">`;
  for(let i=0;i<=4;i++){
    const y=padT+plotH*i/4, v=max*(1-i/4);
    svg+=`<line x1="${padL}" y1="${y}" x2="${W-padR}" y2="${y}" stroke="#eef1f7"/>`;
    svg+=`<text x="${padL-8}" y="${y+4}" text-anchor="end" font-size="10" fill="#98a2b3">${fmtShort(v)}</text>`;
  }
  svg+=`</g>`;
  dates.forEach((d,di)=>{
    const x=padL+di*bw+(bw-barW)/2;
    let y=padT+plotH;
    const segs={};
    Object.entries(byDate[d]).forEach(([pid,v])=>{ segs[order.includes(pid)?pid:'__other']=(segs[order.includes(pid)?pid:'__other']||0)+v; });
    order.forEach(pid=>{
      const v=segs[pid]||0; if(v<=0) return;
      const h=v/max*plotH; y-=h;
      const color = pid==='__other' ? '#cbd5e1' : colorFor(pid);
      svg+=`<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${h.toFixed(1)}" fill="${color}" rx="2"><title>${d} · ${pid==='__other'?'其他项目':projById[pid].name}：${fmt(v)} 元</title></rect>`;
    });
    if(dates.length<=20 || di%Math.ceil(dates.length/14)===0){
      svg+=`<text x="${(x+barW/2).toFixed(1)}" y="${H-12}" text-anchor="middle" font-size="10" fill="#98a2b3">${d.slice(5)}</text>`;
    }
  });
  $('#chart').innerHTML=svg;
  $('#legend').innerHTML=order.map(pid=>`<span><i style="background:${pid==='__other'?'#cbd5e1':colorFor(pid)}"></i>${pid==='__other'?'其他项目':projById[pid].name}</span>`).join('');
}

/* project summary */
function renderProjects(){
  const m=state.month;
  let rows=projectsIn(m).map(p=>{
    const share=p.pretax/Math.max(monthCells(m).reduce((a,c)=>a+c.pretax,0),0.0001)*100;
    return {id:p.id,name:p.name,pretax:p.pretax,share,days:p.days,avg:p.pretax/Math.max(p.days,1)};
  });
  const k=state.sortK,d=state.sortDir;
  rows.sort((a,b)=> typeof a[k]==='number' ? (a[k]-b[k])*d : String(a[k]).localeCompare(String(b[k]),'zh')*d);
  $('#projTable tbody').innerHTML=rows.map(r=>`<tr>
    <td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${colorFor(r.id)};margin-right:8px"></span>${r.name}</td>
    <td><span class="tag">${r.id}</span></td>
    <td class="num" style="font-weight:700">${fmt(r.pretax)}</td>
    <td class="num"><div class="share"><div class="bar"><i style="width:${Math.min(r.share,100)}%;background:${colorFor(r.id)}"></i></div><span>${r.share.toFixed(1)}%</span></div></td>
    <td class="num">${r.days}</td>
    <td class="num">${fmt(r.avg)}</td>
  </tr>`).join('') || `<tr><td colspan="6" class="empty">暂无数据</td></tr>`;
}

/* ledger detail */
const noteKey='ark-ledger-notes';
function getNotes(){ try{return JSON.parse(localStorage.getItem(noteKey)||'{}')}catch(e){return {}} }
function renderLedger(){
  const q=($('#fSearch').value||'').trim().toLowerCase();
  const m=state.month;
  const notes=getNotes();
  let rows=DATA.cells.filter(c=> m==='all' || c.date.startsWith(m));
  if(state.project!=='all') rows=rows.filter(c=>c.project===state.project);
  if(q) rows=rows.filter(c=> (c.projectName+' '+c.project+' '+c.date).toLowerCase().includes(q));
  rows=[...rows].sort((a,b)=> b.date.localeCompare(a.date) || b.pretax-a.pretax);
  const tb=$('#ledgerTable tbody');
  tb.innerHTML=rows.map(c=>`<tr>
    <td>${c.date}</td>
    <td>${c.projectName}</td>
    <td><span class="tag">${c.project}</span></td>
    <td class="num" style="font-weight:600">${fmt(c.pretax)}</td>
    <td class="num">${fmt(c.payable)}</td>
    <td><input class="note-input" data-k="${c.date}|${c.project}" value="${(notes[c.date+'|'+c.project]||'').replace(/"/g,'&quot;')}" placeholder="填写备注"></td>
  </tr>`).join('') || `<tr><td colspan="6" class="empty">没有匹配的记录</td></tr>`;
  tb.querySelectorAll('.note-input').forEach(inp=>{
    inp.addEventListener('change',()=>{
      const n=getNotes(); const v=inp.value.trim();
      if(v) n[inp.dataset.k]=v; else delete n[inp.dataset.k];
      localStorage.setItem(noteKey,JSON.stringify(n));
    });
  });
}

/* matrix */
function renderMatrix(){
  const m=state.month==='all' ? mSel[mSel.length-1] : state.month;
  const cells=DATA.cells.filter(c=>c.date.startsWith(m));
  const dates=[...new Set(cells.map(c=>c.date))].sort();
  let projects=[...new Set(cells.map(c=>c.project))].map(id=>{
    const total=cells.filter(c=>c.project===id).reduce((a,c)=>a+c.pretax,0);
    return {id,total,name:projById[id].name};
  });
  if(state.order==='total') projects.sort((a,b)=>b.total-a.total); else projects.sort((a,b)=>a.name.localeCompare(b.name,'zh'));
  const mm={}; cells.forEach(c=>mm[c.date+'|'+c.project]=c.pretax);
  const max=Math.max(...cells.map(c=>c.pretax),0.0001);
  const thead=`<tr><th class="first">项目 \\ 日期</th>${dates.map(d=>`<th class="num" style="min-width:64px">${d.slice(5)}</th>`).join('')}<th class="num">合计</th></tr>`;
  $('#matrixTable thead').innerHTML=thead;
  $('#matrixTable tbody').innerHTML=projects.map(p=>{
    const sum=dates.reduce((a,d)=>a+(mm[d+'|'+p.id]||0),0);
    const tds=dates.map(d=>{
      const v=mm[d+'|'+p.id]||0;
      const a=v>0? Math.min(.14+v/max*.86,1):0;
      return `<td class="num heat" style="background:rgba(47,107,255,${a.toFixed(3)});color:${a>.55?'#fff':'#101828'}">${v?fmtShort(v):'—'}</td>`;
    }).join('');
    return `<tr><td class="first">${p.name}</td>${tds}<td class="num" style="font-weight:700">${fmt(sum)}</td></tr>`;
  }).join('') || `<tr><td class="empty" colspan="3">暂无数据</td></tr>`;
}

function renderAll(){ renderChart(); renderProjects(); renderLedger(); renderMatrix(); }

/* CSV export */
$('#btnCsv').addEventListener('click',()=>{
  const notes=getNotes();
  const rows=[['日期','项目名称','项目标识','消费金额(元)','应付金额(元)','备注']];
  const m=state.month;
  DATA.cells.filter(c=>m==='all'||c.date.startsWith(m))
    .sort((a,b)=>a.date.localeCompare(b.date)||a.project.localeCompare(b.project))
    .forEach(c=>rows.push([c.date,c.projectName,c.project,c.pretax.toFixed(2),c.payable.toFixed(2),notes[c.date+'|'+c.project]||'']));
  const csv='\uFEFF'+rows.map(r=>r.map(x=>`"${String(x).replace(/"/g,'""')}"`).join(',')).join('\r\n');
  const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download=`火山方舟消费台账_${state.month==='all'?'全部':state.month}.csv`;
  a.click();
});
$('#btnPrint').addEventListener('click',()=>window.print());

renderAll();
</script>
</body>
</html>
"""


def main():
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(PUBLIC, exist_ok=True)
    html = HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    with open(os.path.join(PUBLIC, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"built {os.path.join(PUBLIC, 'index.html')} ({len(html)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
