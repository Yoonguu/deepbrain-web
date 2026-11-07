from __future__ import annotations
import json, math, os, secrets, time, threading, logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
import numpy as np
import SimpleITK as sitk
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from . import store
from typing import Annotated
from .algorithms import RigidRegistration, RegistrationParams, ConfidenceConnectedSegmentation, HessianVesselness, DiceEvaluator
from .algorithms import classic, c2amorph

@asynccontextmanager
async def lifespan(app):
 store.recover_jobs()
 yield

app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
FRONT=Path(__file__).resolve().parent.parent/'frontend'
IMAGES=store.ROOT/'images'; IMAGES.mkdir(exist_ok=True)
POOL=ThreadPoolExecutor(max_workers=1)
SECURE=os.getenv('COOKIE_SECURE','1')=='1'
ATTEMPTS={}; LOCK=threading.Lock()
DUMMY_HASH=store.password('invalid-dummy-password')
def fail(status,message): raise HTTPException(status,message)
def identity(request:Request):
 token=request.cookies.get('session','')
 with store.connect() as c:
  row=c.execute('SELECT u.*,s.csrf FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?',(store.digest(token),time.time())).fetchone()
 if not row: fail(401,'로그인이 필요합니다.')
 return dict(row)
def approved(request:Request):
 u=identity(request)
 if not u['approved']: fail(403,'부서 소속 확인 후 이용할 수 있습니다.')
 return u
@app.middleware('http')
async def guard(req,call_next):
 root=req.scope.get('root_path',''); route=req.scope.get('path','')
 if root and route.startswith(root): route=route[len(root):] or '/'
 public=route in ('/','/auth','/api/auth/login','/api/auth/signup','/api/auth/me','/api/auth/logout')
 try:
  if not public: approved(req)
  if req.method not in ('GET','HEAD','OPTIONS'):
   origin=req.headers.get('origin')
   allowed={str(req.base_url).rstrip('/'),os.getenv('APP_PUBLIC_ORIGIN','').rstrip('/')}
   if origin and origin not in allowed: fail(403,'요청 출처를 확인할 수 없습니다.')
   if route not in ('/api/auth/login','/api/auth/signup'):
    u=identity(req)
    if not secrets.compare_digest(req.headers.get('x-csrf-token',''),u['csrf']): fail(403,'화면을 새로고침한 뒤 다시 시도하세요.')
  response=await call_next(req)
 except HTTPException as e: response=JSONResponse({'detail':e.detail},status_code=e.status_code)
 response.headers['Cache-Control']='private, max-age=3600' if route.startswith('/previews/') and response.status_code==200 else 'no-store'
 response.headers['X-Content-Type-Options']='nosniff'
 response.headers['X-Frame-Options']='DENY'
 response.headers['Referrer-Policy']='no-referrer'
 return response
class Credentials(BaseModel):
 email:str=Field(min_length=3,max_length=160)
 password:str=Field(min_length=12,max_length=128)
 name:str=Field(default='',max_length=80)
 department:str=Field(default='',max_length=80)
FAIL_WINDOW=60; FAIL_MAX=12
def _recent(key,now):
 return [t for t in ATTEMPTS.get(key,[]) if now-t<FAIL_WINDOW]
def limit(key):
 """계정(email) 단위로 최근 60초 실패 횟수만 검사한다. 프록시 뒤에서 IP가 하나로 보여도 다른 사용자에게 영향이 없다."""
 now=time.time()
 with LOCK:
  if len(ATTEMPTS)>10000: ATTEMPTS.clear()
  recent=_recent(key,now); ATTEMPTS[key]=recent
  if len(recent)>=FAIL_MAX: fail(429,'잠시 후 다시 시도하세요.')
def record_failure(key):
 now=time.time()
 with LOCK: ATTEMPTS[key]=_recent(key,now)+[now]
def clear_failures(key):
 with LOCK: ATTEMPTS.pop(key,None)
@app.post('/api/auth/signup')
def signup(req:Request,p:Credentials):
 key='signup:'+p.email.strip().lower(); limit(key); record_failure(key)
 if not p.name.strip() or not p.department.strip(): fail(400,'이름과 부서를 입력하세요.')
 with store.connect() as c:
  c.execute('INSERT OR IGNORE INTO users VALUES(?,?,?,?,?,?,?)',(secrets.token_hex(16),p.email.strip().lower(),p.name.strip(),p.department.strip(),'doctor',0,store.password(p.password)))
 return {'message':'가입 요청을 접수했습니다. 로그인 후 소속 확인 상태를 확인하세요.'}
