const {chromium}=require('playwright'),fs=require('fs'),assert=require('assert');
(async()=>{
 const base=process.env.MEDICAL_UI_BASE_URL||'http://127.0.0.1:8502',config=JSON.parse(fs.readFileSync(process.env.MEDICAL_UI_SESSION));assert(config.fixture_server);assert(['localhost','127.0.0.1'].includes(new URL(base).hostname));
 const browser=await chromium.launch({args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const context=await browser.newContext({ignoreHTTPSErrors:true});const p=await context.newPage();const errors=[];p.on('pageerror',e=>errors.push(String(e)));
 if(process.env.NIIVUE_ESM_PATH)await p.route('https://cdn.jsdelivr.net/npm/@niivue/niivue@0.42.0/+esm',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.NIIVUE_ESM_PATH,'utf8')}));
 const login=await context.request.post(base+'/api/auth/login',{data:{email:config.email,password:config.password}});assert(login.ok());await p.goto(base+'/');await p.waitForFunction(()=>document.getElementById('who').textContent.includes('관리 모드'));
 assert.equal((await context.request.get(base+'/api/images/'+config.ids.fixed+'.nii.gz')).status(),403);
 assert(await p.locator('#fileRows button').filter({hasText:'Fixed 열기'}).evaluateAll(nodes=>nodes.length>0&&nodes.every(n=>n.disabled)));
 await p.click('#clinicalMode');await p.waitForFunction(()=>document.getElementById('who').textContent.includes('진료 모드'));
 assert.equal((await context.request.get(base+'/api/images/'+config.ids.fixed+'.nii.gz')).status(),200);
 await p.click('#clinicalMode');await p.waitForFunction(()=>document.getElementById('who').textContent.includes('관리 모드'));
 assert.equal((await context.request.get(base+'/api/images/'+config.ids.fixed+'.nii.gz')).status(),403);assert.equal(errors.length,0);
 console.log(JSON.stringify({status:'passed',checks:['management denies original','management open buttons disabled','clinical switch permits original','return to management denies again'],errors}));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
