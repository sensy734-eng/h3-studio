# 设置页 CDP 验证:SETTINGS 页签 + 预设库 + 模型状态
param(
  [int]$Port = 9444,
  [string]$Url = 'http://127.0.0.1:8188/h3-studio',
  [string]$EdgePath = ''
)
$ErrorActionPreference = 'Stop'
$script:eventQueue = New-Object System.Collections.ArrayList
$edge = $EdgePath
if (-not $edge) {
  foreach ($cand in @(
    'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
  )) { if (Test-Path $cand) { $edge = $cand; break } }
}
if (-not $edge) { throw '未找到浏览器' }
$userData = Join-Path $env:TEMP ("edge_set_" + [guid]::NewGuid().ToString('N'))

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
  if (-not $page) { throw '找不到页面' }
  $ws.ConnectAsync([uri]$page.webSocketDebuggerUrl, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
  $script:id = 0
  foreach ($m in @('Runtime.enable', 'Log.enable')) {
    $script:id++
    Send-Cdp $script:id $m
    Receive-Cdp $script:id | Out-Null
  }
  for ($i = 0; $i -lt 40; $i++) {
    $rs = Eval-Json 'document.readyState'
    if ($rs -eq 'complete') { break }
    Start-Sleep -Milliseconds 500
  }
  Start-Sleep -Seconds 2

  $probe = @'
(() => {
  const out = { lines: [], errors: [] };
  const g = id => { const e = document.getElementById(id); return e ? getComputedStyle(e).display : 'NO-EL'; };
  // 1. 切到 SETTINGS
  const st = document.querySelector('.tab[data-mode="SETTINGS"]');
  st.click();
  out.lines.push('SETTINGS tab: ' + (st ? st.classList.contains('active') : 'missing'));
  out.lines.push('settingsCard display: ' + g('settingsCard'));
  out.lines.push('promptCard display(设置页应隐藏): ' + g('promptCard'));
  // 2. 预设模式 chips
  out.lines.push('presetModeChips: ' + document.getElementById('presetModeChips').children.length + ' 个 chip');
  // 3. 新建版本
  document.getElementById('presetNewName').value = '测试版';
  document.getElementById('presetEditText').value = 'A test prompt for versioning.';
  document.getElementById('presetNewBtn').click();
  out.lines.push('新建版本后: ' + document.getElementById('presetVersions').textContent.replace(/\s+/g,' ').slice(0, 80));
  // 4. 保存修改
  document.getElementById('presetEditText').value = 'Updated test prompt v2.';
  document.getElementById('presetNewName').value = '测试版';
  document.getElementById('presetSave').click();
  out.lines.push('保存后 localStorage: ' + localStorage.getItem('h3studio_presets').slice(0, 120));
  // 5. 模型状态
  out.lines.push('modelStatus: ' + document.getElementById('modelStatus').textContent.replace(/\s+/g,' ').slice(0, 200));
  // 6. 生成页预设下拉(切回 T2VA)
  document.querySelector('.tab[data-mode="T2VA"]').click();
  const ps = document.getElementById('presetSelect');
  out.lines.push('presetSelect options: ' + ps.options.length + ' 个, 当前值: ' + ps.value);
  // 7. 清理测试数据
  localStorage.removeItem('h3studio_presets');
  localStorage.removeItem('h3studio_preset_default');
  return out.lines.join('\n');
})()
'@
  $result = Eval-Json $probe
  Write-Host '========== 设置页验证 =========='
  foreach ($line in ($result -split "`n")) { Write-Host "  $line" }
  Write-Host '========== 浏览器错误 =========='
  if ($script:eventQueue.Count -eq 0) { Write-Host '  (无)' }
  else { $script:eventQueue | ForEach-Object { Write-Host "  $_" } }
}
finally {
  if ($ws -and $ws.State -eq 'Open') { $ws.Dispose() }
  Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
  Remove-Item $userData -Recurse -Force -ErrorAction SilentlyContinue
}
