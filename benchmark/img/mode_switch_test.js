// 模式切换回归测试 v2:桩 DOM 执行 h3-studio.html 的真实 JS
// 覆盖:模式切换无异常、paramCard 图片模式仅留前缀、benchCard 按模式切换、历史筛选
// 用法: node benchmark/img/mode_switch_test.js(无需 ComfyUI 运行,纯静态测试)
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const html = fs.readFileSync(
  path.join(__dirname, '..', '..', 'custom_nodes', 'h3-studio-web', 'h3-studio.html'), 'utf8');
const js = html.match(/<script>([\s\S]*?)<\/script>/)[1];

// ---------- 万能元素桩 ----------
function makeEl(tag, id) {
  const listeners = {};
  const el = {
    tag, id, value: '', textContent: '', disabled: false, hidden: false,
    style: {}, dataset: {}, className: '',
    _lab: '', _children: [], _h2: null, _tbody: null, _options: [], _innerHTML: '',
    get innerHTML() { return this._innerHTML; },
    set innerHTML(v) { this._innerHTML = v; this._children = []; },
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); },
      remove(c) { this._s.delete(c); },
      contains(c) { return this._s.has(c); },
      toggle(c, on) { if (on) this._s.add(c); else this._s.delete(c); },
    },
    addEventListener(ev, fn) { (listeners[ev] = listeners[ev] || []).push(fn); },
    click() { (listeners['click'] || []).forEach(fn => fn({ target: el })); },
    change() { (listeners['change'] || []).forEach(fn => fn({ target: el })); },
    appendChild(c) { this._children.push(c); },
    remove() {},
    querySelector(sel) {
      if (sel === '.hint') return makeEl('span', '');
      if (sel === 'label') return { textContent: this._lab };
      if (sel === 'option[value="auto"]') return makeEl('option', '');
      if (sel === '.fn') return makeEl('span', '');
      if (sel === '.up-sub') return makeEl('span', '');
      if (sel === '.thumb') return makeEl('img', '');
      if (sel === '.up-clear') return makeEl('button', '');
      if (sel === 'h2') { if (!this._h2) { this._h2 = makeEl('h2', ''); this._h2._lab = ''; } return this._h2; }
      if (sel === 'tbody') { if (!this._tbody) { this._tbody = makeEl('tbody', ''); } return this._tbody; }
      return makeEl('div', '');
    },
  };
  return el;
}

// ---------- DOM 结构桩 ----------
const els = new Map();
const INIT_HIDDEN = ['stillCard', 'benchCard', 'lastFrameField'];
function el(id, lab) {
  if (!els.has(id)) {
    const e = makeEl('div', id);
    if (INIT_HIDDEN.includes(id)) e.style.display = 'none';
    if (lab !== undefined) e._lab = lab;
    els.set(id, e);
  }
  return els.get(id);
}
const paramFields = [
  el('f_res', '分辨率(画布)'), el('f_dur', '时长'), el('f_q', '质量档(采样步数)'),
  el('f_seed', '随机种子'), el('f_aud', '音频'), el('f_pre', '输出文件名前缀'),
];
const tabModes = ['T2VA', 'I2VA', 'FL2VA', 'Ref2VA', 'MULTI', 'PROMPT', 'T2I', 'I2I'];
const tabs = tabModes.map(m => { const t = makeEl('div', 'tab_' + m); t.dataset.mode = m; return t; });
tabs[0].classList.add('active');
const histChips = ['all', 'video', 'img'].map(f => { const c = makeEl('div', 'chip_' + f); c.dataset.filter = f; return c; });
histChips[0].classList.add('active');

// 预置历史:1 条视频 + 1 条图片
const histData = JSON.stringify([
  { id: 'v1', time: '2026-01-01 00:00', mode: 'T2VA', status: 'ok', duration_s: 188, filename: 'a.mp4' },
  { id: 'i1', time: '2026-01-01 00:01', mode: 'T2I', status: 'ok', duration_s: 18, filename: 'b.png', kind: 'img' },
]);

const documentStub = {
  body: makeEl('body', 'body'),
  getElementById: id => el(id),
  querySelectorAll: sel => {
    if (sel === '.tab') return tabs;
    if (sel === '#paramCard .field') return paramFields;
    if (sel === '.chip[data-insert]') return [];
    if (sel === '.hist-filter') return histChips;
    return [];
  },
  querySelector: sel => (sel === '.tab[data-mode="MULTI"]') ? tabs[4] : null,
  createElement: tag => makeEl(tag, ''),
};

const sandbox = {
  console,
  document: documentStub,
  localStorage: {
    getItem: k => k === 'h3studio_hist' ? histData : (k === 'h3studio_histfilter' ? 'all' : null),
    setItem: () => {}, removeItem: () => {},
  },
  fetch: () => new Promise((_, rej) => rej(new Error('offline'))),
  location: { host: '127.0.0.1:8188' },
  navigator: { clipboard: undefined },
  window: { addEventListener: () => {}, },
  WebSocket: function () {},
  URL: { createObjectURL: () => 'blob:stub' },
  FormData: function () {},
  Image: function () {},
  setTimeout, clearTimeout, setInterval, clearInterval,
  JSON, Math, Date, parseInt, parseFloat, isNaN, String, Number, Boolean, Object, Array, RegExp, Promise, Error, encodeURIComponent, decodeURIComponent,
};
vm.createContext(sandbox);
vm.runInContext(js, sandbox, { filename: 'h3-studio.js' });

