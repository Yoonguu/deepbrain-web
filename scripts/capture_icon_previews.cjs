// Capture actual isolated application operations as screen frames.
const {chromium}=require('playwright');const fs=require('fs'),path=require('path');
const work=path.resolve(process.env.ICON_CAPTURE_DIR||require('os').tmpdir()+'/medical-icon-previews'),config=JSON.parse(fs.readFileSync(process.env.MEDICAL_UI_SESSION)),base=process.env.MEDICAL_UI_BASE_URL||'http://127.0.0.1:8502';if(!config.fixture_server||!['localhost','127.0.0.1'].includes(new URL(base).hostname))throw Error('Use an isolated local fixture server.');fs.mkdirSync(work,{recursive:true});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const browser=await chromium.launch({args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const context=await browser.newContext({viewport:{width:1440,height:900},ignoreHTTPSErrors:true});const p=await context.newPage();p.setDefaultTimeout(45000);const errors=[];p.on('pageerror',e=>errors.push(String(e)));p.on('dialog',d=>d.accept());
 if(process.env.NIIVUE_ESM_PATH)await p.route('https://cdn.jsdelivr.net/npm/@niivue/niivue@0.42.0/+esm',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.NIIVUE_ESM_PATH,'utf8')}));
 await p.route(base+'/',async route=>{const response=await route.fetch();let html=await response.text();html=html.replace('</script>','window.__app={state,nv,grid,measurements,definitions,execute,conditions,iconActive,show,nav,resetWorkspace,inspector,applyLayer,layerSettings};</script>');await route.fulfill({response,body:html});});
 let response=await context.request.post(base+'/api/auth/login',{data:{email:config.email,password:config.password}});if(!response.ok())throw Error(await response.text());const me=await(await context.request.get(base+'/api/auth/me')).json();await context.request.post(base+'/api/auth/mode',{headers:{'X-CSRF-Token':me.csrf},data:{clinical:true}});
 await p.goto(base+'/');await p.waitForFunction(()=>window.__app);
 await p.addStyleTag({content:'#tooltip,#tooltipNested,#radialMenu{visibility:hidden!important}'});
 await p.evaluate(async ids=>{const a=__app;a.state.fixed={image_id:ids.fixed,name:'Fixed',size:[160,192,224]};a.state.moving={image_id:ids.moving,name:'Moving',size:[160,192,224]};await a.nav('viewer');await a.show(ids.fixed);},config.ids);
 await p.evaluate(async()=>{const jobs=await(await fetch('/api/jobs')).json();const job=jobs.find(j=>j.status==='done'&&j.kind==='deep-learning');if(job){__app.state.regResult=job.result;__app.state.lastResult=job.result.result_id;}});
 const definitions=await p.evaluate(()=>__app.definitions.map(d=>({id:d.id,key:d.key,name:d.name,group:d.group})));const manifest=fs.existsSync(path.join(work,'capture-manifest.json'))?JSON.parse(fs.readFileSync(path.join(work,'capture-manifest.json'))):[];const forced=(process.env.CAPTURE_FORCE||'').split(',').filter(Boolean);
 async function clipFor(d){
  if(d.group==='tool'&&['distance','angle','roi','stop'].includes(d.key)){
   const tile=await p.evaluate(()=>{const n=__app.nv,s=n.screenSlices.find(s=>s.axCorSag===0);if(!s)return null;const r=n.canvas.getBoundingClientRect(),[l,t,w,h]=s.leftTopWidthHeight;return{x:r.x+l*r.width/n.canvas.width,y:r.y+t*r.height/n.canvas.height,width:w*r.width/n.canvas.width,height:h*r.height/n.canvas.height};});
   if(tile)return tile;
  }
  let selector=d.group==='cmp'?'#compare .viewer':['contrast','colormap'].includes(d.key)?'#inspector':['seed','point','eval'].includes(d.key)?'#workspaceAside':'#workspace .viewer';
  if(['eval','point','seed'].includes(d.key))await p.locator(d.key==='eval'?'#evalSection':d.key==='point'?'#capturePoint':'#regionSection').scrollIntoViewIfNeeded();
  if(['contrast','colormap'].includes(d.key)&&!(await p.locator('#inspector').isVisible()))selector='#workspace .viewer';
  if(['seed','point','eval'].includes(d.key)){
   const target=d.key==='seed'?'seedList':d.key==='point'?'pointList':'evalTable';await p.evaluate(target=>document.getElementById(target).scrollIntoView({block:'center'}),target);
   const r=await p.locator('#workspaceAside').boundingBox(),t=await p.locator('#'+target).boundingBox(),height=Math.min(900-r.y,r.width*9/16);
   return {x:r.x,y:Math.max(r.y,Math.min(t.y-35,900-height)),width:r.width,height};
  }
  if(['contrast','colormap'].includes(d.key)&&await p.locator('#inspector').isVisible()){
   const target=await p.locator(d.key==='contrast'?'#ctPlot':'#cmCanvas').boundingBox();if(target)return {x:target.x,y:Math.max(0,target.y-45),width:Math.min(target.width,1440-target.x),height:Math.min(target.width*9/16,900-Math.max(0,target.y-45))};
  }
  const r=await p.locator(selector).boundingBox();return {x:Math.max(0,r.x),y:Math.max(0,r.y),width:Math.min(r.width,1440-Math.max(0,r.x)),height:Math.min(r.height,900-Math.max(0,r.y))};
 }
 async function capture(d,fn){
  const folder=path.join(work,'frames',d.id);fs.mkdirSync(folder,{recursive:true});let counter=0,run=true,pending;
  const shot=async()=>{const clip=await clipFor(d);await p.evaluate(({name,clip})=>{let el=document.getElementById('captureCaption');if(!el){el=document.createElement('div');el.id='captureCaption';document.body.append(el);}Object.assign(el.style,{position:'fixed',left:clip.x+'px',top:clip.y+'px',width:clip.width+'px',height:'32px',padding:'5px 10px',background:'rgba(0,0,0,.8)',color:'white',zIndex:'2000',font:'16px system-ui',pointerEvents:'none'});el.textContent=name;},{name:d.name,clip});await p.screenshot({path:path.join(folder,String(counter++).padStart(4,'0')+'.png'),clip,animations:'disabled'});};
  await shot();pending=(async()=>{while(run){await sleep(230);if(run)await shot();}})();
  const started=Date.now();try{await fn();await sleep(900);}finally{run=false;await pending;await shot();}
  const entry={...d,frames:counter,source_duration_ms:Date.now()-started,status:'captured',source:'actual NiiVue/FastAPI operation',errors:[...errors]};const previous=manifest.findIndex(x=>x.id===d.id);if(previous>=0)manifest.splice(previous,1);manifest.push(entry);fs.writeFileSync(path.join(work,'capture-manifest.json'),JSON.stringify(manifest,null,2));console.log('CAPTURED',d.id,counter);
 }
 for(const d of definitions){
  if(manifest.some(x=>x.id===d.id)&&!forced.includes(d.id))continue;
  await p.evaluate(async ({d,ids})=>{
   const a=__app;if(a.inspector.open&&!['contrast','colormap'].includes(d.key))document.getElementById('inspectorClose').click();a.measurements.select(null);a.nv.setDrawingEnabled(false);a.state.focusViewer=false;
   if(d.group==='reg'){a.state.fixed={image_id:ids.fixed,name:'Fixed',size:[160,192,224]};a.state.moving={image_id:ids.moving,name:'Moving',size:[160,192,224]};document.getElementById('regIter').value='2';}
   if(d.group==='seg'){const target=d.key==='interp'?ids.sparse:ids.fixed;a.state.image={image_id:target,name:'Image'};await a.show(target);if(['draw','erase','clear','stop'].includes(d.key))a.state.segResult={operation:'manual-mask',base_id:target,result_id:ids.fixed_labels,label_count:35};}
   if(d.group==='tool'){await a.show(ids.fixed);}
   await a.nav(d.group==='reg'?'registration':d.group==='seg'?'seg-vessel':d.group==='cmp'?'compare':d.group==='view'?'viewer':'tools');
   if(d.group==='view'){a.nv.setSliceType(3);a.nv.setSliceMosaicString('');a.nv.setMultiplanarLayout(0);a.nv.scene.pan2Dxyzmm=[0,0,0,1];document.getElementById('layoutSelect').value='0';await a.show(ids.fixed);}
   if(['point','seed','region','contour'].includes(d.key)){a.state.location={mm:Array.from(a.nv.frac2mm([.5,.5,.5])).slice(0,3)};if(['region','contour'].includes(d.key))a.state.seeds=[a.state.location.mm];document.getElementById('addSeed').disabled=false;document.getElementById('runRg').disabled=false;document.getElementById('contourIter').value='2';}
   if(d.key==='eval'){document.getElementById('evalPred').value='fixed';document.getElementById('evalRef').value='fixed';}
   if(d.key==='threshold'){const v=a.nv.volumes[0];document.getElementById('thresholdLow').value=v.global_max*.4;document.getElementById('thresholdHigh').value=v.global_max*.9;}
   if(d.key==='mip'){const maximum=Number(document.getElementById('slabEnd').max);document.getElementById('slabStart').value=Math.round(maximum*.2);document.getElementById('slabEnd').value=Math.round(maximum*.8);}
   if(d.key==='reset'){a.nv.scene.pan2Dxyzmm=[15,10,0,1.8];a.nv.volumes[0].cal_min=.2;a.nv.drawScene();}
   if(d.key==='restore'){a.state.focusViewer=true;a.nv.setSliceType(0);document.getElementById('imageGrid').hidden=true;document.getElementById('mainCanvas').hidden=false;}
   if(d.key==='stop'&&d.group==='seg')await a.execute(a.definitions.find(x=>x.id==='icon-seg-draw'));
   if(d.key==='clear')await a.execute(a.definitions.find(x=>x.id==='icon-seg-draw'));
  },{d,ids:config.ids});
  if(d.group==='cmp'&&d.key!=='load')await p.evaluate(()=>__app.execute(__app.definitions.find(x=>x.id==='icon-cmp-load')));
  if(d.group==='tool'&&d.key==='stop'){
   await p.evaluate(()=>__app.execute(__app.definitions.find(x=>x.id==='icon-tool-distance')));
   const spot=await p.evaluate(()=>{const n=__app.nv,s=n.screenSlices.find(s=>s.axCorSag===0),r=n.canvas.getBoundingClientRect(),[l,t,w,h]=s.leftTopWidthHeight;return{x:r.x+(l+w*.4)*r.width/n.canvas.width,y:r.y+(t+h*.5)*r.height/n.canvas.height,dx:w*.18*r.width/n.canvas.width};});await p.mouse.click(spot.x,spot.y);await p.mouse.move(spot.x+spot.dx,spot.y,{steps:8});await p.waitForFunction(()=>__app.measurements.pending.length===1&&__app.measurements.preview);
  }
  await capture(d,async()=>{
   if(d.key==='modality'){const chooser=p.waitForEvent('filechooser');await p.click('#'+d.id);await(await chooser).setFiles(path.resolve(__dirname,'../tests/data/oasis/OASIS_OAS1_0010_MR1/aligned_norm.nii.gz'));await p.waitForFunction(()=>__app.nv.volumes.length===2);return;}
   const result=await p.evaluate(async id=>{const a=__app,d=a.definitions.find(x=>x.id===id),reasons=a.conditions(d);if(reasons.length)throw Error(id+': '+reasons.join(','));await a.execute(d);return document.getElementById('statusText').textContent;},d.id);
   if(result.startsWith('실패:'))throw Error(d.id+': '+result);
   const canvas=p.locator(d.group==='cmp'?'#compareFixed':'#gl');const r=await canvas.boundingBox();
   if(['distance','angle','roi'].includes(d.key)){
    const spots=await p.evaluate(()=>{const n=__app.nv,s=n.screenSlices.find(s=>s.axCorSag===0),r=n.canvas.getBoundingClientRect(),[l,t,w,h]=s.leftTopWidthHeight;return {x:r.x+(l+w*.4)*r.width/n.canvas.width,y:r.y+(t+h*.5)*r.height/n.canvas.height,dx:w*.22*r.width/n.canvas.width};});
    await p.mouse.click(spots.x,spots.y);if(d.key!=='roi'){await p.mouse.move(spots.x+spots.dx,spots.y-30,{steps:10});await sleep(400);await p.mouse.click(spots.x+spots.dx,spots.y-30);if(d.key==='angle')await p.mouse.click(spots.x+spots.dx,spots.y+40);}await sleep(600);
   }else if(['wl','panzoom','3d','draw','erase'].includes(d.key)&&r){
    const point=await p.evaluate(cmp=>{const n=cmp?null:__app.nv;if(!n||n.opts.sliceType===4)return null;const s=n.screenSlices.find(s=>s.axCorSag===0),r=n.canvas.getBoundingClientRect();if(!s)return null;const[l,t,w,h]=s.leftTopWidthHeight;return{x:r.x+(l+w*.5)*r.width/n.canvas.width,y:r.y+(t+h*.5)*r.height/n.canvas.height};},d.group==='cmp');const x=point?.x??r.x+r.width*.55,y=point?.y??r.y+r.height*.5;await p.mouse.move(x,y);await p.mouse.down({button:['wl','panzoom'].includes(d.key)?'right':'left'});await p.mouse.move(x+60,y-45,{steps:12});await p.mouse.up({button:['wl','panzoom'].includes(d.key)?'right':'left'});if(d.key==='panzoom')await p.mouse.wheel(0,180);
   }else if(['mpr','crosshair'].includes(d.key)&&r){for(const k of [.4,.55,.65]){await p.mouse.click(r.x+r.width*k,r.y+r.height*.45);await sleep(200);}}
   else if(d.key==='colormap'){await p.selectOption('#cmPreset','Jet');await sleep(350);}
   else if(d.key==='contrast'){const value=await p.locator('#ctMin').inputValue();await p.fill('#ctMin',String(Number(value)+.05));await p.press('#ctMin','Enter');}
  });
 }
 await browser.close();if(errors.length)throw Error(errors.join('\n'));console.log('COMPLETE',manifest.length);
})().catch(e=>{console.error(e);process.exit(1)});
