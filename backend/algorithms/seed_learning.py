"""Per-image supervised logistic classification from explicit positive/negative seeds."""
import numpy as np
import SimpleITK as sitk
from .region_growing import ConfidenceConnectedSegmentation
from .common import report,validate_scalar_volume

def seeded_logistic(input_path,positive,negative,output_path,progress=None):
 if not positive or not negative: raise ValueError('학습 분할에는 전경·배경 Seed가 각각 1개 이상 필요합니다.')
 image=sitk.ReadImage(str(input_path),sitk.sitkFloat32);validate_scalar_volume(image,'Image')
 arr=sitk.GetArrayFromImage(image)
 if not np.isfinite(arr).all(): raise ValueError('유한한 영상 값이 필요합니다.')
 from scipy.ndimage import gaussian_filter
 smooth=gaussian_filter(arr,1);scale=max(float(arr.std()),1e-6)
 z=(arr-float(arr.mean()))/scale
 features=np.stack([np.ones_like(z),z,z*z,(smooth-float(arr.mean()))/scale],axis=-1).reshape(-1,4)
 examples=[];labels=[];seed_indices=[];classes=[]
 for value,seeds in [(1,positive),(0,negative)]:
  indices=[]
  for seed in seeds:
   x,y,zz=ConfidenceConnectedSegmentation._seed_index(image,seed);indices.append((zz,y,x))
   for k in range(max(0,zz-1),min(arr.shape[0],zz+2)):
    for j in range(max(0,y-1),min(arr.shape[1],y+2)):
     for i in range(max(0,x-1),min(arr.shape[2],x+2)):
      examples.append(np.ravel_multi_index((k,j,i),arr.shape));labels.append(value)
  classes.append(set(indices))
  if value:seed_indices=indices
 if classes[0]&classes[1]:raise ValueError('같은 위치에 전경과 배경 Seed를 지정할 수 없습니다.')
 X=features[examples].astype(np.float64);y=np.asarray(labels);weights=np.zeros(4)
 # Balance foreground/background samples so seed count does not determine the class prior.
 sample_weights=np.where(y==1,.5/max(1,(y==1).sum()),.5/max(1,(y==0).sum()))
 def loss():
  logits=X@weights
  return float(np.sum(sample_weights*(np.logaddexp(0,logits)-y*logits)))
 initial=loss();report(progress,.2,'전경·배경 Seed로 Logistic Regression 학습 중')
 for _ in range(400):
  prediction=1/(1+np.exp(-np.clip(X@weights,-30,30)))
  gradient=X.T@((prediction-y)*sample_weights)+.001*np.r_[0,weights[1:]]
  weights-=.1*gradient
 predicted=np.empty(features.shape[0],dtype=np.uint8)
 for start in range(0,len(predicted),262144):predicted[start:start+262144]=(features[start:start+262144]@weights>=0)
 mask=sitk.GetImageFromArray(predicted.reshape(arr.shape));mask.CopyInformation(image)
 components=sitk.ConnectedComponent(mask);lab=sitk.GetArrayFromImage(components)
 keep={int(lab[p]) for p in seed_indices}-{0}
 result=np.isin(lab,list(keep)).astype(np.uint8)
 output=sitk.GetImageFromArray(result);output.CopyInformation(image);sitk.WriteImage(output,str(output_path),True)
 return {'method':'seed-supervised-logistic-regression','training_samples':len(y),'initial_loss':initial,'final_loss':loss(),'weights':weights.tolist(),'foreground_voxels':int(result.sum()),'label_count':1,'pretrained':False}
