# =========================================================
# web.py
# =========================================================

import socket
import ujson as json
import config

def _http_response(body, content_type="text/html"):
    return "HTTP/1.1 200 OK\r\nContent-Type: {}\r\nConnection: close\r\n\r\n{}".format(
        content_type, body
    ).encode('utf-8')

def _parse_query(path):
    params = {}
    if "?" in path:
        path, qs = path.split("?", 1)
        for pair in qs.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k] = v
    return path, params

GENERATOR_PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ESP32 Signal Generator</title>
<style>
:root{
  --bg1:#0f0c29; --bg2:#302b63; --bg3:#24243e;
  --accent:#6ee7ff; --accent2:#a78bfa;
  --card:rgba(255,255,255,0.06); --border:rgba(255,255,255,0.14);
  --text:#f1f5f9; --muted:#94a3b8; --ok:#34d399; --bad:#f87171;
}
[data-theme="light"]{
  --bg1:#e0e7ff; --bg2:#f5f3ff; --bg3:#ffffff;
  --card:rgba(255,255,255,0.65); --border:rgba(15,23,42,0.10);
  --text:#0f172a; --muted:#64748b;
}
*{box-sizing:border-box}
body{
  margin:0; min-height:100vh;
  font-family:'Segoe UI', system-ui, -apple-system, sans-serif;
  background:linear-gradient(135deg,var(--bg1),var(--bg2) 50%,var(--bg3));
  color:var(--text);
  display:flex; align-items:center; justify-content:center;
  padding:24px; transition:background .3s ease, color .3s ease;
}
.card{
  width:100%; max-width:440px;
  background:var(--card); border:1px solid var(--border);
  border-radius:22px; padding:26px 26px 30px;
  backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
  box-shadow:0 20px 60px rgba(0,0,0,0.35);
  position:relative;
}
.top{display:flex; justify-content:space-between; align-items:flex-start}
h2{
  margin:0 0 4px; font-size:22px; font-weight:700;
  background:linear-gradient(90deg,var(--accent),var(--accent2));
  -webkit-background-clip:text; background-clip:text; color:transparent;
}
.sub{color:var(--muted); font-size:12.5px; display:flex; align-items:center; gap:6px}
.conn{width:8px; height:8px; border-radius:50%; background:var(--bad); box-shadow:0 0 6px var(--bad); transition:.3s}
.conn.on{background:var(--ok); box-shadow:0 0 8px var(--ok)}
.themebtn{
  background:var(--card); border:1px solid var(--border); color:var(--text);
  width:34px; height:34px; border-radius:10px; cursor:pointer; font-size:16px;
  display:flex; align-items:center; justify-content:center;
}
.preview{
  margin-top:18px; height:70px; border-radius:12px;
  background:rgba(0,0,0,0.18); border:1px solid var(--border);
}
[data-theme="light"] .preview{background:rgba(15,23,42,0.05)}
label{
  display:flex; justify-content:space-between; align-items:baseline;
  font-size:11.5px; color:var(--muted); text-transform:uppercase; letter-spacing:.06em;
  margin:16px 0 6px;
}
label span.val{color:var(--accent); font-weight:700; font-size:12.5px; letter-spacing:0}
.row{display:flex; gap:10px; align-items:center}
select,input[type=number]{
  width:100%; font-size:15px; padding:11px 13px;
  border-radius:10px; border:1px solid var(--border);
  background:rgba(127,127,127,0.08); color:var(--text);
  outline:none; transition:border-color .2s, box-shadow .2s;
  appearance:none; -webkit-appearance:none;
}
select:focus,input:focus{border-color:var(--accent); box-shadow:0 0 0 3px rgba(110,231,255,0.18)}
input[type=range]{
  -webkit-appearance:none; width:100%; height:4px; border-radius:2px;
  background:linear-gradient(90deg,var(--accent),var(--accent2)); outline:none;
}
input[type=range]::-webkit-slider-thumb{
  -webkit-appearance:none; width:16px; height:16px; border-radius:50%;
  background:#fff; border:3px solid var(--accent2); cursor:pointer; margin-top:-6px;
}
option{background:#1e1b3a; color:#f1f5f9}
[data-theme="light"] option{background:#fff; color:#0f172a}
.presets{display:flex; gap:8px; margin-top:8px; flex-wrap:wrap}
.chip{
  padding:6px 12px; border-radius:999px; font-size:12px; cursor:pointer;
  background:rgba(127,127,127,0.10); border:1px solid var(--border); color:var(--muted);
  transition:.15s;
}
.chip:hover{color:var(--text); border-color:var(--accent)}
button.apply{
  width:100%; margin-top:22px; padding:14px; font-size:15px; font-weight:700;
  letter-spacing:.03em; border:none; border-radius:12px; cursor:pointer; color:#0b1220;
  background:linear-gradient(90deg,var(--accent),var(--accent2));
  box-shadow:0 8px 24px rgba(110,231,255,0.25);
  transition:transform .15s ease, box-shadow .15s ease;
}
button.apply:hover{transform:translateY(-2px); box-shadow:0 12px 30px rgba(167,139,250,0.35)}
.autoapply{display:flex; align-items:center; gap:8px; margin-top:14px; font-size:12.5px; color:var(--muted)}
.switch{position:relative; width:36px; height:20px}
.switch input{opacity:0; width:0; height:0}
.slider{
  position:absolute; inset:0; background:rgba(127,127,127,0.3); border-radius:999px; cursor:pointer; transition:.2s;
}
.slider:before{
  content:""; position:absolute; width:14px; height:14px; left:3px; top:3px;
  background:#fff; border-radius:50%; transition:.2s;
}
.switch input:checked + .slider{background:var(--accent)}
.switch input:checked + .slider:before{transform:translateX(16px)}
.history{margin-top:18px}
.history .label{font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; margin-bottom:6px}
.hchips{display:flex; gap:6px; flex-wrap:wrap}
.hchip{font-size:10.5px; padding:4px 9px; border-radius:999px; background:rgba(127,127,127,0.10); color:var(--muted); border:1px solid var(--border)}
#toast{
  position:fixed; left:50%; bottom:26px; transform:translate(-50%,20px);
  background:#0f172a; color:#f1f5f9; padding:11px 18px; border-radius:10px;
  font-size:13px; opacity:0; pointer-events:none; transition:.3s ease;
  border:1px solid rgba(255,255,255,0.1); box-shadow:0 10px 30px rgba(0,0,0,0.4);
}
#toast.show{opacity:1; transform:translate(-50%,0)}
#toast.err{border-color:rgba(248,113,113,0.5)}
</style>
</head>
<body data-theme="dark">
<div class="card">
  <div class="top">
    <div>
      <h2>Signal Generator</h2>
      <div class="sub"><span class="conn" id="conn"></span><span id="connText">Menghubungkan...</span></div>
    </div>
    <button class="themebtn" id="themeBtn" onclick="toggleTheme()">&#9788;</button>
  </div>

  <canvas class="preview" id="preview" width="380" height="70"></canvas>

  <label>Waveform</label>
  <select id="wf" onchange="updatePreview(); maybeAuto()">
    <option value="sine">Sine</option>
    <option value="square">Square</option>
    <option value="triangle">Triangle</option>
  </select>

  <label>Frekuensi <span class="val" id="freqVal">10 Hz</span></label>
  <div class="row">
    <input id="freqRange" type="range" min="1" max="2000" value="10" oninput="syncFreq('range')">
  </div>
  <input id="freq" type="number" value="10" style="margin-top:8px" oninput="syncFreq('num')">
  <div class="presets">
    <span class="chip" onclick="setFreq(1)">1 Hz</span>
    <span class="chip" onclick="setFreq(10)">10 Hz</span>
    <span class="chip" onclick="setFreq(100)">100 Hz</span>
    <span class="chip" onclick="setFreq(1000)">1 kHz</span>
  </div>

  <label>Amplitudo <span class="val" id="ampVal">150</span></label>
  <input id="ampRange" type="range" min="0" max="255" value="150" oninput="syncAmp('range')">
  <input id="amp" type="number" value="150" max="255" min="0" style="margin-top:8px" oninput="syncAmp('num')">

  <div class="autoapply">
    <label class="switch"><input type="checkbox" id="autoChk"><span class="slider"></span></label>
    Auto-apply saat parameter berubah
  </div>

  <button class="apply" onclick="apply()">Terapkan</button>

  <div class="history" id="historyBox" style="display:none">
    <div class="label">Riwayat</div>
    <div class="hchips" id="hchips"></div>
  </div>
</div>
<div id="toast"></div>

<script>
var hist = [];
var theme = 'dark';

function toggleTheme(){
  theme = theme === 'dark' ? 'light' : 'dark';
  document.body.setAttribute('data-theme', theme);
  document.getElementById('themeBtn').innerHTML = theme === 'dark' ? '&#9788;' : '&#9789;';
  try{ localStorage.setItem('sg_theme', theme); }catch(e){}
  updatePreview();
}
(function(){
  try{
    var saved = localStorage.getItem('sg_theme');
    if(saved === 'light'){ theme='light'; document.body.setAttribute('data-theme','light');
      document.getElementById('themeBtn').innerHTML = '&#9789;'; }
  }catch(e){}
})();

function syncFreq(src){
  var v = src === 'range' ? document.getElementById('freqRange').value : document.getElementById('freq').value;
  document.getElementById('freqRange').value = v;
  document.getElementById('freq').value = v;
  document.getElementById('freqVal').innerText = v + ' Hz';
  updatePreview(); maybeAuto();
}
function setFreq(v){
  document.getElementById('freqRange').value = v;
  document.getElementById('freq').value = v;
  document.getElementById('freqVal').innerText = v + ' Hz';
  updatePreview(); maybeAuto();
}
function syncAmp(src){
  var v = src === 'range' ? document.getElementById('ampRange').value : document.getElementById('amp').value;
  document.getElementById('ampRange').value = v;
  document.getElementById('amp').value = v;
  document.getElementById('ampVal').innerText = v;
  updatePreview(); maybeAuto();
}

var autoTimer = null;
function maybeAuto(){
  if(!document.getElementById('autoChk').checked) return;
  clearTimeout(autoTimer);
  autoTimer = setTimeout(apply, 400);
}

var pctx = document.getElementById('preview').getContext('2d');
function updatePreview(){
  var c = document.getElementById('preview');
  var w = c.width, h = c.height, mid = h/2;
  pctx.clearRect(0,0,w,h);
  var wf = document.getElementById('wf').value;
  var color = getComputedStyle(document.body).getPropertyValue('--accent').trim() || '#6ee7ff';
  pctx.strokeStyle = color; pctx.lineWidth = 2.5; pctx.beginPath();
  var cycles = 3;
  for(var x=0; x<=w; x++){
    var t = (x/w) * cycles * 2 * Math.PI;
    var y;
    if(wf === 'sine') y = Math.sin(t);
    else if(wf === 'square') y = Math.sin(t) >= 0 ? 1 : -1;
    else { var frac = ((t/(2*Math.PI)) % 1 + 1) % 1; y = frac < 0.5 ? (4*frac-1) : (3-4*frac); }
    var py = mid - y*(h*0.38);
    if(x===0) pctx.moveTo(x,py); else pctx.lineTo(x,py);
  }
  pctx.stroke();
}
updatePreview();

function apply(){
  var wf = document.getElementById('wf').value;
  var freq = document.getElementById('freq').value;
  var amp = document.getElementById('amp').value;
  fetch('/set?waveform=' + wf + '&frequency=' + freq + '&amplitude=' + amp)
    .then(r => r.json())
    .then(d => {
      showToast(d.waveform + ' \u2022 ' + d.frequency + ' Hz \u2022 amp ' + d.amplitude, false);
      pushHistory(d);
    })
    .catch(() => showToast('Gagal menghubungi perangkat', true));
}

function pushHistory(d){
  hist.unshift(d.waveform + ' ' + d.frequency + 'Hz/' + d.amplitude);
  hist = hist.slice(0,5);
  document.getElementById('historyBox').style.display = 'block';
  document.getElementById('hchips').innerHTML = hist.map(function(t){ return '<span class="hchip">'+t+'</span>'; }).join('');
}

var toastTimer;
function showToast(msg, isErr){
  var t = document.getElementById('toast');
  t.innerText = msg;
  t.className = isErr ? 'show err' : 'show';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function(){ t.className=''; }, 2600);
}

