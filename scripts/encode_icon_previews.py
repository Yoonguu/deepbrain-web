"""Encode actual capture frames into 320x180 GIF, PNG and 4-second VP9 WebM."""
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
import json,subprocess,math,os,shutil
work=Path(os.environ['ICON_CAPTURE_DIR']).resolve()
repo=Path(__file__).resolve().parents[1];destination=Path(os.environ.get('ICON_PREVIEW_DEST',str(repo/'frontend/previews')));destination.mkdir(parents=True,exist_ok=True)
font_path=subprocess.check_output(['fc-match','-f','%{file}',':lang=ko'],text=True).strip();font=ImageFont.truetype(font_path,11)
manifest=json.loads((work/'capture-manifest.json').read_text());results=[]
for row in manifest:
 identity=row['id'];prepared=work/'encoded-frames'/identity;prepared.mkdir(parents=True,exist_ok=True)
 count=row['frames'];indices=sorted(set(round(i*(count-1)/min(29,max(1,count-1))) for i in range(min(30,count))))
 images=[]
 for index in indices:
  original=Image.open(work/'frames'/identity/f'{index:04d}.png').convert('RGB');original.thumbnail((320,158),Image.Resampling.LANCZOS)
  canvas=Image.new('RGB',(320,180),'#14171c');canvas.paste(original,((320-original.width)//2,(158-original.height)//2));draw=ImageDraw.Draw(canvas);draw.text((7,161),row['name'],font=font,fill='white');images.append(canvas)
 for n,canvas in enumerate(images):canvas.save(prepared/f'{n:04d}.png')
 durations=[4000//len(images)]*len(images);durations[-1]+=4000-sum(durations)
 images[0].save(destination/(identity+'.gif'),save_all=True,append_images=images[1:],duration=durations,loop=0,optimize=True)
 images[-1].save(destination/(identity+'.png'))
 subprocess.run([os.environ.get('ICON_FFMPEG') or shutil.which('ffmpeg') or 'ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',f'{len(images)}/4','-i',str(prepared/'%04d.png'),'-t','4','-c:v','libvpx-vp9','-b:v','0','-crf','34','-pix_fmt','yuv420p','-an',str(destination/(identity+'.webm'))],check=True)
 assert (destination/(identity+'.webm')).stat().st_size<1024*1024
 with Image.open(destination/(identity+'.gif')) as gif:
  frames=gif.n_frames;assert frames>1,identity+' has no visible operation change';duration=sum(gif.seek(i) or gif.info['duration'] for i in range(frames));assert gif.size==(320,180);assert 3000<=duration<=6000
 results.append({**row,'gif_frames':frames,'duration_ms':duration,'width':320,'height':180,'webm_bytes':(destination/(identity+'.webm')).stat().st_size})
 print(identity,frames,'GIF frames')
(work/'encoded-manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
