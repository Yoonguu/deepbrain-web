// 실행: node tests/ui/v8_ui_check.js frontend/index.html out.png  (Playwright 필요, 실제 서버·NiiVue 없이 가짜 모듈로 점검)
// v8 UI 점검: 가짜 NiiVue와 가짜 API로 index.html을 띄워 메뉴별 섹션, Deep Learning, 평가, Layer Inspector를 확인한다.
const { chromium } = require('playwright');
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8');
const fakeNiivue = `
class FakeVol{constructor(x){Object.assign(this,x);this.id=x.url;const n=4096;this.img=new Float32Array(n);for(let i=0;i<n;i++)this.img[i]=i%100;this.img[5]=NaN;
 this.hdr={scl_slope:1,scl_inter:0,dims:[3,16,16,16],pixDims:[1,1.2,1.2,2],datatypeCode:16,affine:[[-1.2,0,0,10],[0,1.2,0,-20],[0,0,2,30],[0,0,0,1]]};
 this.global_min=0;this.global_max=99;this.robust_min=2;this.robust_max=97;this.cal_min=2;this.cal_max=97;this._colormap=x.colormap||'gray';}
 get colormap(){return this._colormap} set colormap(c){this._colormap=c;this.cal_min=this.robust_min;this.cal_max=this.robust_max;}}
export class Niivue{constructor(){this.opts={sliceType:3,dragMode:1,multiplanarLayout:0,drawingEnabled:false};this.volumes=[];this.scene={pan2Dxyzmm:[0,0,0,1]};this.dragModes={contrast:1,pan:2,measurement:3,none:0};this.sliceTypeMultiplanar=3;this.sliceTypeRender=4;this.sliceTypeAxial=0;this.screenSlices=[];this.maps={};window.__nv=window.__nv||this;}
async attachToCanvas(c){this.canvas=c;} setSliceType(t){this.opts.sliceType=t} drawScene(){} updateGLVolume(){this.updated=(this.updated||0)+1}
async loadVolumes(v){this.volumes=v.map(x=>new FakeVol(x))} setOpacity(){} setMultiplanarLayout(){} setSliceMosaicString(){} setDrawingEnabled(b){this.opts.drawingEnabled=b} drawUndo(){} saveImage(){return null} broadcastTo(){} async addVolumeFromUrl(x){this.volumes.push(new FakeVol(x))} removeVolume(){}
addColormap(k,c){this.maps[k]=c} colormap(name){const l=new Uint8ClampedArray(1024);for(let k=0;k<256;k++){l[k*4]=l[k*4+1]=l[k*4+2]=k;l[k*4+3]=name==='red'?k:255;}return l;}}`;
const models = [
  { model_id: 'lfcamorph-oasis', name: 'LFCAMorph', dataset: 'OASIS', description: 'LapIRN 계열', available: false, reason: 'PyTorch가 설치되지 않았습니다. 서버 venv에 torch를 설치하세요.' },
  { model_id: 'lfcamorph-lpba40', name: 'LFCAMorph', dataset: 'LPBA40', available: false, reason: '준비 중: LPBA40 학습 가중치 미수신.' },
  { model_id: 'voxelmorph-oasis', name: 'VoxelMorph', dataset: 'OASIS', available: false, reason: '준비 중: 가중치와 추론 코드 미수신.' },
  { model_id: 'voxelmorph-lpba40', name: 'VoxelMorph', dataset: 'LPBA40', available: false, reason: '준비 중: 가중치와 추론 코드 미수신.' },
  { model_id: 'hypermorph-oasis', name: 'HyperMorph', dataset: 'OASIS', available: false, reason: '준비 중: 가중치와 추론 코드 미수신.' }];