function checkConn(){
  fetch('/status').then(r => { if(!r.ok) throw 0; return r.json(); })
    .then(function(){ setConn(true); })
    .catch(function(){ setConn(false); });
}
function setConn(ok){
  document.getElementById('conn').className = 'conn' + (ok?' on':'');
  document.getElementById('connText').innerText = ok ? 'Terhubung' : 'Tidak terhubung';
}
checkConn();
setInterval(checkConn, 4000);

document.addEventListener('keydown', function(e){
  if(e.key === 'Enter') apply();
});
</script>
</body></html>
"""

SCOPE_PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ESP32 Oscilloscope</title>
<style>
:root{
  --bg1:#05070d; --bg2:#0a1420;
  --trace:#39ff88; --text:#e6f1ea; --muted:#5f7a6c;
  --panel:rgba(255,255,255,0.04); --border:rgba(57,255,136,0.15); --ok:#39ff88; --bad:#f87171;
}
*{box-sizing:border-box}
body{
  margin:0; min-height:100vh;
  font-family:'Segoe UI', system-ui, -apple-system, sans-serif;
  background:radial-gradient(circle at 50% -10%, var(--bg2), var(--bg1) 60%);
  color:var(--text); display:flex; flex-direction:column; align-items:center; padding:22px;
}
.header{display:flex; align-items:center; justify-content:space-between; width:100%; max-width:660px; margin-bottom:4px}
.htitle{display:flex; align-items:center; gap:10px}
.dot{width:9px; height:9px; border-radius:50%; background:var(--ok); box-shadow:0 0 10px var(--ok); animation:pulse 1.4s infinite ease-in-out}
.dot.paused{background:#fbbf24; box-shadow:0 0 10px #fbbf24; animation:none}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
h2{margin:0; font-size:20px; font-weight:700; letter-spacing:.02em}
.conn{display:flex; align-items:center; gap:6px; font-size:11.5px; color:var(--muted)}
.conndot{width:7px; height:7px; border-radius:50%; background:var(--bad)}
.conndot.on{background:var(--ok); box-shadow:0 0 6px var(--ok)}
.sub{color:var(--muted); font-size:12px; margin-bottom:14px; width:100%; max-width:660px}
.scope-wrap{
  position:relative; width:100%; max-width:660px;
  background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:14px;
  box-shadow:0 20px 60px rgba(0,0,0,0.5), inset 0 0 40px rgba(57,255,136,0.03);
  backdrop-filter:blur(10px);
}
canvas{width:100%; height:auto; display:block; background:#000; border-radius:10px; border:1px solid rgba(57,255,136,0.1); cursor:crosshair}
.legend{display:flex; justify-content:space-between; font-size:11px; color:var(--muted); margin-top:10px; letter-spacing:.04em}
.stats{display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-top:12px}
.stat{background:rgba(57,255,136,0.05); border:1px solid var(--border); border-radius:10px; padding:8px 10px; text-align:center}
.stat .k{font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.06em}
.stat .v{font-size:15px; font-weight:700; color:var(--trace); margin-top:2px}
.controls{display:flex; gap:8px; margin-top:14px; flex-wrap:wrap}
.btn{
  flex:1; min-width:100px; padding:10px 12px; border-radius:10px; border:1px solid var(--border);
  background:rgba(57,255,136,0.06); color:var(--text); font-size:12.5px; cursor:pointer; text-align:center;
  transition:.15s;
}
.btn:hover{background:rgba(57,255,136,0.14)}
.btn.active{background:var(--trace); color:#04120a; font-weight:700}
#tooltip{
  position:absolute; background:#0f172a; color:#e6f1ea; padding:5px 9px; border-radius:6px;
  font-size:11px; pointer-events:none; opacity:0; transition:opacity .1s; border:1px solid rgba(57,255,136,0.3);
  white-space:nowrap;
}
</style>
</head>
<body>
<div class="header">
  <div class="htitle"><span class="dot" id="pdot"></span><h2>Oscilloscope</h2></div>
  <div class="conn"><span class="conndot" id="conndot"></span><span id="conntext">menghubungkan</span></div>
</div>
<div class="sub">ESP32 &middot; Live signal monitor</div>

<div class="scope-wrap">
  <div style="position:relative">
    <canvas id="scope" width="600" height="300"></canvas>
    <div id="tooltip"></div>
  </div>
  <div class="legend">
    <span>CH1</span>
    <span id="fps">-- fps</span>
    <span id="rangeLabel">0 &ndash; 4095</span>
  </div>
  <div class="stats">
    <div class="stat"><div class="k">Min</div><div class="v" id="sMin">--</div></div>
    <div class="stat"><div class="k">Max</div><div class="v" id="sMax">--</div></div>
    <div class="stat"><div class="k">Avg</div><div class="v" id="sAvg">--</div></div>
    <div class="stat"><div class="k">Vpp</div><div class="v" id="sVpp">--</div></div>
  </div>
  <div class="controls">
    <div class="btn" id="pauseBtn" onclick="togglePause()">Pause</div>
    <div class="btn" id="autoscaleBtn" onclick="toggleAutoscale()">Autoscale</div>
    <div class="btn" id="persistBtn" onclick="togglePersist()">Persistence</div>
    <div class="btn" onclick="downloadCSV()">Download CSV</div>
    <div class="btn" onclick="toggleFullscreen()">Fullscreen</div>
  </div>
</div>

<script>
var canvas = document.getElementById('scope');
var ctx = canvas.getContext('2d');
var lastTime = performance.now();
var paused = false, autoscale = false, persist = false;
var lastData = [];
var fadeCanvas = document.createElement('canvas');
fadeCanvas.width = canvas.width; fadeCanvas.height = canvas.height;
var fctx = fadeCanvas.getContext('2d');

function drawGrid(){
  var w = canvas.width, h = canvas.height;
  ctx.strokeStyle = 'rgba(57,255,136,0.10)'; ctx.lineWidth = 1;
  var cols = 10, rows = 8;
  for(var i=0;i<=cols;i++){ var x=i*(w/cols); ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,h); ctx.stroke(); }
  for(var j=0;j<=rows;j++){ var y=j*(h/rows); ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(w,y); ctx.stroke(); }
  ctx.strokeStyle = 'rgba(57,255,136,0.22)';
  ctx.beginPath(); ctx.moveTo(0,h/2); ctx.lineTo(w,h/2); ctx.stroke();
}

function computeStats(data){
  if(!data.length) return {min:0,max:0,avg:0,vpp:0};
  var min=data[0], max=data[0], sum=0;
  for(var i=0;i<data.length;i++){ var v=data[i]; if(v<min)min=v; if(v>max)max=v; sum+=v; }
  return {min:min, max:max, avg:Math.round(sum/data.length), vpp:max-min};
}

function draw(data){
  var w = canvas.width, h = canvas.height;

  if(persist){
    fctx.fillStyle = 'rgba(0,0,0,0.18)';
    fctx.fillRect(0,0,w,h);
  } else {
    fctx.clearRect(0,0,w,h);
  }

  var lo = 0, hi = 4095;
  if(autoscale){
    var st = computeStats(data);
    var pad = Math.max(20, (st.max-st.min)*0.1);
    lo = Math.max(0, st.min - pad); hi = Math.min(4095, st.max + pad);
    if(hi<=lo) hi = lo+1;
  }
  document.getElementById('rangeLabel').innerText = lo + ' \u2013 ' + hi;

  fctx.lineWidth = 2.5; fctx.lineJoin = 'round';
  fctx.shadowColor = '#39ff88'; fctx.shadowBlur = 10; fctx.strokeStyle = '#39ff88';
  fctx.beginPath();
  for(var i=0;i<data.length;i++){
    var x = i * (w/data.length);
    var y = h - ((data[i]-lo)/(hi-lo))*h;
    if(i===0) fctx.moveTo(x,y); else fctx.lineTo(x,y);
  }
  fctx.stroke(); fctx.shadowBlur = 0;

  ctx.clearRect(0,0,w,h);
  drawGrid();
  ctx.drawImage(fadeCanvas,0,0);

  var st2 = computeStats(data);
  document.getElementById('sMin').innerText = st2.min;
  document.getElementById('sMax').innerText = st2.max;
  document.getElementById('sAvg').innerText = st2.avg;
  document.getElementById('sVpp').innerText = st2.vpp;

  var now = performance.now();
  document.getElementById('fps').innerText = (1000/(now-lastTime)).toFixed(1) + ' fps';
  lastTime = now;
}

function poll(){
  if(paused){ setTimeout(poll, 200); return; }
  fetch('/data').then(r => r.json()).then(d => {
    lastData = d; draw(d); setConn(true);
    setTimeout(poll, 150);
  }).catch(e => { setConn(false); setTimeout(poll, 1000); });
}
poll();

function setConn(ok){
  document.getElementById('conndot').className = 'conndot' + (ok?' on':'');
  document.getElementById('conntext').innerText = ok ? 'terhubung' : 'terputus';
}

function togglePause(){
  paused = !paused;
  document.getElementById('pauseBtn').innerText = paused ? 'Resume' : 'Pause';
  document.getElementById('pauseBtn').classList.toggle('active', paused);
  document.getElementById('pdot').classList.toggle('paused', paused);
}
function toggleAutoscale(){
  autoscale = !autoscale;
  document.getElementById('autoscaleBtn').classList.toggle('active', autoscale);
}
function togglePersist(){
  persist = !persist;
  document.getElementById('persistBtn').classList.toggle('active', persist);
  fctx.clearRect(0,0,fadeCanvas.width,fadeCanvas.height);
}
function toggleFullscreen(){
  if(!document.fullscreenElement){ canvas.requestFullscreen && canvas.requestFullscreen(); }
  else{ document.exitFullscreen && document.exitFullscreen(); }
}
function downloadCSV(){
  if(!lastData.length) return;
  var rows = ['index,value'];
  for(var i=0;i<lastData.length;i++) rows.push(i + ',' + lastData[i]);
  var blob = new Blob([rows.join('\\n')], {type:'text/csv'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'scope_buffer.csv';
  a.click();
}

var tooltip = document.getElementById('tooltip');
canvas.addEventListener('mousemove', function(e){
  if(!lastData.length) return;
  var rect = canvas.getBoundingClientRect();
  var scaleX = canvas.width / rect.width;
  var x = (e.clientX - rect.left) * scaleX;
  var idx = Math.max(0, Math.min(lastData.length-1, Math.round(x / (canvas.width/lastData.length))));
  tooltip.innerText = 'i=' + idx + '  v=' + lastData[idx];
  tooltip.style.left = (e.clientX - rect.left + 12) + 'px';
  tooltip.style.top = (e.clientY - rect.top - 24) + 'px';
  tooltip.style.opacity = 1;
});
canvas.addEventListener('mouseleave', function(){ tooltip.style.opacity = 0; });
</script>
</body></html>
"""