@app.post('/api/auth/login')
def login(req:Request,p:Credentials):
 key='login:'+p.email.strip().lower(); limit(key)
 with store.connect() as c:
  u=c.execute('SELECT * FROM users WHERE email=?',(p.email.strip().lower(),)).fetchone()
  hashed=u['password'] if u else DUMMY_HASH
  if not store.verify(p.password,hashed) or not u: record_failure(key); fail(401,'로그인 정보를 확인해 주세요.')
  clear_failures(key)
  token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(32)
  c.execute('DELETE FROM sessions WHERE token=? OR expires<?',(store.digest(req.cookies.get('session','')),time.time()))
  c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(store.digest(token),u['id'],csrf,time.time()+7*86400))
 response=JSONResponse({'ok':True}); response.set_cookie('session',token,max_age=7*86400,httponly=True,secure=SECURE,samesite='strict'); return response
@app.get('/api/auth/me')
def me(req:Request):
 u=identity(req); return {k:u[k] for k in ('id','name','department','role','approved','csrf')}
@app.post('/api/auth/logout')
def logout(req:Request):
 with store.connect() as c: c.execute('DELETE FROM sessions WHERE token=?',(store.digest(req.cookies.get('session','')),))
 r=JSONResponse({'ok':True}); r.delete_cookie('session'); return r
@app.get('/')
@app.get('/auth')
def entry(req:Request):
 try: approved(req); page='index.html'
 except HTTPException: page='auth.html'
 return FileResponse(FRONT/page)
@app.get('/api/members')
def members(u=Depends(approved)):
 if u['role']!='head': fail(403,'부서장만 계정을 관리할 수 있습니다.')
 with store.connect() as c: return [dict(r) for r in c.execute('SELECT id,name,email,approved FROM users WHERE department=?',(u['department'],))]
class Approval(BaseModel): approved:bool
@app.post('/api/members/{uid}')
def approve(uid:str,p:Approval,u=Depends(approved)):
 if u['role']!='head': fail(403,'부서장만 소속을 확인할 수 있습니다.')
 if uid==u['id']: fail(400,'자신의 소속은 변경할 수 없습니다.')
 with store.connect() as c:
  cur=c.execute('UPDATE users SET approved=? WHERE id=? AND department=?',(int(p.approved),uid,u['department']))
  if not cur.rowcount: fail(404,'계정을 찾을 수 없습니다.')
  c.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
 store.audit(u['id'],'membership_changed',uid); return {'ok':True}
def file_for(fid,u):
 with store.connect() as c: row=c.execute('SELECT * FROM files WHERE id=? AND department=? AND deleted=0',(fid,u['department'])).fetchone()
 if not row: fail(404,'접근할 수 없는 자료입니다.')
 return dict(row)
def path_for(fid,u): file_for(fid,u); return IMAGES/(fid+'.nii.gz')
def add_file(fid,u,name,kind='original',base=None):
 img=sitk.ReadImage(str(IMAGES/(fid+'.nii.gz')))
 meta={'size':list(img.GetSize()),'spacing':list(img.GetSpacing())}
 with store.connect() as c: c.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?,0)',(fid,u['department'],name,kind,base,json.dumps(meta),time.time()))
 return dict(image_id=fid,name=name,**meta)
@app.get('/api/files')
def files(q:str='',u=Depends(approved)):
 with store.connect() as c: return [dict(r) for r in c.execute('SELECT * FROM files WHERE department=? AND deleted=0 AND name LIKE ? ORDER BY created DESC',(u['department'],'%'+q[:100]+'%'))]
@app.post('/api/images')
async def upload(req:Request,name:str='image.nii.gz',u=Depends(approved)):
 if not name.lower().endswith(('.nii','.nii.gz')): fail(400,'NIfTI(.nii, .nii.gz) 파일을 선택하세요.')
 fid=secrets.token_hex(16); temp=IMAGES/(fid+('.upload.nii.gz' if name.lower().endswith('.gz') else '.upload.nii')); size=0
 try:
  with temp.open('wb') as f:
   async for chunk in req.stream():
    size+=len(chunk)
    if size>256*1024*1024: fail(413,'파일은 256MiB 이하여야 합니다.')
    f.write(chunk)
  img=sitk.ReadImage(str(temp))
  if img.GetDimension()!=3 or img.GetNumberOfComponentsPerPixel()!=1 or img.GetNumberOfPixels()>67000000: fail(400,'지원되는 크기의 단일 성분 3D 영상이 필요합니다.')
  sitk.WriteImage(img,str(IMAGES/(fid+'.nii.gz')))
 except HTTPException: raise
 except Exception: fail(400,'영상 파일을 읽을 수 없습니다.')
 finally: temp.unlink(missing_ok=True)
 r=add_file(fid,u,Path(name).name[:160]); store.audit(u['id'],'upload',fid); return r
