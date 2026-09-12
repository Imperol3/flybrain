(function(global){
  const Lab=global.FlyLab=global.FlyLab||{};
  class ArenaWorld{
    constructor(scene){this.scene=scene;this.trail=[];this._build();}
    _build(){
      const hemi=new THREE.HemisphereLight(0x9ec6d5,0x170e08,.62);this.scene.add(hemi);
      const key=new THREE.DirectionalLight(0xffe3bf,1.45);key.position.set(-9,17,8);key.castShadow=true;key.shadow.mapSize.set(2048,2048);this.scene.add(key);
      const rim=new THREE.PointLight(0x4fd1e8,1.5,28);rim.position.set(9,5,-6);this.scene.add(rim);
      const floor=new THREE.Mesh(new THREE.CircleGeometry(17,80),new THREE.MeshStandardMaterial({color:0x11181b,roughness:.97}));floor.rotation.x=-Math.PI/2;floor.receiveShadow=true;this.scene.add(floor);
      const grid=new THREE.GridHelper(28,14,0x294851,0x1b2c31);grid.position.y=.012;grid.material.transparent=true;grid.material.opacity=.2;this.scene.add(grid);
      const wallMat=new THREE.MeshPhysicalMaterial({color:0x507889,transparent:true,opacity:.045,side:THREE.DoubleSide,depthWrite:false});
      const wall=(x,y,z,ry)=>{const m=new THREE.Mesh(new THREE.PlaneGeometry(13.2,5),wallMat);m.position.set(x,y,z);m.rotation.y=ry;this.scene.add(m)};
      wall(0,2.5,6.6,0);wall(-6.6,2.5,0,Math.PI/2);wall(6.6,2.5,0,-Math.PI/2);
      const frameMat=new THREE.MeshStandardMaterial({color:0x2d956d,emissive:0x0b3023});const piece=(x,y,z,sx,sy,sz)=>{const p=new THREE.Mesh(new THREE.BoxGeometry(sx,sy,sz),frameMat);p.position.set(x,y,z);p.castShadow=true;this.scene.add(p)};
      piece(-2.2,1.25,-6.6,.12,2.5,.14);piece(2.2,1.25,-6.6,.12,2.5,.14);piece(0,2.5,-6.6,4.5,.12,.14);
      this.exitGlow=new THREE.PointLight(0x58d68d,1.8,8);this.exitGlow.position.set(0,1.5,-6.9);this.scene.add(this.exitGlow);
      this.threat=new THREE.Group();const core=new THREE.Mesh(new THREE.SphereGeometry(.42,24,16),new THREE.MeshPhysicalMaterial({color:0x090d0f,roughness:.22}));core.castShadow=true;this.threat.add(core);const ring=new THREE.Mesh(new THREE.TorusGeometry(.58,.025,8,48),new THREE.MeshBasicMaterial({color:0xff4d6d,transparent:true,opacity:.8}));ring.rotation.x=Math.PI/2;this.threat.add(ring);this.scene.add(this.threat);
      this.trailGeometry=new THREE.BufferGeometry();this.trailPositions=new Float32Array(1200);this.trailGeometry.setAttribute('position',new THREE.BufferAttribute(this.trailPositions,3));this.trailGeometry.setDrawRange(0,0);this.trailLine=new THREE.Line(this.trailGeometry,new THREE.LineBasicMaterial({color:0x4fd1e8,transparent:true,opacity:.7}));this.scene.add(this.trailLine);
    }
    updateThreat(t){if(t)this.threat.position.lerp(new THREE.Vector3(t.x_cm*.55,.65+t.y_cm*.15,t.z_cm*.55),.35);}
    resetTrail(){this.trail.length=0;this.trailGeometry.setDrawRange(0,0);}
    addTrail(body){if(!body||this.trail.length>=400)return;const p=new THREE.Vector3(body.x_cm*.55,.03,body.z_cm*.55);if(this.trail.length&&this.trail[this.trail.length-1].distanceToSquared(p)<.008)return;this.trail.push(p);const i=(this.trail.length-1)*3;this.trailPositions[i]=p.x;this.trailPositions[i+1]=p.y;this.trailPositions[i+2]=p.z;this.trailGeometry.setDrawRange(0,this.trail.length);this.trailGeometry.attributes.position.needsUpdate=true;}
    update(time){this.exitGlow.intensity=1.35+Math.sin(time*2.4)*.35;this.threat.rotation.y=time*.8;}
  }
  Lab.ArenaWorld=ArenaWorld;
})(window);