def run_server(mode, generator=None, scope=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", config.WEB_PORT))
    s.listen(2)
    print("Web server aktif di port", config.WEB_PORT)

    while True:
        conn = None
        try:
            conn, addr = s.accept()
            conn.settimeout(2.0) 
            request = conn.recv(1024).decode('utf-8')
            
            if not request:
                conn.close()
                continue
                
            first_line = request.split("\r\n")[0]
            parts = first_line.split(" ")
            if len(parts) < 3:
                conn.close()
                continue
                
            method, path, _ = parts
            path, params = _parse_query(path)

            if mode == "GENERATOR":
                if path == "/":
                    conn.sendall(_http_response(GENERATOR_PAGE))
                elif path == "/set":
                    generator.set_params(
                        waveform=params.get("waveform"),
                        frequency=int(params["frequency"]) if "frequency" in params else None,
                        amplitude=int(params["amplitude"]) if "amplitude" in params else None,
                    )
                    conn.sendall(_http_response(json.dumps(generator.get_status()), "application/json"))
                elif path == "/status":
                    conn.sendall(_http_response(json.dumps(generator.get_status()), "application/json"))
                else:
                    conn.sendall(_http_response("Not found"))

            elif mode == "SCOPE":
                if path == "/":
                    conn.sendall(_http_response(SCOPE_PAGE))
                elif path == "/data":
                    conn.sendall(_http_response(json.dumps(scope.get_buffer()), "application/json"))
                else:
                    conn.sendall(_http_response("Not found"))
                    
        except OSError:
            pass 
        except Exception as e:
            print("Error request:", e)
        finally:
            if conn:
                try: conn.close()
                except: pass