@app.post('/api/demo')
def demo(u=Depends(approved)):
 z,y,x=np.mgrid[:48,:48,:48]; arr=(100*np.exp(-((x-24)**2+(y-24)**2+(z-24)**2)/200)).astype('float32')
 img=sitk.GetImageFromArray(arr); img.SetSpacing((1.2,1.2,2.0)); fid=secrets.token_hex(16); sitk.WriteImage(img,str(IMAGES/(fid+'.nii.gz')))
 return add_file(fid,u,'합성 테스트 영상 — 실제 MRI 아님')
@app.get('/api/images/{fid}.nii.gz')
def image(fid:str,u=Depends(approved)):
 p=path_for(fid,u); store.audit(u['id'],'read_image',fid); return FileResponse(p,media_type='application/gzip')
@app.delete('/api/files/{fid}')
def delete(fid:str,u=Depends(approved)):
 file_for(fid,u)
 if u['role']!='head': fail(403,'삭제 권한이 없습니다. 해당 부서장만 삭제할 수 있습니다.')
 with store.connect() as c:
  c.execute('WITH RECURSIVE descendants(id) AS (SELECT id FROM files WHERE id=? AND department=? UNION SELECT f.id FROM files f JOIN descendants d ON f.base_id=d.id WHERE f.department=?) UPDATE files SET deleted=1 WHERE id IN (SELECT id FROM descendants)',(fid,u['department'],u['department']))
 store.audit(u['id'],'soft_delete',fid); return {'ok':True}
@app.get('/api/trash')
def trash(u=Depends(approved)):
 if u['role']!='head': fail(403,'부서장만 삭제 목록을 볼 수 있습니다.')
 with store.connect() as c:
  return [dict(r) for r in c.execute('SELECT id,name,kind,created FROM files WHERE department=? AND deleted=1 ORDER BY created DESC',(u['department'],))]
@app.delete('/api/trash/{fid}')
def purge(fid:str,u=Depends(approved)):
 if u['role']!='head': fail(403,'부서장만 영구 삭제할 수 있습니다.')
 with store.connect() as c:
  rows=c.execute('WITH RECURSIVE descendants(id) AS (SELECT id FROM files WHERE id=? AND department=? AND deleted=1 UNION SELECT f.id FROM files f JOIN descendants d ON f.base_id=d.id WHERE f.department=? AND f.deleted=1) SELECT id FROM descendants',(fid,u['department'],u['department'])).fetchall()
  ids=[r['id'] for r in rows]
  if not ids: fail(404,'삭제 목록에서 자료를 찾을 수 없습니다.')
  for item in ids:
   c.execute('DELETE FROM notes WHERE file_id=?',(item,))
   c.execute('DELETE FROM report_history WHERE file_id=?',(item,))
   c.execute('DELETE FROM reports WHERE file_id=?',(item,))
   c.execute('DELETE FROM files WHERE id=? AND department=? AND deleted=1',(item,u['department']))
  marks=','.join('?'*len(ids))
  c.execute(f"DELETE FROM jobs WHERE department=? AND json_extract(payload,'$.result.result_id') IN ({marks})",(u['department'],*ids))
 for item in ids:
  for suffix in ('.nii.gz','.tfm','.field.nii.gz'): (IMAGES/(item+suffix)).unlink(missing_ok=True)
 store.audit(u['id'],'purge',fid)
 return {'ok':True,'deleted_count':len(ids)}
@app.get('/api/records/{fid}')
def records(fid:str,u=Depends(approved)):
 file_for(fid,u)
 with store.connect() as c:
  report=c.execute('SELECT body,version FROM reports WHERE file_id=?',(fid,)).fetchone()
  notes=[dict(r) for r in c.execute('SELECT n.*,u.name FROM notes n JOIN users u ON u.id=n.author WHERE file_id=? ORDER BY n.id',(fid,))]
  history=[dict(r) for r in c.execute('SELECT h.*,u.name FROM report_history h JOIN users u ON u.id=h.author WHERE file_id=? ORDER BY h.id DESC',(fid,))]
 return {'report':dict(report) if report else {'body':'','version':0},'notes':notes,'history':history}
