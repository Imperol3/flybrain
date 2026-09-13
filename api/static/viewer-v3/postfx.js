(function(global){
  const Lab=global.FlyLab=global.FlyLab||{};
  class PostFX{
    constructor(renderer,scene,camera){this.renderer=renderer;this.scene=scene;this.camera=camera;this.composer=null;try{if(THREE.EffectComposer&&THREE.RenderPass&&THREE.UnrealBloomPass){this.composer=new THREE.EffectComposer(renderer);this.composer.addPass(new THREE.RenderPass(scene,camera));const bloom=new THREE.UnrealBloomPass(new THREE.Vector2(innerWidth,innerHeight),.72,.62,.82);this.composer.addPass(bloom)}}catch(e){console.warn('Post-processing fallback:',e)}}
    render(){this.composer?this.composer.render():this.renderer.render(this.scene,this.camera)}
    resize(w,h){if(this.composer)this.composer.setSize(w,h)}
  }
  Lab.PostFX=PostFX;
})(window);
