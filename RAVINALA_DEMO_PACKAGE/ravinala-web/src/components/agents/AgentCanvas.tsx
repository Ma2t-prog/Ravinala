import { useEffect, useRef } from 'react';
import type { AgentState } from '../../hooks/useAgentMonitor';

interface AgentCanvasProps {
  agentStates: Record<string, AgentState>;
}

/* ── Canvas size ─────────────────────────────────────────────────────────── */
const W  = 1120;
const H  = 640;
const CP = 3; // canvas-pixels per game-pixel

/* ── Palette ─────────────────────────────────────────────────────────────── */
const SKIN  = '#FFCFA0';
const EYE   = '#140828';
const DARK  = '#04060C';
const PANEL = '#0D1A28';
const CORR  = '#09121E';

/* ── 12-agent grid: 4 columns × 3 rows ──────────────────────────────────── */
type Role =
  'captain'|'market'|'analyst'|'risk'|'portfolio'|'backtest'|
  'ml'|'monitor'|'repair'|'logger'|'reporter'|'alerter';

interface AgentDef { x:number; y:number; color:string; name:string; role:Role; zone:string }

export const AGENTS: Record<string, AgentDef> = {
  // Row 1
  MarketAgent:       { x:143, y:180, color:'#00D4FF', name:'MARKET OPS',   role:'market',    zone:'MARKET DECK'     },
  OrchestratorAgent: { x:403, y:180, color:'#D4AF37', name:'CAPTAIN',      role:'captain',   zone:'COMMAND BRIDGE'  },
  RiskAgent:         { x:672, y:180, color:'#EF4444', name:'SECURITY',     role:'risk',       zone:'DEFENSE GRID'   },
  LoggerAgent:       { x:955, y:180, color:'#64748B', name:'COMMS',        role:'logger',    zone:'COMMS RELAY'     },
  // Row 2
  AnalysisAgent:     { x:143, y:348, color:'#3B82F6', name:'ANALYST',      role:'analyst',   zone:'SCIENCE LAB'     },
  PortfolioAgent:    { x:403, y:348, color:'#10B981', name:'NAVIGATOR',    role:'portfolio', zone:'NAVIGATION HUB'  },
  BacktestAgent:     { x:672, y:348, color:'#F59E0B', name:'ENGINEER',     role:'backtest',  zone:'ENGINE ROOM'     },
  ReportAgent:       { x:955, y:348, color:'#A78BFA', name:'ARCHIVIST',    role:'reporter',  zone:'ARCHIVE VAULT'   },
  // Row 3
  MonitoringAgent:   { x:143, y:512, color:'#6366F1', name:'SENTINEL',     role:'monitor',   zone:'RADAR STATION'   },
  MLAgent:           { x:403, y:512, color:'#8B5CF6', name:'AI CORE',      role:'ml',        zone:'NEURAL CLUSTER'  },
  ErrorHandlerAgent: { x:672, y:512, color:'#F43F5E', name:'MECHANIC',     role:'repair',    zone:'REPAIR BAY'      },
  AlertAgent:        { x:955, y:512, color:'#FB923C', name:'HERALD',       role:'alerter',   zone:'ALERT NEXUS'     },
};

/* ── Room zones (4×3 grid, no voids) ────────────────────────────────────── */
const ROOMS = [
  { x:12,  y:98,  w:247, h:158, agent:'MarketAgent'       },
  { x:272, y:98,  w:267, h:158, agent:'OrchestratorAgent' },
  { x:552, y:98,  w:267, h:158, agent:'RiskAgent'         },
  { x:832, y:98,  w:276, h:158, agent:'LoggerAgent'       },
  { x:12,  y:268, w:247, h:158, agent:'AnalysisAgent'     },
  { x:272, y:268, w:267, h:158, agent:'PortfolioAgent'    },
  { x:552, y:268, w:267, h:158, agent:'BacktestAgent'     },
  { x:832, y:268, w:276, h:158, agent:'ReportAgent'       },
  { x:12,  y:438, w:247, h:140, agent:'MonitoringAgent'   },
  { x:272, y:438, w:267, h:140, agent:'MLAgent'           },
  { x:552, y:438, w:267, h:140, agent:'ErrorHandlerAgent' },
  { x:832, y:438, w:276, h:140, agent:'AlertAgent'        },
];

/* ── Pre-computed starfield ──────────────────────────────────────────────── */
const STARS = Array.from({ length: 220 }, (_, i) => ({
  x:  ((i * 137.508 + 0.24) % 1) * W,
  y:  ((i * 97.321  + 0.13) % 1) * 93,
  r:  ((i * 43.191  + 0.07) % 1) * 1.6 + 0.3,
  b:  ((i * 73.117  + 0.31) % 1) * 0.6 + 0.4,
  sp: ((i * 31.773  + 0.55) % 1) * 0.5 + 0.06,
}));