class Report(BaseModel): body:str=Field(max_length=20000); version:int=Field(ge=0)
@app.put('/api/records/{fid}')
def report(fid:str,p:Report,u=Depends(approved)):
 file_for(fid,u)
 with store.connect() as c:
  c.execute('BEGIN IMMEDIATE'); old=c.execute('SELECT version FROM reports WHERE file_id=?',(fid,)).fetchone()
  if (old['version'] if old else 0)!=p.version: fail(409,'동료가 소견서를 수정했습니다. 작성 내용을 보관한 뒤 최신 기록을 다시 불러오세요.')
  c.execute('INSERT OR REPLACE INTO reports VALUES(?,?,?)',(fid,p.body,p.version+1))
  c.execute('INSERT INTO report_history(file_id,body,version,author,created) VALUES(?,?,?,?,?)',(fid,p.body,p.version+1,u['id'],time.time()))
 store.audit(u['id'],'report_update',fid); return {'version':p.version+1}
class Note(BaseModel): body:str=Field(min_length=1,max_length=5000)
@app.post('/api/records/{fid}/notes')
def note(fid:str,p:Note,u=Depends(approved)):
 file_for(fid,u)
 with store.connect() as c: c.execute('INSERT INTO notes(file_id,author,body,created) VALUES(?,?,?,?)',(fid,u['id'],p.body,time.time()))
 return {'ok':True}
class Operation(BaseModel):
 fixed_id:str|None=None; moving_id:str|None=None; image_id:str|None=None
 metric:str='mattes'; iterations_per_level:int=Field(150,ge=1,le=2000)
 sigma:float=Field(.7,gt=0,le=10); alpha1:float=Field(.3,gt=0); alpha2:float=Field(3,gt=0)
 seeds_ras_mm:list[Annotated[list[float],Field(min_length=3,max_length=3)]]=Field(default_factory=list,max_length=100)
 multiplier:float=Field(2.5,gt=0,le=20); iterations:int=Field(4,ge=0,le=100); radius:int=Field(1,ge=0,le=10)
 contour_iterations:int=Field(300,ge=1,le=5000)
 start:int=Field(0,ge=0); end:int=Field(10,ge=0)
 lower:float=0; upper:float=100

def put_job(j,u):
 with store.connect() as c: c.execute('INSERT OR REPLACE INTO jobs VALUES(?,?,?)',(j['job_id'],u['department'],json.dumps(j)))
@app.get('/api/jobs/{jid}')
def job(jid:str,u=Depends(approved)):
 with store.connect() as c: row=c.execute('SELECT payload FROM jobs WHERE id=? AND department=?',(jid,u['department'])).fetchone()
 if not row: fail(404,'접근할 수 없는 작업입니다.')
 return json.loads(row['payload'])
@app.post('/api/{kind}')
def run(kind:str,p:Operation,u=Depends(approved)):
 pair=('registration','deformable','c2amorph')
 if kind not in pair+('vessel','region-growing','mip','threshold','active-contour','interpolate'): fail(404,'지원되지 않는 기능입니다.')
 if kind=='c2amorph':
  st=c2amorph.status()
  if not st['available']: fail(503,st['reason'])
 base=p.fixed_id if kind in pair else p.image_id
 inp=path_for(base,u); moving=path_for(p.moving_id,u) if kind in pair else None
 fid=secrets.token_hex(16); out=IMAGES/(fid+'.nii.gz'); jid=secrets.token_hex(16)
 j={'job_id':jid,'kind':kind,'status':'queued','progress':0,'message':'대기 중'}; put_job(j,u)
 def progress(f,msg): j.update(progress=f,message=msg); put_job(j,u)
 def work():
  try:
   j['status']='running'; progress(.05,'처리 중')
   if kind=='registration': result=RigidRegistration(RegistrationParams(metric=p.metric,iterations_per_level=p.iterations_per_level)).run(inp,moving,out,IMAGES/(fid+'.tfm'),progress)
   elif kind=='deformable': result=classic.deformable_registration(inp,moving,out,IMAGES/(fid+'.tfm'),p.iterations_per_level,progress)
   elif kind=='c2amorph': result=c2amorph.C2AMorph().predict(inp,moving,out,IMAGES/(fid+'.field.nii.gz'),progress)
   elif kind=='vessel': result=HessianVesselness(p.sigma,p.alpha1,p.alpha2).run(inp,out,progress)
   elif kind=='region-growing': result=ConfidenceConnectedSegmentation(p.multiplier,p.iterations,p.radius).run(inp,p.seeds_ras_mm,out,progress)
   else:
    image=sitk.ReadImage(str(inp),sitk.sitkFloat32); result={}
    if kind=='mip': image,result=classic.maximum_intensity_projection(image,p.start,p.end)
    elif kind=='threshold': image=classic.binary_threshold(image,p.lower,p.upper)
    elif kind=='active-contour':
     if not p.seeds_ras_mm: raise ValueError('Seed를 추가하세요.')
     image,result=classic.geodesic_active_contour(image,p.seeds_ras_mm[0],p.radius,p.contour_iterations,progress)
    else: image,result=classic.interpolate_axial_mask(image)
    sitk.WriteImage(image,str(out))
   file_for(base,u)
   meta=add_file(fid,u,kind+' 결과','result',base); result.update(base_id=base,result_id=fid,**meta)
   j.update(status='done',result=result,progress=1,message='완료')
  except Exception as exc:
   logging.exception('Processing failed')
   for suffix in ('.nii.gz','.tfm','.field.nii.gz'): (IMAGES/(fid+suffix)).unlink(missing_ok=True)
   reason=str(exc) if isinstance(exc,ValueError) else (str(exc.detail) if isinstance(exc,HTTPException) else kind+' 처리 중 오류가 발생했습니다. 서버 기록을 확인하세요.')
   j.update(status='failed',error=reason,message='실패: '+reason)
  put_job(j,u)
 POOL.submit(work); return {'job_id':jid}
