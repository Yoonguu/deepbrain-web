import json
import unittest
import test_v3 as base
from backend import store
from backend.app import file_for, add_file, IMAGES
import numpy as np
import SimpleITK as sitk

class V10(base.Workflow):
 # Reuse helpers without rerunning inherited workflows twice.
 test_workflow = None
 test_signup_and_interpolation = None
 test_job_recovery = None
 test_preferences = None
 test_v7_fixes = None
 test_v8_features = None
 def test_owner_and_admin_permissions(self):
  owner=self.client('v10-owner@example.invalid','V10')
  peer=self.client('v10-peer@example.invalid','V10')
  admin=self.client('v10-admin@example.invalid','V10','head')
  foreign=self.client('v10-foreign@example.invalid','foreign','head')
  fid=self.fixture(owner)['image_id']
  self.assertEqual(len(owner.get('/api/files?q='+fid[:12]).json()),1)
  self.assertEqual(peer.get('/api/files').json(),[])
  for suffix in ['', '/axial']:
   url='/api/images/'+fid+('.nii.gz' if not suffix else suffix)
   self.assertEqual(peer.get(url).status_code,404)
   self.assertEqual(foreign.get(url).status_code,404)
  self.assertEqual(admin.get('/api/images/'+fid+'.nii.gz').status_code,200)
  self.assertNotIn('synthetic-fixture',admin.get('/api/files').text)
  self.assertEqual(owner.delete('/api/files/'+fid).status_code,200)
  self.assertEqual(owner.get('/api/images/'+fid+'.nii.gz').status_code,404)
 def test_provenance_colors_and_measurement_records(self):
  owner=self.client('v10-records@example.invalid','V10Records')
  peer=self.client('v10-outsider@example.invalid','V10Records')
  fid=self.fixture(owner)['image_id']
  job=self.wait(owner,owner.post('/api/threshold',json={'image_id':fid,'lower':20,'upper':80}).json()['job_id'])
  self.assertEqual(job['status'],'done',job);result=job['result'];rid=result['result_id']
  self.assertGreater(result['label_count'],0)
  rows=owner.get('/api/files').json();item=next(x for x in rows if x['id']==rid)
  self.assertEqual(item['parents'],[{'parent_id':fid,'role':'source'}])
  payload={'colors':{'1':'#112233'}}
  self.assertEqual(owner.put('/api/files/'+rid+'/colors',json=payload).status_code,200)
  self.assertEqual(peer.put('/api/files/'+rid+'/colors',json=payload).status_code,404)
  self.assertEqual(owner.put('/api/files/'+rid+'/colors',json={'colors':{'-1':'red'}}).status_code,400)
  record={'mode':'distance','points':[[-28,-28,40],[-30,-28,40]],'radius':4}
  saved=owner.post('/api/measurements/'+fid,json=record)
  self.assertEqual(saved.status_code,200,saved.text);self.assertEqual(saved.json()['result']['distance_mm'],2)
  self.assertEqual(len(owner.get('/api/measurements/'+fid).json()),1)
  self.assertEqual(peer.get('/api/measurements/'+fid).status_code,404)
  self.assertEqual(peer.get('/api/jobs/'+job['job_id']).status_code,404)
  self.assertEqual(peer.get('/api/jobs').json(),[])
  self.assertEqual(owner.post('/api/measurements/'+fid,json={**record,'mode':'angle'}).status_code,400)
 def test_public_demo_shared_but_not_peer_deletable(self):
  admin=self.client('v10-demo-head@example.invalid','공개 데모','head')
  peer=self.client('v10-demo-doc@example.invalid','공개 데모')
  fid=self.fixture(admin)['image_id']
  self.assertEqual(peer.get('/api/images/'+fid+'.nii.gz').status_code,200)
  self.assertEqual(peer.delete('/api/files/'+fid).status_code,403)
  self.assertEqual(admin.delete('/api/files/'+fid).status_code,200)
 def test_threshold_distinct_components(self):
  from backend.algorithms.classic import label_threshold
  array=np.zeros((6,6,6),dtype=np.float32);array[1,1,1]=5;array[4,4,4]=5
  labels,info=label_threshold(sitk.GetImageFromArray(array),4,6)
  result=sitk.GetArrayFromImage(labels)
  self.assertEqual(info['label_count'],2);self.assertNotEqual(result[1,1,1],result[4,4,4])
 def test_migration_is_repeatable(self):
  owner=self.client('v10-migration@example.invalid','V10Migrate');fid=self.fixture(owner)['image_id']
  store.init();store.init()
  self.assertEqual(owner.get('/api/images/'+fid+'.nii.gz').status_code,200)
 def test_icon_registry_matches_ui(self):
  import re
  from pathlib import Path
  from backend.app import ICON_IDS
  html=(Path(__file__).resolve().parents[1]/'frontend/index.html').read_text()
  section=html.split('const definitions=[')[1].split('].map(')[0]
  ids={'icon-'+group+'-'+name for group,name in re.findall(r"\['(view|reg|seg|tool|cmp)','([^']+)'",section)}
  self.assertEqual(ids,ICON_IDS)
 def test_other_authors_descendants_require_admin(self):
  owner=self.client('v10-root-owner@example.invalid','공개 데모')
  peer=self.client('v10-result-owner@example.invalid','공개 데모')
  admin=self.client('v10-root-admin@example.invalid','공개 데모','head')
  fid=self.fixture(owner)['image_id']
  job=self.wait(peer,peer.post('/api/threshold',json={'image_id':fid,'lower':20,'upper':80}).json()['job_id'])
  self.assertEqual(job['status'],'done',job)
  self.assertEqual(owner.delete('/api/files/'+fid).status_code,403)
  self.assertEqual(admin.delete('/api/files/'+fid).status_code,200)
  self.assertEqual(peer.get('/api/images/'+job['result']['result_id']+'.nii.gz').status_code,404)
 def test_legacy_owner_and_unknown_owner_migration(self):
  owner=self.client('v10-legacy@example.invalid','V10Legacy')
  admin=self.client('v10-legacy-admin@example.invalid','V10Legacy','head')
  known=self.fixture(owner)['image_id'];unknown=self.fixture(owner)['image_id']
  with store.connect() as c:
   c.execute('DELETE FROM file_access WHERE file_id IN (?,?)',(known,unknown))
   c.execute('DELETE FROM audit WHERE object_id IN (?,?)',(known,unknown))
   c.execute("UPDATE files SET name='old-identifying-name.nii.gz' WHERE id IN (?,?)",(known,unknown))
  store.audit('v10-legacy@example.invalid','upload',known)
  store.init();store.init()
  self.assertEqual(owner.get('/api/images/'+known+'.nii.gz').status_code,200)
  self.assertEqual(owner.get('/api/images/'+unknown+'.nii.gz').status_code,404)
  self.assertEqual(admin.get('/api/images/'+unknown+'.nii.gz').status_code,200)
  self.assertNotIn('old-identifying-name',admin.get('/api/files').text)

 def test_management_mode_blocks_original_pixels(self):
  owner=self.client('restricted-owner@example.invalid','Private')
  head=self.client('restricted-head@example.invalid','Private','head')
  fid=self.fixture(owner)['image_id']
  self.assertEqual(head.post('/api/auth/mode',json={'clinical':False}).status_code,200)
  self.assertTrue(head.get('/api/files').json())
  self.assertEqual(head.get('/api/images/'+fid+'.nii.gz').status_code,403)
  self.assertEqual(head.post('/api/threshold',json={'image_id':fid}).status_code,403)
  head.post('/api/auth/mode',json={'clinical':True})
  self.assertEqual(head.get('/api/images/'+fid+'.nii.gz').status_code,200)
 def test_seed_supervised_learning(self):
  owner=self.client('learning-owner@example.invalid','Learning')
  fid=self.fixture(owner)['image_id']
  payload={'image_id':fid,'region_method':'seed-logistic','seeds_ras_mm':[[-28.8,-28.8,48]],'background_seeds':[[-2.4,-2.4,4]]}
  job=self.wait(owner,owner.post('/api/region-growing',json=payload).json()['job_id'])
  self.assertEqual(job['status'],'done',job)
  result=job['result'];self.assertLess(result['final_loss'],result['initial_loss']);self.assertGreater(result['foreground_voxels'],0);self.assertFalse(result['pretrained'])
