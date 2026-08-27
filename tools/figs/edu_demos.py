"""Interactive demos for the guide.

These are teaching tools, not measurements. Each one runs a small, honest
version of the real dynamics in the browser so a slider produces the same
qualitative behaviour a real simulator would -- and each says so on the page.
"""

EDU_JS = """
// ---- 1. PD gain tuner ---------------------------------------------------
// A single joint with inertia, driven to a target angle by
//     tau = kp*(target - q) - kd*qdot
// This is the whole of PD control. Watch what each gain does on its own:
// kp alone oscillates forever, kd alone never arrives, together they settle.
(function(){
  const c=document.getElementById('pd'); if(!c) return;
  const ctx=c.getContext('2d');
  const kpI=document.getElementById('kp'), kdI=document.getElementById('kd');
  const kpO=document.getElementById('kpv'), kdO=document.getElementById('kdv');
  const verdict=document.getElementById('pdverdict');
  const I=1.0, DT=0.004, TARGET=0.8;
  let q=0, v=0, hist=[], t=0;
  function reset(){q=0;v=0;hist=[];t=0;}
  kpI.addEventListener('input',reset); kdI.addEventListener('input',reset);
  function cv(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
  function frame(){
    const kp=+kpI.value, kd=+kdI.value;
    kpO.textContent='kp = '+kp; kdO.textContent='kd = '+kd;
    for(let k=0;k<4;k++){
      const tau=kp*(TARGET-q)-kd*v;
      v+=DT*tau/I; q+=DT*v; t+=DT;
      hist.push(q); if(hist.length>460) hist.shift();
    }
    const w=c.width=c.clientWidth,h=c.height=c.clientHeight;
    ctx.clearRect(0,0,w,h);
    const midY=h*0.62, sc=h*0.34/1.6;
    // target line
    ctx.strokeStyle=cv('--green')||'#5FB44A'; ctx.lineWidth=2; ctx.setLineDash([5,5]);
    ctx.beginPath(); ctx.moveTo(0,midY-TARGET*sc); ctx.lineTo(w,midY-TARGET*sc); ctx.stroke();
    ctx.setLineDash([]);
    // response trace
    ctx.strokeStyle=cv('--blue')||'#0C8FCB'; ctx.lineWidth=2; ctx.beginPath();
    hist.forEach(function(y,i){const X=i/460*w, Y=midY-Math.max(-2,Math.min(2,y))*sc;
      i?ctx.lineTo(X,Y):ctx.moveTo(X,Y);});
    ctx.stroke();
    // the joint itself, drawn as an arm
    const cx=w*0.5, cy=h*0.18, L=Math.min(w,h)*0.14;
    const qq=Math.max(-3,Math.min(3,q));
    ctx.strokeStyle=cv('--ink')||'#000'; ctx.lineWidth=4; ctx.beginPath();
    ctx.moveTo(cx,cy); ctx.lineTo(cx+L*Math.sin(qq),cy+L*Math.cos(qq)); ctx.stroke();
    ctx.strokeStyle=cv('--green')||'#5FB44A'; ctx.lineWidth=2; ctx.setLineDash([3,3]);
    ctx.beginPath(); ctx.moveTo(cx,cy);
    ctx.lineTo(cx+L*Math.sin(TARGET),cy+L*Math.cos(TARGET)); ctx.stroke(); ctx.setLineDash([]);
    const err=Math.abs(q-TARGET);
    let msg, cls;
    if(!isFinite(q)||Math.abs(q)>6){msg='UNSTABLE';cls='v-bad';}
    else if(kd<0.5&&kp>1){msg='RINGING FOREVER';cls='v-bad';}
    else if(err<0.02){msg='SETTLED';cls='v-ok';}
    else if(t>3&&err>0.2){msg='TOO SLOW / SLUGGISH';cls='v-bad';}
    else {msg='MOVING';cls='v-ok';}
    verdict.textContent=msg; verdict.className='verdict '+cls;
    requestAnimationFrame(frame);
  }
  frame();
})();

// ---- 2. forward kinematics ---------------------------------------------
// Two joint angles in, one end-effector position out. That is all forward
// kinematics is. Inverse kinematics is the same picture read backwards, and
// is much harder because more than one pose can reach the same point.
(function(){
  const c=document.getElementById('fk'); if(!c) return;
  const ctx=c.getContext('2d');
  const a1=document.getElementById('j1'), a2=document.getElementById('j2');
  const out=document.getElementById('fkout');
  function cv(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
  let trail=[];
  function draw(){
    const q1=+a1.value*Math.PI/180, q2=+a2.value*Math.PI/180;
    const w=c.width=c.clientWidth,h=c.height=c.clientHeight;
    const cx=w*0.5, cy=h*0.72, L1=Math.min(w,h)*0.26, L2=Math.min(w,h)*0.22;
    const x1=cx+L1*Math.cos(-q1), y1=cy+L1*Math.sin(-q1);
    const x2=x1+L2*Math.cos(-(q1+q2)), y2=y1+L2*Math.sin(-(q1+q2));
    ctx.clearRect(0,0,w,h);
    ctx.strokeStyle=cv('--ash')||'#B4B4B4'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(0,cy); ctx.lineTo(w,cy); ctx.stroke();
    trail.push([x2,y2]); if(trail.length>90) trail.shift();
    ctx.strokeStyle=cv('--yellow')||'#F2B01E'; ctx.lineWidth=2; ctx.beginPath();
    trail.forEach(function(p,i){i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]);}); ctx.stroke();
    ctx.strokeStyle=cv('--blue')||'#0C8FCB'; ctx.lineWidth=6;
    ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(x1,y1); ctx.stroke();
    ctx.strokeStyle=cv('--red')||'#DE3A3E';
    ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
    ctx.fillStyle=cv('--ink')||'#000';
    [[cx,cy],[x1,y1]].forEach(function(p){ctx.fillRect(p[0]-5,p[1]-5,10,10);});
    ctx.fillStyle=cv('--green')||'#5FB44A'; ctx.fillRect(x2-6,y2-6,12,12);
    const rx=((x2-cx)/L1).toFixed(2), ry=((cy-y2)/L1).toFixed(2);
    out.textContent='tip at x='+rx+'  y='+ry;
  }
  a1.addEventListener('input',draw); a2.addEventListener('input',draw);
  addEventListener('resize',draw); draw();
})();

// ---- 3. timestep explorer ----------------------------------------------
// The same orbit integrated at different timesteps. Too large a step and the
// energy grows visibly -- the orbit spirals out. This is why dt is the first
// thing to check when a simulation "explodes".
(function(){
  const c=document.getElementById('dt'); if(!c) return;
  const ctx=c.getContext('2d');
  const dtI=document.getElementById('dtr'), dtO=document.getElementById('dtv');
  const en=document.getElementById('dten');
  function cv(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
  let st, path=[], E0=0;
  function reset(){st={x:1,y:0,vx:0,vy:1}; path=[]; E0=energy(st);}
  function energy(s){return 0.5*(s.vx*s.vx+s.vy*s.vy)-1/Math.hypot(s.x,s.y);}
  dtI.addEventListener('input',reset); reset();
  function frame(){
    const dt=+dtI.value/1000;
    dtO.textContent='dt = '+dt.toFixed(3)+' s';
    for(let k=0;k<6;k++){
      const r=Math.hypot(st.x,st.y), a=-1/(r*r*r);
      st.vx+=dt*a*st.x; st.vy+=dt*a*st.y;      // semi-implicit Euler
      st.x+=dt*st.vx;  st.y+=dt*st.vy;
      path.push([st.x,st.y]); if(path.length>900) path.shift();
    }
    const w=c.width=c.clientWidth,h=c.height=c.clientHeight;
    const cx=w/2, cy=h/2, S=Math.min(w,h)*0.30;
    ctx.clearRect(0,0,w,h);
    ctx.fillStyle=cv('--yellow')||'#F2B01E'; ctx.fillRect(cx-4,cy-4,8,8);
    ctx.strokeStyle=cv('--blue')||'#0C8FCB'; ctx.lineWidth=1.5; ctx.beginPath();
    path.forEach(function(p,i){const X=cx+p[0]*S,Y=cy+p[1]*S;
      i?ctx.lineTo(X,Y):ctx.moveTo(X,Y);});
    ctx.stroke();
    ctx.fillStyle=cv('--red')||'#DE3A3E';
    ctx.fillRect(cx+st.x*S-4,cy+st.y*S-4,8,8);
    const drift=(energy(st)-E0)/Math.abs(E0)*100;
    en.textContent='energy drift '+(drift>=0?'+':'')+drift.toFixed(1)+'%';
    en.className='verdict '+(Math.abs(drift)>15?'v-bad':'v-ok');
    if(!isFinite(st.x)||Math.hypot(st.x,st.y)>8) reset();
    requestAnimationFrame(frame);
  }
  frame();
})();
"""