class Measure(BaseModel): image_id:str; points:list[Annotated[list[float],Field(min_length=3,max_length=3)]]=Field(min_length=1,max_length=3); radius:float=Field(5,gt=0,le=100)
@app.post('/api/tools/measure')
def measure(p:Measure,u=Depends(approved)):
 im=sitk.ReadImage(str(path_for(p.image_id,u))); pts=np.array(p.points,dtype=float)
 if pts.shape[1]!=3 or not np.isfinite(pts).all(): fail(400,'유효한 RAS 좌표가 필요합니다.')
 result={}
 if len(pts)>=2: result['distance_mm']=float(np.linalg.norm(pts[1]-pts[0]))
 if len(pts)==3:
  a,b=pts[0]-pts[1],pts[2]-pts[1]; den=np.linalg.norm(a)*np.linalg.norm(b)
  if den: result['angle_degrees']=float(np.degrees(np.arccos(np.clip(a@b/den,-1,1))))
 try: center=ConfidenceConnectedSegmentation._seed_index(im,p.points[0])
 except ValueError: fail(400,'영상 안의 지점을 선택하세요.')
 arr=sitk.GetArrayFromImage(im); zz,yy,xx=np.ogrid[:arr.shape[0],:arr.shape[1],:arr.shape[2]]; sx,sy,sz=im.GetSpacing()
 roi=((xx-center[0])*sx)**2+((yy-center[1])*sy)**2+((zz-center[2])*sz)**2<=p.radius**2
 vals=arr[roi]; result.update(roi_shape='sphere',roi_radius_mm=p.radius,roi_mean=float(vals.mean()),roi_std=float(vals.std()),roi_volume_mm3=float(roi.sum()*sx*sy*sz),nonzero_volume_mm3=float(np.count_nonzero(arr)*sx*sy*sz))
 return result

@app.post('/api/tools/dice')
def dice(p:Operation,u=Depends(approved)):
 a=sitk.ReadImage(str(path_for(p.fixed_id,u))); b=sitk.ReadImage(str(path_for(p.moving_id,u)))
 if a.GetSize()!=b.GetSize() or not np.allclose(a.GetSpacing(),b.GetSpacing()) or not np.allclose(a.GetOrigin(),b.GetOrigin()) or not np.allclose(a.GetDirection(),b.GetDirection()): fail(400,'두 Mask의 크기와 좌표계가 같아야 합니다.')
 x=sitk.GetArrayFromImage(a);y=sitk.GetArrayFromImage(b)
 labelled=all(np.issubdtype(v.dtype,np.integer) for v in (x,y)) and len(np.union1d(np.unique(x),np.unique(y)))<=256
 if not labelled: x,y=(x>0).astype(np.uint8),(y>0).astype(np.uint8)
 r=DiceEvaluator().evaluate(x,y)
 return {'dice':r['dice_mean'] if labelled and r['dice_mean'] is not None else r['dice_foreground'],'mode':'label' if labelled else 'binary',**r}

