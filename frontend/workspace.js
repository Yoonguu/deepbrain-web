// v10 viewer utilities. All measurements are stored in physical RAS millimetres.
export function intersectionAngle(a, b, tolerance = 0.1) {
  const sub=(a,b)=>a.map((v,i)=>v-b[i]),dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
  const u=sub(a[1],a[0]),v=sub(b[1],b[0]),w=sub(a[0],b[0]);
  const A=dot(u,u),B=dot(u,v),C=dot(v,v),D=dot(u,w),E=dot(v,w),den=A*C-B*B;
  if(den<1e-9)return null;
  const s=(B*E-C*D)/den,t=(A*E-B*D)/den;
  if(s<0||s>1||t<0||t>1)return null;
  const p=a[0].map((x,i)=>x+s*u[i]),q=b[0].map((x,i)=>x+t*v[i]);
  if(Math.hypot(...sub(p,q))>tolerance)return null;
  return {point:p,degrees:Math.acos(Math.min(1,Math.abs(B)/Math.sqrt(A*C)))*180/Math.PI};
}
export function installZoom(nv, canvas, changed = ()=>{}) {
  canvas.addEventListener('wheel',e=>{
    // Normal wheel keeps slice scrolling. Pan/Zoom or Ctrl uses the requested reversed zoom.
    if(!nv.volumes.length || !(e.ctrlKey || nv.opts.dragMode===nv.dragModes.pan))return;
    e.preventDefault();e.stopImmediatePropagation();
    const pan=nv.scene.pan2Dxyzmm;pan[3]=Math.max(.1,Math.min(20,pan[3]*Math.exp(e.deltaY*.0015)));
    nv.drawScene();changed();
  },{capture:true,passive:false});
}
export class ImageGrid {
  constructor(Niivue,element,imageUrl,onLocation) {
    Object.assign(this,{Niivue,element,imageUrl,onLocation,cells:[],generation:0});
  }
  show(rows) {
    const generation=++this.generation;
    const task=(this.pending||Promise.resolve()).catch(()=>{}).then(()=>generation===this.generation?this.renderRows(rows,generation):undefined);
    this.pending=task;return task;
  }
  cancel(){this.generation++;}
  async renderRows(rows,generation) {
    this.element.style.gridTemplateRows=`repeat(${rows.length},minmax(0,1fr))`;
    for(let row=0;row<3;row++)for(let col=0;col<3;col++) {
      if(generation!==this.generation)return;
      const index=row*3+col,source=rows[row];
      let cell=this.cells[index];
      if(!cell && source) {
        const wrap=document.createElement('div'),label=document.createElement('span'),canvas=document.createElement('canvas');
        wrap.className='image-cell';wrap.append(label,canvas);this.element.append(wrap);
        const nv=new this.Niivue({backColor:[.08,.09,.11,1],show3Dcrosshair:true,isColorbar:false});
        await nv.attachToCanvas(canvas);nv.setSliceType([2,1,0][col]);
        cell=this.cells[index]={wrap,label,canvas,nv,key:''};installZoom(nv,canvas);
        nv.onIntensityChange=volume=>this.onAppearance?.(String(volume.name).replace(/\.nii(\.gz)?$/,''),volume);
        nv.onLocationChange=data=>{
          if(this.syncing||!data.mm)return;
          this.syncing=true;
          try { for(const peer of this.cells)if(peer!==cell&&peer.nv.volumes.length){peer.nv.scene.crosshairPos=peer.nv.mm2frac(data.mm);peer.nv.drawScene();} }
          finally {this.syncing=false;}
          this.onLocation(data,cell.source);
        };
      }
      if(!cell)continue;
      cell.wrap.hidden=!source;if(!source)continue;
      cell.canvas.hidden=!source.id;cell.source=source;cell.label.textContent=`${source.label} · ${['X / Sagittal','Y / Coronal','Z / Axial'][col]}${!source.id?(source.label==='Warped'||source.label==='Segmentation'?' · 결과 대기':' · 미선택'):''}`;
      if(generation!==this.generation)return;
      const key=JSON.stringify([source.id,source.overlay,source.color,source.overlayColor]);
      if(key!==cell.key){
        const vols=source.id?[{url:this.imageUrl(source.id),name:source.id+'.nii.gz',colormap:source.color||'gray'}]:[];
        if(source.overlay)vols.push({url:this.imageUrl(source.overlay),name:source.overlay+'.nii.gz',colormap:source.overlayColor||'drawing',opacity:.5});
        await cell.nv.loadVolumes(vols);cell.key=key;
        cell.initial=cell.nv.volumes.map(v=>[v.cal_min,v.cal_max,v.colormap]);
      }
      cell.nv.resizeListener?.();
    }
  }
  opacity(value){for(const c of this.cells)if(c.nv.volumes.length>1)c.nv.setOpacity(1,value);}
  reset(){for(const c of this.cells){c.nv.scene.pan2Dxyzmm=[0,0,0,1];c.nv.scene.crosshairPos=[.5,.5,.5];c.nv.volumes.forEach((v,i)=>{if(c.initial?.[i]){v.colormap=c.initial[i][2];[v.cal_min,v.cal_max]=c.initial[i];}});c.nv.updateGLVolume();c.nv.drawScene();}}
  appearance(id,source,lut){for(const c of this.cells)for(const v of c.nv.volumes)if(v.name===id+'.nii.gz'){
    if(lut)c.nv.addColormap(source.colormap,lut);v.colormap=source.colormap;v.cal_min=source.cal_min;v.cal_max=source.cal_max;c.nv.updateGLVolume();
  }}
}
export class Measurements {
  constructor(nv,svg,{imageId,api,status,changed}){
    Object.assign(this,{nv,svg,imageId,api,status,changed,mode:null,pending:[],records:[],serial:0});
    const canvas=nv.canvas;
    canvas.addEventListener('mousedown',e=>{if(e.button===0&&this.mode){e.preventDefault();e.stopImmediatePropagation();this.click(e).catch(error=>status(error.message,true));}},{capture:true});
    canvas.addEventListener('mousemove',e=>{if(this.mode&&this.pending.length){this.preview=this.hit(e)?.mm;this.render();}});
    canvas.addEventListener('mouseleave',()=>{this.preview=null;this.render();});
    const draw=nv.drawScene.bind(nv);nv.drawScene=(...args)=>{const result=draw(...args);this.render();return result;};
    document.addEventListener('keydown',e=>{if(e.key==='Escape'){this.pending=[];this.preview=null;this.render();}});
  }
  async load(){const id=this.imageId(),serial=++this.serial;this.pending=[];this.preview=null;this.records=[];this.render();if(!id)return;
    const records=await this.api('/api/measurements/'+id);if(serial===this.serial){this.records=records;this.render();this.changed();}}
  select(mode){this.mode=mode;this.pending=[];this.preview=null;this.nv.setDrawingEnabled(false);this.render();this.changed();this.status(mode?`${{distance:'거리',angle:'각도',roi:'ROI'}[mode]}: 영상의 측정 위치를 클릭하세요.`:'측정 모드를 종료했습니다.');}
  hit(e){
    const c=this.nv.canvas,r=c.getBoundingClientRect(),x=(e.clientX-r.left)*c.width/r.width,y=(e.clientY-r.top)*c.height/r.height;
    const slice=this.nv.screenSlices.find(s=>{const[l,t,w,h]=s.leftTopWidthHeight;return s.axCorSag<3&&x>=Math.min(l,l+w)&&x<=Math.max(l,l+w)&&y>=t&&y<=t+h;});
    if(!slice)return null;const frac=this.nv.canvasPos2frac([x,y]);if(frac.some(v=>v<0||v>1))return null;
    return {mm:Array.from(this.nv.frac2mm(frac)).slice(0,3),axis:2-slice.axCorSag};
  }
  async click(e){
    if(this.saving||!this.imageId())return;const h=this.hit(e);if(!h)return;
    if(this.pending.length&&(h.axis!==this.axis||Math.abs(h.mm[h.axis]-this.pending[0][h.axis])>.1)){this.status('같은 단면에서 측정점을 선택하세요.',true);return;}
    this.axis=h.axis;this.pending.push(h.mm);this.preview=null;this.render();
    const count={distance:2,angle:3,roi:1}[this.mode];if(this.pending.length!==count)return;
    this.saving=true;const image=this.imageId(),serial=this.serial;
    try{const record=await this.api('/api/measurements/'+image,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:this.mode,points:this.pending,radius:Number(document.getElementById('roiRadius').value)})});
      if(serial===this.serial){this.records.push(record);this.pending=[];this.status('측정 완료');this.changed();}}
    finally {this.saving=false;this.pending=[];this.render();}
  }
  project(mm,slice){
    const axes=slice.axCorSag===0?[0,1,2]:slice.axCorSag===1?[0,2,1]:[1,2,0];
    const[l,t,w,h]=slice.leftTopWidthHeight,f=slice.fovMM,o=slice.leftTopMM;
    if(!f?.[0]||!f?.[1])return null;
    const center=this.nv.frac2mm(this.nv.scene.crosshairPos);
    const spacing=Math.max(...(this.nv.volumes[0]?.hdr?.pixDims?.slice(1,4)||[1]));
    if(Math.abs(mm[axes[2]]-center[axes[2]])>spacing*.55)return null;
    const x=(mm[axes[0]]-o[0])/f[0],y=(mm[axes[1]]-o[1])/f[1];
    return [w<0?l+w+x*(-w):l+x*w,t+(1-y)*h];
  }
  render(){
    if(!this.svg)return;const c=this.nv.canvas;this.svg.setAttribute('viewBox',`0 0 ${c.width||1} ${c.height||1}`);this.svg.replaceChildren();
    const add=(tag,attrs,text)=>{const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))el.setAttribute(k,v);if(text)el.textContent=text;this.svg.append(el);};
    const records=[...this.records];if(this.pending.length)records.push({mode:this.mode,points:this.preview?[...this.pending,this.preview]:this.pending,result:{},preview:true});
    for(const slice of this.nv.screenSlices||[]){if(slice.axCorSag>2)continue;
      for(const record of records){const pts=record.points.map(p=>this.project(p,slice));if(pts.some(p=>!p))continue;
        const color='var(--accent)';if(pts.length>1)add('polyline',{points:pts.map(p=>p.join(',')).join(' '),fill:'none',stroke:color,'stroke-width':2,'stroke-dasharray':record.preview?'5 4':'none'});
        for(const p of pts)add('circle',{cx:p[0],cy:p[1],r:3,fill:color});
        let text=record.mode==='distance'&&pts.length===2?Math.hypot(...record.points[0].map((x,i)=>x-record.points[1][i])).toFixed(2)+' mm':record.mode==='angle'&&record.result.angle_degrees!=null?record.result.angle_degrees.toFixed(1)+'°':record.mode==='roi'&&record.result.roi_mean!=null?'ROI 평균 '+record.result.roi_mean.toFixed(2):'';
        if(record.mode==='roi'&&record.radius){const rx=Math.abs(record.radius/slice.fovMM[0]*slice.leftTopWidthHeight[2]),ry=Math.abs(record.radius/slice.fovMM[1]*slice.leftTopWidthHeight[3]);add('ellipse',{cx:pts[0][0],cy:pts[0][1],rx,ry,stroke:color,fill:'none'});}
        if(text)add('text',{x:pts[0][0]+7,y:pts[0][1]-7,fill:color,'font-size':14},text);
      }
      const lines=this.records.filter(r=>r.mode==='distance');
      for(let i=0;i<lines.length;i++)for(let j=i+1;j<lines.length;j++){const hit=intersectionAngle(lines[i].points,lines[j].points);if(!hit)continue;const p=this.project(hit.point,slice);if(p)add('text',{x:p[0]+7,y:p[1]+18,fill:'var(--accent)','font-size':14},hit.degrees.toFixed(1)+'°');}
    }
  }
}
