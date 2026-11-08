import os,tempfile,unittest,secrets,time
sandbox=tempfile.TemporaryDirectory(); os.environ['MEDICAL_DATA_DIR']=sandbox.name; os.environ['COOKIE_SECURE']='0'
from fastapi.testclient import TestClient
from backend import store
from backend.app import app, ATTEMPTS
class Workflow(unittest.TestCase):
 def setUp(self):
  ATTEMPTS.clear()
 def client(self,email,department='A',role='doctor',approved=1):
  with store.connect() as c:c.execute('INSERT OR IGNORE INTO users VALUES(?,?,?,?,?,?,?)',(email,email,email,department,role,approved,store.password('long-demo-password')))
  cl=TestClient(app);r=cl.post('/api/auth/login',json={'email':email,'password':'long-demo-password'});self.assertEqual(r.status_code,200)
  me=cl.get('/api/auth/me').json();cl.headers['X-CSRF-Token']=me['csrf'];
  if role=='head':self.assertEqual(cl.post('/api/auth/mode',json={'clinical':True}).status_code,200)
  return cl
 def fixture(self,cl):
  import numpy as np
  import SimpleITK as sitk
  z,y,x=np.mgrid[:48,:48,:48]
  image=sitk.GetImageFromArray((100*np.exp(-((x-24)**2+(y-24)**2+(z-24)**2)/200)).astype('float32'))
  image.SetSpacing((1.2,1.2,2.0));path=store.ROOT/(secrets.token_hex(8)+'.nii.gz');sitk.WriteImage(image,str(path))
  response=cl.post('/api/images?name=synthetic-fixture.nii.gz',content=path.read_bytes());path.unlink()
  self.assertEqual(response.status_code,200,response.text);return response.json()
 def test_workflow(self):
  anonymous=TestClient(app)
  self.assertNotIn('Registration',anonymous.get('/').text)
  self.assertEqual(anonymous.get('/api/files').status_code,401)
  head=self.client('head@example.invalid',role='head');doctor=self.client('doctor@example.invalid');other=self.client('other@example.invalid','B');pending=self.client('pending@example.invalid',approved=0)
  self.assertEqual(pending.get('/api/files').status_code,403)
  bad=head.post('/api/demo',headers={'X-CSRF-Token':'bad'});self.assertEqual(bad.status_code,403)
  f=self.fixture(doctor);fid=f['image_id']
  self.assertEqual(head.post('/api/demo').status_code,403)
  self.assertEqual(doctor.get('/api/images/'+fid+'.nii.gz').status_code,200)
  self.assertEqual(other.get('/api/images/'+fid+'.nii.gz').status_code,404)
  self.assertEqual(other.get('/api/files').json(),[])
  peer=self.client('peer@example.invalid')
  self.assertEqual(peer.get('/api/images/'+fid+'.nii.gz').status_code,404)
  self.assertEqual(peer.delete('/api/files/'+fid).status_code,404)
  self.assertEqual(doctor.put('/api/records/'+fid,json={'body':'first','version':0}).status_code,200)
  self.assertEqual(head.put('/api/records/'+fid,json={'body':'stale','version':0}).status_code,409)
  self.assertEqual(head.put('/api/records/'+fid,json={'body':'second','version':1}).status_code,200)
  self.assertEqual(doctor.post('/api/records/'+fid+'/notes',json={'body':'shared note'}).status_code,200)
  self.assertEqual(len(head.get('/api/records/'+fid).json()['history']),2)
  measure=doctor.post('/api/tools/measure',json={'image_id':fid,'points':[[-28,-28,40],[-30,-28,40]],'radius':4})
  self.assertEqual(measure.status_code,200);self.assertAlmostEqual(measure.json()['distance_mm'],2)
  for kind,extra in [('registration',{'fixed_id':fid,'moving_id':fid,'iterations_per_level':2}),('deformable',{'fixed_id':fid,'moving_id':fid,'iterations_per_level':2}),('vessel',{}),('mip',{'start':10,'end':20}),('threshold',{'lower':20,'upper':80}),('region-growing',{'seeds_ras_mm':[[-28,-28,40]]}),('active-contour',{'seeds_ras_mm':[[-28,-28,40]],'iterations':2})]:
   r=doctor.post('/api/'+kind,json={'image_id':fid,**extra});self.assertEqual(r.status_code,200,r.text)
   jid=r.json()['job_id'];self.assertEqual(other.get('/api/jobs/'+jid).status_code,404)
   for _ in range(800):
    job=doctor.get('/api/jobs/'+jid).json()
    if job['status'] in ('done','failed'):break
    time.sleep(.05)
   self.assertEqual(job['status'],'done',job)
  self.assertEqual(doctor.post('/api/tools/dice',json={'fixed_id':fid,'moving_id':fid}).json()['dice'],1.0)
  self.assertEqual(head.delete('/api/files/'+fid).status_code,200)
  self.assertEqual(doctor.get('/api/images/'+fid+'.nii.gz').status_code,404)
  self.assertEqual(doctor.post('/api/auth/logout').status_code,200)
  self.assertEqual(doctor.get('/api/files').status_code,401)
 def test_signup_and_interpolation(self):
  import SimpleITK as sitk
  import numpy as np
  cl=TestClient(app)
  payload={'email':'new@example.invalid','password':'long-demo-password','name':'가상 신규 의사','department':'A'}
  self.assertEqual(cl.post('/api/auth/signup',json=payload).status_code,200)
  self.assertEqual(cl.post('/api/auth/login',json=payload).status_code,200)
  me=cl.get('/api/auth/me').json();cl.headers['X-CSRF-Token']=me['csrf']
  self.assertEqual(cl.get('/api/files').status_code,403)
  head=self.client('head2@example.invalid',role='head')
  self.assertEqual(head.post('/api/members/'+me['id'],json={'approved':True}).status_code,200)
  self.assertEqual(cl.get('/api/auth/me').status_code,401)
  cl.post('/api/auth/login',json=payload);cl.headers['X-CSRF-Token']=cl.get('/api/auth/me').json()['csrf']
  arr=np.zeros((12,16,16),dtype='uint8');arr[2,4:12,4:12]=1;arr[9,5:11,5:11]=1
  image=sitk.GetImageFromArray(arr)
  temp=store.ROOT/'test-mask.nii';sitk.WriteImage(image,str(temp))
  r=cl.post('/api/images?name=mask.nii',content=temp.read_bytes());self.assertEqual(r.status_code,200,r.text)
  jid=cl.post('/api/interpolate',json={'image_id':r.json()['image_id']}).json()['job_id']
  for _ in range(200):
   j=cl.get('/api/jobs/'+jid).json()
   if j['status'] in ('done','failed'):break
   time.sleep(.02)
  self.assertEqual(j['status'],'done',j)
  result=sitk.GetArrayFromImage(sitk.ReadImage(str(store.ROOT/'images'/(j['result']['result_id']+'.nii.gz'))))
  self.assertTrue(result[5].any())
 def test_job_recovery(self):
  import json
  owner=self.client('recovery@example.invalid','recovery-dept')
  outsider=self.client('outsider@example.invalid','elsewhere')
  with store.connect() as c:
   c.execute('INSERT INTO jobs VALUES(?,?,?)',('interrupted-example','recovery-dept',json.dumps({'owner_id':'recovery@example.invalid','job_id':'interrupted-example','kind':'registration','status':'running','message':'처리 중'})))
  store.recover_jobs()
  rows=owner.get('/api/jobs').json()
  self.assertEqual(rows[0]['status'],'failed')
  self.assertIn('재시작',rows[0]['message'])
  self.assertEqual(outsider.get('/api/jobs').json(),[])
 def test_preferences(self):
  a=self.client('pref-a@example.invalid');b=self.client('pref-b@example.invalid')
  headers={'Content-Type':'application/json'}
  good=['icon-view-wl','icon-reg-rigid']
  self.assertEqual(a.put('/api/preferences/pinned',json={'pinned':good}).status_code,200)
  self.assertEqual(a.get('/api/preferences').json()['pinned'],good)
  self.assertEqual(b.get('/api/preferences').json()['pinned'],[])
  self.assertEqual(a.put('/api/preferences/pinned',json={'pinned':['invalid']}).status_code,400)
  self.assertEqual(a.put('/api/preferences/pinned',json={'pinned':['icon-view-wl']*7}).status_code,422)
  self.assertEqual(a.post('/api/preferences/usage',json={'icon_id':'icon-view-wl'}).json()['count'],1)
  self.assertEqual(a.post('/api/preferences/usage',json={'icon_id':'icon-view-wl'}).json()['count'],2)
  self.assertEqual(b.get('/api/preferences').json()['usage'],{})
  self.assertEqual(a.post('/api/preferences/usage',json={'icon_id':'icon-view-wl'},headers={'X-CSRF-Token':'bad'}).status_code,403)
 def wait(self,cl,jid):
  for _ in range(1200):
   job=cl.get('/api/jobs/'+jid).json()
   if job['status'] in ('done','failed'):return job
   time.sleep(.05)
  return job
 def test_v7_fixes(self):
  head=self.client('v7-head@example.invalid','V7',role='head');other=self.client('v7-other@example.invalid','V8')
  for _ in range(12):self.assertEqual(TestClient(app).post('/api/auth/login',json={'email':'v7-target@example.invalid','password':'wrong-password-123'}).status_code,401)
  self.assertEqual(TestClient(app).post('/api/auth/login',json={'email':'v7-target@example.invalid','password':'wrong-password-123'}).status_code,429)
  self.client('v7-other-user@example.invalid','V7')  # 다른 계정은 영향 없음
  fid=self.fixture(head)['image_id']
  self.assertEqual(head.get('/api/images/'+fid+'/axial').json()['axial_index_axis'],'k')
  self.assertEqual(head.post('/api/tools/measure',json={'image_id':fid,'points':[[1,2,3],[1,2]]}).status_code,422)
  bad=self.wait(head,head.post('/api/threshold',json={'image_id':fid,'lower':50,'upper':10}).json()['job_id'])
  self.assertEqual(bad['status'],'failed');self.assertIn('하한',bad['error'])
  job=self.wait(head,head.post('/api/registration',json={'fixed_id':fid,'moving_id':fid,'iterations_per_level':2}).json()['job_id'])
  rid=job['result']['result_id']
  self.assertEqual(head.get('/api/transforms/'+rid+'.tfm').status_code,200)
  self.assertEqual(other.get('/api/transforms/'+rid+'.tfm').status_code,404)
  contour=self.wait(head,head.post('/api/active-contour',json={'image_id':fid,'seeds_ras_mm':[[-28,-28,40]],'radius':3,'contour_iterations':50}).json()['job_id'])
  self.assertEqual(contour['status'],'done',contour);self.assertLess(contour['result']['sigmoid_alpha'],0)
  self.assertEqual(head.delete('/api/files/'+fid).status_code,200)
  self.assertEqual(head.delete('/api/trash/'+fid).json()['deleted_count'],3)
  self.assertFalse((store.ROOT/'images'/(rid+'.tfm')).exists())
  self.assertFalse(any(j.get('result',{}) and j['result'].get('result_id')==rid for j in head.get('/api/jobs').json()))
 def test_v8_features(self):
  head=self.client('v8-head@example.invalid','V8A',role='head');other=self.client('v8-other@example.invalid','V8B')
  fid=self.fixture(head)['image_id']
  models=head.get('/api/dl/models').json();ids=[m['model_id'] for m in models]
  self.assertEqual(ids[0],'lfcamorph-oasis');self.assertFalse(next(m for m in models if m['model_id']=='voxelmorph-oasis')['available'])
  self.assertEqual(head.post('/api/deep-learning',json={'fixed_id':fid,'moving_id':fid,'model_id':'voxelmorph-oasis'}).status_code,503)
  self.assertEqual(head.post('/api/deep-learning',json={'fixed_id':fid,'moving_id':fid,'model_id':'unknown'}).status_code,400)
  self.assertEqual(head.post('/api/c2amorph',json={'fixed_id':fid,'moving_id':fid}).status_code,404)
  job=self.wait(head,head.post('/api/threshold',json={'image_id':fid,'lower':20,'upper':200}).json()['job_id'])
  mask=job['result']['result_id']
  r=head.post('/api/tools/evaluate',json={'prediction_id':mask,'reference_id':mask,'metrics':['dice','hd','hd95','asd','assd']})
  self.assertEqual(r.status_code,200,r.text);body=r.json()
  self.assertEqual(body['summary']['dice']['mean'],1.0);self.assertEqual(body['summary']['hd95']['mean'],0.0)
  self.assertEqual(head.post('/api/tools/evaluate',json={'prediction_id':mask,'reference_id':mask,'metrics':['volume']}).status_code,400)
  self.assertEqual(other.post('/api/tools/evaluate',json={'prediction_id':mask,'reference_id':mask}).status_code,404)
  self.assertEqual(head.post('/api/tools/dice',json={'fixed_id':mask,'moving_id':mask}).json()['dice'],1.0)
  with store.connect() as c:c.execute("INSERT OR REPLACE INTO preferences VALUES(?,?,?)",(head.get('/api/auth/me').json()['id'],'["icon-reg-c2amorph","icon-reg-dl"]','{"icon-reg-c2amorph":3}'))
  prefs=head.get('/api/preferences').json();self.assertEqual(prefs['pinned'],['icon-reg-dl']);self.assertEqual(prefs['usage'],{})
  self.assertEqual(head.put('/api/preferences/pinned',json={'pinned':['icon-tool-contrast','icon-tool-colormap','icon-seg-eval']}).status_code,200)
  preset={'points':[{'position':0,'left':[0,0,0,0],'right':[0,0,128,255],'style':'two-sided'},{'position':1,'left':[128,0,0,255],'right':[128,0,0,255]}],'nan':[0,0,0,0]}
  self.assertEqual(head.put('/api/preferences/colormaps/내 Jet',json=preset).json()['내 Jet']['points'][0]['style'],'two-sided')
  self.assertEqual(other.get('/api/preferences/colormaps').json(),{})
  self.assertEqual(head.put('/api/preferences/colormaps/Jet',json=preset).status_code,400)
  bad={**preset,'points':list(reversed(preset['points']))}
  self.assertEqual(head.put('/api/preferences/colormaps/bad',json=bad).status_code,400)
  self.assertEqual(head.delete('/api/preferences/colormaps/내 Jet').json(),{})
  self.assertEqual(head.delete('/api/preferences/colormaps/내 Jet').status_code,404)
if __name__=='__main__':unittest.main()
