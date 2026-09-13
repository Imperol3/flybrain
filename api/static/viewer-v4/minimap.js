(function(){
  const Lab=window.FlyLab=window.FlyLab||{};
  class ChamberMap{
    constructor(canvas){this.canvas=canvas;this.ctx=canvas.getContext('2d');this.frame=null;this.path=[]}
    reset(){this.path=[];this.frame=null;this.draw()}
    push(frame){this.frame=frame;if(frame&&frame.body){const p=[frame.body.x_cm,frame.body.z_cm];if(!this.path.length||Math.hypot(p[0]-this.path.at(-1)[0],p[1]-this.path.at(-1)[1])>.15)this.path.push(p)}this.draw()}
    draw(){const c=this.canvas,x=c.getContext('2d'),w=c.width,h=c.height;x.clearRect(0,0,w,h);x.fillStyle='#050a12';x.fillRect(0,0,w,h);const f=this.frame,ch=f&&f.chamber;if(!ch){x.fillStyle='#607089';x.font='11px monospace';x.fillText('WAITING FOR WORLD',18,30);return}const sx=w/(ch.half_width_cm*2+4),sz=h/(ch.south_z_cm-ch.north_z_cm+4),px=v=>(v+ch.half_width_cm+2)*sx,pz=v=>(v-ch.north_z_cm+2)*sz;
      x.strokeStyle='#294154';x.lineWidth=2;x.strokeRect(px(-ch.half_width_cm),pz(ch.north_z_cm),ch.half_width_cm*2*sx,(ch.south_z_cm-ch.north_z_cm)*sz);
      x.strokeStyle='#27e8ff';x.lineWidth=5;x.beginPath();x.moveTo(px(ch.exit_x_cm-ch.exit_half_width_cm),pz(ch.north_z_cm));x.lineTo(px(ch.exit_x_cm+ch.exit_half_width_cm),pz(ch.north_z_cm));x.stroke();
      x.fillStyle='#223344';for(const o of ch.obstacles){x.beginPath();x.arc(px(o.x_cm),pz(o.z_cm),o.radius_cm*Math.min(sx,sz),0,Math.PI*2);x.fill()}
      if(this.path.length>1){x.strokeStyle='#29dff5';x.lineWidth=1.5;x.beginPath();this.path.forEach((p,i)=>i?x.lineTo(px(p[0]),pz(p[1])):x.moveTo(px(p[0]),pz(p[1])));x.stroke()}
      if(f.threat){x.fillStyle='#ff376f';x.beginPath();x.arc(px(f.threat.x_cm),pz(f.threat.z_cm),5,0,Math.PI*2);x.fill()}
      if(f.body){x.save();x.translate(px(f.body.x_cm),pz(f.body.z_cm));x.rotate(-f.body.heading_rad);x.fillStyle='#eef8ff';x.beginPath();x.moveTo(0,-7);x.lineTo(5,6);x.lineTo(-5,6);x.closePath();x.fill();x.restore()}
    }
  }
  Lab.ChamberMap=ChamberMap;
})();