const evalResult = { mode: 'label', metrics: ['dice', 'hd95', 'assd'], labels: 2, per_label: { '1': { dice: 0.9, hd95: 1.5, assd: 0.4 }, '2': { dice: 0, hd95: null, assd: null, undefined_reason: '예측 mask가 비어 있습니다.' } }, foreground: { dice: 0.95, hd95: 1.2, assd: 0.3 }, summary: { dice: { mean: 0.45 }, hd95: { mean: 1.5 }, assd: { mean: 0.4 } } };
let presets = {}; const calls = [];
const api = { '/api/auth/me': { id: 'u1', name: '테스트', department: 'A', role: 'head', approved: 1, csrf: 't' },
  '/api/files': [{ id: 'f1', name: 'brain.nii.gz', kind: 'original', created: 1, metadata: '{"size":[16,16,16],"spacing":[1,1,1]}' }],
  '/api/preferences': { pinned: [], usage: {} }, '/api/previews': [], '/api/dl/models': models, '/api/jobs': [],
  '/api/images/f1/axial': { axial_index_axis: 'k', axial_slices: 16 } };
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = []; p.on('pageerror', e => errors.push(String(e))); p.on('console', m => { if (m.type() === 'error' && !m.text().includes('404')) errors.push(m.text()); });
  await p.route('**/*', async r => {
    const u = new URL(r.request().url()); const method = r.request().method();
    if (u.hostname === 'cdn.jsdelivr.net') return r.fulfill({ contentType: 'text/javascript', body: fakeNiivue });
    if (u.hostname !== 'app.test') return r.abort();
    if (u.pathname === '/') return r.fulfill({ contentType: 'text/html', body: html });
    calls.push(method + ' ' + decodeURIComponent(u.pathname));
    if (u.pathname === '/api/tools/evaluate') return r.fulfill({ contentType: 'application/json', body: JSON.stringify(evalResult) });
    if (u.pathname.startsWith('/api/preferences/colormaps')) {
      const name = decodeURIComponent(u.pathname.split('/').pop());
      if (method === 'PUT') presets[name] = JSON.parse(r.request().postData()); if (method === 'DELETE') delete presets[name];
      return r.fulfill({ contentType: 'application/json', body: JSON.stringify(presets) });
    }
    if (u.pathname === '/api/preferences/usage') return r.fulfill({ contentType: 'application/json', body: '{"count":1}' });
    const key = u.pathname; if (key in api) return r.fulfill({ contentType: 'application/json', body: JSON.stringify(api[key]) });
    return r.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"x"}' });
  });
  await p.goto('http://app.test/'); await p.waitForTimeout(500);
  const out = {}; const check = (k, v) => { out[k] = v; };
  const visibleSections = () => p.$$eval('#workspaceAside section', els => els.filter(e => !e.hidden).map(e => e.id));
  const icons = () => p.$$eval('#iconBar .iconButton', els => els.map(e => e.dataset.icon.replace('icon-', '')));
  check('docH', await p.evaluate(() => document.documentElement.scrollHeight));
  check('headerSpan', await p.$$eval('header span', e => e.length));
  await p.click('[data-nav=registration]'); await p.waitForTimeout(80);
  check('regSections', await visibleSections()); check('regIcons', await icons());
  check('dlOptions', await p.$$eval('#dlModel option', o => o.map(x => x.textContent + (x.disabled ? ' [disabled]' : ''))));
  check('dlStatus', await p.textContent('#dlStatus')); check('runDlDisabled', await p.$eval('#runDl', e => e.disabled));
  await p.click('[data-nav=segmentation]'); await p.waitForTimeout(80);
  check('segBrainSections', await visibleSections()); check('segBrainIcons', await icons());
  check('subnavVisible', await p.$eval('#segSubnav', e => !e.hidden));
  check('segCurrent', await p.$$eval('[aria-current=page]', e => e.map(x => x.dataset.nav)));
  await p.click('[data-nav=seg-vessel]'); await p.waitForTimeout(80);
  check('segVesselSections', await visibleSections()); check('segVesselHasVesselIcon', (await icons()).includes('seg-vessel'));
  await p.click('[data-nav=tools]'); await p.waitForTimeout(80);
  check('toolSections', await visibleSections()); check('toolIcons', await icons());
  check('subnavHiddenInTools', await p.$eval('#segSubnav', e => e.hidden));
  // 영상 열기: Fixed, Moving 모두 같은 자료
  await p.click('[data-nav=manager]'); await p.waitForTimeout(50);
  await p.click('text=Moving 열기'); await p.waitForTimeout(80);
  await p.click('[data-nav=manager]'); await p.click('text=Fixed 열기'); await p.waitForTimeout(150);
  // 평가
  await p.click('[data-nav=segmentation]'); await p.click('[data-nav=seg-brain]'); await p.waitForTimeout(50);
  check('runEvalEnabled', await p.$eval('#runEval', e => !e.disabled));
  await p.click('#runEval'); await p.waitForTimeout(150);
  check('evalRequest', calls.filter(c => c.includes('evaluate')).length);
  check('evalRows', await p.$$eval('#evalTable tr', rows => rows.map(r => [...r.cells].map(c => c.textContent).join(' | '))));
  // 방사형 메뉴에 vessel 없음(seg-brain)
  const gl = await (await p.$('#gl')).boundingBox(); const cx = gl.x + gl.width / 2, cy = gl.y + gl.height / 2;
  await p.mouse.move(cx, cy); await p.mouse.down({ button: 'right' }); await p.waitForTimeout(320);
  check('radialHasVesselInBrain', await p.$$eval('#radialMenu .iconButton', e => e.some(x => x.dataset.icon === 'icon-seg-vessel')));
  await p.keyboard.press('Escape'); await p.mouse.up({ button: 'right' }); await p.waitForTimeout(50);
  // Layer Inspector
  await p.click('[data-nav=tools]'); await p.waitForTimeout(50);
  check('toolTarget', await p.textContent('#toolTarget'));
  await p.click('#openContrast'); await p.waitForTimeout(100);
  check('inspectorOpen', await p.$eval('#inspector', e => !e.hidden && getComputedStyle(e).zIndex));
  check('inspectorInsideViewport', await p.$eval('#inspector', e => { const r = e.getBoundingClientRect(); return r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight; }));
  check('layers', await p.$$eval('#layerList button', e => e.map(x => x.textContent)));
  check('histBars', await p.$$eval('#ctPlot rect.hist', e => e.length));
  check('ctFields', await p.evaluate(() => ['ctMin', 'ctMax', 'ctLevel', 'ctWindow'].map(id => document.getElementById(id).value)));
  await p.fill('#ctMin', '10'); await p.press('#ctMin', 'Enter'); await p.waitForTimeout(80);
  check('afterMin', await p.evaluate(() => { const v = __nv.volumes[0], l = __nv.maps['inspector-layer-0']; return { cal: [v.cal_min, v.cal_max], colormap: v.colormap, lut0: l.R[0], lut128: l.R[128], lut255: l.R[255], len: l.R.length }; }));
  await p.click('#ctAdd'); await p.waitForTimeout(50);
  await p.fill('#ctY', '0.8'); await p.press('#ctY', 'Enter'); await p.waitForTimeout(80);
  check('curvePoints', await p.$$eval('#ctPlot circle', e => e.length));
  check('lutAfterCurve', await p.evaluate(() => { const l = __nv.maps['inspector-layer-0']; return [l.R[64], l.R[128], l.R[192]]; }));
  // 잘못된 Max
  await p.fill('#ctMax', '5'); await p.press('#ctMax', 'Enter'); await p.waitForTimeout(80);
  check('badMaxRejected', await p.evaluate(() => [__nv.volumes[0].cal_max, document.getElementById('inspectorStatus').textContent]));
  // 우클릭 W/L 동기화 흉내
  await p.evaluate(() => { const v = __nv.volumes[0]; v.cal_min = 20; v.cal_max = 60; __nv.onIntensityChange(v); });
  await p.waitForTimeout(50);
  check('syncFromDrag', await p.evaluate(() => ['ctMin', 'ctMax', 'ctWindow'].map(id => document.getElementById(id).value)));
  // 곡선 점 끌기
  const handle = await p.$('#ctPlot circle:nth-of-type(2)'); const hb = await handle.boundingBox();
  await p.mouse.move(hb.x + hb.width / 2, hb.y + hb.height / 2); await p.mouse.down(); await p.mouse.move(hb.x + hb.width / 2, hb.y + 20, { steps: 4 }); await p.mouse.up(); await p.waitForTimeout(80);
  check('dragY', await p.$eval('#ctY', e => e.value));
  // Color Map
  await p.click('#inspector [data-tab=colormap]'); await p.waitForTimeout(60);
  check('presetOptions', await p.$$eval('#cmPreset option', o => o.map(x => x.textContent)));
  await p.selectOption('#cmPreset', 'Jet'); await p.waitForTimeout(80);
  check('jetLut', await p.evaluate(() => { const l = __nv.maps['inspector-layer-0']; return { k0: [l.R[0], l.G[0], l.B[0], l.A[0]], k1: [l.R[1], l.G[1], l.B[1], l.A[1]], k255: [l.R[255], l.G[255], l.B[255], l.A[255]] }; }));
  check('jetPoint0', await p.evaluate(() => [document.getElementById('cmStyle').value, document.getElementById('cmSide').value, document.getElementById('cmOpacity').value]));
  await p.selectOption('#cmSide', 'left'); await p.waitForTimeout(40);
  check('jetLeftOpacity', await p.$eval('#cmOpacity', e => e.value));
  await p.selectOption('#cmPoint', '2'); await p.waitForTimeout(40);
  await p.fill('#cmOpacity', '0.5'); await p.press('#cmOpacity', 'Enter'); await p.waitForTimeout(60);
  check('presetAfterEdit', await p.$eval('#cmPreset', e => e.value));
  check('nanInfo', await p.textContent('#cmNanInfo'));
  await p.fill('#cmName', '내 Jet'); await p.click('#cmSave'); await p.waitForTimeout(100);
  check('savedPreset', [Object.keys(presets), await p.$eval('#cmPreset', e => e.value)]);
  await p.click('#cmRemove'); await p.waitForTimeout(100);
  check('removedPreset', Object.keys(presets));
  // Info
  await p.click('#inspector [data-tab=info]'); await p.waitForTimeout(40);
  check('info', await p.$$eval('#infoTable tr', rows => rows.map(r => r.textContent)));
  // 창 끌기
  const head = await (await p.$('#inspectorHead')).boundingBox(); const before = await (await p.$('#inspector')).boundingBox();
  await p.mouse.move(head.x + 40, head.y + 10); await p.mouse.down(); await p.mouse.move(head.x - 160, head.y + 90, { steps: 5 }); await p.mouse.up();
  const after = await (await p.$('#inspector')).boundingBox();
  check('dragMoved', [Math.round(after.x - before.x), Math.round(after.y - before.y)]);
  // 보기 초기화가 cal과 inspector를 되돌림
  await p.click('#resetView'); await p.waitForTimeout(40);
  await p.click('#inspector [data-tab=contrast]'); await p.waitForTimeout(40);
  check('afterReset', await p.evaluate(() => [__nv.volumes[0].cal_min, document.getElementById('ctMin').value]));
  // 재로드 시 설정 유지
  await p.click('[data-nav=registration]'); await p.click('#showFixed'); await p.waitForTimeout(120);
  check('reapplyOnReload', await p.evaluate(() => __nv.volumes[0].colormap));
  // 아이콘으로 Contrast 열기
  await p.click('#inspectorClose'); await p.click('[data-nav=tools]'); await p.click('#icon-tool-colormap'); await p.waitForTimeout(80);
  check('iconOpensColormap', await p.evaluate(() => !document.getElementById('inspector').hidden && document.querySelector('#inspector [aria-selected=true][role=tab]').dataset.tab));
  check('docHEnd', await p.evaluate(() => document.documentElement.scrollHeight));
  await p.screenshot({ path: process.argv[3] || 'v8.png' });
  out.errors = errors;
  console.log(JSON.stringify(out, null, 1));
  await b.close();
})();
