# CDP 驱动 headless Edge 真实加载 H3 Studio 页面,模拟模式切换并收集 console 错误/状态
# 用法: powershell -File cdp_ui_test.ps1 [-Url http://127.0.0.1:8188/h3-studio](需 ComfyUI 运行中)
param(
  [int]$Port = 9333,
  [string]$Url = 'http://127.0.0.1:8188/h3-studio',
  [string]$EdgePath = ''
)
$ErrorActionPreference = 'Stop'
$script:eventQueue = New-Object System.Collections.ArrayList
# 自动探测 Edge / Chrome(也可用 -EdgePath 显式指定)
$edge = $EdgePath
if (-not $edge) {
  foreach ($cand in @(
    'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
  )) { if (Test-Path $cand) { $edge = $cand; break } }
}
if (-not $edge) { throw '未找到 Edge/Chrome,请用 -EdgePath 指定浏览器路径' }
$userData = Join-Path $env:TEMP ("edge_cdp_" + [guid]::NewGuid().ToString('N'))

$p = Start-Process -FilePath $edge -ArgumentList @(
  '--headless=new', "--remote-debugging-port=$Port",
  "--user-data-dir=$userData", '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  'about:blank'
) -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3

$ws = [System.Net.WebSockets.ClientWebSocket]::new()

function Send-Cdp([int]$id, [string]$method, $params = $null) {
  $msg = @{ id = $id; method = $method }
  if ($null -ne $params) { $msg.params = $params }
  $json = $msg | ConvertTo-Json -Depth 20 -Compress
  $bytes = [Text.Encoding]::UTF8.GetBytes($json)
  $seg = [ArraySegment[byte]]::new($bytes)
  $ws.SendAsync($seg, [Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
}

function Receive-One {
  $buf = New-Object byte[] 4194304
  $sb = New-Object Text.StringBuilder
  while ($true) {
    $res = $ws.ReceiveAsync([ArraySegment[byte]]::new($buf), [Threading.CancellationToken]::None).GetAwaiter().GetResult()
    [void]$sb.Append([Text.Encoding]::UTF8.GetString($buf, 0, $res.Count))
    if ($res.EndOfMessage) { break }
  }
  return ($sb.ToString() | ConvertFrom-Json)
}

function Receive-Cdp([int]$wantId) {
  while ($true) {
    $obj = Receive-One
    if ($obj.method) {
      if ($obj.method -in @('Runtime.exceptionThrown', 'Log.entryAdded', 'Runtime.consoleAPICalled')) {
        [void]$script:eventQueue.Add(($obj | ConvertTo-Json -Depth 8 -Compress))
      }
      continue
    }
    if ($obj.id -eq $wantId) { return $obj }
  }
}

function Eval-Json([string]$expr) {
  $script:id++
  Send-Cdp $script:id 'Runtime.evaluate' @{ expression = $expr; returnByValue = $true }
  $r = Receive-Cdp $script:id
  return $r.result.result.value
}

try {
  $null = Invoke-RestMethod -Method Put "http://127.0.0.1:$Port/json/new?$([uri]::EscapeDataString($Url))" -TimeoutSec 10
  Start-Sleep -Milliseconds 800
  $list = Invoke-RestMethod "http://127.0.0.1:$Port/json/list" -TimeoutSec 10
  $page = $list | Where-Object { $_.type -eq 'page' -and $_.url -like '*h3-studio*' } | Select-Object -First 1
  if (-not $page) { throw '找不到 h3-studio 页面' }
  $ws.ConnectAsync([uri]$page.webSocketDebuggerUrl, [Threading.CancellationToken]::None).GetAwaiter().GetResult()

  $script:id = 0
  foreach ($m in @('Runtime.enable', 'Log.enable', 'Page.enable')) {
    $script:id++
    Send-Cdp $script:id $m
    Receive-Cdp $script:id | Out-Null
  }

  $ready = $false
  for ($i = 0; $i -lt 40; $i++) {
    $rs = Eval-Json 'document.readyState'
    if ($rs -eq 'complete') { $ready = $true; break }
    Start-Sleep -Milliseconds 500
  }
  Write-Host "页面加载: $ready"
  Start-Sleep -Seconds 2

  $probeScript = @'
(() => {
  const out = { errors: [], states: {}, fields: {} };
  const snap = (tag) => {
    const g = id => { const e = document.getElementById(id); return e ? getComputedStyle(e).display : 'NO-EL'; };
    out.states[tag] = {
      paramCard: g('paramCard'), stillCard: g('stillCard'), imageCard: g('imageCard'),
      refCard: g('refCard'), optCard: g('optCard'), multiCard: g('multiCard'), genCard: g('genCard'),
      lastFrameField: g('lastFrameField'), promptCard: g('promptCard'), benchCard: g('benchCard'),
    };
  };
  const click = (mode) => { const t = document.querySelector('.tab[data-mode="' + mode + '"]'); if (t) t.click(); return !!t; };
  snap('init_T2VA');
  click('I2VA'); snap('I2VA');
  click('FL2VA'); snap('FL2VA');
  click('Ref2VA'); snap('Ref2VA');
  click('T2VA'); snap('back_T2VA');
  click('T2I'); snap('T2I');
  click('I2I'); snap('I2I');
  click('MULTI'); snap('MULTI');
  click('PROMPT'); snap('PROMPT');
  click('T2VA'); snap('final_T2VA');
  const lines = [];
  const keys = ['paramCard','stillCard','imageCard','refCard','optCard','multiCard','genCard','lastFrameField','promptCard','benchCard'];
  Object.entries(out.states).forEach(([tag, s]) => {
    lines.push('ST|' + tag + '|' + keys.map(k => k + '=' + s[k]).join(','));
  });
  document.querySelectorAll('#paramCard .field').forEach(f => {
    const lab = (f.querySelector('label')||{}).textContent || '';
    out.fields[lab] = getComputedStyle(f).display;
  });
  Object.entries(out.fields).forEach(([k, v]) => lines.push('FL|' + k + '=' + v));
  return lines.join('\n');
})()
'@
  $result = Eval-Json $probeScript
  Write-Host '========== 模式切换 DOM 状态 =========='
  foreach ($line in ($result -split "`n")) {
    if ($line -like 'ST|*') {
      $parts = $line -split '\|'
      Write-Host ("[{0}] {1}" -f $parts[1], $parts[2])
    } elseif ($line -like 'FL|*') {
      $parts = $line -split '\|'
      Write-Host ("  {0} -> {1}" -f $parts[1], $parts[2])
    }
  }
  Write-Host '========== 浏览器 console 错误/异常 =========='
  if ($script:eventQueue.Count -eq 0) { Write-Host '  (无)' }
  else { $script:eventQueue | ForEach-Object { Write-Host "  $_" } }
}
finally {
  if ($ws -and $ws.State -eq 'Open') { $ws.Dispose() }
  Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
  Remove-Item $userData -Recurse -Force -ErrorAction SilentlyContinue
}
