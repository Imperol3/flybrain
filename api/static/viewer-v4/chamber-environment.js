(function(){
  const Lab=window.FlyLab=window.FlyLab||{},S=.55;
  class ChamberEnvironment{
    constructor(scene){
      this.scene=scene;this.group=new THREE.Group();scene.add(this.group);this.trail=[];this.trailGeometry=new THREE.BufferGeometry();
      this.trailLine=new THREE.Line(this.trailGeometry,new THREE.LineBasicMaterial({color:0x31e7ff,transparent:true,opacity:.72}));this.group.add(this.trailLine);
      this.sensorGroup=new THREE.Group();this.group.add(this.sensorGroup);this.sensorLines=[];this._build();
    }
    _mesh(geometry,material,x,y,z){const m=new THREE.Mesh(geometry,material);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;this.group.add(m);return m}
    _box(x,y,z,color,emissive=0){return this._mesh(new THREE.BoxGeometry(x,y,z),new THREE.MeshStandardMaterial({color,roughness:.6,metalness:.25,emissive,emissiveIntensity:emissive?1.2:0}),0,0,0)}
    _build(){
      const floorMat=new THREE.MeshStandardMaterial({color:0x07101a,roughness:.72,metalness:.32});this.floor=this._mesh(new THREE.PlaneGeometry(17,17,32,32),floorMat,0,.02,-1.1);this.floor.rotation.x=-Math.PI/2;
      const grid=new THREE.GridHelper(17,28,0x17485a,0x10293a);grid.position.set(0,.035,-1.1);grid.material.transparent=true;grid.material.opacity=.48;this.group.add(grid);
      const wallMat=new THREE.MeshStandardMaterial({color:0x121b29,roughness:.42,metalness:.55});
      const sideL=this._mesh(new THREE.BoxGeometry(.35,4.4,15.5),wallMat,-7.85,2.2,-1.1),sideR=sideL.clone();sideR.position.x=7.85;this.group.add(sideR);
      const south=this._mesh(new THREE.BoxGeometry(16,4.4,.35),wallMat,0,2.2,6.75);
      const northZ=-9.0,exitX=-5.5,exitHalf=1.32;
      const leftWidth=7.85+(exitX-exitHalf),rightStart=exitX+exitHalf,rightWidth=7.85-rightStart;
      const left=this._mesh(new THREE.BoxGeometry(leftWidth,4.4,.35),wallMat,-7.85+leftWidth/2,2.2,northZ);
      const right=this._mesh(new THREE.BoxGeometry(rightWidth,4.4,.35),wallMat,rightStart+rightWidth/2,2.2,northZ);
      const frameMat=new THREE.MeshStandardMaterial({color:0x0e3f4b,emissive:0x19dbff,emissiveIntensity:2.3,metalness:.7,roughness:.22});
      this._mesh(new THREE.BoxGeometry(.16,4.5,.45),frameMat,exitX-exitHalf,2.2,northZ);this._mesh(new THREE.BoxGeometry(.16,4.5,.45),frameMat,exitX+exitHalf,2.2,northZ);this._mesh(new THREE.BoxGeometry(exitHalf*2+.3,.18,.45),frameMat,exitX,4.4,northZ);
      this.exitGlow=this._mesh(new THREE.PlaneGeometry(exitHalf*2.05,4.1),new THREE.MeshBasicMaterial({color:0x21e6ff,transparent:true,opacity:.10,side:THREE.DoubleSide}),exitX,2.1,northZ-.2);
      this.exitGlow.rotation.y=Math.PI;
      [[0,-1.8,2.15,'column'],[-7.4,-7.4,1.65,'column'],[5.8,-9.2,2,'column'],[7,3.7,1.45,'equipment']].forEach(([x,z,r,kind])=>this._obstacle(x*S,z*S,r*S,kind));
      const ceiling=new THREE.HemisphereLight(0x74d9ff,0x05070c,1.25);this.scene.add(ceiling);
      const key=new THREE.SpotLight(0x64dfff,26,32,Math.PI/4,.55,1.5);key.position.set(4,10,3);key.target.position.set(-1,0,-2);key.castShadow=true;this.scene.add(key,key.target);
      const magenta=new THREE.PointLight(0xff245f,8,18,2);magenta.position.set(-7,2,-7);this.scene.add(magenta);
      const exitLight=new THREE.PointLight(0x25eaff,9,12,2);exitLight.position.set(exitX,2,northZ+1);this.scene.add(exitLight);this.exitLight=exitLight;
      const threatMat=new THREE.MeshPhysicalMaterial({color:0x07080c,roughness:.12,metalness:.65,clearcoat:1,emissive:0x320016,emissiveIntensity:1.3});this.threat=this._mesh(new THREE.SphereGeometry(.62,32,20),threatMat,0,.75,6);
      this.threatRing=this._mesh(new THREE.TorusGeometry(.78,.035,8,42),new THREE.MeshBasicMaterial({color:0xff3b77,transparent:true,opacity:.75}),0,.08,6);this.threatRing.rotation.x=-Math.PI/2;
      const dustGeo=new THREE.BufferGeometry(),dust=[];for(let i=0;i<420;i++)dust.push((Math.random()-.5)*16,Math.random()*5,(Math.random()-.5)*16-1);dustGeo.setAttribute('position',new THREE.Float32BufferAttribute(dust,3));this.dust=new THREE.Points(dustGeo,new THREE.PointsMaterial({color:0x50cce5,size:.018,transparent:true,opacity:.32}));this.group.add(this.dust);
      for(let i=0;i<3;i++){const g=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3()]);const line=new THREE.Line(g,new THREE.LineBasicMaterial({color:i?0xffc04a:0x31e7ff,transparent:true,opacity:.72}));this.sensorGroup.add(line);this.sensorLines.push(line)}
    }
    _obstacle(x,z,r,kind){
      const h=kind==='equipment'?2.6:3.5,geo=kind==='equipment'?new THREE.BoxGeometry(r*1.5,h,r*1.5):new THREE.CylinderGeometry(r,r*.9,h,28);
      const mat=new THREE.MeshStandardMaterial({color:kind==='equipment'?0x20283a:0x172532,roughness:.38,metalness:.68,emissive:0x071a24,emissiveIntensity:.8});const m=this._mesh(geo,mat,x,h/2,z);
      const ring=this._mesh(new THREE.TorusGeometry(r*1.05,.035,8,32),new THREE.MeshBasicMaterial({color:0xf23f77,transparent:true,opacity:.5}),x,.07,z);ring.rotation.x=-Math.PI/2;return m
    }
    configure(chamber){if(!chamber)return;this.chamber=chamber}
    updateFrame(frame,avatar){
      if(!frame)return;this.updateThreat(frame.threat);
      const p=new THREE.Vector3(frame.body.x_cm*S,.12,frame.body.z_cm*S);if(!this.trail.length||p.distanceTo(this.trail[this.trail.length-1])>.12){this.trail.push(p);if(this.trail.length>500)this.trail.shift();this.trailGeometry.setFromPoints(this.trail)}
      const n=frame.navigation;if(n){const heading=frame.body.heading_rad;const values=[n.forward_clearance_cm,n.left_clearance_cm,n.right_clearance_cm],angles=[heading,heading+Math.PI/3,heading-Math.PI/3];this.sensorLines.forEach((line,i)=>{const start=new THREE.Vector3(frame.body.x_cm*S,.28,frame.body.z_cm*S),d=Math.max(.1,values[i])*S,end=new THREE.Vector3(start.x-Math.sin(angles[i])*d,.28,start.z-Math.cos(angles[i])*d);line.geometry.setFromPoints([start,end]);line.material.color.setHex(values[i]<3.4?0xff416f:(i?0xffb44a:0x31e7ff))})}
      this.threatRing.position.x=this.threat.position.x;this.threatRing.position.z=this.threat.position.z;
    }
    updateThreat(threat){if(!threat)return;this.threat.position.set(threat.x_cm*S,.72+threat.y_cm*.08,threat.z_cm*S);this.threat.scale.setScalar(Math.max(.6,threat.radius_cm*.58))}
    reset(){this.trail=[];this.trailGeometry.setFromPoints([])}
    update(time,frame){this.exitGlow.material.opacity=.08+Math.sin(time*3)*.035;this.exitLight.intensity=8+Math.sin(time*4)*2;this.threatRing.rotation.z=time*.7;this.threatRing.scale.setScalar(1+Math.sin(time*5)*.08);this.dust.rotation.y=time*.008;if(frame&&frame.captured)this.threat.material.emissiveIntensity=4}
  }
  Lab.ChamberEnvironment=ChamberEnvironment;
})();
