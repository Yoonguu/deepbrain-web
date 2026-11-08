"""Run an isolated browser fixture server; never use the production data directory."""
import argparse,json,os,secrets,shutil,sys,tempfile
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir',default=None)
parser.add_argument('--session-file',required=True)
parser.add_argument('--port',type=int,default=8502)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
data=Path(args.data_dir or tempfile.mkdtemp(prefix='medical-v10-ui-')).resolve()
if data==Path('/data/medical-web-v7/medical-web/data') or (data/'medical.sqlite3').exists():
 raise SystemExit('Use a new, empty fixture data directory.')
sys.path.insert(0,str(root));os.chdir(root)
os.environ['MEDICAL_DATA_DIR']=str(data);os.environ['COOKIE_SECURE']='0'
import SimpleITK as sitk
sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(2)
from backend import store
from backend.app import app,IMAGES,add_file
user={'id':'v10-browser-test','department':'V10 UI tests'};secret=secrets.token_urlsafe(24)
with store.connect() as c:
 c.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)',(user['id'],'v10-ui@example.invalid','V10 UI',user['department'],'head',1,store.password(secret)))
manifest=json.loads((root/'tests/data/oasis_pair.json').read_text());ids={}
for role in ['fixed','moving','fixed_labels','moving_labels']:
 fid=secrets.token_hex(16);shutil.copyfile(root/'tests/data/oasis'/manifest[role],IMAGES/(fid+'.nii.gz'));add_file(fid,user,role);ids[role]=fid
# Sparse two-slice mask used to exercise interpolation through the actual UI.
import numpy as np
array=np.zeros((48,48,48),dtype=np.uint8);array[10,15:30,15:30]=1;array[30,17:28,17:28]=1
sparse=sitk.GetImageFromArray(array);fid=secrets.token_hex(16);sitk.WriteImage(sparse,str(IMAGES/(fid+'.nii.gz')));add_file(fid,user,'interpolation fixture');ids['sparse']=fid
session=Path(args.session_file);session.parent.mkdir(parents=True,exist_ok=True)
session.write_text(json.dumps({'fixture_server':True,'email':'v10-ui@example.invalid','password':secret,'ids':ids}));session.chmod(0o600)
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=args.port,log_level='warning')