/* ── Particle system ─────────────────────────────────────────────────────── */
interface Particle { x:number; y:number; vx:number; vy:number; life:number; max:number; color:string; sz:number }
function mkP(x:number, y:number, c:string): Particle {
  const a = Math.random()*Math.PI*2, sp = 0.3+Math.random()*0.7;
  return { x, y, vx:Math.cos(a)*sp, vy:Math.sin(a)*sp, life:0, max:60+Math.random()*60, color:c, sz:1+Math.random()*1.5 };
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */
/** Fill gw×gh game-pixels at offset (gx,gy) from anchor (ax,ay) */
function g(ctx:CanvasRenderingContext2D, ax:number, ay:number, gx:number, gy:number, gw:number, gh:number, c:string) {
  ctx.fillStyle = c; ctx.fillRect(ax+gx*CP, ay+gy*CP, gw*CP, gh*CP);
}
function hexA(hex:string, a:number) {
  const r=parseInt(hex.slice(1,3),16), gn=parseInt(hex.slice(3,5),16), b=parseInt(hex.slice(5,7),16);
  return `rgba(${r},${gn},${b},${a})`;
}
function rr(ctx:CanvasRenderingContext2D, x:number, y:number, w:number, h:number, rad:number) {
  ctx.beginPath();
  ctx.moveTo(x+rad,y); ctx.lineTo(x+w-rad,y); ctx.arcTo(x+w,y,x+w,y+rad,rad);
  ctx.lineTo(x+w,y+h-rad); ctx.arcTo(x+w,y+h,x+w-rad,y+h,rad);
  ctx.lineTo(x+rad,y+h); ctx.arcTo(x,y+h,x,y+h-rad,rad);
  ctx.lineTo(x,y+rad); ctx.arcTo(x,y,x+rad,y,rad);
  ctx.closePath();
}

/* ═══════════════════════════════════════════════════════════════════════════
   ENVIRONMENT
═══════════════════════════════════════════════════════════════════════════ */

function drawSpace(ctx:CanvasRenderingContext2D, t:number) {
  const gr = ctx.createLinearGradient(0,0,0,96);
  gr.addColorStop(0,'#01020B'); gr.addColorStop(1,'#060D1C');
  ctx.fillStyle=gr; ctx.fillRect(0,0,W,96);

  // Nebula clouds
  for (let i=0; i<4; i++) {
    const nx = (W*0.55 + i*120 + Math.sin(t/30000+i)*15), ny = 38+i*6;
    const ng = ctx.createRadialGradient(nx,ny,0,nx,ny,90+i*20);
    ng.addColorStop(0,`rgba(${50+i*8},${15+i*4},${130+i*20},0.07)`);
    ng.addColorStop(1,'transparent');
    ctx.fillStyle=ng; ctx.beginPath(); ctx.ellipse(nx,ny,90+i*20,35+i*8,0.25,0,Math.PI*2); ctx.fill();
  }
  // Planet
  const px=W-140, py=44;
  const pg = ctx.createRadialGradient(px-10,py-10,2,px,py,34);
  pg.addColorStop(0,'#5A2898'); pg.addColorStop(0.6,'#2A0A58'); pg.addColorStop(1,'#12042A');
  ctx.fillStyle=pg; ctx.beginPath(); ctx.arc(px,py,34,0,Math.PI*2); ctx.fill();
  ctx.strokeStyle='rgba(120,60,220,0.4)'; ctx.lineWidth=3;
  ctx.beginPath(); ctx.ellipse(px,py+5,54,13,-0.2,0,Math.PI*2); ctx.stroke();
  ctx.fillStyle='rgba(90,40,180,0.25)';
  ctx.beginPath(); ctx.ellipse(px,py+5,34,7,0,0,Math.PI*2); ctx.fill();
  // Moon
  ctx.fillStyle='#8898B0'; ctx.beginPath(); ctx.arc(px+46,py-22,7,0,Math.PI*2); ctx.fill();
  ctx.fillStyle='#6878A0'; ctx.beginPath(); ctx.arc(px+44,py-23,2.5,0,Math.PI*2); ctx.fill();

  // Stars parallax
  for (const s of STARS) {
    const sx = ((s.x - t*s.sp*0.04)%W+W)%W;
    const tw = 0.7+Math.sin(t/900+s.x)*0.3;
    ctx.fillStyle = s.r>1.3 ? hexA('#FFE8C0',s.b*tw) : s.r>0.9 ? hexA('#C0D8FF',s.b*tw) : hexA('#FFFFFF',s.b*tw);
    ctx.fillRect(sx, s.y, s.r, s.r);
  }
  // Distant galaxy smear
  ctx.fillStyle='rgba(80,40,160,0.04)';
  ctx.beginPath(); ctx.ellipse(W*0.25, 50, 120, 18, -0.1, 0, Math.PI*2); ctx.fill();
}

function drawHull(ctx:CanvasRenderingContext2D, t:number) {
  // Top hull edge
  ctx.fillStyle='#0A1628'; ctx.fillRect(0,88,W,12);
  // Rivets
  ctx.fillStyle='#182840';
  for (let rx=18; rx<W; rx+=28) { ctx.beginPath(); ctx.arc(rx,94,2.2,0,Math.PI*2); ctx.fill(); }
  // Bottom floor
  ctx.fillStyle='#060E1A'; ctx.fillRect(0,578,W,62);
  ctx.fillStyle='#0C1A28'; ctx.fillRect(0,574,W,5);
  // Side walls
  ctx.fillStyle='#0A1628'; ctx.fillRect(0,88,12,490); ctx.fillRect(W-12,88,12,490);

  // LED strip (animated)
  const ledAlpha = 0.5+Math.sin(t/700)*0.2;
  ctx.fillStyle=hexA('#00C8FF',ledAlpha); ctx.fillRect(12,89,W-24,2);

  // Horizontal corridors
  const hCorrs = [{y1:258,y2:268},{y1:428,y2:438}];
  for (const {y1,y2} of hCorrs) {
    ctx.fillStyle=CORR; ctx.fillRect(12,y1,W-24,y2-y1);
    ctx.strokeStyle='rgba(15,30,50,0.9)'; ctx.lineWidth=1;
    for (let gx=12; gx<W-12; gx+=10) {
      ctx.beginPath(); ctx.moveTo(gx,y1); ctx.lineTo(gx,y2); ctx.stroke();
    }
    // Amber warning strips at corridor edges
    ctx.fillStyle='rgba(245,158,11,0.2)'; ctx.fillRect(12,y1,W-24,2); ctx.fillRect(12,y2-2,W-24,2);
  }
  // Vertical corridors
  const vCorrs = [{x1:259,x2:272},{x1:539,x2:552},{x1:819,x2:832}];
  for (const {x1,x2} of vCorrs) {
    ctx.fillStyle=CORR; ctx.fillRect(x1,98,x2-x1,480);
    ctx.strokeStyle='rgba(15,30,50,0.9)'; ctx.lineWidth=1;
    for (let gy=98; gy<578; gy+=10) {
      ctx.beginPath(); ctx.moveTo(x1,gy); ctx.lineTo(x2,gy); ctx.stroke();
    }
    ctx.fillStyle='rgba(245,158,11,0.2)';
    ctx.fillRect(x1,98,2,480); ctx.fillRect(x2-2,98,2,480);
    // Ceiling junction light
    const jl = hexA('#00C8FF', Math.sin(t/500+x1)*0.3+0.5);
    ctx.fillStyle=jl; ctx.beginPath(); ctx.arc((x1+x2)/2,100,3,0,Math.PI*2); ctx.fill();
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   CORRIDOR LIFE  — doors, pipes, robots, signage
═══════════════════════════════════════════════════════════════════════════ */

function drawBenderBot(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, facingRight:boolean) {
  const dir = facingRight ? 1 : -1;
  const leg = Math.sin(t/180)*1.4;
  // Antenna
  ctx.fillStyle='#8090A0'; ctx.fillRect(cx, cy-7, 1, 3);
  ctx.fillStyle='#EF4444'; ctx.beginPath(); ctx.arc(cx+0.5,cy-7,1.2,0,Math.PI*2); ctx.fill();
  // Head
  ctx.fillStyle='#9AABB8'; ctx.beginPath(); ctx.arc(cx,cy-4,3,0,Math.PI*2); ctx.fill();
  ctx.fillStyle='#7A8E9A'; ctx.beginPath(); ctx.arc(cx,cy-4,3,Math.PI*0.2,Math.PI*0.8); ctx.fill();
  // Eyes (gold)
  ctx.fillStyle='#FFD700';
  ctx.beginPath(); ctx.arc(cx+dir*1,cy-5,1,0,Math.PI*2); ctx.fill();
  ctx.beginPath(); ctx.arc(cx+dir*2.2,cy-4.5,0.8,0,Math.PI*2); ctx.fill();
  ctx.fillStyle='#FFF'; ctx.beginPath(); ctx.arc(cx+dir*1,cy-5.4,0.35,0,Math.PI*2); ctx.fill();
  // Mouth
  ctx.fillStyle='#2A3A4A'; ctx.fillRect(cx-2*dir,cy-2.5,3,0.8);
  // Body
  ctx.fillStyle='#8898A8'; rr(ctx,cx-2.5,cy-1,5,5,1); ctx.fill();
  ctx.fillStyle='#3A4A5A'; ctx.fillRect(cx-1,cy+0.5,2,2);
  ctx.fillStyle=hexA('#00C8FF',0.6+Math.sin(t/400)*0.3); ctx.fillRect(cx-0.4,cy+1,0.8,0.8);
  // Arms
  ctx.fillStyle='#8898A8'; ctx.fillRect(cx-4,cy-0.5,2,3); ctx.fillRect(cx+2.5,cy-0.5,2,3);
  // Legs
  ctx.fillStyle='#6878A0';
  ctx.fillRect(cx-2,cy+4,1.5,2+Math.max(0,leg));
  ctx.fillRect(cx+0.5,cy+4,1.5,2+Math.max(0,-leg));
  // Feet
  ctx.fillStyle='#4A5A6A';
  ctx.fillRect(cx-2.8,cy+6+Math.max(0,leg),2.8,1);
  ctx.fillRect(cx+0,cy+6+Math.max(0,-leg),2.8,1);
}

function drawDroneBot(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number) {
  const pa=(t/100)%(Math.PI*2);
  // Thruster glow
  const tg=ctx.createRadialGradient(cx,cy+3,0,cx,cy+3,5);
  tg.addColorStop(0,hexA('#00C8FF',0.25+Math.sin(t/250)*0.1)); tg.addColorStop(1,hexA('#00C8FF',0));
  ctx.fillStyle=tg; ctx.beginPath(); ctx.ellipse(cx,cy+3,5,2,0,0,Math.PI*2); ctx.fill();
  // Saucer body
  ctx.fillStyle='#607080'; ctx.beginPath(); ctx.ellipse(cx,cy,5,2.5,0,0,Math.PI*2); ctx.fill();
  ctx.fillStyle='#8098B0'; ctx.beginPath(); ctx.ellipse(cx,cy-0.5,5,2,0,0,Math.PI*2); ctx.fill();
  // Dome
  ctx.fillStyle='#A0C8E0'; ctx.beginPath(); ctx.ellipse(cx,cy-1.5,2.5,1.8,0,Math.PI,0); ctx.fill();
  ctx.fillStyle=hexA('#FFF',0.3); ctx.beginPath(); ctx.ellipse(cx-0.5,cy-2,1,0.8,-0.3,Math.PI,0); ctx.fill();
  // Propeller
  ctx.strokeStyle=hexA('#8898A8',0.7); ctx.lineWidth=0.8;
  for (let bi=0;bi<3;bi++) {
    const ba=pa+bi*(Math.PI*2/3);
    ctx.beginPath(); ctx.moveTo(cx,cy-3.5); ctx.lineTo(cx+Math.cos(ba)*4,cy-3.5+Math.sin(ba)*0.8); ctx.stroke();
  }
  // Eye
  ctx.fillStyle=hexA('#FF4444',0.8+Math.sin(t/300)*0.2); ctx.beginPath(); ctx.arc(cx+1,cy-1,0.8,0,Math.PI*2); ctx.fill();
  // Side strobes
  for (const sx of [-4.5,4.5]) {
    ctx.fillStyle=hexA('#F59E0B',Math.sin(t/500+sx)>0?0.9:0.2);
    ctx.beginPath(); ctx.arc(cx+sx,cy,0.7,0,Math.PI*2); ctx.fill();
  }
}

function drawCargoBot(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number) {
  // Cargo crate on back
  ctx.fillStyle='#3A2808'; ctx.fillRect(cx-2.5,cy-8,5,4);
  ctx.strokeStyle='#F59E0B'; ctx.lineWidth=0.5; ctx.strokeRect(cx-2.5,cy-8,5,4);
  ctx.strokeStyle=hexA('#F59E0B',0.5); ctx.beginPath(); ctx.moveTo(cx-2.5,cy-6); ctx.lineTo(cx+2.5,cy-6); ctx.stroke();
  if (Math.sin(t/700)>0.4) { ctx.fillStyle=hexA('#10B981',0.6); ctx.fillRect(cx-1,cy-7,2,1); }
  // Body
  ctx.fillStyle='#4A5A6A'; ctx.fillRect(cx-2,cy-4,4,4);
  ctx.fillStyle='#3A4A5A'; ctx.fillRect(cx-1.5,cy-3.5,3,3);
  // Visor
  ctx.fillStyle=hexA('#00C8FF',0.7); ctx.fillRect(cx-2,cy-3,4,1);
  // Arm
  ctx.fillStyle='#606878'; ctx.fillRect(cx+2,cy-2,2,1);
  ctx.fillStyle='#8090A0'; ctx.beginPath(); ctx.arc(cx+4,cy-1.5,1,0,Math.PI*2); ctx.fill();
  // Treads
  ctx.fillStyle='#2A3A4A'; ctx.fillRect(cx-3,cy,6,2);
  const to2=(t/150)%1.2;
  ctx.fillStyle='#1A2A3A';
  for (let wi=0;wi<6;wi++) ctx.fillRect(cx-3+(wi*1.2),cy,0.8,2);
  ctx.fillStyle=hexA('#3A4A5A',0.5);
  for (let wi=0;wi<6;wi++) ctx.fillRect(cx-3+((wi*1.2+to2)%6),cy+0.5,0.5,1);
}

function drawCorridorLife(ctx:CanvasRenderingContext2D, t:number) {
  const blk=Math.sin(t/400)>0;

  /* ── Horizontal corridors ─────────────────────────────────────────── */
  for (const cy of [258,428]) {
    // Pipe bundle along ceiling of corridor
    ctx.fillStyle='#0D1E30'; ctx.fillRect(12,cy+1,W-24,2);
    ctx.fillStyle='rgba(100,160,200,0.06)'; ctx.fillRect(12,cy+1,W-24,1);
    // Clamps + LED nodes
    for (let px=45;px<W-24;px+=52) {
      ctx.fillStyle='rgba(80,130,170,0.32)'; ctx.fillRect(px-1,cy,3,4);
      if (Math.floor(px/52)%3===0) {
        ctx.fillStyle=hexA('#00C8FF',0.45+Math.sin(t/600+px)*0.3);
        ctx.fillRect(px,cy,1,1);
      }
    }
    // Emergency floor strip
    ctx.fillStyle=hexA('#F59E0B',0.06+Math.sin(t/1200+cy)*0.03);
    ctx.fillRect(12,cy+9,W-24,1);

    // Sliding DOORS at each vertical corridor junction
    for (const dx of [259,539,819]) {
      const w2=13;
      // Door panels (dark)
      ctx.fillStyle='rgba(8,22,38,0.95)'; ctx.fillRect(dx-8,cy,7,10); ctx.fillRect(dx+w2+1,cy,7,10);
      // Top / bottom frame strip (cyan)
      ctx.fillStyle=hexA('#00C8FF',0.4); ctx.fillRect(dx-8,cy,28,1); ctx.fillRect(dx-8,cy+9,28,1);
      // Seam
      ctx.fillStyle=hexA('#00C8FF',0.12); ctx.fillRect(dx+w2/2-0.5,cy+1,1,8);
      // Status indicator
      ctx.fillStyle=blk&&Math.floor(t/2000)%7===0?'#EF4444':hexA('#10B981',0.65);
      ctx.fillRect(dx+w2/2,cy+2,2,2);
      // Hazard stripes on door side walls
      for (let si=0;si<3;si++) {
        ctx.fillStyle=si%2===0?hexA('#F59E0B',0.18):hexA('#0A0808',0.1);
        ctx.fillRect(dx-8+si*2.3,cy+1,2.3,8); ctx.fillRect(dx+w2+1+si*2.3,cy+1,2.3,8);
      }
    }

    // Wall signs between doors
    for (const from of [12,272,552,832]) {
      const to=[259,539,819,W-12].find(v=>v>from)||W-12;
      const mx=(from+to)/2;
      ctx.fillStyle=hexA('#F59E0B',0.18); ctx.fillRect(mx-10,cy+3,20,4);
      for (let si=0;si<5;si++) {
        ctx.fillStyle=hexA('#0A0808',0.28); ctx.fillRect(mx-10+si*4,cy+3,2,4);
      }
    }
  }

  /* ── Vertical corridors ──────────────────────────────────────────── */
  for (const cx2 of [259,539,819]) {
    // Cable conduit left wall
    ctx.fillStyle='#0C1E30'; ctx.fillRect(cx2+1,98,2,480);
    ctx.fillStyle='rgba(0,200,255,0.05)'; ctx.fillRect(cx2+1,98,1,480);

    // Junction control boxes at horizontal corridor crossings
    for (const jy of [252,416]) {
      ctx.fillStyle='#0A1828'; rr(ctx,cx2+2,jy,9,6,1); ctx.fill();
      ctx.strokeStyle=hexA('#00C8FF',0.28); ctx.lineWidth=0.5; ctx.stroke();
      for (let li=0;li<3;li++) {
        const ph=(t/320+li*0.9)%3;
        const lc=li===0?'#10B981':li===1?'#00C8FF':'#F59E0B';
        ctx.fillStyle=hexA(lc,ph<0.35?0.9:0.2);
        ctx.beginPath(); ctx.arc(cx2+4+li*3,jy+3,1,0,Math.PI*2); ctx.fill();
      }
    }

    // Floor arrows (directional nav markers)
    for (let ay=120;ay<565;ay+=65) {
      ctx.fillStyle=hexA('#00C8FF',0.08);
      ctx.beginPath(); ctx.moveTo(cx2+6.5,ay+6); ctx.lineTo(cx2+3.5,ay); ctx.lineTo(cx2+9.5,ay); ctx.closePath(); ctx.fill();
    }
  }

  /* ── ROBOTS ──────────────────────────────────────────────────────── */

  // Robot 1 — Bender-bot, top horizontal corridor
  {
    const travel=W-60;
    const phase=(t/5000)%2;
    const rx=20+(phase<1?phase*travel:(2-phase)*travel);
    const facingRight=(t/5000)%2<1;
    drawBenderBot(ctx,rx,263,t,facingRight);
  }

  // Robot 2 — Floating maintenance drone, bottom corridor
  {
    const travel=W-60;
    const phase=(t/6500)%2;
    const rx=W-20-(phase<1?phase*travel:(2-phase)*travel);
    const ry=433+Math.sin(t/800)*1.5;
    drawDroneBot(ctx,rx,ry,t);
  }

  // Robot 3 — Cargo bot, right vertical corridor (going up/down)
  {
    const travel=460;
    const phase=(t/7000)%2;
    const ry2=108+(phase<1?phase*travel:(2-phase)*travel);
    drawCargoBot(ctx,825+6,ry2,t);
  }

  // Robot 4 — Mini Bender clone (smaller) in middle vertical corridor
  {
    const travel=460;
    const phase=((t+3500)/8000)%2;
    const ry3=108+(phase<1?phase*travel:(2-phase)*travel);
    // Tiny version: scale down via save/transform
    ctx.save();
    ctx.translate(539+6.5,ry3);
    ctx.scale(0.7,0.7);
    drawBenderBot(ctx,0,0,t,phase<1);
    ctx.restore();
  }
}

function drawRoom(ctx:CanvasRenderingContext2D, room:typeof ROOMS[0], ag:AgentDef, state:AgentState, t:number) {
  const { x, y, w, h } = room;
  const col = ag.color;
  const active = state.status==='running'||state.status==='completed';
  const alpha  = state.status==='idle' ? 0.42 : 1;

  // Floor
  const fg = ctx.createLinearGradient(x,y+h-24,x,y+h);
  fg.addColorStop(0,'#0A1520'); fg.addColorStop(1,'#060D16');
  ctx.fillStyle=fg; ctx.fillRect(x,y,w,h);

  // Floor grating
  ctx.strokeStyle='rgba(14,26,42,0.85)'; ctx.lineWidth=1;
  for (let gx=x; gx<x+w; gx+=14) { ctx.beginPath(); ctx.moveTo(gx,y+h-28); ctx.lineTo(gx,y+h); ctx.stroke(); }
  for (let gy=y+h-28; gy<y+h; gy+=5) { ctx.beginPath(); ctx.moveTo(x,gy); ctx.lineTo(x+w,gy); ctx.stroke(); }

  // Back wall
  ctx.fillStyle=PANEL; ctx.fillRect(x,y,w,h-38);
  ctx.strokeStyle='rgba(18,35,56,0.9)'; ctx.lineWidth=1;
  for (let px=x+38; px<x+w; px+=38) { ctx.beginPath(); ctx.moveTo(px,y+2); ctx.lineTo(px,y+h-38); ctx.stroke(); }
  for (const py of [y+18,y+52,y+82]) { ctx.beginPath(); ctx.moveTo(x,py); ctx.lineTo(x+w,py); ctx.stroke(); }

  // Per-room unique environment
  drawRoomEnv(ctx, x, y, w, h, ag.role, col, t);

  // Active floor glow
  if (active) {
    const glow = ctx.createLinearGradient(x,y+h-20,x,y+h);
    glow.addColorStop(0,hexA(col,0.12)); glow.addColorStop(1,'transparent');
    ctx.fillStyle=glow; ctx.fillRect(x,y+h-20,w,20);
  }

  // Ceiling LED strip
  ctx.fillStyle=hexA(col, active ? 0.65 : 0.18); ctx.fillRect(x+2,y,w-4,3);
  if (active) {
    const cg = ctx.createLinearGradient(x,y,x,y+35);
    cg.addColorStop(0,hexA(col,0.15)); cg.addColorStop(1,'transparent');
    ctx.fillStyle=cg; ctx.fillRect(x,y,w,35);
  }

  // Corner brackets
  ctx.strokeStyle=hexA(col,alpha*0.65); ctx.lineWidth=1.5;
  const cb=9;
  for (const [bx,by] of [[x,y],[x+w,y],[x,y+h],[x+w,y+h]]) {
    const sx=bx===x?1:-1, sy=by===y?1:-1;
    ctx.beginPath(); ctx.moveTo(bx,by+sy*cb); ctx.lineTo(bx,by); ctx.lineTo(bx+sx*cb,by); ctx.stroke();
  }

  // Zone label (larger, readable, with backdrop)
  const labelY = y + 15;
  const labelText = `◈  ${ag.zone}  ◈`;
  ctx.font = 'bold 9px "JetBrains Mono", monospace';
  ctx.textAlign = 'center';
  const lw = ctx.measureText(labelText).width;
  // Label backdrop
  ctx.fillStyle=hexA(DARK,0.5); rr(ctx, x+w/2-lw/2-5, labelY-9, lw+10, 13, 3); ctx.fill();
  ctx.fillStyle=hexA(col,alpha*0.9); ctx.fillText(labelText, x+w/2, labelY);

  // Status blinky lights (top-right corner)
  const blink = Math.sin(t/280+x)>0;
  for (let li=0; li<3; li++) {
    const lc = li===0&&active ? (blink?col:hexA(col,0.3)) : hexA(col,0.25);
    ctx.fillStyle=lc; ctx.beginPath(); ctx.arc(x+w-10+li*6,labelY,2.2,0,Math.PI*2); ctx.fill();
  }

  // Front floor line
  ctx.fillStyle=hexA(col,alpha*0.22); ctx.fillRect(x,y+h-29,w,2);
}

/* ═══════════════════════════════════════════════════════════════════════════
   ROOM ENVIRONMENTS  (retro 2D — drawn on the back wall of each room)
═══════════════════════════════════════════════════════════════════════════ */
function drawRoomEnv(
  ctx: CanvasRenderingContext2D,
  rx: number, ry: number, rw: number, rh: number,
  role: Role, col: string, t: number
) {
  const bx  = rx + 4;
  const by  = ry + 24;          // below the zone label
  const bw  = rw - 8;
  const bh  = rh - 62;          // above the floor grating
  const mid = rx + rw / 2;
  const blk  = Math.sin(t / 380) > 0;
  const blk2 = Math.sin(t / 620 + 2.1) > 0;

  if (role === 'market') {
    /* ── Market Deck: candlestick chart + scrolling ticker ── */
    const bars = [0.35, 0.6, 0.28, 0.75, 0.5, 0.82, 0.45, 0.68, 0.55, 0.9];
    const panW = Math.min(bw * 0.54, 88);
    // Chart panel
    ctx.fillStyle = '#051018'; ctx.fillRect(bx, by, panW, bh * 0.72);
    ctx.strokeStyle = hexA(col, 0.3); ctx.lineWidth = 0.5; ctx.strokeRect(bx, by, panW, bh * 0.72);
    for (let i = 0; i < bars.length; i++) {
      const bh2 = bars[i] * (bh * 0.6);
      const bxp = bx + 4 + i * (panW - 8) / bars.length;
      const bw2 = (panW - 8) / bars.length - 2;
      const green = i % 2 === 0;
      ctx.fillStyle = green ? '#0F4028' : '#3D0A0A';
      ctx.fillRect(bxp, by + bh * 0.66 - bh2, bw2, bh2);
      ctx.strokeStyle = green ? '#10B981' : '#EF4444'; ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.moveTo(bxp + bw2 / 2, by + bh * 0.66 - bh2 * 1.2);
      ctx.lineTo(bxp + bw2 / 2, by + bh * 0.66 - bh2 * 0.8); ctx.stroke();
    }
    // Trend line on chart
    ctx.strokeStyle = hexA(col, 0.5); ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(bx + 4, by + bh * 0.6);
    for (let i = 0; i < 10; i++) ctx.lineTo(bx + 4 + i * (panW - 8) / 9, by + bh * 0.6 - bars[i] * bh * 0.5);
    ctx.stroke();
    // Right panel: line chart
    const rpx = bx + panW + 4;
    ctx.fillStyle = '#051018'; ctx.fillRect(rpx, by, bw - panW - 4, bh * 0.72);
    ctx.strokeStyle = hexA(col, 0.25); ctx.lineWidth = 0.5; ctx.strokeRect(rpx, by, bw - panW - 4, bh * 0.72);
    const pts = [0.4, 0.5, 0.35, 0.6, 0.45, 0.7, 0.55, 0.65, 0.8, 0.72, 0.85];
    ctx.strokeStyle = col; ctx.lineWidth = 1; ctx.beginPath();
    for (let i = 0; i < pts.length; i++) {
      const px2 = rpx + 3 + i * (bw - panW - 10) / (pts.length - 1);
      const py2 = by + 4 + (1 - pts[i]) * (bh * 0.6);
      i === 0 ? ctx.moveTo(px2, py2) : ctx.lineTo(px2, py2);
    }
    ctx.stroke();
    // Scrolling ticker tape
    const off = (t / 40) % 200;
    ctx.fillStyle = '#030C14'; ctx.fillRect(bx, by + bh * 0.76, bw, 10);
    ctx.save(); ctx.beginPath(); ctx.rect(bx, by + bh * 0.76, bw, 10); ctx.clip();
    ctx.fillStyle = hexA(col, 0.75); ctx.font = '5px "JetBrains Mono", monospace'; ctx.textAlign = 'left';
    const tck = 'AAPL +2.1%  MSFT +0.8%  GOOGL -0.3%  TSLA +5.2%  AMZN +1.4%  ';
    ctx.fillText(tck + tck, bx - off, by + bh * 0.76 + 8);
    ctx.restore();

  } else if (role === 'captain') {
    /* ── Command Bridge: circular viewport + holographic rings ── */
    const vr = Math.min(bh * 0.38, bw * 0.19, 32);
    const vx = mid, vy = by + bh * 0.42;
    // Space viewport
    ctx.save(); ctx.beginPath(); ctx.arc(vx, vy, vr, 0, Math.PI * 2); ctx.clip();
    ctx.fillStyle = '#01020A'; ctx.fill();
    for (let si = 0; si < 22; si++) {
      const sx = vx - vr + ((si * 47.3 + 3) % 1) * vr * 2;
      const sy = vy - vr + ((si * 31.7 + 7) % 1) * vr * 2;
      ctx.fillStyle = `rgba(255,255,255,${0.35 + (si % 3) * 0.2})`; ctx.fillRect(sx, sy, 1, 1);
    }
    ctx.fillStyle = '#3A0080'; ctx.beginPath(); ctx.arc(vx + vr * 0.35, vy - vr * 0.2, vr * 0.28, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
    // Viewport frame
    ctx.strokeStyle = hexA(col, 0.65); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(vx, vy, vr, 0, Math.PI * 2); ctx.stroke();
    for (let fi = 0; fi < 4; fi++) {
      const fa = fi * Math.PI / 2;
      ctx.strokeStyle = hexA(col, 0.35); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(vx + Math.cos(fa) * vr, vy + Math.sin(fa) * vr);
      ctx.lineTo(vx + Math.cos(fa) * (vr + 7), vy + Math.sin(fa) * (vr + 7)); ctx.stroke();
    }
    // Scan line across viewport
    const scanY = vy - vr + ((t / 1400) % 1) * vr * 2;
    const dx = Math.sqrt(Math.max(0, vr * vr - (scanY - vy) ** 2));
    ctx.strokeStyle = hexA(col, 0.2); ctx.lineWidth = 0.8;
    ctx.beginPath(); ctx.moveTo(vx - dx, scanY); ctx.lineTo(vx + dx, scanY); ctx.stroke();
    // Holographic orbit rings (sides)
    for (const [ox, oa] of [[-bw * 0.34, 0.3], [bw * 0.34, 0.3]] as [number, number][]) {
      for (let ri = 0; ri < 3; ri++) {
        ctx.strokeStyle = hexA(col, 0.15 + ri * 0.05); ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.ellipse(mid + ox, vy, 7 + ri * 5, 2 + ri * 2, oa + t / 5000 * (ri + 1), 0, Math.PI * 2); ctx.stroke();
      }
    }

  } else if (role === 'risk') {
    /* ── Defense Grid: threat radar + shield racks + warning stripes ── */
    // Left: shield rack
    const srw2 = bw * 0.27;
    ctx.fillStyle = '#0A0808'; ctx.fillRect(bx, by + 2, srw2, bh * 0.72);
    ctx.strokeStyle = hexA(col, 0.2); ctx.lineWidth = 0.5; ctx.strokeRect(bx, by + 2, srw2, bh * 0.72);
    for (let si = 0; si < 3; si++) {
      const sy = by + 8 + si * (bh * 0.21);
      ctx.fillStyle = hexA(col, 0.15);
      ctx.beginPath(); ctx.moveTo(bx + srw2 * 0.5, sy + bh * 0.14);
      ctx.lineTo(bx + srw2 * 0.12, sy); ctx.lineTo(bx + srw2 * 0.88, sy); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = hexA(col, 0.35); ctx.lineWidth = 0.7; ctx.stroke();
    }
    // Right: warning stripes column
    for (let si = 0; si < 8; si++) {
      ctx.fillStyle = si % 2 === 0 ? hexA('#F59E0B', 0.12) : hexA('#0A0808', 0.08);
      ctx.fillRect(bx + bw * 0.78, by + si * (bh * 0.09), bw * 0.18, bh * 0.09);
    }
    // Center: threat radar
    const tdx = bx + bw * 0.52, tdy = by + bh * 0.4, tdr = bh * 0.27;
    ctx.fillStyle = '#040B10'; ctx.beginPath(); ctx.arc(tdx, tdy, tdr, 0, Math.PI * 2); ctx.fill();
    for (let ri = 1; ri <= 3; ri++) {
      ctx.strokeStyle = hexA(col, 0.1 + ri * 0.06); ctx.lineWidth = 0.6;
      ctx.beginPath(); ctx.arc(tdx, tdy, tdr * ri / 3, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.strokeStyle = hexA(col, 0.15); ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(tdx - tdr, tdy); ctx.lineTo(tdx + tdr, tdy); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(tdx, tdy - tdr); ctx.lineTo(tdx, tdy + tdr); ctx.stroke();
    const sw = (t / 1800) % (Math.PI * 2);
    const tg = ctx.createRadialGradient(tdx, tdy, 0, tdx, tdy, tdr);
    tg.addColorStop(0, hexA(col, 0.28)); tg.addColorStop(1, hexA(col, 0));
    ctx.fillStyle = tg; ctx.beginPath(); ctx.moveTo(tdx, tdy);
    ctx.arc(tdx, tdy, tdr, sw, sw + 0.6); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = hexA(col, 0.7); ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(tdx, tdy);
    ctx.lineTo(tdx + Math.cos(sw) * tdr, tdy + Math.sin(sw) * tdr); ctx.stroke();
    for (const [ba, bd] of [[0.8, 0.6], [2.2, 0.8], [3.9, 0.5]] as [number, number][]) {
      const vis = ((sw - ba + Math.PI * 4) % (Math.PI * 2)) < 1.8 ? 0.9 : 0.2;
      ctx.fillStyle = hexA(col, vis);
      ctx.beginPath(); ctx.arc(tdx + Math.cos(ba) * tdr * bd, tdy + Math.sin(ba) * tdr * bd, 2, 0, Math.PI * 2); ctx.fill();
    }

  } else if (role === 'logger') {
    /* ── Comms Relay: antenna mast + satellite dish + waveform ── */
    const mast_x = bx + bw * 0.25;
    ctx.strokeStyle = hexA(col, 0.55); ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(mast_x, by + bh * 0.72); ctx.lineTo(mast_x, by + 3); ctx.stroke();
    for (const ay2 of [0.12, 0.28, 0.44]) {
      const aw = (0.5 - ay2) * 24 + 5;
      ctx.strokeStyle = hexA(col, 0.4); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(mast_x - aw, by + bh * ay2); ctx.lineTo(mast_x + aw, by + bh * ay2); ctx.stroke();
    }
    if (blk) {
      for (let ri = 1; ri <= 3; ri++) {
        ctx.strokeStyle = hexA(col, 0.15 * (4 - ri)); ctx.lineWidth = 0.7;
        ctx.beginPath(); ctx.arc(mast_x, by + 3, ri * 8, Math.PI * 1.1, Math.PI * 1.9); ctx.stroke();
      }
    }
    // Satellite dish
    const dx2 = bx + bw * 0.7, dy2 = by + bh * 0.3;
    ctx.strokeStyle = hexA(col, 0.55); ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.arc(dx2, dy2, 15, -Math.PI * 0.2, Math.PI * 0.8); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(dx2, dy2); ctx.lineTo(dx2, dy2 + 20); ctx.stroke();
    ctx.fillStyle = hexA(col, 0.35); ctx.beginPath(); ctx.arc(dx2, dy2, 3, 0, Math.PI * 2); ctx.fill();
    // Waveform
    const waveY = by + bh * 0.76;
    ctx.fillStyle = '#040C16'; ctx.fillRect(bx, waveY, bw, bh * 0.2);
    ctx.strokeStyle = hexA(col, 0.65); ctx.lineWidth = 1; ctx.beginPath();
    for (let wx = 0; wx <= bw; wx += 2) {
      const wy = waveY + bh * 0.1 + Math.sin((wx / bw * 8 + t / 400) * Math.PI) * bh * 0.06;
      wx === 0 ? ctx.moveTo(bx + wx, wy) : ctx.lineTo(bx + wx, wy);
    }
    ctx.stroke();

  } else if (role === 'analyst') {
    /* ── Science Lab: whiteboard + test tube rack ── */
    const wbw2 = bw * 0.55, wbh2 = bh * 0.68;
    ctx.fillStyle = '#0A1830'; ctx.fillRect(bx + 2, by + 2, wbw2, wbh2);
    ctx.strokeStyle = hexA(col, 0.4); ctx.lineWidth = 1; ctx.strokeRect(bx + 2, by + 2, wbw2, wbh2);
    // Formula lines
    ctx.strokeStyle = hexA('#FFFFFF', 0.18); ctx.lineWidth = 0.5;
    const lineLens = [0.7, 0.5, 0.8, 0.45, 0.65];
    for (let li = 0; li < 5; li++) {
      const ly = by + 8 + li * (wbh2 - 10) / 4;
      ctx.beginPath(); ctx.moveTo(bx + 8, ly); ctx.lineTo(bx + 8 + lineLens[li] * (wbw2 - 10), ly); ctx.stroke();
    }
    ctx.fillStyle = hexA(col, 0.55); ctx.font = '6px serif'; ctx.textAlign = 'left';
    for (const [sym, si, sl] of [['α=', 0, 0], ['β²', 1, 1], ['∑x', 2, 2], ['∫dt', 3, 3], ['σ²', 4, 4]] as [string, number, number][]) {
      ctx.fillText(sym, bx + 8 + si * (wbw2 * 0.17), by + 10 + sl * 10);
    }
    // Test tube rack
    const ttx = bx + bw * 0.62;
    ctx.fillStyle = '#060E1A'; ctx.fillRect(ttx, by + 6, bw * 0.34, bh * 0.65);
    ctx.strokeStyle = hexA(col, 0.18); ctx.lineWidth = 0.5; ctx.strokeRect(ttx, by + 6, bw * 0.34, bh * 0.65);
    for (let ti = 0; ti < 4; ti++) {
      const tx = ttx + 6 + ti * 9;
      const tc = ['#0080FF', '#10B981', '#F59E0B', '#EF4444'][ti];
      ctx.fillStyle = hexA(tc, 0.12); ctx.fillRect(tx, by + 10, 5, bh * 0.5);
      ctx.strokeStyle = hexA(tc, 0.45); ctx.lineWidth = 0.7;
      ctx.strokeRect(tx, by + 10, 5, bh * 0.5);
      const lvl = 0.4 + Math.sin(t / 1000 + ti) * 0.08;
      ctx.fillStyle = hexA(tc, 0.5); ctx.fillRect(tx + 1, by + 10 + bh * (0.5 - lvl * 0.45), 3, bh * lvl * 0.45);
    }
    ctx.fillStyle = hexA(col, 0.3); ctx.fillRect(ttx + 4, by + 10, bw * 0.26, 2);

  } else if (role === 'portfolio') {
    /* ── Navigation Hub: star chart grid + constellation + compass ── */
    ctx.strokeStyle = hexA(col, 0.07); ctx.lineWidth = 0.5;
    for (let gx2 = bx; gx2 < bx + bw; gx2 += 14) { ctx.beginPath(); ctx.moveTo(gx2, by); ctx.lineTo(gx2, by + bh); ctx.stroke(); }
    for (let gy2 = by; gy2 < by + bh; gy2 += 14) { ctx.beginPath(); ctx.moveTo(bx, gy2); ctx.lineTo(bx + bw, gy2); ctx.stroke(); }
    const cstars: [number, number][] = [
      [mid - bw * 0.3, by + bh * 0.22], [mid - bw * 0.1, by + bh * 0.13],
      [mid + bw * 0.16, by + bh * 0.19], [mid + bw * 0.3, by + bh * 0.38],
      [mid - bw * 0.2, by + bh * 0.52], [mid + bw * 0.05, by + bh * 0.56],
    ];
    ctx.strokeStyle = hexA(col, 0.22); ctx.lineWidth = 0.8;
    for (const [a, b] of [[0,1],[1,2],[2,3],[3,5],[4,5],[0,4]] as [number,number][]) {
      ctx.beginPath(); ctx.moveTo(cstars[a][0], cstars[a][1]); ctx.lineTo(cstars[b][0], cstars[b][1]); ctx.stroke();
    }
    for (const [sx, sy] of cstars) { ctx.fillStyle = col; ctx.beginPath(); ctx.arc(sx, sy, 2.5, 0, Math.PI * 2); ctx.fill(); }
    ctx.strokeStyle = hexA('#10B981', 0.55); ctx.lineWidth = 1.2;
    ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(bx + 8, by + bh * 0.72); ctx.lineTo(bx + bw - 8, by + bh * 0.28); ctx.stroke();
    ctx.setLineDash([]);
    // Compass rose
    const crx = bx + bw * 0.84, cry = by + bh * 0.76, crr = 10;
    for (const ca of [0, Math.PI / 2, Math.PI, Math.PI * 1.5]) {
      ctx.strokeStyle = hexA(col, 0.5); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(crx, cry); ctx.lineTo(crx + Math.cos(ca) * crr, cry + Math.sin(ca) * crr); ctx.stroke();
    }
    ctx.fillStyle = col; ctx.beginPath(); ctx.arc(crx, cry, 2.5, 0, Math.PI * 2); ctx.fill();

  } else if (role === 'backtest') {
    /* ── Engine Room: gear + steam pipes + reactor core ── */
    // Steam pipes (top strip)
    ctx.fillStyle = '#0A1822'; ctx.fillRect(bx, by + 2, bw, 9);
    ctx.fillStyle = '#152535'; ctx.fillRect(bx + 6, by + 3, bw - 12, 7);
    for (let pi2 = 0; pi2 < 5; pi2++) {
      const px2 = bx + 16 + pi2 * (bw - 32) / 4;
      ctx.fillStyle = hexA(col, 0.3); ctx.beginPath(); ctx.arc(px2, by + 6.5, 3, 0, Math.PI * 2); ctx.fill();
    }
    if (blk) {
      for (let si = 0; si < 3; si++) {
        const sx2 = bx + 30 + si * (bw - 60) / 2;
        ctx.strokeStyle = hexA('#AACCDD', 0.12); ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(sx2, by + 2); ctx.quadraticCurveTo(sx2 + 4, by - 4, sx2 + 8, by - 7); ctx.stroke();
      }
    }
    // Large gear (left-center)
    const gx = bx + bw * 0.3, gy = by + bh * 0.52, gr = Math.min(bh * 0.3, 24);
    const ga = (t / 2000) % (Math.PI * 2);
    ctx.strokeStyle = hexA(col, 0.4); ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.arc(gx, gy, gr, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(gx, gy, gr * 0.32, 0, Math.PI * 2); ctx.stroke();
    for (let ti = 0; ti < 10; ti++) {
      const ta = ga + ti * Math.PI / 5;
      ctx.beginPath();
      ctx.moveTo(gx + Math.cos(ta) * gr * 0.88, gy + Math.sin(ta) * gr * 0.88);
      ctx.lineTo(gx + Math.cos(ta) * (gr + 5), gy + Math.sin(ta) * (gr + 5));
      ctx.lineTo(gx + Math.cos(ta + 0.25) * (gr + 5), gy + Math.sin(ta + 0.25) * (gr + 5));
      ctx.lineTo(gx + Math.cos(ta + 0.25) * gr, gy + Math.sin(ta + 0.25) * gr);
      ctx.fillStyle = hexA(col, 0.15); ctx.fill();
      ctx.strokeStyle = hexA(col, 0.35); ctx.lineWidth = 0.8; ctx.stroke();
    }
    // Reactor core (right)
    const rcx = bx + bw * 0.76, rcy = by + bh * 0.5, rcr = bh * 0.2;
    const rcG = ctx.createRadialGradient(rcx, rcy, 0, rcx, rcy, rcr);
    rcG.addColorStop(0, hexA(col, 0.5 + Math.sin(t / 400) * 0.15));
    rcG.addColorStop(1, hexA(col, 0));
    ctx.fillStyle = rcG; ctx.beginPath(); ctx.arc(rcx, rcy, rcr, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = hexA(col, 0.6); ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(rcx, rcy, rcr * 0.5, 0, Math.PI * 2); ctx.stroke();

  } else if (role === 'reporter') {
    /* ── Archive Vault: bookshelves + filing cabinet ── */
    const shH = Math.max(Math.floor(bh / 3.2), 18);
    const numSh = Math.floor(bh / shH);
    for (let si = 0; si < numSh; si++) {
      const sy = by + si * shH;
      ctx.fillStyle = '#0C1B2C'; ctx.fillRect(bx, sy + shH - 3, bw * 0.78, 3);
      let bkx = bx + 2;
      let bi2 = 0;
      while (bkx < bx + bw * 0.76) {
        const bkw = 5 + (bi2 * 3 + si * 7) % 6;
        const bkh2 = shH * 0.55 + ((bi2 * 7 + si * 3) % 3) * shH * 0.1;
        const bkCol = ['#0A3060', '#1A4820', '#5A1A08', '#2A1A50', '#0A3840', '#3A2808'][(bi2 * 3 + si * 5) % 6];
        ctx.fillStyle = bkCol; ctx.fillRect(bkx, sy + shH - 3 - bkh2, bkw, bkh2);
        ctx.strokeStyle = hexA('#FFFFFF', 0.04); ctx.lineWidth = 0.5;
        ctx.strokeRect(bkx, sy + shH - 3 - bkh2, bkw, bkh2);
        bkx += bkw + 1; bi2++;
      }
    }
    // Filing cabinet (right)
    const fcx = bx + bw * 0.82, fcy = by + 2;
    ctx.fillStyle = '#0C1828'; ctx.fillRect(fcx, fcy, bw * 0.14, bh * 0.78);
    ctx.strokeStyle = hexA(col, 0.25); ctx.lineWidth = 0.5; ctx.strokeRect(fcx, fcy, bw * 0.14, bh * 0.78);
    for (let di = 0; di < 4; di++) {
      const dy = fcy + 3 + di * (bh * 0.18);
      ctx.fillStyle = '#091520'; ctx.fillRect(fcx + 1, dy, bw * 0.12, bh * 0.15);
      ctx.strokeStyle = hexA(col, 0.2); ctx.lineWidth = 0.4; ctx.strokeRect(fcx + 1, dy, bw * 0.12, bh * 0.15);
      ctx.fillStyle = hexA(col, 0.35); ctx.fillRect(fcx + bw * 0.04, dy + bh * 0.065, bw * 0.04, 2);
    }

  } else if (role === 'monitor') {
    /* ── Radar Station: two animated radar screens ── */
    const rR = Math.min(bw * 0.19, bh * 0.3, 26);
    const radars: [number, number][] = [[bx + bw * 0.27, by + bh * 0.44], [bx + bw * 0.72, by + bh * 0.44]];
    ctx.fillStyle = hexA(col, 0.4); ctx.font = '5px "JetBrains Mono", monospace'; ctx.textAlign = 'center';
    ctx.fillText('RAD-A', radars[0][0], by + 5); ctx.fillText('RAD-B', radars[1][0], by + 5);
    for (let ri = 0; ri < 2; ri++) {
      const [rdx, rdy] = radars[ri];
      const sw2 = (t / 1200 + ri * 1.8) % (Math.PI * 2);
      ctx.fillStyle = '#040E18'; ctx.beginPath(); ctx.arc(rdx, rdy, rR + 4, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = hexA(col, 0.5); ctx.lineWidth = 1.5; ctx.stroke();
      ctx.fillStyle = '#020B10'; ctx.beginPath(); ctx.arc(rdx, rdy, rR, 0, Math.PI * 2); ctx.fill();
      for (let gi = 1; gi <= 3; gi++) {
        ctx.strokeStyle = hexA(col, 0.08 + gi * 0.05); ctx.lineWidth = 0.5;
        ctx.beginPath(); ctx.arc(rdx, rdy, rR * gi / 3, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.strokeStyle = hexA(col, 0.1); ctx.lineWidth = 0.4;
      ctx.beginPath(); ctx.moveTo(rdx - rR, rdy); ctx.lineTo(rdx + rR, rdy); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(rdx, rdy - rR); ctx.lineTo(rdx, rdy + rR); ctx.stroke();
      const sg2 = ctx.createRadialGradient(rdx, rdy, 0, rdx, rdy, rR);
      sg2.addColorStop(0, hexA(col, 0.22)); sg2.addColorStop(1, hexA(col, 0));
      ctx.fillStyle = sg2; ctx.beginPath(); ctx.moveTo(rdx, rdy);
      ctx.arc(rdx, rdy, rR, sw2, sw2 + 0.7); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = hexA(col, 0.7); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(rdx, rdy); ctx.lineTo(rdx + Math.cos(sw2) * rR, rdy + Math.sin(sw2) * rR); ctx.stroke();
      for (const [ba, bd] of [[0.6, 0.65], [2.1, 0.8], [4.2, 0.5], [5.1, 0.75]] as [number, number][]) {
        const vis = ((sw2 - ba + Math.PI * 4) % (Math.PI * 2)) < 1.5 ? 0.9 : 0.2;
        ctx.fillStyle = hexA(col, vis);
        ctx.beginPath(); ctx.arc(rdx + Math.cos(ba) * rR * bd, rdy + Math.sin(ba) * rR * bd, 2, 0, Math.PI * 2); ctx.fill();
      }
    }

  } else if (role === 'ml') {
    /* ── Neural Cluster: server racks + neural net viz ── */
    const rkW = bw * 0.4;
    for (const rkx of [bx + 2, bx + bw * 0.52]) {
      ctx.fillStyle = '#060E18'; ctx.fillRect(rkx, by + 2, rkW, bh * 0.74);
      ctx.strokeStyle = hexA(col, 0.3); ctx.lineWidth = 0.7; ctx.strokeRect(rkx, by + 2, rkW, bh * 0.74);
      for (let su = 0; su < 5; su++) {
        const sy = by + 5 + su * (bh * 0.14);
        ctx.fillStyle = '#0A1A2E'; ctx.fillRect(rkx + 2, sy, rkW - 4, bh * 0.11);
        ctx.strokeStyle = hexA(col, 0.15); ctx.lineWidth = 0.4; ctx.strokeRect(rkx + 2, sy, rkW - 4, bh * 0.11);
        for (let li = 0; li < 4; li++) {
          const lp = (t / 200 + su * 0.7 + li * 1.3) % 3;
          const lc = li === 0 ? '#10B981' : li === 1 ? col : '#F59E0B';
          ctx.fillStyle = hexA(lc, lp < 0.3 ? 0.9 : 0.22);
          ctx.beginPath(); ctx.arc(rkx + rkW - 5 - li * 5, sy + bh * 0.055, 1.5, 0, Math.PI * 2); ctx.fill();
        }
      }
    }
    // Neural net nodes between racks
    const nnNodes: [number, number][] = [
      [mid - 7, by + bh * 0.16], [mid + 7, by + bh * 0.26],
      [mid, by + bh * 0.42], [mid - 9, by + bh * 0.58], [mid + 9, by + bh * 0.58],
    ];
    ctx.strokeStyle = hexA(col, 0.2); ctx.lineWidth = 0.6;
    for (let a = 0; a < nnNodes.length - 1; a++) {
      for (let b = a + 1; b < nnNodes.length; b++) {
        if (Math.hypot(nnNodes[a][0] - nnNodes[b][0], nnNodes[a][1] - nnNodes[b][1]) < 42) {
          ctx.beginPath(); ctx.moveTo(nnNodes[a][0], nnNodes[a][1]); ctx.lineTo(nnNodes[b][0], nnNodes[b][1]); ctx.stroke();
        }
      }
    }
    for (const [nx, ny] of nnNodes) { ctx.fillStyle = hexA(col, 0.85); ctx.beginPath(); ctx.arc(nx, ny, 2.5, 0, Math.PI * 2); ctx.fill(); }

  } else if (role === 'repair') {
    /* ── Repair Bay: pegboard + warning tape + workbench ── */
    ctx.fillStyle = '#060E1A'; ctx.fillRect(bx, by + 2, bw * 0.58, bh * 0.66);
    ctx.strokeStyle = hexA('#F59E0B', 0.18); ctx.lineWidth = 0.5;
    ctx.strokeRect(bx, by + 2, bw * 0.58, bh * 0.66);
    for (let py2 = by + 8; py2 < by + bh * 0.62; py2 += 8) {
      for (let px2 = bx + 6; px2 < bx + bw * 0.54; px2 += 8) {
        ctx.fillStyle = hexA('#FFFFFF', 0.06); ctx.beginPath(); ctx.arc(px2, py2, 1.5, 0, Math.PI * 2); ctx.fill();
      }
    }
    // Hung tools
    const toolDefs: [number, number, number, number, string][] = [
      [8, 10, 3, 15, '#B0B0C0'], [20, 8, 9, 5, '#8090A0'],
      [36, 7, 4, 18, '#B0A060'], [50, 10, 11, 3, '#9090A0'],
      [66, 8, 3, 16, '#C0B080'],
    ];
    for (const [tx, ty, tw, th, tc] of toolDefs) {
      ctx.fillStyle = hexA(tc, 0.38); ctx.fillRect(bx + tx, by + ty, tw, th);
    }
    // Warning tape floor strip
    for (let wi = 0; wi < Math.floor(bw / 9); wi++) {
      ctx.fillStyle = wi % 2 === 0 ? hexA('#F59E0B', 0.45) : hexA('#080808', 0.25);
      ctx.fillRect(bx + wi * 9, by + bh * 0.71, 9, 7);
    }
    // Workbench (right)
    ctx.fillStyle = '#0A1624'; ctx.fillRect(bx + bw * 0.62, by + bh * 0.33, bw * 0.34, bh * 0.33);
    ctx.strokeStyle = hexA('#F59E0B', 0.22); ctx.lineWidth = 0.7;
    ctx.strokeRect(bx + bw * 0.62, by + bh * 0.33, bw * 0.34, bh * 0.33);
    for (let ci = 0; ci < 4; ci++) {
      const cs = 4 + ci * 2;
      ctx.fillStyle = hexA(['#EF4444', '#10B981', '#3B82F6', '#F59E0B'][ci], 0.42);
      ctx.fillRect(bx + bw * 0.64 + ci * 7, by + bh * 0.36, cs, cs * 0.6);
    }

  } else if (role === 'alerter') {
    /* ── Alert Nexus: siren lights + warning display ── */
    const sirens: [number, number][] = [[bx + 14, by + bh * 0.22], [bx + bw - 14, by + bh * 0.22]];
    for (let si = 0; si < 2; si++) {
      const [sx, sy] = sirens[si];
      ctx.fillStyle = '#0A1420'; ctx.beginPath(); ctx.arc(sx, sy, 11, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = hexA(col, 0.4); ctx.lineWidth = 1; ctx.stroke();
      const flashOn = si === 0 ? blk : !blk;
      if (flashOn) {
        const sg3 = ctx.createRadialGradient(sx, sy, 0, sx, sy, 24);
        sg3.addColorStop(0, hexA(col, 0.55)); sg3.addColorStop(1, hexA(col, 0));
        ctx.fillStyle = sg3; ctx.beginPath(); ctx.arc(sx, sy, 24, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = hexA(col, 0.85); ctx.beginPath(); ctx.arc(sx, sy, 6, 0, Math.PI * 2); ctx.fill();
      } else {
        ctx.fillStyle = hexA(col, 0.15); ctx.beginPath(); ctx.arc(sx, sy, 6, 0, Math.PI * 2); ctx.fill();
      }
    }
    // Alert level display (center)
    const adx = bx + bw * 0.18, ady = by + bh * 0.35, adw = bw * 0.64, adh = bh * 0.48;
    ctx.fillStyle = '#040810'; ctx.fillRect(adx, ady, adw, adh);
    ctx.strokeStyle = hexA(col, 0.4); ctx.lineWidth = 1; ctx.strokeRect(adx, ady, adw, adh);
    const levels = ['CRITICAL', 'WARNING', 'INFO', 'NOMINAL'];
    const lcolors = ['#EF4444', '#F59E0B', '#3B82F6', '#64748B'];
    for (let li = 0; li < 4; li++) {
      const act = li === 0 && blk2;
      ctx.fillStyle = hexA(lcolors[li], act ? 0.28 : 0.08);
      ctx.fillRect(adx + 3, ady + 3 + li * (adh - 6) / 4, adw - 6, (adh - 6) / 4 - 1);
      ctx.fillStyle = hexA(lcolors[li], act ? 0.9 : 0.3);
      ctx.font = '5px "JetBrains Mono", monospace'; ctx.textAlign = 'left';
      ctx.fillText(levels[li], adx + 7, ady + 3 + li * (adh - 6) / 4 + (adh - 6) / 8 + 2);
    }
    // Warning stripes bottom
    for (let wi = 0; wi < Math.floor(bw / 10); wi++) {
      ctx.fillStyle = wi % 2 === 0 ? hexA(col, 0.16) : hexA('#080808', 0.08);
      ctx.fillRect(bx + wi * 10, by + bh * 0.89, 10, bh * 0.09);
    }
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   CONSOLES
═══════════════════════════════════════════════════════════════════════════ */
function drawConsole(ctx:CanvasRenderingContext2D, cx:number, cy:number, role:Role, col:string, t:number) {
  const blink  = Math.sin(t/380)>0;
  const blink2 = Math.sin(t/220+1.4)>0;
  const cw = role==='captain' ? 100 : 78;
  const ch = 26;
  const top = cy-30;

  // Desk body
  ctx.fillStyle='#0B1A2C'; rr(ctx,cx-cw/2,top,cw,ch,3); ctx.fill();
  ctx.strokeStyle=hexA(col,0.42); ctx.lineWidth=1; ctx.stroke();
  // Screen
  ctx.fillStyle='#05101E'; rr(ctx,cx-cw/2+4,top+3,cw-8,ch-8,2); ctx.fill();
  ctx.strokeStyle=hexA(col,0.22); ctx.lineWidth=0.5; ctx.stroke();

  if (role==='captain') {
    // Holographic arcs
    for (let i=1;i<=4;i++) {
      ctx.strokeStyle=hexA(col,0.12*i); ctx.lineWidth=1;
      ctx.beginPath(); ctx.arc(cx,top+ch+2,12+i*11,Math.PI,Math.PI*2); ctx.stroke();
    }
    // Command star
    ctx.fillStyle=blink?col:hexA(col,0.5); ctx.beginPath(); ctx.arc(cx,top+11,3.5,0,Math.PI*2); ctx.fill();
    // Side wing screens
    for (const sx of [-cw/2-22, cw/2+2]) {
      ctx.fillStyle='#091520'; rr(ctx,cx+sx,top+2,20,ch-4,2); ctx.fill();
      ctx.strokeStyle=hexA(col,0.3); ctx.lineWidth=0.5; ctx.stroke();
      ctx.fillStyle=hexA(col,0.2); ctx.fillRect(cx+sx+3,top+5,14,ch-10);
    }

  } else if (role==='market') {
    const bars=[0.4,0.65,0.3,0.82,0.55,0.7,0.45,0.6];
    for (let i=0;i<bars.length;i++) {
      const bh=(bars[i]+Math.sin(t/300+i*1.2)*0.06)*16;
      const bx=cx-cw/2+6+i*8;
      ctx.fillStyle=i%2===0?'#10B981':'#EF4444';
      ctx.fillRect(bx,top+ch-5-bh,5,bh);
    }
    // Ticker line
    ctx.strokeStyle=hexA(col,0.5); ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(cx-cw/2+5,top+5);
    for (let i=0;i<10;i++) ctx.lineTo(cx-cw/2+5+i*7,top+5+Math.sin(t/200+i)*3);
    ctx.stroke();

  } else if (role==='analyst') {
    ctx.strokeStyle=hexA(col,0.25); ctx.lineWidth=0.5;
    for (let ri=1;ri<4;ri++) { ctx.beginPath(); ctx.moveTo(cx-cw/2+4,top+3+ri*4); ctx.lineTo(cx+cw/2-4,top+3+ri*4); ctx.stroke(); }
    [[6,9],[16,4],[26,11],[36,5],[46,8],[56,3]].forEach(([dx,dy]) => {
      ctx.fillStyle=hexA(col,0.8); ctx.beginPath(); ctx.arc(cx-cw/2+8+dx,top+4+dy,1.8,0,Math.PI*2); ctx.fill();
    });
    // Trend line
    ctx.strokeStyle=hexA(col,0.5); ctx.lineWidth=1.2;
    ctx.beginPath(); ctx.moveTo(cx-cw/2+8,top+13); ctx.lineTo(cx+cw/2-8,top+5); ctx.stroke();

  } else if (role==='risk') {
    const sw=(t/1100)%(Math.PI*2);
    for (let i=1;i<=3;i++) { ctx.strokeStyle=hexA(col,0.15*i); ctx.lineWidth=0.7; ctx.beginPath(); ctx.arc(cx,top+12,i*7,0,Math.PI*2); ctx.stroke(); }
    const rg=ctx.createRadialGradient(cx,top+12,0,cx,top+12,22);
    rg.addColorStop(0,hexA(col,0.35)); rg.addColorStop(1,hexA(col,0));
    ctx.fillStyle=rg; ctx.beginPath(); ctx.moveTo(cx,top+12); ctx.arc(cx,top+12,22,sw,sw+0.65); ctx.closePath(); ctx.fill();
    ctx.strokeStyle=col; ctx.lineWidth=1.2; ctx.beginPath(); ctx.moveTo(cx,top+12); ctx.lineTo(cx+Math.cos(sw)*20,top+12+Math.sin(sw)*20); ctx.stroke();
    // Alert blips
    [[1.2,0.7],[2.8,0.85],[4.5,0.6]].forEach(([a,d]) => {
      const vis=((sw-a+Math.PI*4)%(Math.PI*2))<1.6?1:0.2;
      ctx.fillStyle=hexA(col,vis); ctx.beginPath(); ctx.arc(cx+Math.cos(a)*21*d,top+12+Math.sin(a)*21*d,2,0,Math.PI*2); ctx.fill();
    });

  } else if (role==='portfolio') {
    const slices: [number, string][] = [[1.5,'#10B981'],[1.1,'#3B82F6'],[0.9,'#D4AF37'],[2.8,'#8B5CF6']];
    let sa=t/2500;
    for (const [ang,sc] of slices) {
      ctx.fillStyle=hexA(sc,0.75); ctx.beginPath(); ctx.moveTo(cx,top+12); ctx.arc(cx,top+12,10,sa,sa+ang); ctx.closePath(); ctx.fill();
      sa+=ang;
    }
    ctx.fillStyle='#091520'; ctx.beginPath(); ctx.arc(cx,top+12,4,0,Math.PI*2); ctx.fill();
    // Bar chart beside
    [0.4,0.7,0.55,0.85,0.6].forEach((v,i) => {
      ctx.fillStyle=hexA('#10B981',0.6); ctx.fillRect(cx+14+i*8,top+ch-5-v*15,5,v*15);
    });

  } else if (role==='backtest') {
    ctx.strokeStyle=hexA(col,0.35); ctx.lineWidth=1; ctx.beginPath(); ctx.arc(cx,top+12,11,0,Math.PI*2); ctx.stroke();
    const ang=(t/1400)%(Math.PI*2);
    ctx.strokeStyle=col; ctx.lineWidth=1.5; ctx.beginPath(); ctx.moveTo(cx,top+12); ctx.lineTo(cx+Math.cos(ang-Math.PI/2)*9,top+12+Math.sin(ang-Math.PI/2)*9); ctx.stroke();
    ctx.strokeStyle=hexA(col,0.55); ctx.lineWidth=1; ctx.beginPath(); ctx.moveTo(cx,top+12); ctx.lineTo(cx+Math.cos(ang*0.25-Math.PI/2)*6,top+12+Math.sin(ang*0.25-Math.PI/2)*6); ctx.stroke();
    // Tick marks
    for (let ti=0;ti<12;ti++) { const ta=ti*Math.PI/6; ctx.fillStyle=hexA(col,0.4); ctx.beginPath(); ctx.arc(cx+Math.cos(ta)*11,top+12+Math.sin(ta)*11,1,0,Math.PI*2); ctx.fill(); }
    // Rewind arc
    ctx.strokeStyle=hexA(col,0.5); ctx.lineWidth=1.5; ctx.beginPath(); ctx.arc(cx,top+12,14,2.3,5.1); ctx.stroke();

  } else if (role==='ml') {
    const nodes=[[-24,0],[-24,8],[-24,-8],[-8,4],[-8,-4],[8,4],[8,-4],[24,0]];
    ctx.strokeStyle=hexA(col,0.2); ctx.lineWidth=0.7;
    for (let i=0;i<3;i++) for (let j=3;j<5;j++) { ctx.beginPath(); ctx.moveTo(cx+nodes[i][0],top+12+nodes[i][1]); ctx.lineTo(cx+nodes[j][0],top+12+nodes[j][1]); ctx.stroke(); }
    for (let i=3;i<5;i++) for (let j=5;j<7;j++) { ctx.beginPath(); ctx.moveTo(cx+nodes[i][0],top+12+nodes[i][1]); ctx.lineTo(cx+nodes[j][0],top+12+nodes[j][1]); ctx.stroke(); }
    for (let i=5;i<7;i++) { ctx.beginPath(); ctx.moveTo(cx+nodes[i][0],top+12+nodes[i][1]); ctx.lineTo(cx+nodes[7][0],top+12+nodes[7][1]); ctx.stroke(); }
    const pi=Math.floor(t/280)%6, pt=(t%280)/280;
    const pairs=[[0,3],[1,4],[2,3],[3,5],[4,6],[5,7]];
    const [pi2,pj2]=pairs[pi];
    const plx=cx+nodes[pi2][0]+(nodes[pj2][0]-nodes[pi2][0])*pt, ply=top+12+nodes[pi2][1]+(nodes[pj2][1]-nodes[pi2][1])*pt;
    ctx.fillStyle='#FFFFFF'; ctx.beginPath(); ctx.arc(plx,ply,2.5,0,Math.PI*2); ctx.fill();
    nodes.forEach(([nx,ny]) => { ctx.fillStyle=hexA(col,0.8); ctx.beginPath(); ctx.arc(cx+nx,top+12+ny,2.2,0,Math.PI*2); ctx.fill(); });

  } else if (role==='monitor') {
    const sw2=(t/1300)%(Math.PI*2);
    for (let i=1;i<=3;i++) { ctx.strokeStyle=hexA(col,0.15*i); ctx.lineWidth=0.7; ctx.beginPath(); ctx.arc(cx,top+12,i*7,0,Math.PI*2); ctx.stroke(); }
    const sg=ctx.createRadialGradient(cx,top+12,0,cx,top+12,22);
    sg.addColorStop(0,hexA(col,0.4)); sg.addColorStop(1,hexA(col,0));
    ctx.fillStyle=sg; ctx.beginPath(); ctx.moveTo(cx,top+12); ctx.arc(cx,top+12,22,sw2,sw2+0.7); ctx.closePath(); ctx.fill();
    ctx.strokeStyle=col; ctx.lineWidth=1.2; ctx.beginPath(); ctx.moveTo(cx,top+12); ctx.lineTo(cx+Math.cos(sw2)*21,top+12+Math.sin(sw2)*21); ctx.stroke();

  } else if (role==='repair') {
    ctx.fillStyle=hexA('#F59E0B',0.25); ctx.fillRect(cx-cw/2+4,top+3,(cw-8)/2,ch-8);
    ctx.fillStyle=hexA('#EF4444',0.25); ctx.fillRect(cx,top+3,(cw-8)/2,ch-8);
    // Warning stripes
    ctx.strokeStyle=hexA('#F59E0B',0.4); ctx.lineWidth=2;
    for (let si=0;si<5;si++) { ctx.beginPath(); ctx.moveTo(cx-cw/2+4+si*12,top+3); ctx.lineTo(cx-cw/2+4+(si+1)*12,top+ch-5); ctx.stroke(); }
    ctx.fillStyle=blink2?'#F43F5E':hexA('#F43F5E',0.5); ctx.font='bold 12px monospace'; ctx.textAlign='center'; ctx.fillText('⚠',cx,top+16);

  } else if (role==='logger') {
    const la=Math.floor(t/180)%6;
    ctx.font='5px "JetBrains Mono",monospace'; ctx.textAlign='left';
    for (let li=0;li<4;li++) { ctx.fillStyle=li===la?col:hexA(col,0.28); ctx.fillText(`> LOG_${String(li).padStart(3,'0')}`,cx-cw/2+5,top+6+li*5); }
    if (blink) { ctx.fillStyle=col; ctx.fillRect(cx-cw/2+5,top+22,3,4); }

  } else if (role==='reporter') {
    // Archive scroll / document lines
    ctx.fillStyle=hexA('#F5F0E0',0.1); rr(ctx,cx-cw/2+4,top+3,cw-8,ch-8,1); ctx.fill();
    ctx.strokeStyle=hexA('#A78BFA',0.4); ctx.lineWidth=0.5;
    for (let li=0;li<4;li++) { ctx.beginPath(); ctx.moveTo(cx-cw/2+8,top+5+li*5); ctx.lineTo(cx+cw/2-8,top+5+li*5); ctx.stroke(); }
    // Quill icon hint
    ctx.strokeStyle=hexA('#A78BFA',0.7); ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(cx+cw/2-14,top+4); ctx.quadraticCurveTo(cx+cw/2-8,top+18,cx+cw/2-16,top+22); ctx.stroke();
    // Writing cursor blink
    if (blink2) { ctx.fillStyle='#A78BFA'; ctx.fillRect(cx-cw/2+8,top+21,8,1); }

  } else if (role==='alerter') {
    // Alert bell animation
    const bell = Math.sin(t/200)*0.2;
    ctx.strokeStyle=hexA(col,0.5); ctx.lineWidth=1.5;
    ctx.save(); ctx.translate(cx,top+12); ctx.rotate(bell);
    ctx.beginPath(); ctx.arc(0,-2,7,Math.PI,Math.PI*2); ctx.lineTo(7,6); ctx.lineTo(-7,6); ctx.closePath(); ctx.stroke();
    ctx.beginPath(); ctx.arc(0,8,2,0,Math.PI*2); ctx.stroke();
    ctx.restore();
    // Alert rings
    if (blink) { const rg=ctx.createRadialGradient(cx,top+12,4,cx,top+12,20); rg.addColorStop(0,hexA(col,0.4)); rg.addColorStop(1,hexA(col,0)); ctx.fillStyle=rg; ctx.beginPath(); ctx.arc(cx,top+12,20,0,Math.PI*2); ctx.fill(); }
  }

  // Desk bottom (keyboard)
  ctx.fillStyle='#0E2038'; rr(ctx,cx-cw/2,top+ch,cw,7,2); ctx.fill();
  ctx.strokeStyle=hexA(col,0.2); ctx.lineWidth=0.5; ctx.stroke();
  // Keys
  for (let ki=0;ki<5;ki++) {
    ctx.fillStyle=ki===2&&blink2?col:hexA(col,0.25);
    rr(ctx,cx-cw/2+4+ki*14,top+ch+1,11,5,1); ctx.fill();
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   PIXEL ART CHARACTERS  (base + per-role)
   Anchor (cx, cy) = waist. Char spans cy-14*CP..cy+8*CP (22 game-px = 66 canvas-px)
═══════════════════════════════════════════════════════════════════════════ */

/**
 * Base character body.
 * sit=true  → seated pose (L-shaped legs, arms resting on lap)
 * sit=false → standing pose with optional working-arm animation
 * armT is used to animate arms when working (pass `now`)
 */
function base(
  ctx: CanvasRenderingContext2D,
  cx: number, cy: number,
  uniform: string,
  leg: string = '#0D1A28',
  accent: string = uniform,
  sit: boolean = false,
  working: boolean = false,
  armT: number = 0,
) {
  // ── Body ──────────────────────────────────────────────────────────
  g(ctx,cx,cy, -4,-6, 8,5, uniform);

  // ── Arms ──────────────────────────────────────────────────────────
  if (sit) {
    // Resting on lap: arms lower, forearms horizontal
    g(ctx,cx,cy, -5,-4, 1,2, accent);
    g(ctx,cx,cy,  4,-4, 1,2, accent);
    g(ctx,cx,cy, -6,-2, 2,1, accent); // L forearm on lap
    g(ctx,cx,cy,  4,-2, 2,1, accent); // R forearm on lap
    g(ctx,cx,cy, -6,-2, 1,1, SKIN);   // L hand
    g(ctx,cx,cy,  5,-2, 1,1, SKIN);   // R hand
  } else {
    // Standing – alternate L/R arm when working (2-frame typing anim)
    const frame = working ? Math.floor(armT / 420) % 2 : 0;
    const lOff  = working ? (frame === 0 ? -1 : 0) : 0; // L arm up on frame 0
    const rOff  = working ? (frame === 1 ? -1 : 0) : 0; // R arm up on frame 1
    g(ctx,cx,cy, -5,-6+lOff, 1,5, accent);
    g(ctx,cx,cy,  4,-6+rOff, 1,5, accent);
    g(ctx,cx,cy, -5,-1+lOff, 1,1, SKIN);
    g(ctx,cx,cy,  4,-1+rOff, 1,1, SKIN);
  }

  // ── Neck + face ───────────────────────────────────────────────────
  g(ctx,cx,cy, -1,-6, 2,1, SKIN);
  g(ctx,cx,cy, -4,-11, 8,5, SKIN);
  g(ctx,cx,cy, -5,-10, 1,2, SKIN); // ears
  g(ctx,cx,cy,  4,-10, 1,2, SKIN);
  g(ctx,cx,cy, -3,-10, 1,1, EYE);
  g(ctx,cx,cy,  2,-10, 1,1, EYE);
  // Expression: relaxed when sitting, focused when working
  if (sit) {
    g(ctx,cx,cy, -1,-8, 3,1, '#996622'); // neutral/slight smile
  } else {
    g(ctx,cx,cy, -1,-8, 2,1, '#BB4422'); // focused mouth
  }

  // ── Legs ──────────────────────────────────────────────────────────
  if (sit) {
    // L-shaped seated legs
    g(ctx,cx,cy, -5,-1, 4,2, leg); // L thigh (horizontal)
    g(ctx,cx,cy,  1,-1, 4,2, leg); // R thigh (horizontal)
    g(ctx,cx,cy, -5, 1, 2,4, leg); // L shin (vertical, from outer knee)
    g(ctx,cx,cy,  3, 1, 2,4, leg); // R shin
    g(ctx,cx,cy, -6, 5, 4,2, '#080E1A'); // L boot (pointing forward)
    g(ctx,cx,cy,  2, 5, 4,2, '#080E1A'); // R boot
  } else {
    // Standing legs
    g(ctx,cx,cy, -4,-1, 3,6, leg);
    g(ctx,cx,cy,  1,-1, 3,6, leg);
    g(ctx,cx,cy, -4, 5, 4,2, '#080E1A');
    g(ctx,cx,cy,  0, 5, 4,2, '#080E1A');
  }
}

function drawCaptain(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, status:string) {
  const sit = status==='idle'||status==='waiting';
  const working = status==='running';
  // Elaborate admiral hat
  g(ctx,cx,cy, -5,-16, 10,1, '#D4AF37'); // gold top bar
  g(ctx,cx,cy, -4,-15,  8,3, '#0C1A35'); // navy hat body
  g(ctx,cx,cy, -3,-14,  6,1, '#D4AF37'); // gold stripe 1
  g(ctx,cx,cy, -2,-13,  4,1, '#C4A027'); // gold stripe 2
  g(ctx,cx,cy, -6,-12, 12,1, '#0C1A35'); // wide brim

  base(ctx, cx, cy, '#14284A', '#0A1830', '#D4AF37', sit, working, t);

  // Gold collar trim
  g(ctx,cx,cy, -4,-6, 8,1, '#D4AF37');
  // Chest medal / badge
  g(ctx,cx,cy, -2,-5, 4,1, '#D4AF37');
  g(ctx,cx,cy, -1,-4, 2,1, '#FFE860');
  // Epaulettes (gold pads on shoulders)
  g(ctx,cx,cy, -6,-6, 2,2, '#C4A027');
  g(ctx,cx,cy,  4,-6, 2,2, '#C4A027');
  // Cape hint (dark behind body)
  g(ctx,cx,cy, -5,-6, 1,5, '#09182A');
  g(ctx,cx,cy,  4,-6, 1,5, '#09182A');
  // Gold trouser stripe
  g(ctx,cx,cy, -4,-1, 1,6, '#D4AF37');
  g(ctx,cx,cy,  3,-1, 1,6, '#D4AF37');
  // Eyebrows (stern look)
  g(ctx,cx,cy, -3,-11, 2,1, '#1A0800');
  g(ctx,cx,cy,  1,-11, 2,1, '#1A0800');
  // Stars on epaulettes blink
  if (status==='running'&&Math.sin(t/350)>0) { g(ctx,cx,cy,-6,-7,1,1,'#FFE860'); g(ctx,cx,cy,5,-7,1,1,'#FFE860'); }
  // Telescoping baton in hand
  g(ctx,cx,cy,  4,-5, 3,4, '#8090A0');
  g(ctx,cx,cy,  4,-5, 3,1, '#D4AF37');
}

function drawMarket(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, status:string) {
  const sit = status==='idle'||status==='waiting';
  const working = status==='running';
  // Flat-top hair
  g(ctx,cx,cy, -4,-12, 8,1, '#180C00');
  // Headset band (cyan) across top
  g(ctx,cx,cy, -4,-12, 8,1, '#00AABB');
  // Earpiece left + right
  g(ctx,cx,cy, -6,-11, 2,3, '#00889A');
  g(ctx,cx,cy,  4,-11, 2,3, '#00889A');
  // Mic boom (right side)
  g(ctx,cx,cy,  5,-9, 3,1, '#004A55');
  g(ctx,cx,cy,  7,-9, 1,1, '#00D4FF');

  base(ctx,cx,cy,'#00263A','#001825','#00A0C0',sit,working,t);

  // Collar
  g(ctx,cx,cy,-3,-6,6,1,'#00D4FF');
  // Data visor over left eye
  g(ctx,cx,cy,-4,-10,2,1,'#001A25');
  g(ctx,cx,cy,-4,-10,2,1,hexA('#00D4FF',0.45));
  // Suit tech stripes
  g(ctx,cx,cy, 3,-5,1,4,'#00AACC');
  g(ctx,cx,cy,-4,-5,1,4,'#00AACC');
  // Floating data tablet in L hand (animated scroll)
  g(ctx,cx,cy,-8,-4,3,4,'#001220');
  g(ctx,cx,cy,-8,-4,3,1,hexA('#00D4FF',0.6));
  const td=Math.floor(t/250)%3;
  g(ctx,cx,cy,-8,-4+td,3,1,hexA('#00D4FF',0.35));
  // Eyebrow
  g(ctx,cx,cy,-3,-11,2,1,'#100600');
  g(ctx,cx,cy, 1,-11,2,1,'#100600');
}

function drawAnalyst(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, status:string) {
  const sit = status==='idle'||status==='waiting';
  const working = status==='running';
  // Hair (neat, parted)
  g(ctx,cx,cy,-4,-12,8,1,'#150C00');
  g(ctx,cx,cy,-4,-11,4,1,'#201000');
  g(ctx,cx,cy, 0,-11,4,1,'#201000');
  // Side hair
  g(ctx,cx,cy,-5,-11,1,3,'#180E00');
  g(ctx,cx,cy, 4,-11,1,3,'#180E00');

  base(ctx,cx,cy,'#C8DCE8','#0D1A28','#A0B8C8',sit,working,t);

  // Blue shirt visible at collar
  g(ctx,cx,cy,-2,-6,4,1,'#2255A0');
  // White coat (lighter lapels)
  g(ctx,cx,cy,-4,-6,1,5,'#B8CCD8');
  g(ctx,cx,cy, 3,-6,1,5,'#B8CCD8');
  // Belt
  g(ctx,cx,cy,-4,-2,8,1,'#506070');
  // Glasses frames
  g(ctx,cx,cy,-4,-10,3,1,'#161616');
  g(ctx,cx,cy, 1,-10,3,1,'#161616');
  g(ctx,cx,cy,-1,-10,1,1,'#161616');
  // Pocket pen set
  g(ctx,cx,cy,-3,-3,1,3,'#4466FF');
  g(ctx,cx,cy,-2,-3,1,3,'#FF4466');
  // Clipboard in R hand
  g(ctx,cx,cy, 4,-5,3,4,'#C8A050');
  g(ctx,cx,cy, 4,-5,3,1,'#1A44AA');
  g(ctx,cx,cy, 4,-4,3,1,hexA('#3B82F6',0.5));
  g(ctx,cx,cy, 5,-3,1,1,'#FFE860');
}

function drawRisk(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, status:string) {
  const sit = status==='idle'||status==='waiting';
  const working = status==='running';
  // Helmet (bulky, military)
  g(ctx,cx,cy,-5,-16,10,4,'#7A0000');
  g(ctx,cx,cy,-4,-13, 8,2,'#A00000');
  g(ctx,cx,cy,-6,-13,12,1,'#600000'); // helmet brim
  // Visor (dark red)
  g(ctx,cx,cy,-4,-12, 8,2,'#1A0000');
  g(ctx,cx,cy,-4,-12, 8,2,hexA('#EF4444',0.2));
  if (status==='running') g(ctx,cx,cy,-4,-12,8,2,hexA('#EF4444',Math.sin(t/300)*0.2+0.2));
  // Chin strap
  g(ctx,cx,cy,-4,-10, 1,3,'#600000');
  g(ctx,cx,cy, 3,-10, 1,3,'#600000');

  base(ctx,cx,cy,'#3A0000','#1A0000','#600000',sit,working,t);

  // Armor chest plate
  g(ctx,cx,cy,-3,-6,6,1,'#5A0000');
  g(ctx,cx,cy,-3,-5,6,4,'#480000');
  // Shield emblem on chest
  g(ctx,cx,cy,-1,-5,2,1,'#EF4444');
  g(ctx,cx,cy,-1,-4,2,1,'#EF4444');
  // Knee pads
  g(ctx,cx,cy,-4, 1,3,2,'#5A0000');
  g(ctx,cx,cy, 1, 1,3,2,'#5A0000');
  // Shoulder armor spikes
  g(ctx,cx,cy,-6,-6,2,1,'#6B0000');
  g(ctx,cx,cy, 4,-6,2,1,'#6B0000');
  g(ctx,cx,cy,-7,-7,1,1,'#AA1010');
  g(ctx,cx,cy, 6,-7,1,1,'#AA1010');
  // Alert flash on helmet top
  if (status==='error'&&Math.sin(t/120)>0) g(ctx,cx,cy,-1,-17,2,1,'#FF3333');
  // Heavy boots (wider)
  g(ctx,cx,cy,-5,5,5,3,'#0A0000');
  g(ctx,cx,cy, 0,5,5,3,'#0A0000');
}

function drawPortfolio(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, status:string) {
  const sit = status==='idle'||status==='waiting';
  const working = status==='running';
  // Slick pompadour hair
  g(ctx,cx,cy,-4,-14,8,3,'#0A0500');
  g(ctx,cx,cy,-3,-12,6,1,'#150A00');
  g(ctx,cx,cy,-2,-11,4,1,'#0A0500');
  // Side burns
  g(ctx,cx,cy,-5,-11,1,3,'#0A0500');
  g(ctx,cx,cy, 4,-11,1,3,'#0A0500');

  base(ctx,cx,cy,'#0C2818','#081A10','#185030',sit,working,t);

  // Suit lapels
  g(ctx,cx,cy,-4,-6,1,5,'#163C22');
  g(ctx,cx,cy, 3,-6,1,5,'#163C22');
  // White shirt
  g(ctx,cx,cy,-2,-6,4,5,'#B0DCC0');
  // Tie (green)
  g(ctx,cx,cy,-1,-6,2,4,'#10B981');
  g(ctx,cx,cy, 0,-6,1,4,'#0D8060');
  // Pocket square
  g(ctx,cx,cy,-3,-3,1,2,'#10B981');
  // Monocle hint
  g(ctx,cx,cy, 2,-9,2,2,'#0A1A0A');
  g(ctx,cx,cy, 2,-9,2,2,hexA('#10B981',0.35));
  // Holographic briefcase (L hand, animated)
  g(ctx,cx,cy,-8,-5,3,4,'#081A10');
  g(ctx,cx,cy,-8,-5,3,3,hexA('#10B981',0.4));
  const pa=(t/2500)%(Math.PI*2);
  ctx.fillStyle=hexA('#10B981',0.5); ctx.beginPath(); ctx.moveTo(cx-5*CP,cy-4*CP); ctx.arc(cx-5*CP,cy-4*CP,CP*1.2,pa,pa+2); ctx.closePath(); ctx.fill();
}

function drawBacktest(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, status:string) {
  const sit = status==='idle'||status==='waiting';
  const working = status==='running';
  // Hair
  g(ctx,cx,cy,-4,-12,8,2,'#201408');
  // Goggles on forehead (amber)
  g(ctx,cx,cy,-4,-12,8,2,'#D4800A');
  g(ctx,cx,cy,-3,-12,3,2,hexA('#F59E0B',0.5));
  g(ctx,cx,cy, 0,-12,3,2,hexA('#F59E0B',0.5));
  // Headband
  g(ctx,cx,cy,-5,-12,1,2,'#8B6030');
  g(ctx,cx,cy, 4,-12,1,2,'#8B6030');

  base(ctx,cx,cy,'#2A1A08','#1A1008','#F59E0B',sit,working,t);

  // Engineer vest with pockets
  g(ctx,cx,cy,-3,-6,6,5,'#3A2210');
  g(ctx,cx,cy,-4,-6,1,5,'#2A1A08');
  g(ctx,cx,cy, 3,-6,1,5,'#2A1A08');
  // Pockets
  g(ctx,cx,cy,-3,-4,2,2,'#1A1008');
  g(ctx,cx,cy, 1,-4,2,2,'#1A1008');
  // Tool belt
  g(ctx,cx,cy,-4,-2,8,1,'#1A1008');
  g(ctx,cx,cy,-3,-2,1,1,'#F59E0B');
  g(ctx,cx,cy, 2,-2,1,1,'#F59E0B');
  // Rolled-up sleeves
  g(ctx,cx,cy,-5,-4,1,2,'#FFCFA0');
  g(ctx,cx,cy, 4,-4,1,2,'#FFCFA0');
  // Wrench in R hand (animated)
  const wr=Math.sin(t/700)*0.25;
  ctx.save(); ctx.translate(cx+5*CP, cy-3*CP); ctx.rotate(wr);
  ctx.fillStyle='#909AB0'; ctx.fillRect(-CP/2,-4*CP,CP,6*CP);
  ctx.fillRect(-2*CP,-4*CP,4*CP,CP); ctx.fillRect(-2*CP,2*CP,4*CP,CP); ctx.restore();
}

function drawML(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, status:string) {
  const sit = status==='idle'||status==='waiting';
  const working = status==='running';
  // Shaved head / dark
  g(ctx,cx,cy,-4,-12,8,2,'#100520');
  // Neural crown/halo device
  g(ctx,cx,cy,-5,-14,10,1,'#4B1080');
  g(ctx,cx,cy,-4,-15, 8,1,'#6B20A0');
  g(ctx,cx,cy,-3,-16, 6,1,'#8B35C0');
  // Neural nodes on crown
  for (let i=0;i<5;i++) { const blink=Math.sin(t/300+i*1.3)>0; g(ctx,cx,cy,-4+i*2,-16,1,1,blink?'#C060FF':hexA('#8B5CF6',0.4)); }
  // Side implant wires
  g(ctx,cx,cy,-6,-11,1,4,'#3B0070');
  g(ctx,cx,cy, 5,-11,1,4,'#3B0070');

  base(ctx,cx,cy,'#1E0840','#0E0420','#8B5CF6',sit,working,t);

  // Robe collar
  g(ctx,cx,cy,-4,-6,8,1,'#2A0860');
  // Circuit lines on robe
  g(ctx,cx,cy,-2,-5,1,4,hexA('#8B5CF6',0.3));
  g(ctx,cx,cy, 1,-5,1,4,hexA('#8B5CF6',0.3));
  g(ctx,cx,cy,-3,-3,6,1,hexA('#8B5CF6',0.2));
  // Cybernetic left eye
  g(ctx,cx,cy,-3,-10,1,1,'#8B5CF6');
  if (status==='running') {
    const eg=ctx.createRadialGradient(cx-2*CP,cy-10*CP,0,cx-2*CP,cy-10*CP,CP*3);
    eg.addColorStop(0,hexA('#8B5CF6',0.9)); eg.addColorStop(1,'transparent');
    ctx.fillStyle=eg; ctx.fillRect(cx-5*CP,cy-13*CP,6*CP,6*CP);
  }
  // Data orb in L hand
  const og=Math.sin(t/450)*0.3+0.7;
  const orbG=ctx.createRadialGradient(cx-6*CP,cy-4*CP,0,cx-6*CP,cy-4*CP,CP*2.5);
  orbG.addColorStop(0,hexA('#8B5CF6',og)); orbG.addColorStop(1,hexA('#8B5CF6',0));
  ctx.fillStyle=orbG; ctx.fillRect(cx-9*CP,cy-7*CP,6*CP,6*CP);
  g(ctx,cx,cy,-7,-5,3,3,hexA('#8B5CF6',og*0.2));
}

function drawMonitor(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, status:string) {
  const sit = status==='idle'||status==='waiting';
  const working = status==='running';
  // Hair (dark, short)
  g(ctx,cx,cy,-4,-12,8,2,'#060608');
  // Full tactical visor
  g(ctx,cx,cy,-5,-11,10,2,'#10142A');
  g(ctx,cx,cy,-5,-11,10,2,hexA('#6366F1',0.22));
  // Visor HUD line (animated)
  g(ctx,cx,cy,-4,-11,8,1,hexA('#6366F1',Math.sin(t/280)*0.3+0.4));
  g(ctx,cx,cy,-2,-10,4,1,hexA('#00FFFF',0.3));

  base(ctx,cx,cy,'#0C1030','#060814','#1E2550',sit,working,t);

  // Hexagonal armor pattern
  g(ctx,cx,cy,-4,-6,2,2,'#162050');
  g(ctx,cx,cy,-2,-6,2,2,'#0E1840');
  g(ctx,cx,cy, 0,-6,2,2,'#162050');
  g(ctx,cx,cy, 2,-6,2,2,'#0E1840');
  // Shoulder comms array
  g(ctx,cx,cy,-6,-6,2,1,'#1E2550');
  g(ctx,cx,cy, 4,-6,2,1,'#1E2550');
  g(ctx,cx,cy,-6,-7,1,1,'#6366F1');
  g(ctx,cx,cy, 5,-7,1,1,hexA('#6366F1',Math.sin(t/350)*0.5+0.5));
  // Tech patches on arms
  g(ctx,cx,cy,-5,-4,1,1,'#6366F1');
  g(ctx,cx,cy, 4,-4,1,1,'#6366F1');
  // Back-mounted radar dish suggestion
  g(ctx,cx,cy, 5,-6,2,3,'#0C1430');
  g(ctx,cx,cy, 6,-8,1,1,hexA('#6366F1',Math.sin(t/400)*0.5+0.5));
}

function drawRepair(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, status:string) {
  const sit = status==='idle'||status==='waiting';
  const working = status==='running';
  // Hair
  g(ctx,cx,cy,-4,-12,8,2,'#180C04');
  // Safety goggles (orange lenses)
  g(ctx,cx,cy,-5,-12,10,2,'#D4700A');
  g(ctx,cx,cy,-4,-12,4,2,hexA('#FF8C00',0.45));
  g(ctx,cx,cy, 0,-12,4,2,hexA('#FF8C00',0.45));

  base(ctx,cx,cy,'#6A2200','#2A0E00','#F43F5E',sit,working,t);

  // Hazmat stripes
  g(ctx,cx,cy,-4,-6,8,1,'#F59E0B');
  g(ctx,cx,cy,-4,-2,8,1,'#F59E0B');
  // Radiation symbol hint
  g(ctx,cx,cy,-1,-5,2,1,'#F43F5E');
  // Heavy gloves
  g(ctx,cx,cy,-6,-1,2,2,'#3A1800');
  g(ctx,cx,cy, 4,-1,2,2,'#3A1800');
  // Boots with treads
  g(ctx,cx,cy,-5,5,5,3,'#180800');
  g(ctx,cx,cy, 0,5,5,3,'#180800');
  g(ctx,cx,cy,-5,7,5,1,'#F59E0B');
  g(ctx,cx,cy, 0,7,5,1,'#F59E0B');
  // Wrench + sparks
  ctx.fillStyle='#8090A0';
  ctx.fillRect(cx+5*CP,cy-6*CP,CP,6*CP);
  ctx.fillRect(cx+3*CP,cy-6*CP,4*CP,CP);
  ctx.fillRect(cx+3*CP,cy-2*CP,4*CP,CP);
  if (status==='running') {
    for (let i=0;i<4;i++) {
      const sa=(t/160+i*1.6)%(Math.PI*2), sd=CP+Math.random()*CP*2.5;
      ctx.fillStyle=hexA('#F59E0B',0.9);
      ctx.fillRect(cx+6*CP+Math.cos(sa)*sd,cy-4*CP+Math.sin(sa)*sd,CP,CP);
    }
  }
}

function drawLogger(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, status:string) {
  const sit = status==='idle'||status==='waiting';
  const working = status==='running';
  // Hair
  g(ctx,cx,cy,-4,-12,8,2,'#0C0806');
  // Large antenna headset
  g(ctx,cx,cy,-6,-12,12,1,'#3A4A5A'); // band
  g(ctx,cx,cy,-6,-11, 2,3,'#3A4A5A'); // L earpiece
  g(ctx,cx,cy, 4,-11, 2,3,'#3A4A5A'); // R earpiece
  // Main antenna tower
  g(ctx,cx,cy,-1,-16, 2,4,'#4A5A6A');
  g(ctx,cx,cy,-2,-17, 4,1,'#5A6A7A');
  g(ctx,cx,cy, 0,-18, 1,2,hexA('#64748B',Math.sin(t/350)*0.5+0.5)); // blinking tip
  // Side antenna dish
  g(ctx,cx,cy,-9,-13, 3,2,'#3A4A5A');
  g(ctx,cx,cy,-9,-12, 3,1,hexA('#64748B',0.4));
  // Mic boom
  g(ctx,cx,cy,-8,-11, 4,1,'#2A3A4A');
  g(ctx,cx,cy,-8,-11, 1,1,'#64748B');

  base(ctx,cx,cy,'#0A1A28','#060E18','#64748B',sit,working,t);

  // Comms insignia stripes
  g(ctx,cx,cy,-3,-5,6,1,'#64748B');
  g(ctx,cx,cy,-3,-3,6,1,'#3A4A5A');
  // Signal waves from headset (animated)
  ctx.strokeStyle=hexA('#64748B',0.35*(Math.sin(t/450)*0.5+0.5)); ctx.lineWidth=0.8;
  for (let i=1;i<=3;i++) { ctx.beginPath(); ctx.arc(cx-7*CP,cy-12*CP,i*5,-1,1); ctx.stroke(); }
  // Recording light
  const recOn=Math.sin(t/600)>0;
  g(ctx,cx,cy, 3,-6,1,1,recOn?'#EF4444':hexA('#EF4444',0.25));
}

function drawReporter(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, status:string) {
  const sit = status==='idle'||status==='waiting';
  const working = status==='running';
  // Tall archivist hat (dark purple with gold trim)
  g(ctx,cx,cy,-3,-17, 6,5,'#1A0A28');
  g(ctx,cx,cy,-2,-16, 4,4,'#220D35');
  g(ctx,cx,cy,-4,-12, 8,1,'#1A0A28'); // wide brim
  g(ctx,cx,cy,-3,-13, 6,1,'#A78BFA'); // gold-purple band

  // Spectacles (round, double)
  g(ctx,cx,cy,-4,-10,3,2,'#2A1840');
  g(ctx,cx,cy, 1,-10,3,2,'#2A1840');
  g(ctx,cx,cy,-1,-10,1,1,'#2A1840'); // bridge

  // Hair (grey, elderly archivist vibe)
  g(ctx,cx,cy,-5,-11,1,4,'#8090A0');
  g(ctx,cx,cy, 4,-11,1,4,'#8090A0');
  g(ctx,cx,cy,-4,-11,1,1,'#8090A0');
  g(ctx,cx,cy, 3,-11,1,1,'#8090A0');

  base(ctx,cx,cy,'#20103A','#10081E','#A78BFA',sit,working,t);

  // Academic robe lapels
  g(ctx,cx,cy,-4,-6,1,5,'#2E1550');
  g(ctx,cx,cy, 3,-6,1,5,'#2E1550');
  // Gold chain across chest
  g(ctx,cx,cy,-2,-5,4,1,hexA('#D4AF37',0.6));
  // Quill in R hand
  g(ctx,cx,cy, 4,-6,1,5,'#C8D0A0');
  g(ctx,cx,cy, 5,-6,2,1,'#8090A0'); // feather tip
  // Scroll in L hand
  g(ctx,cx,cy,-8,-5,3,5,'#D8C090');
  g(ctx,cx,cy,-8,-5,3,1,'#A08040');
  g(ctx,cx,cy,-8,-1,3,1,'#A08040');
  g(ctx,cx,cy,-7,-4,2,3,'#E8D0A0');
}

function drawAlerter(ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, status:string) {
  const sit = status==='idle'||status==='waiting';
  const working = status==='running';
  // Herald hood/cowl
  g(ctx,cx,cy,-5,-15,10,5,'#7C2500');
  g(ctx,cx,cy,-4,-11, 8,1,'#5C1800');
  g(ctx,cx,cy,-3,-12, 6,1,'#FB923C'); // orange inner band
  // Horn/bugle on side
  g(ctx,cx,cy, 5,-13, 4,1,'#C06010');
  g(ctx,cx,cy, 6,-14, 5,1,'#C06010');
  g(ctx,cx,cy, 9,-15, 2,1,'#FB923C');
  // Bell flash from horn (animated)
  if (status==='running'||Math.sin(t/200)>0.5) {
    ctx.fillStyle=hexA('#FB923C',0.4); ctx.beginPath(); ctx.arc(cx+11*CP,cy-15*CP,CP*3,0,Math.PI*2); ctx.fill();
  }

  base(ctx,cx,cy,'#5C1A00','#3A1000','#FB923C',sit,working,t);

  // Tabard / herald vest
  g(ctx,cx,cy,-3,-6,6,1,'#FB923C');
  g(ctx,cx,cy,-3,-5,6,4,'#7C2500');
  g(ctx,cx,cy,-2,-4,4,2,'#FB923C'); // diamond pattern
  g(ctx,cx,cy,-1,-3,2,2,'#5C1800');
  // Alert bell in L hand
  const bs=Math.sin(t/180)*0.3;
  ctx.save(); ctx.translate(cx-6*CP,cy-4*CP); ctx.rotate(bs);
  ctx.strokeStyle=hexA('#FB923C',0.8); ctx.lineWidth=1.5;
  ctx.beginPath(); ctx.arc(0,0,CP*2,-Math.PI,0); ctx.lineTo(CP*2,CP*2); ctx.lineTo(-CP*2,CP*2); ctx.closePath(); ctx.stroke();
  ctx.restore();
  // Warning aura when running
  if (status==='running') {
    const wa=Math.sin(t/200)*0.3+0.2;
    const wg=ctx.createRadialGradient(cx,cy,0,cx,cy,40);
    wg.addColorStop(0,hexA('#FB923C',wa)); wg.addColorStop(1,hexA('#FB923C',0));
    ctx.fillStyle=wg; ctx.beginPath(); ctx.arc(cx,cy,40,0,Math.PI*2); ctx.fill();
  }
}

const CHAR_FNS: Record<Role, (ctx:CanvasRenderingContext2D, cx:number, cy:number, t:number, status:string)=>void> = {
  captain:   drawCaptain,
  market:    drawMarket,
  analyst:   drawAnalyst,
  risk:      drawRisk,
  portfolio: drawPortfolio,
  backtest:  drawBacktest,
  ml:        drawML,
  monitor:   drawMonitor,
  repair:    drawRepair,
  logger:    drawLogger,
  reporter:  drawReporter,
  alerter:   drawAlerter,
};

/* ═══════════════════════════════════════════════════════════════════════════
   FLOW LINES
═══════════════════════════════════════════════════════════════════════════ */
function drawFlows(ctx:CanvasRenderingContext2D, states:Record<string,AgentState>, t:number) {
  const orch = AGENTS.OrchestratorAgent;
  ctx.lineWidth=1;
  const off=-(t/75);
  for (const [name,ag] of Object.entries(AGENTS)) {
    if (name==='OrchestratorAgent') continue;
    const state=states[name];
    const active=state&&(state.status==='running'||state.status==='completed');
    ctx.strokeStyle=hexA(ag.color,active?0.5:0.1);
    ctx.setLineDash([2,6]); ctx.lineDashOffset=off;
    ctx.beginPath();
    const mx=(orch.x+ag.x)/2, my=(orch.y+ag.y)/2-18;
    ctx.moveTo(orch.x,orch.y); ctx.quadraticCurveTo(mx,my,ag.x,ag.y); ctx.stroke();
  }
  ctx.setLineDash([]); ctx.lineDashOffset=0;
}

/* ═══════════════════════════════════════════════════════════════════════════
   MAIN COMPONENT
═══════════════════════════════════════════════════════════════════════════ */
export function AgentCanvas({ agentStates }: AgentCanvasProps) {
  const canvasRef  = useRef<HTMLCanvasElement>(null);
  const rafRef     = useRef<number>(0);
  const statesRef  = useRef(agentStates);
  const particles  = useRef<Particle[]>([]);
  const frames     = useRef(0);

  useEffect(() => { statesRef.current = agentStates; }, [agentStates]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.imageSmoothingEnabled = false;

    function draw(now:number) {
      if (!ctx||!canvas) return;
      frames.current++;
      const states = statesRef.current;

      /* background */
      ctx.fillStyle=DARK; ctx.fillRect(0,0,W,H);
      drawSpace(ctx,now);
      drawHull(ctx,now);
      drawCorridorLife(ctx,now);

      /* rooms */
      for (const room of ROOMS) {
        const ag = AGENTS[room.agent];
        if (!ag) continue;
        const state = states[room.agent] ?? { status:'idle', progress:0, lastEvent:'', lastData:{} };
        drawRoom(ctx,room,ag,state,now);
      }

      /* data flows */
      drawFlows(ctx,states,now);

      /* agents */
      for (const [name,ag] of Object.entries(AGENTS)) {
        const state = states[name] ?? { status:'idle', progress:0, lastEvent:'', lastData:{} };
        const { x,y,color,role } = ag;
        const status  = state.status;
        const progress= state.progress;

        let dy=0, dx=0, alpha=1;
        if (status==='running')      { dy=Math.sin(now/380+x*0.06)*1.8; } // bob while working
        else if (status==='waiting') { alpha=0.55+Math.sin(now/800)*0.1; } // seated, dimmed
        else if (status==='completed'){ dy=Math.sin(now/900)*0.5; }        // standing, slight sway
        else if (status==='error')   { dx=Math.sin(now/55)*2.5; }          // shake
        else if (status==='idle')    { alpha=0.4; }                         // seated, dim

        ctx.globalAlpha = alpha;

        /* floor glow */
        if (status==='running'||status==='completed') {
          const gr=32+(status==='running'?Math.sin(now/260)*7:0);
          const glow=ctx.createRadialGradient(x+dx,y+dy,0,x+dx,y+dy,gr);
          glow.addColorStop(0,hexA(color,0.25)); glow.addColorStop(1,hexA(color,0));
          ctx.fillStyle=glow; ctx.beginPath(); ctx.arc(x+dx,y+dy,gr,0,Math.PI*2); ctx.fill();
        }

        drawConsole(ctx,x+dx,y+dy,role,color,now);
        CHAR_FNS[role]?.(ctx,x+dx,y+dy,now,status);

        /* spinning ring when active */
        if (status==='running') {
          const ra=(now/650)%(Math.PI*2);
          ctx.strokeStyle=hexA(color,(Math.sin(now/320)+1)/2*0.5);
          ctx.lineWidth=1.5; ctx.setLineDash([3,6]);
          ctx.beginPath(); ctx.arc(x+dx,y+dy,30,ra,ra+Math.PI*1.5); ctx.stroke();
          ctx.setLineDash([]);
          if (frames.current%5===0) particles.current.push(mkP(x+dx,y+dy,color));
        }

        /* error flash */
        if (status==='error') {
          const f=Math.sin(now/140);
          if (f>0) { ctx.strokeStyle=hexA('#EF4444',f*0.7); ctx.lineWidth=2; ctx.beginPath(); ctx.arc(x+dx,y+dy,28,0,Math.PI*2); ctx.stroke(); }
        }

        /* name label (larger, readable) */
        ctx.globalAlpha=alpha*0.95;
        ctx.font='bold 9px "JetBrains Mono",monospace';
        ctx.textAlign='center';
        const lw2=ctx.measureText(ag.name).width;
        ctx.fillStyle=hexA(DARK,0.55); rr(ctx,x+dx-lw2/2-4,y+43,lw2+8,12,2); ctx.fill();
        ctx.fillStyle=status==='idle'?'#475569':color;
        ctx.fillText(ag.name,x+dx,y+53);

        /* status text */
        ctx.globalAlpha=alpha*0.55;
        ctx.font='7px "JetBrains Mono",monospace';
        ctx.fillStyle='#64748B';
        ctx.fillText(status.toUpperCase(),x+dx,y+64);

        /* progress bar */
        if (progress>0) {
          const bw=42,bh=3,bx=x+dx-bw/2,by=y+67;
          ctx.globalAlpha=0.18; ctx.fillStyle='#1A2332'; rr(ctx,bx,by,bw,bh,1); ctx.fill();
          ctx.globalAlpha=alpha;
          ctx.fillStyle=status==='error'?'#EF4444':color;
          rr(ctx,bx,by,bw*Math.min(progress,1),bh,1); ctx.fill();
        }

        ctx.globalAlpha=1;
      }

      /* particles */
      const ps=particles.current;
      for (let i=ps.length-1;i>=0;i--) {
        const p=ps[i]; p.x+=p.vx; p.y+=p.vy; p.life++;
        if (p.life>p.max) { ps.splice(i,1); continue; }
        const f=1-p.life/p.max;
        ctx.fillStyle=hexA(p.color,f*0.65);
        ctx.fillRect(p.x,p.y,p.sz*f+0.5,p.sz*f+0.5);
      }

      /* scanline */
      const sy=(now/20)%H;
      ctx.strokeStyle='rgba(0,200,255,0.02)'; ctx.lineWidth=1;
      ctx.beginPath(); ctx.moveTo(0,sy); ctx.lineTo(W,sy); ctx.stroke();

      /* HUD corner */
      ctx.font='6px "JetBrains Mono",monospace'; ctx.textAlign='right';
      ctx.fillStyle='rgba(0,160,220,0.18)';
      ctx.fillText(`SYS:NOMINAL  CREW:${Object.keys(AGENTS).length}  T+${Math.floor(now/1000)}s`,W-18,86);

      rafRef.current=requestAnimationFrame(draw);
    }

    rafRef.current=requestAnimationFrame(draw);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  return (
    <div style={{ borderRadius:8, overflow:'hidden', border:'1px solid #1A2332', width:'100%', background:'#04060C' }}>
      <canvas
        ref={canvasRef}
        width={W} height={H}
        style={{ width:'100%', height:'auto', display:'block', imageRendering:'pixelated' }}
      />
    </div>
  );
}
