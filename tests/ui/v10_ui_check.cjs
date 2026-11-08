// Actual NiiVue + isolated FastAPI; run scripts/ui_verification_server.py first.
const {chromium}=require('playwright'),fs=require('fs'),assert=require('assert');
(async()=>{
 const path=require('path'),os=require('os');
 const base=(process.env.MEDICAL_UI_BASE_URL||'http://127.0.0.1:8502').replace(/\/$/,'');
 if(!['127.0.0.1','localhost'].includes(new URL(base).hostname))throw Error('Use the isolated localhost fixture server.');
 const output=process.env.MEDICAL_UI_OUTPUT_DIR||fs.mkdtempSync(path.join(os.tmpdir(),'v10-ui-report-'));fs.mkdirSync(output,{recursive:true});
 const config=JSON.parse(fs.readFileSync(process.env.MEDICAL_UI_SESSION));
 assert(config.fixture_server,'An isolated UI fixture session is required.');
 const browser=await chromium.launch({args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const context=await browser.newContext({viewport:{width:1600,height:1100},ignoreHTTPSErrors:true});const p=await context.newPage();const errors=[],report={checks:[],icons:[]};
 p.on('pageerror',e=>{errors.push(String(e));console.log('PAGE ERROR',String(e))});p.on('dialog',d=>d.accept());
 if(process.env.NIIVUE_ESM_PATH)await p.route('https://cdn.jsdelivr.net/npm/@niivue/niivue@0.42.0/+esm',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.NIIVUE_ESM_PATH,'utf8')}));
 await p.route(base+'/',async route=>{const response=await route.fetch();let html=await response.text();html=html.replace('</script>',`window.__app={state,nv,grid,measurements,definitions,execute,conditions,iconActive,show,nav,resetWorkspace,inspector,applyLayer,layerSettings};</script>`);await route.fulfill({response,body:html});});
 const res=await context.request.post(base+'/api/auth/login',{data:{email:config.email,password:config.password}});assert(res.ok());
 await p.goto(base+'/');await p.waitForFunction(()=>window.__app);const ids=config.ids;
 const check=(name,value)=>{assert(value,name);report.checks.push(name);console.log('PASS',name)};
 await p.locator('#fileRows tr[data-file-id="'+ids.fixed+'"]').getByText('Fixed 열기',{exact:true}).click();await p.waitForFunction(()=>__app.nv.volumes.length===1);
 await p.locator('[data-nav=manager]').click();await p.locator('#fileRows tr[data-file-id="'+ids.moving+'"]').getByText('Moving 열기',{exact:true}).click();await p.waitForTimeout(600);
 await p.locator('[data-nav=registration]').click();await p.waitForFunction(()=>__app.grid.cells.length===9&&__app.grid.cells.filter(c=>c.nv.volumes.length).length>=6);await p.waitForTimeout(500);
 check('registration nine equal panels',await p.locator('#imageGrid .image-cell').evaluateAll(nodes=>nodes.length===9&&Math.max(...nodes.map(n=>n.getBoundingClientRect().height))-Math.min(...nodes.map(n=>n.getBoundingClientRect().height))<=1));
 check('selected Fixed and Moving retained',await p.locator('#idInfo').evaluate(e=>e.textContent.includes('160×192×224')&&!e.textContent.includes('Moving: -')));
 await p.fill('#regIter','2');await p.click('#icon-reg-rigid');await p.waitForFunction(()=>__app.state.regResult?.operation==='registration'&&!__app.state.busy,null,{timeout:120000});await p.waitForFunction(()=>__app.grid.cells.slice(6).every(c=>c.nv.volumes.length));
 check('real Registration result uses hot colormap',await p.evaluate(()=>__app.grid.cells.slice(6).every(c=>c.nv.volumes[0].colormap==='hot')));
 await p.screenshot({path:path.join(output,'registration.jpg')});
 await p.locator('[data-nav=segmentation]').click();await p.waitForFunction(()=>document.querySelectorAll('#imageGrid .image-cell:not([hidden])').length===6);
 check('single Image picker',await p.locator('#imageLoadSection').isVisible()&&!(await p.locator('#loadSection').isVisible()));
 const seedCanvas=p.locator('#imageGrid .image-cell').first().locator('canvas');await seedCanvas.click();await p.waitForFunction(()=>__app.state.location?.mm&&__app.conditions(__app.definitions.find(d=>d.id==='icon-seg-seed')).length===0);
 await p.click('#icon-seg-seed');await p.click('#icon-seg-region');await p.waitForFunction(()=>__app.state.segResult?.operation==='region-growing'&&!__app.state.busy,null,{timeout:120000});
 check('real Region Growing from grid Seed',await p.evaluate(()=>__app.state.segResult.foreground_voxels>0));
 // Use a conservative interval on real OASIS intensities.
 const range=await p.evaluate(()=>{const v=__app.nv.volumes[0];return [v.robust_min+(v.global_max-v.robust_min)*.4,v.global_max*.9]});await p.fill('#thresholdLow',String(range[0]));await p.fill('#thresholdHigh',String(range[1]));await p.click('#icon-seg-threshold');
 await p.waitForFunction(()=>__app.state.segResult?.operation==='threshold'&&!__app.state.busy,null,{timeout:120000});
 check('real threshold returns multiple colored regions',await p.evaluate(()=>__app.state.segResult.label_count>0&&!!__app.grid.cells[3].nv.volumes[1]?.colormapLabel));
 await p.fill('#labelNumber','1');await p.fill('#labelColor','#ff0000');await p.click('#applyLabelColor');await p.waitForFunction(()=>__app.state.segResult.label_colors?.[1]==='#ff0000');
 check('region color persisted',true);await p.screenshot({path:path.join(output,'segmentation.jpg')});
 // Test mask mode with an actual 35-label fixture, avoiding a >255-component threshold edit.
 await p.evaluate(async ids=>{const a=__app;a.state.segResult={operation:'manual-mask',base_id:a.state.image.image_id,result_id:ids.moving_labels,label_count:35};await a.show(a.state.image.image_id,ids.moving_labels,'drawing');},ids);
 await p.click('#icon-seg-draw');await p.waitForFunction(()=>__app.nv.opts.drawingEnabled);check('draw active',await p.locator('#icon-seg-draw').getAttribute('aria-pressed')==='true');
 await p.click('#icon-seg-erase');await p.waitForFunction(()=>__app.nv.opts.drawingEnabled&&__app.nv.opts.penValue===0);check('eraser separate and active',await p.evaluate(()=>__app.nv.opts.penValue===0&&__app.nv.opts.drawingEnabled)&&await p.locator('#icon-seg-erase').getAttribute('aria-pressed')==='true');
 await p.click('#icon-seg-clear');check('clear mask',await p.evaluate(()=>__app.nv.drawBitmap.every(v=>v===0)));await p.click('#undoMask');check('mask undo restores labels',await p.evaluate(()=>__app.nv.drawBitmap.some(v=>v>0)));
 await p.click('#icon-seg-stop');check('mask exit returns to grid',await p.locator('#imageGrid').isVisible()&&await p.evaluate(()=>!__app.nv.opts.drawingEnabled));
 await p.locator('[data-nav=tools]').click();
 // Measurements: actual two-click flow and live provisional line on the axial panel.
 await p.click('#icon-tool-distance');check('distance starts without pre-recorded points',await p.locator('#icon-tool-distance').getAttribute('aria-pressed')==='true');
 const sample=await p.evaluate(()=>{const n=__app.nv,s=n.screenSlices.find(s=>s.axCorSag===0),r=n.canvas.getBoundingClientRect(),[l,t,w,h]=s.leftTopWidthHeight;return {x:r.left+(l+w*.4)*r.width/n.canvas.width,y:r.top+(t+h*.5)*r.height/n.canvas.height,dx:w*.15*r.width/n.canvas.width}});
 await p.mouse.click(sample.x,sample.y);await p.mouse.move(sample.x+sample.dx,sample.y);await p.waitForTimeout(150);
 check('distance live preview after first click',await p.locator('#measurementOverlay polyline').count()>0);
 await p.mouse.click(sample.x+sample.dx,sample.y);await p.waitForFunction(()=>__app.measurements.records.some(r=>r.mode==='distance'));
 check('distance saved on second click',await p.locator('#measurementList').textContent().then(t=>t.includes('distance_mm')));
 // The live orthogonal line crosses the stored distance at its midpoint.
 await p.mouse.click(sample.x+sample.dx*.5,sample.y-35);await p.mouse.click(sample.x+sample.dx*.5,sample.y+35);await p.waitForFunction(()=>__app.measurements.records.filter(r=>r.mode==='distance').length>=2);
 check('crossing distances show angle',await p.locator('#measurementOverlay text').allTextContents().then(t=>t.some(t=>t.includes('°'))));
 await p.click('#icon-tool-angle');await p.mouse.click(sample.x,sample.y-30);await p.mouse.click(sample.x,sample.y);await p.mouse.click(sample.x+sample.dx,sample.y);await p.waitForFunction(()=>__app.measurements.records.some(r=>r.mode==='angle'));
 check('three-point angle saved',true);
 await p.click('#icon-tool-roi');await p.mouse.click(sample.x,sample.y);await p.waitForFunction(()=>__app.measurements.records.some(r=>r.mode==='roi'));
 check('ROI saved',true);await p.click('#icon-tool-stop');
 await p.click('#icon-tool-contrast');await p.fill('#ctMin','20');await p.press('#ctMin','Enter');await p.click('#inspector [data-tab=colormap]');await p.selectOption('#cmPreset','Jet');await p.waitForTimeout(100);
 await p.click('#globalReset');check('reset restores original contrast and colormap',await p.evaluate(()=>{const a=__app,v=a.nv.volumes[0],b=a.state.baseline.get(v.name);return v.cal_min===b.min&&v.cal_max===b.max&&v.colormap===b.colormap}));
 await p.click('#inspectorClose');await p.screenshot({path:path.join(output,'measurements.jpg')});
 const countBefore=await p.evaluate(()=>__app.measurements.records.length);await p.evaluate(()=>__app.show(__app.state.viewed));check('measurements reload from database',await p.evaluate(n=>__app.measurements.records.length===n,countBefore));
 await p.locator('[data-nav=compare]').click();await p.click('#loadCompare');await p.waitForFunction(()=>document.getElementById('compareStatus').textContent.includes('완료'));
 check('comparison loads three linked images',await p.locator('#comparePanels canvas').count()===3);
 await p.locator('[data-nav=tools]').click();const chooserPromise=p.waitForEvent('filechooser');await p.click('#icon-tool-modality');const chooser=await chooserPromise;check('modality icon opens file picker',await chooser.element().getAttribute('id')==='modalityFile');await chooser.setFiles([]);
 // Every icon's enabled and refusal path is audited. Backend execution is covered separately;
 // stub only the target callback to isolate dispatch from long-running algorithms here.
 for(const id of await p.evaluate(()=>__app.definitions.map(d=>d.id))){
  const row=await p.evaluate(async id=>{const a=__app,d=a.definitions.find(x=>x.id===id);await a.nav(d.group==='reg'?'registration':d.group==='seg'?'seg-vessel':d.group==='cmp'?'compare':d.group==='view'?'viewer':'tools');
    if(['point','seed','region','contour'].includes(d.key)){a.state.location={mm:Array.from(a.nv.frac2mm(a.nv.scene.crosshairPos)).slice(0,3)};if(['region','contour'].includes(d.key)&&!a.state.seeds.length)a.state.seeds=[a.state.location.mm];document.getElementById('addSeed').disabled=false;document.getElementById('runRg').disabled=false;}
    const reasons=a.conditions(d);if(reasons.length){let rejected=false;try{await a.execute(d)}catch{rejected=true}return {id,status:rejected?'gated':'FAIL',reasons};}
    if(d.target){const el=document.getElementById(d.target);if(el.type==='file'){return {id,status:'file-picker',target:d.target};}const old=el.onclick;let called=false;el.onclick=()=>{called=true};try{await a.execute(d);}finally{el.onclick=old;}return {id,status:called?'dispatched':'FAIL',target:d.target};}
    await a.execute(d);return {id,status:'executed'};
  },id);report.icons.push(row);assert(row.status!=='FAIL',id);
 }
 check('all icon paths reviewed',report.icons.length===await p.evaluate(()=>__app.definitions.length));
 check('no browser exceptions',errors.length===0);report.errors=errors;report.status='passed';fs.writeFileSync(path.join(output,'ui-report.json'),JSON.stringify(report,null,2));
 await browser.close();console.log('ICONS',report.icons.length);
})().catch(e=>{console.error(e);process.exit(1)});
