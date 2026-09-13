(function(global){
  const Lab=global.FlyLab=global.FlyLab||{};
  class LabEnvironment{
    constructor(scene){this.scene=scene;this.mode='lab';this.lab=new THREE.Group();this.arena=new THREE.Group();scene.add(this.lab,this.arena);this._lights();this._buildLab();this._buildArena();this._buildThreat();this.setMode('lab');}
    material(color,roughness=.72,metalness=.08,emissive=0){return new THREE.MeshStandardMaterial({color,roughness,metalness,emissive});}
    box(parent,size,pos,material,rotation=[0,0,0]){const m=new THREE.Mesh(new THREE.BoxGeometry(...size),material);m.position.set(...pos);m.rotation.set(...rotation);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;}
    _lights(){
      this.scene.add(new THREE.HemisphereLight(0x17243a,0x050307,.28));
      const cyan=new THREE.PointLight(0x39d8ff,2.4,24);cyan.position.set(0,5.7,-3);this.scene.add(cyan);
      const magenta=new THREE.PointLight(0xff286c,1.8,14);magenta.position.set(-5,2.2,1);this.scene.add(magenta);
      const key=new THREE.SpotLight(0xc6e8ff,3.8,24,.62,.55,1.2);key.position.set(-3,8,5);key.target.position.set(0,0,0);key.castShadow=true;key.shadow.mapSize.set(2048,2048);this.scene.add(key,key.target);
      const monitorGlow=new THREE.PointLight(0x315dff,2.2,10);monitorGlow.position.set(3.4,2.6,-4.2);this.scene.add(monitorGlow);
    }
    _buildLab(){
      const dark=this.material(0x080b13,.78,.3),desk=this.material(0x101722,.6,.35),edge=this.material(0x101c25,.45,.5,0x0a7180),panel=this.material(0x0b101a,.72,.18),metal=this.material(0x1b2632,.38,.72);
      this.box(this.lab,[22,.65,15],[0,-.42,0],desk);this.box(this.lab,[22,.12,.08],[0,-.05,-7.45],edge);this.box(this.lab,[.08,.12,15],[-10.95,-.05,0],edge);this.box(this.lab,[.08,.12,15],[10.95,-.05,0],edge);
      this.box(this.lab,[22,9,.5],[0,4.1,-8],dark);this.box(this.lab,[.5,9,16],[-11,4.1,0],dark);this.box(this.lab,[.5,9,16],[11,4.1,0],dark);
      for(let x=-9.5;x<=9.5;x+=1.15){for(let y=.5;y<=7.5;y+=.65){if(Math.random()>.48){const c=Math.random()>.7?0xff315f:0x27d9ff;const dot=this.box(this.lab,[.035,.16,.06],[x,y,-7.72],new THREE.MeshBasicMaterial({color:c,transparent:true,opacity:.3+Math.random()*.5}));dot.position.x+=Math.random()*.35}}}
      // desk seams and illuminated work rails
      for(let z=-6;z<=6;z+=3){this.box(this.lab,[21.4,.018,.012],[0,-.065,z],new THREE.MeshBasicMaterial({color:0x284052,transparent:true,opacity:.42}));}
      this.box(this.lab,[7.2,.08,.05],[-3.1,-.02,1.7],new THREE.MeshBasicMaterial({color:0x28d7e8}));this.box(this.lab,[4.2,.08,.05],[5.2,-.02,-.4],new THREE.MeshBasicMaterial({color:0xff2767}));
      // monitor mount and articulated arm
      this.monitorMount=new THREE.Group();this.monitorMount.position.set(3.9,2.55,-4.9);this.monitorMount.rotation.y=-.18;this.lab.add(this.monitorMount);
      this.box(this.lab,[.22,2.2,.22],[5.65,1.02,-5.4],metal);this.box(this.lab,[2.1,.16,.16],[4.7,2.05,-5.35],metal,[0,.1,-.22]);
      // keyboard
      this.box(this.lab,[4.3,.18,1.45],[2.8,.05,-1.95],panel,[-.08,0,0]);
      const keyMat=this.material(0x182230,.75,.2);for(let r=0;r<4;r++)for(let c=0;c<13;c++)this.box(this.lab,[.24,.08,.19],[1.35+c*.245,.19-r*.008,-2.38+r*.3],keyMat,[-.08,0,0]);
      // terminal blocks
      this.box(this.lab,[2.2,.72,1.5],[-6.5,.34,-4.9],metal);this.box(this.lab,[1.95,.12,.08],[-6.5,.48,-4.12],new THREE.MeshBasicMaterial({color:0x27d9ff}));
      for(let i=0;i<4;i++){const led=new THREE.Mesh(new THREE.CircleGeometry(.055,12),new THREE.MeshBasicMaterial({color:i===3?0xff315f:0x47efc0}));led.position.set(-7.1+i*.42,.55,-4.08);led.rotation.x=-Math.PI/2;this.lab.add(led)}
      // mug and handle
      const mugMat=this.material(0x251629,.5,.2);const mug=new THREE.Mesh(new THREE.CylinderGeometry(.42,.36,.72,24,1,true),mugMat);mug.position.set(6.6,.36,-1.25);mug.castShadow=true;this.lab.add(mug);const handle=new THREE.Mesh(new THREE.TorusGeometry(.29,.065,8,22,Math.PI*1.55),mugMat);handle.position.set(7.02,.4,-1.25);handle.rotation.y=Math.PI/2;this.lab.add(handle);
      // cables
      this._cable([[-1,.03,2.4],[.4,.08,2.1],[1.1,.06,.8],[2.4,.05,-.6]],0x10141a,.045,this.lab);this._cable([[5.7,.1,-4.6],[6.4,.05,-3.6],[5.9,.04,-2.4],[4.8,.05,-1.8]],0x3b1326,.035,this.lab);
      // data pedestal near fly
      this.box(this.lab,[1.7,.06,1.05],[-2.6,.02,-.4],panel);this.box(this.lab,[1.3,.025,.045],[-2.6,.06,-.88],new THREE.MeshBasicMaterial({color:0x25d6ef}));
      this._dust();
    }
    _buildArena(){
      const floor=this.material(0x0c1319,.92,.08),wall=new THREE.MeshPhysicalMaterial({color:0x2d6476,transparent:true,opacity:.08,roughness:.18,side:THREE.DoubleSide,depthWrite:false});
      const f=new THREE.Mesh(new THREE.CircleGeometry(9,64),floor);f.rotation.x=-Math.PI/2;f.receiveShadow=true;this.arena.add(f);const grid=new THREE.GridHelper(16,16,0x1e7788,0x17323b);grid.material.transparent=true;grid.material.opacity=.28;this.arena.add(grid);
      const plane=(x,y,z,ry)=>{const p=new THREE.Mesh(new THREE.PlaneGeometry(13.2,5),wall);p.position.set(x,y,z);p.rotation.y=ry;this.arena.add(p)};plane(0,2.5,6.6,0);plane(-6.6,2.5,0,Math.PI/2);plane(6.6,2.5,0,-Math.PI/2);
      const frame=this.material(0x1d8d68,.42,.55,0x0a3125);this.box(this.arena,[.14,2.8,.16],[-2.2,1.4,-6.6],frame);this.box(this.arena,[.14,2.8,.16],[2.2,1.4,-6.6],frame);this.box(this.arena,[4.5,.14,.16],[0,2.8,-6.6],frame);
    }
    _buildThreat(){this.threat=new THREE.Group();const core=new THREE.Mesh(new THREE.SphereGeometry(.38,20,14),new THREE.MeshPhysicalMaterial({color:0x080b0d,roughness:.18,clearcoat:.7}));core.castShadow=true;this.threat.add(core);const ring=new THREE.Mesh(new THREE.TorusGeometry(.55,.024,7,48),new THREE.MeshBasicMaterial({color:0xff3b75}));ring.rotation.x=Math.PI/2;this.threat.add(ring);this.scene.add(this.threat);}
    _cable(points,color,radius,parent){const curve=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p)));const mesh=new THREE.Mesh(new THREE.TubeGeometry(curve,40,radius,6,false),this.material(color,.78,.1));mesh.castShadow=true;parent.add(mesh);}
    _dust(){const count=420,a=new Float32Array(count*3);for(let i=0;i<count;i++){a[i*3]=(Math.random()-.5)*20;a[i*3+1]=Math.random()*7;a[i*3+2]=(Math.random()-.5)*14}const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(a,3));this.dust=new THREE.Points(g,new THREE.PointsMaterial({color:0x93dfff,size:.018,transparent:true,opacity:.25,depthWrite:false}));this.lab.add(this.dust);}
    setMode(mode){this.mode=mode;this.lab.visible=mode==='lab';this.arena.visible=mode==='arena';}
    updateThreat(t){if(t)this.threat.position.lerp(new THREE.Vector3(t.x_cm*.55,.45+t.y_cm*.15,t.z_cm*.55),.32);}
    monitorWorldPosition(){const p=new THREE.Vector3();this.monitorMount&&this.monitorMount.getWorldPosition(p);return p;}
    update(time){if(this.dust){this.dust.rotation.y=time*.002;this.dust.position.y=Math.sin(time*.15)*.08}this.threat.rotation.y=time*.9;}
  }
  Lab.LabEnvironment=LabEnvironment;
})(window);
