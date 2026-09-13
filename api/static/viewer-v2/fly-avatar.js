(function(global){
  const Lab=global.FlyLab=global.FlyLab||{};
  const V=new THREE.Vector3();

  class FlyAvatar{
    constructor(scene){
      this.root=new THREE.Group();this.root.name='FlyAvatar';scene.add(this.root);
      this.visual=new THREE.Group();this.visual.scale.setScalar(.46);this.root.add(this.visual);
      this.legs=[];this.wings=[];this.antennae=[];this.behaviour='idle';this.speed=0;this.elapsed=0;this.groundY=1.05;
      this.materials={
        thorax:new THREE.MeshPhysicalMaterial({color:0x6a3818,roughness:.82,clearcoat:.06}),
        abdomen:new THREE.MeshPhysicalMaterial({color:0x26130a,roughness:.86}),
        dark:new THREE.MeshStandardMaterial({color:0x100907,roughness:.9}),
        eye:new THREE.MeshPhysicalMaterial({color:0x73091b,roughness:.52,clearcoat:.3,flatShading:true}),
        wing:new THREE.MeshPhysicalMaterial({color:0xcce9e7,transparent:true,opacity:.25,roughness:.08,side:THREE.DoubleSide,depthWrite:false}),
        vein:new THREE.LineBasicMaterial({color:0x6f4a32,transparent:true,opacity:.52}),
      };
      this._build();
    }

    mesh(geometry,material,position,scale,parent=this.visual){
      const m=new THREE.Mesh(geometry,material);m.position.set(...position);m.scale.set(...scale);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;
    }

    ellipsoid(radius,position,scale,material,segments=28,parent=this.visual){
      return this.mesh(new THREE.SphereGeometry(radius,segments,Math.max(10,segments/2)),material,position,scale,parent);
    }

    cylinderBetween(a,b,r,material,parent=this.visual){
      const d=V.subVectors(b,a).clone(),mid=a.clone().add(b).multiplyScalar(.5);
      const mesh=new THREE.Mesh(new THREE.CylinderGeometry(r,r*.72,d.length(),8),material);
      mesh.position.copy(mid);mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),d.normalize());mesh.castShadow=true;parent.add(mesh);return mesh;
    }

    _build(){
      const M=this.materials;
      this.thorax=this.ellipsoid(1,[0,0,0],[1.12,.96,1.25],M.thorax);
      this.abdomen=this.ellipsoid(1,[0,-.08,2.38],[.86,.66,2.14],M.abdomen);
      this.head=this.ellipsoid(1,[0,.08,-1.62],[.98,.86,.8],M.thorax);
      this.ellipsoid(.64,[-.77,.17,-1.84],[.61,.92,.72],M.eye,12);
      this.ellipsoid(.64,[.77,.17,-1.84],[.61,.92,.72],M.eye,12);
      [-.18,0,.18].forEach((x,i)=>this.ellipsoid(.065,[x,.82,-2.02],[1,1,.65],new THREE.MeshBasicMaterial({color:i===1?0xffd65a:0xff9d26}),8));
      this.ellipsoid(.64,[0,.84,.02],[.62,.16,1.22],M.dark,20);

      [1.16,1.82,2.46,3.05,3.55].forEach((z,i)=>{
        const band=new THREE.Mesh(new THREE.TorusGeometry(.77-i*.073,.052,8,32),M.dark);band.scale.y=.72;band.position.set(0,-.08,z);this.visual.add(band);
      });

      this.brainAnchor=new THREE.Group();this.brainAnchor.position.set(0,.14,-1.62);this.visual.add(this.brainAnchor);
      this.brainShell=this.ellipsoid(.68,[0,0,0],[.88,.62,.66],new THREE.MeshBasicMaterial({color:0x4fd1e8,wireframe:true,transparent:true,opacity:.16}),18,this.brainAnchor);

      [-1,1].forEach(side=>{
        const antenna=new THREE.Group();antenna.position.set(side*.38,.62,-2.28);this.visual.add(antenna);
        this.cylinderBetween(new THREE.Vector3(),new THREE.Vector3(side*.18,.28,-.5),.045,M.dark,antenna);
        this.cylinderBetween(new THREE.Vector3(side*.18,.28,-.5),new THREE.Vector3(side*.58,.48,-.9),.018,M.dark,antenna);
        this.antennae.push({pivot:antenna,side});
      });
      this.cylinderBetween(new THREE.Vector3(0,-.38,-2.28),new THREE.Vector3(0,-.68,-2.86),.06,M.dark);

      this._buildWing(-1);this._buildWing(1);
      [-1,1].forEach(side=>{this._buildLeg(side,-.58,0);this._buildLeg(side,.04,2.1);this._buildLeg(side,.62,4.2);this.ellipsoid(.13,[side*.9,.32,.92],[1,.86,1],M.thorax,10)});
      [[-.44,.7,-.42],[.44,.7,-.42],[-.5,.72,.22],[.5,.72,.22],[-.34,.52,1.35],[.34,.52,1.35]].forEach((p,i)=>this.cylinderBetween(new THREE.Vector3(...p),new THREE.Vector3(p[0]+(i%2?.11:-.11),p[1]+.46,p[2]-.08),.016,M.dark));
    }

    _buildWing(side){
      const pivot=new THREE.Group();pivot.position.set(side*.55,.61,.22);pivot.rotation.z=side*.14;this.visual.add(pivot);
      const s=new THREE.Shape();s.moveTo(0,0);s.bezierCurveTo(side*1.1,.18,side*2.9,.35,side*4.25,.2);s.bezierCurveTo(side*4.05,-.55,side*2.3,-1.12,0,0);
      const wing=new THREE.Mesh(new THREE.ShapeGeometry(s,26),this.materials.wing);wing.rotation.x=-Math.PI/2;wing.castShadow=true;pivot.add(wing);
      [[[0,0],[side*3.7,-.1]],[[side*.58,-.12],[side*2.9,-.65]],[[side*1.45,-.2],[side*2.25,-.87]],[[side*2.18,-.13],[side*3.48,-.38]]].forEach(v=>{
        const g=new THREE.BufferGeometry().setFromPoints(v.map(p=>new THREE.Vector3(p[0],p[1],.008)));const line=new THREE.Line(g,this.materials.vein);line.rotation.x=-Math.PI/2;pivot.add(line);
      });
      this.wings.push({pivot,side});
    }

    _buildLeg(side,z,phase){
      const hip=new THREE.Group();hip.position.set(side*.68,-.42,z);this.visual.add(hip);
      const knee=new THREE.Vector3(side*.72,-.32,z<0?-.5:.18),ankle=new THREE.Vector3(side*1.18,-.92,z<0?-1.05:.9),foot=new THREE.Vector3(side*1.56,-1.08,z<0?-1.38:1.3);
      this.cylinderBetween(new THREE.Vector3(),knee,.052,this.materials.dark,hip);this.cylinderBetween(knee,ankle,.038,this.materials.dark,hip);this.cylinderBetween(ankle,foot,.022,this.materials.dark,hip);
      this.legs.push({pivot:hip,side,phase});
    }

    setBrainVisible(visible){this.brainAnchor.visible=visible;}
    setTargetPose(body){this.targetBody=body;this.behaviour=body.behaviour||'idle';this.speed=body.speed_cm_s||0;}

    update(dt,time){
      this.elapsed+=dt;
      if(this.targetBody){
        const scale=.55,target=new THREE.Vector3(this.targetBody.x_cm*scale,this.groundY+this.targetBody.y_cm*scale,this.targetBody.z_cm*scale);
        this.root.position.lerp(target,1-Math.pow(.0005,dt));
        const q=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),this.targetBody.heading_rad);
        this.root.quaternion.slerp(q,1-Math.pow(.001,dt));
      }
      const airborne=this.behaviour==='takeoff'||this.behaviour==='escaping'||this.behaviour==='escaped';
      const moving=this.speed>.2;const gait=time*(moving?10+this.speed*.6:1.2);
      this.legs.forEach(l=>{l.pivot.rotation.x=Math.sin(gait+l.phase)*(.04+(moving?.22:0));l.pivot.rotation.z=l.side*(moving?.05:0)});
      const flap=airborne?Math.sin(time*78)*.72:Math.sin(time*2.2)*.025;
      this.wings.forEach(w=>{w.pivot.rotation.z=w.side*(.14+flap);w.pivot.rotation.x=airborne?Math.sin(time*39)*.12:0});
      this.antennae.forEach(a=>a.pivot.rotation.x=Math.sin(time*2.6+a.side)*.035);
      this.visual.position.y=Math.sin(time*(moving?14:2.1))*(moving?.04:.018);
    }
  }
  Lab.FlyAvatar=FlyAvatar;
})(window);