@app.get('/api/transforms/{fid}.tfm')
def transform_file(fid:str,u=Depends(approved)):
 file_for(fid,u); path=IMAGES/(fid+'.tfm')
 if not path.is_file(): fail(404,'이 결과에는 transform 파일이 없습니다.')
 return FileResponse(path,media_type='text/plain',filename='registration.tfm')
@app.get('/api/fields/{fid}.nii.gz')
def field_file(fid:str,u=Depends(approved)):
 file_for(fid,u); path=IMAGES/(fid+'.field.nii.gz')
 if not path.is_file(): fail(404,'이 결과에는 변형장 파일이 없습니다.')
 return FileResponse(path,media_type='application/gzip',filename='displacement_field.nii.gz')
@app.get('/api/c2amorph/status')
def c2amorph_status(u=Depends(approved)):
 return c2amorph.status()
@app.get('/api/images/{fid}/axial')
def axial_info(fid:str,u=Depends(approved)):
 return classic.axial_axis_info(sitk.ReadImage(str(path_for(fid,u))))

@app.get('/api/jobs')
def jobs(u=Depends(approved)):
 with store.connect() as c:
  return [json.loads(r['payload']) for r in c.execute('SELECT payload FROM jobs WHERE department=? ORDER BY rowid DESC LIMIT 100',(u['department'],))]

ICON_IDS=set(('icon-'+g+'-'+n) for g,names in {'view':'mpr 3d crosshair wl panzoom layout enlarge reset','reg':'rigid deformable overlay c2amorph','seg':'vessel seed region threshold contour draw interp dice','tool':'point distance angle roi mip modality','cmp':'load slice wl panzoom'}.items() for n in names.split())
with store.connect() as c:
 c.execute('CREATE TABLE IF NOT EXISTS preferences(user_id TEXT PRIMARY KEY REFERENCES users(id),pinned TEXT NOT NULL DEFAULT \'[]\',usage TEXT NOT NULL DEFAULT \'{}\')')
@app.get('/api/preferences')
def preferences(u=Depends(approved)):
 with store.connect() as c:r=c.execute('SELECT pinned,usage FROM preferences WHERE user_id=?',(u['id'],)).fetchone()
 return {'pinned':json.loads(r['pinned']) if r else [],'usage':json.loads(r['usage']) if r else {}}
class Pins(BaseModel): pinned:list[str]=Field(max_length=6)
@app.put('/api/preferences/pinned')
def pins(p:Pins,u=Depends(approved)):
 if len(set(p.pinned))!=len(p.pinned) or any(i not in ICON_IDS for i in p.pinned):fail(400,'중복 없이 등록된 아이콘만 고정할 수 있습니다.')
 with store.connect() as c:
  c.execute('INSERT OR IGNORE INTO preferences(user_id) VALUES(?)',(u['id'],))
  c.execute('UPDATE preferences SET pinned=? WHERE user_id=?',(json.dumps(p.pinned),u['id']))
 return preferences(u)
class Usage(BaseModel): icon_id:str
@app.post('/api/preferences/usage')
def usage(p:Usage,u=Depends(approved)):
 if p.icon_id not in ICON_IDS:fail(400,'등록되지 않은 아이콘입니다.')
 with store.connect() as c:
  c.execute('BEGIN IMMEDIATE');c.execute('INSERT OR IGNORE INTO preferences(user_id) VALUES(?)',(u['id'],))
  data=json.loads(c.execute('SELECT usage FROM preferences WHERE user_id=?',(u['id'],)).fetchone()[0]);data[p.icon_id]=data.get(p.icon_id,0)+1
  c.execute('UPDATE preferences SET usage=? WHERE user_id=?',(json.dumps(data),u['id']))
 return {'icon_id':p.icon_id,'count':data[p.icon_id]}
@app.get('/api/previews')
def preview_list(u=Depends(approved)):
 folder=FRONT/'previews'
 return sorted(p.name for p in folder.glob('icon-*') if p.suffix in ('.webm','.png') and p.stem in ICON_IDS) if folder.is_dir() else []
@app.get('/previews/{filename}')
def preview(filename:str,u=Depends(approved)):
 if not any(filename==i+ext for i in ICON_IDS for ext in ('.webm','.png')):fail(404,'예시 준비 중')
 path=FRONT/'previews'/filename
 if not path.is_file():fail(404,'예시 준비 중')
 return FileResponse(path)
