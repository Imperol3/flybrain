(function(global){
  const Lab=global.FlyLab=global.FlyLab||{};
  class NeuralMonitor{
    constructor(mount){this.mount=mount;this.history={lc4:[],lplc2:[],dnp01:[],steer:[]};this.frame=null;this._build();this.draw();}
    _build(){
      this.canvas=document.createElement('canvas');this.canvas.width=1024;this.canvas.height=560;this.ctx=this.canvas.getContext('2d');this.texture=new THREE.CanvasTexture(this.canvas);this.texture.encoding=THREE.sRGBEncoding;
      const screenMat=new THREE.MeshBasicMaterial({map:this.texture});const screen=new THREE.Mesh(new THREE.PlaneGeometry(5.1,2.8),screenMat);screen.position.z=.08;this.mount.add(screen);
      const frameMat=new THREE.MeshStandardMaterial({color:0x080b12,roughness:.4,metalness:.72});const part=(s,p)=>{const m=new THREE.Mesh(new THREE.BoxGeometry(...s),frameMat);m.position.set(...p);m.castShadow=true;this.mount.add(m)};part([5.45,.16,.24],[0,1.48,0]);part([5.45,.16,.24],[0,-1.48,0]);part([.16,2.9,.24],[-2.64,0,0]);part([.16,2.9,.24],[2.64,0,0]);
      const glow=new THREE.PointLight(0x315dff,1.3,5);glow.position.set(0,0,1);this.mount.add(glow);
    }
    push(frame){this.frame=frame;if(frame.neural){const n=frame.neural;this.history.lc4.push(n.lc4_spikes);this.history.lplc2.push(n.lplc2_spikes);this.history.dnp01.push(n.dnp01_spikes);this.history.steer.push(n.steering_hz);Object.values(this.history).forEach(a=>{if(a.length>110)a.shift()})}this.draw();}
    line(values,x,y,w,h,color,maxOverride){const c=this.ctx;if(values.length<2)return;const max=maxOverride||Math.max(1,...values.map(Math.abs));c.beginPath();values.forEach((v,i)=>{const px=x+i/(values.length-1)*w,py=y+h-(v/max*.45+.5)*h;i?c.lineTo(px,py):c.moveTo(px,py)});c.strokeStyle=color;c.lineWidth=2;c.stroke();}
    draw(){const c=this.ctx,w=this.canvas.width,h=this.canvas.height;c.fillStyle='#05070d';c.fillRect(0,0,w,h);c.fillStyle='#10182a';c.fillRect(0,0,w,62);c.fillStyle='#ecf4ff';c.font='600 22px monospace';c.fillText('FLY BRAIN // LIVE CONNECTOME',28,39);c.fillStyle='#37efb4';c.font='14px monospace';c.fillText(this.frame?'STREAMING':'STANDBY',850,38);
      c.strokeStyle='#1b2a3e';c.lineWidth=1;for(let i=0;i<7;i++){const y=88+i*55;c.beginPath();c.moveTo(28,y);c.lineTo(730,y);c.stroke()}
      this.line(this.history.lc4,28,92,700,86,'#4fd1e8');this.line(this.history.lplc2,28,195,700,86,'#f5a623');this.line(this.history.dnp01,28,298,700,86,'#ff4d6d');this.line(this.history.steer,28,410,700,90,'#9b7cff');
      c.font='13px monospace';c.fillStyle='#4fd1e8';c.fillText('LC4',38,112);c.fillStyle='#f5a623';c.fillText('LPLC2',38,215);c.fillStyle='#ff4d6d';c.fillText('DNp01',38,318);c.fillStyle='#9b7cff';c.fillText('DNa02 Δ',38,430);
      c.fillStyle='#0d1422';c.fillRect(760,92,238,408);c.fillStyle='#7d8da8';c.font='13px monospace';const f=this.frame,n=f&&f.neural;c.fillText('BEHAVIOUR',786,126);c.fillStyle='#ffffff';c.font='600 18px monospace';c.fillText(f?f.body.behaviour.toUpperCase():'IDLE',786,153);c.fillStyle='#7d8da8';c.font='13px monospace';c.fillText('ACTIVE NEURONS',786,205);c.fillStyle='#ffffff';c.font='600 23px monospace';c.fillText(n?String(n.active_neurons):'0',786,235);c.fillStyle='#7d8da8';c.font='13px monospace';c.fillText('DISTANCE',786,287);c.fillStyle='#ffffff';c.font='600 20px monospace';c.fillText(f?f.observation.distance_cm.toFixed(1)+' cm':'—',786,316);c.fillStyle='#7d8da8';c.font='13px monospace';c.fillText('BEARING',786,367);c.fillStyle='#ffffff';c.font='600 20px monospace';c.fillText(f?f.observation.azimuth_deg.toFixed(1)+'°':'—',786,396);c.fillStyle=f&&f.escaped?'#37efb4':'#64748b';c.font='600 18px monospace';c.fillText(f&&f.escaped?'ESCAPE COMPLETE':'CLOSED LOOP',786,465);this.texture.needsUpdate=true;}
  }
  Lab.NeuralMonitor=NeuralMonitor;
})(window);