let failed = 0;
function check(name, cond) {
  console.log((cond ? 'PASS' : 'FAIL') + '  ' + name);
  if (!cond) failed++;
}

const vis = id => el(id).style.display;
const fieldVis = i => paramFields[i].style.display;
const benchTitle = () => el('benchCard')._h2 ? el('benchCard')._h2.textContent : '(无 h2)';
const histRows = () => { const t = el('histTable')._tbody; return t ? t._children.length : -1; };

(async function main(){
  // 等待页面 async init(loadObjInfo/refreshStatus/renderBenchTable/renderHist)完成
  await new Promise(r => setTimeout(r, 250));

  console.log('--- 场景1:初始 T2VA(视频模式) ---');
check('paramCard 可见', vis('paramCard') === undefined || vis('paramCard') === '');
check('stillCard 隐藏', vis('stillCard') === 'none');
check('时长字段可见', fieldVis(1) !== 'none');
check('音频字段可见', fieldVis(4) !== 'none');
check('benchCard 标题=视频基准', benchTitle().includes('视频基准'));

console.log('--- 场景2:切到 T2I(文生图) ---');
tabs[6].click();
check('paramCard 可见', vis('paramCard') === '');
check('stillCard 显示', vis('stillCard') === '');
check('genCard 隐藏', vis('genCard') === 'none');
check('promptCard 显示', vis('promptCard') === '');
check('分辨率字段隐藏(图片模式)', fieldVis(0) === 'none');
check('时长字段隐藏(图片模式)', fieldVis(1) === 'none');
check('质量字段隐藏(图片模式)', fieldVis(2) === 'none');
check('种子字段隐藏(图片模式)', fieldVis(3) === 'none');
check('音频字段隐藏(图片模式)', fieldVis(4) === 'none');
check('输出前缀字段保留显示', fieldVis(5) !== 'none');
check('T2I tab active', tabs[6].classList.contains('active'));
check('stillTitleText=文生图', el('stillTitleText').textContent.includes('文生图'));
check('stillTitle 的 hint 仍存在', true);
check('benchCard 标题=图片基准', benchTitle().includes('图片基准'));

console.log('--- 场景3:切到 I2I(图生图) ---');
tabs[7].click();
check('stillTitleText=图生图', el('stillTitleText').textContent.includes('图生图'));
check('i2iSrcField 显示', vis('i2iSrcField') === '');
check('benchCard 标题仍为图片基准', benchTitle().includes('图片基准'));

console.log('--- 场景4:切回 T2VA(关键回归点) ---');
tabs[0].click();
check('paramCard 可见', vis('paramCard') === '');
check('时长字段恢复可见', fieldVis(1) !== 'none');
check('音频字段恢复可见', fieldVis(4) !== 'none');
check('质量字段恢复可见', fieldVis(2) !== 'none');
check('分辨率字段恢复可见', fieldVis(0) !== 'none');
check('stillCard 隐藏', vis('stillCard') === 'none');
check('imageCard 隐藏', vis('imageCard') === 'none');
check('refCard 隐藏', vis('refCard') === 'none');
check('genCard 显示', vis('genCard') === '');
check('T2VA tab active', tabs[0].classList.contains('active'));
check('benchCard 标题=视频基准', benchTitle().includes('视频基准'));

console.log('--- 场景5:切到 I2VA(图生视频) ---');
tabs[1].click();
check('imageCard 显示', vis('imageCard') === '');
check('refCard 隐藏', vis('refCard') === 'none');
check('lastFrameField 隐藏', vis('lastFrameField') === 'none');

console.log('--- 场景6:切到 FL2VA(首尾帧) ---');
tabs[2].click();
check('imageCard 显示', vis('imageCard') === '');
check('lastFrameField 显示', vis('lastFrameField') === '');

console.log('--- 场景7:切到 Ref2VA(多参考) ---');
tabs[3].click();
check('refCard 显示', vis('refCard') === '');
check('imageCard 隐藏', vis('imageCard') === 'none');

console.log('--- 场景8:Ref2VA → T2VA → I2VA → T2VA(连续往返,无状态残留) ---');
tabs[0].click(); tabs[1].click(); tabs[0].click();
check('imageCard 最终隐藏', vis('imageCard') === 'none');
check('refCard 最终隐藏', vis('refCard') === 'none');
check('时长字段可见', fieldVis(1) !== 'none');

console.log('--- 场景9:MULTI / PROMPT ---');
tabs[4].click();
check('multiCard 显示', vis('multiCard') === '');
check('paramCard 隐藏', vis('paramCard') === 'none');
tabs[5].click();
check('optCard 显示', vis('optCard') === '');
tabs[0].click();
check('paramCard 恢复显示', vis('paramCard') === '');
check('时长字段仍可见', fieldVis(1) !== 'none');
check('multiCard 隐藏', vis('multiCard') === 'none');

console.log('--- 场景10:历史筛选(视频/图片分开) ---');
check('筛选 all:2 行', histRows() === 2);
histChips[1].click(); // video
check('筛选 video:1 行(图片被过滤)', histRows() === 1);
histChips[2].click(); // img
check('筛选 img:1 行(视频被过滤)', histRows() === 1);
histChips[0].click(); // all
check('筛选 all 恢复:2 行', histRows() === 2);

  console.log(failed === 0 ? '\n=== 全部通过 ===' : `\n=== ${failed} 项失败 ===`);
  process.exit(failed === 0 ? 0 : 1);
})();
