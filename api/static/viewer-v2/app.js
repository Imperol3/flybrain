(async function(){
  const Lab=window.FlyLab;
  const $=id=>document.getElementById(id);
  const scene=new THREE.Scene();scene.background=new THREE.Color(0x06090b);scene.fog=new THREE.FogExp2(0x06090b,.032);
  const camera=new THREE.PerspectiveCamera(42,innerWidth/innerHeight,.05,120);camera.position.set(7.5,4.8,9.5);
  const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputEncoding=THREE.sRGBEncoding;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.9;$('stage').appendChild(renderer.domElement);
  const world=new Lab.ArenaWorld(scene),fly=new Lab.FlyAvatar(scene);fly.root.position.set(0,1.05,2.2);
  let brain=null,socket=null,sessionId=null,last=performance.now(),orbit=.65,drag=false,lastX=0;
  const totals={lc4:0,lplc2:0,dnp01:0};

  async function json(path,options){const r=await fetch(path,options);if(!r.ok)throw new Error(await r.text());return r.json();}
  try{
    const [health,positions]=await Promise.all([json('/api/health'),json('/api/positions')]);
    $('dataset').innerHTML=`${health.dataset_version}<b>${health.n_neurons.toLocaleString()} neurons</b>`;
    brain=new Lab.BrainOverlay(fly.brainAnchor,positions);
    $('connection').textContent='LIVE CONNECTOME';$('connection').classList.add('ok');
  }catch(error){$('connection').textContent='BACKEND OFFLINE';$('status').textContent=error.message;}

  function updateHud(frame){
    if(!frame)return;fly.setTargetPose(frame.body);world.updateThreat(frame.threat);world.addTrail(frame.body);
    const n=frame.neural;if(n){totals.lc4+=n.lc4_spikes;totals.lplc2+=n.lplc2_spikes;totals.dnp01+=n.dnp01_spikes;$('lc4').textContent=totals.lc4;$('lplc2').textContent=totals.lplc2;$('dnp01').textContent=totals.dnp01;$('dna').textContent=`${n.dna02_left_hz.toFixed(1)} / ${n.dna02_right_hz.toFixed(1)} Hz`;$('steer').textContent=(n.steering_hz>=0?'+':'')+n.steering_hz.toFixed(1)+' Hz';$('active').textContent=n.active_neurons.toLocaleString();brain&&brain.pulse(n)}
    $('behaviour').textContent=(frame.body.behaviour||'idle').replaceAll('_',' ').toUpperCase();$('elapsed').textContent=(frame.elapsed_ms/1000).toFixed(2)+' s';$('distance').textContent=frame.observation.distance_cm.toFixed(1)+' cm';$('angle').textContent=frame.observation.azimuth_deg.toFixed(1)+'°';$('progress').style.width=Math.min(100,frame.elapsed_ms/30)+'%';
    if(frame.escaped){$('status').textContent='ESCAPE COMPLETE';$('status').classList.add('success')}else if(frame.done){$('status').textContent='RUN COMPLETE'}
  }

  async function stepFallback(){
    if(!sessionId)return;try{const frame=await json(`/api/closed-loop/sessions/${sessionId}/step`,{method:'POST'});updateHud(frame);if(!frame.done)setTimeout(stepFallback,16);}catch(e){$('status').textContent=e.message;setRunning(false)}
  }
  function connectStream(){
    const proto=location.protocol==='https:'?'wss':'ws';socket=new WebSocket(`${proto}://${location.host}/api/closed-loop/sessions/${sessionId}/stream`);
    socket.onmessage=e=>updateHud(JSON.parse(e.data));socket.onclose=()=>setRunning(false);socket.onerror=()=>{socket&&socket.close();stepFallback()};
  }
  function setRunning(running){$('run').disabled=running;$('stop').disabled=!running;if(!running)socket=null;}
  async function start(){
    stop();Object.keys(totals).forEach(k=>totals[k]=0);world.resetTrail();$('status').classList.remove('success');$('status').textContent='INITIALISING PERSISTENT BRAIN…';setRunning(true);
    const silenced=[];if($('silenceLC4').checked)silenced.push('LC4');if($('silenceLPLC2').checked)silenced.push('LPLC2');
    try{const start=await json('/api/closed-loop/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({azimuth_deg:Number($('azimuth').value),approach_velocity_cm_s:Number($('velocity').value),object_radius_cm:Number($('radius').value),step_ms:25,maximum_duration_ms:3000,silenced_populations:silenced})});sessionId=start.session_id;updateHud(start.state);$('status').textContent='WORLD → SENSE → BRAIN → ACT';connectStream();}catch(e){$('status').textContent=e.message;setRunning(false)}
  }
  function stop(){if(socket){socket.onclose=null;socket.close()}socket=null;sessionId=null;setRunning(false);}
  $('run').onclick=start;$('stop').onclick=stop;$('brainToggle').onchange=e=>fly.setBrainVisible(e.target.checked);$('experience').onclick=()=>document.body.classList.toggle('experience');

  renderer.domElement.addEventListener('pointerdown',e=>{drag=true;lastX=e.clientX});addEventListener('pointerup',()=>drag=false);addEventListener('pointermove',e=>{if(drag){orbit+=(e.clientX-lastX)*.006;lastX=e.clientX}});renderer.domElement.addEventListener('wheel',e=>{camera.fov=THREE.MathUtils.clamp(camera.fov+e.deltaY*.018,28,65);camera.updateProjectionMatrix()},{passive:true});
  addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)});

  function cameraUpdate(){const target=fly.root.position.clone();target.y+=.35;const mode=$('camera').value;if(mode==='top'){camera.position.lerp(new THREE.Vector3(target.x,15,target.z+.1),.08);camera.lookAt(target)}else if(mode==='chase'){const h=fly.targetBody?.heading_rad||0;camera.position.lerp(target.clone().add(new THREE.Vector3(Math.sin(h)*5.8,3.2,Math.cos(h)*5.8)),.07);camera.lookAt(target)}else if(mode==='eye'){const h=fly.targetBody?.heading_rad||0,forward=new THREE.Vector3(-Math.sin(h),0,-Math.cos(h));camera.position.copy(target).add(forward.clone().multiplyScalar(.85));camera.lookAt(camera.position.clone().add(forward.multiplyScalar(6)))}else{camera.position.lerp(target.clone().add(new THREE.Vector3(Math.sin(orbit)*8,4.4,Math.cos(orbit)*8)),.07);camera.lookAt(target)}}
  function animate(now){requestAnimationFrame(animate);const dt=Math.min(.05,(now-last)/1000),time=now/1000;last=now;fly.update(dt,time);brain&&brain.update(dt);world.update(time);cameraUpdate();renderer.render(scene,camera)}
  requestAnimationFrame(animate);
})();
