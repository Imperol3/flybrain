(function(global){
  const Lab=global.FlyLab=global.FlyLab||{};
  class Soundscape{
    constructor(){this.ctx=null;this.master=null;this.wing=null;this.lastPulse=0;}
    start(){if(this.ctx){this.ctx.resume();return}const AC=window.AudioContext||window.webkitAudioContext;if(!AC)return;this.ctx=new AC();this.master=this.ctx.createGain();this.master.gain.value=.18;this.master.connect(this.ctx.destination);const humGain=this.ctx.createGain();humGain.gain.value=.025;humGain.connect(this.master);[43,86].forEach((f,i)=>{const o=this.ctx.createOscillator();o.type=i?'sine':'triangle';o.frequency.value=f;o.connect(humGain);o.start()});}
    pulse(freq=420,volume=.035,duration=.045){if(!this.ctx)return;const now=this.ctx.currentTime,o=this.ctx.createOscillator(),g=this.ctx.createGain();o.type='square';o.frequency.value=freq;g.gain.setValueAtTime(volume,now);g.gain.exponentialRampToValueAtTime(.0001,now+duration);o.connect(g);g.connect(this.master);o.start(now);o.stop(now+duration);}
    setFrame(frame){if(!this.ctx||!frame)return;const n=frame.neural;if(n&&(n.lc4_spikes+n.lplc2_spikes+n.dnp01_spikes)>0&&performance.now()-this.lastPulse>90){this.pulse(n.dnp01_spikes?620:380,.018);this.lastPulse=performance.now()}const airborne=['takeoff','escaping'].includes(frame.body.behaviour);if(airborne&&!this.wing){const o=this.ctx.createOscillator(),g=this.ctx.createGain();o.type='sawtooth';o.frequency.value=190;g.gain.value=.018;o.connect(g);g.connect(this.master);o.start();this.wing={o,g}}else if(!airborne&&this.wing){this.wing.g.gain.exponentialRampToValueAtTime(.0001,this.ctx.currentTime+.12);this.wing.o.stop(this.ctx.currentTime+.13);this.wing=null}}
  }
  Lab.Soundscape=Soundscape;
})(window);
