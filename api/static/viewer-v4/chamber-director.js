(function(){
  const Lab=window.FlyLab=window.FlyLab||{};
  class ChamberDirector{
    constructor(camera,avatar,environment,label){this.camera=camera;this.avatar=avatar;this.environment=environment;this.label=label;this.mode='auto';this.frame=null;this.current='overview';this.camera.position.set(12,12,14);this.look=new THREE.Vector3(0,0,-2)}
    setFrame(frame){this.frame=frame;if(this.mode!=='auto')return;const b=frame.body||{},n=frame.navigation||{};let shot='follow';if(frame.done)shot='result';else if(b.behaviour==='takeoff')shot='takeoff';else if(n.forward_clearance_cm<3.4)shot='collision';else if(frame.elapsed_ms<700)shot='overview';this.current=shot;if(this.label)this.label.textContent=shot.toUpperCase()}
    setMode(mode){this.mode=mode;if(mode!=='auto')this.current=mode}
    update(dt){const f=this.frame,b=f&&f.body?f.body:{x_cm:0,y_cm:0,z_cm:4,heading_rad:0},p=new THREE.Vector3(b.x_cm*.55,.45+b.y_cm*.55,b.z_cm*.55),desired=new THREE.Vector3(),target=p.clone();let shot=this.mode==='auto'?this.current:this.mode;
      if(shot==='overhead'||shot==='overview')desired.set(0,16,1.5),target.set(0,0,-1.5);
      else if(shot==='takeoff')desired.copy(p).add(new THREE.Vector3(4,2.4,5));
      else if(shot==='collision')desired.copy(p).add(new THREE.Vector3(-3,2.3,3));
      else if(shot==='result')desired.copy(p).add(new THREE.Vector3(5,4.5,6));
      else{const h=b.heading_rad;desired.copy(p).add(new THREE.Vector3(Math.sin(h)*4,2.4,Math.cos(h)*5));target.copy(p).add(new THREE.Vector3(-Math.sin(h)*2,.2,-Math.cos(h)*2))}
      const k=1-Math.pow(.002,dt);this.camera.position.lerp(desired,k);this.look.lerp(target,k);this.camera.lookAt(this.look)
    }
  }
  Lab.ChamberDirector=ChamberDirector;
})();
