(function(global){
  const Lab=global.FlyLab=global.FlyLab||{};
  class BrainOverlay{
    constructor(anchor,positions){
      this.anchor=anchor;this.materials={};this.activity={};this.group=new THREE.Group();anchor.add(this.group);
      this._build(positions);
    }
    _points(records,color,size,opacity){
      const a=new Float32Array(records.length*3),b=this.bounds;
      records.forEach((p,i)=>{a[i*3]=((p.x-b.cx)/b.span)*1.25;a[i*3+1]=-((p.y-b.cy)/b.span)*1.05;a[i*3+2]=((p.z-b.cz)/b.span)*1.15});
      const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(a,3));
      const m=new THREE.PointsMaterial({color,size,transparent:true,opacity,depthWrite:false,blending:THREE.AdditiveBlending});const pts=new THREE.Points(g,m);this.group.add(pts);return m;
    }
    _build(data){
      const b=data.bounds;this.bounds={cx:(b.x[0]+b.x[1])/2,cy:(b.y[0]+b.y[1])/2,cz:(b.z[0]+b.z[1])/2,span:Math.max(b.x[1]-b.x[0],b.y[1]-b.y[0],b.z[1]-b.z[0])};
      this._points(data.background||[],0x61707e,.012,.06);
      const colors={LC4:0x4fd1e8,LPLC2:0xf5a623,DNp01:0xff4d6d,DNa02:0x9b7cff};
      Object.entries(colors).forEach(([name,color])=>{const records=(data.populations||{})[name]||[];this.materials[name]=this._points(records,color,.035,.45);this.activity[name]=0});
      this.group.rotation.set(.12,-.25,.05);this.group.scale.set(1.15,1.15,1.15);
    }
    pulse(neural){
      if(!neural)return;this.activity.LC4=Math.min(1,neural.lc4_spikes/20);this.activity.LPLC2=Math.min(1,neural.lplc2_spikes/24);this.activity.DNp01=Math.min(1,neural.dnp01_spikes/2);this.activity.DNa02=Math.min(1,(Math.abs(neural.dna02_left_hz)+Math.abs(neural.dna02_right_hz))/160);
    }
    update(dt){Object.keys(this.activity).forEach(k=>{this.activity[k]*=Math.pow(.16,dt);const m=this.materials[k];if(m){m.opacity=.28+this.activity[k]*.72;m.size=.028+this.activity[k]*.055}})}
  }
  Lab.BrainOverlay=BrainOverlay;
})(window);
