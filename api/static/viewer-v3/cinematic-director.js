(function(global){
  const Lab=global.FlyLab=global.FlyLab||{};
  class CinematicDirector{
    constructor(camera,avatar,environment,label){this.camera=camera;this.avatar=avatar;this.environment=environment;this.label=label;this.frame=null;this.shot='establishing';this.changedAt=0;this.auto=true;}
    setFrame(frame){this.frame=frame;if(!this.auto||!frame)return;const n=frame.neural||{},b=frame.body.behaviour;let next='establishing';if(frame.escaped)next='victory';else if(b==='takeoff'||b==='escaping')next='chase';else if(b&&b.startsWith('orienting'))next='overhead';else if((n.lc4_spikes||0)+(n.lplc2_spikes||0)>0)next=(frame.elapsed_ms%700<350?'brain':'monitor');if(next!==this.shot&&performance.now()-this.changedAt>450){this.shot=next;this.changedAt=performance.now();this.label.textContent=next.toUpperCase().replace('_',' ');}}
    update(dt){const fly=this.avatar.root.position.clone(),monitor=this.environment.monitorWorldPosition();let pos,target=fly.clone().add(new THREE.Vector3(0,.25,0));
      if(this.shot==='brain'){pos=fly.clone().add(new THREE.Vector3(2.1,1.55,2.8));target=fly.clone().add(new THREE.Vector3(0,.35,0));}
      else if(this.shot==='monitor'&&this.environment.mode==='lab'){pos=monitor.clone().add(new THREE.Vector3(0,.2,5.8));target=monitor;}
      else if(this.shot==='overhead'){pos=fly.clone().add(new THREE.Vector3(0,10,.1));}
      else if(this.shot==='chase'){const h=this.avatar.targetBody?.heading_rad||0;pos=fly.clone().add(new THREE.Vector3(Math.sin(h)*5.5,2.7,Math.cos(h)*5.5));}
      else if(this.shot==='victory'){pos=fly.clone().add(new THREE.Vector3(7,4.2,8));target=fly.clone();}
      else{pos=new THREE.Vector3(8.5,4.7,9.5);if(this.environment.mode==='lab')target.set(.2,.55,-.7);}
      const alpha=1-Math.pow(.025,dt);this.camera.position.lerp(pos,alpha);const direction=target.clone().sub(this.camera.position).normalize(),q=new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,0,-1),direction);this.camera.quaternion.slerp(q,alpha);
    }
  }
  Lab.CinematicDirector=CinematicDirector;
})(window);
