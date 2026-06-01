"""
auth_ui.py — Page de connexion Ravinala.
Theme : "Cosmic Tropical" — ciel nocturne + palmier Ravinala + glassmorphism.

Approche hybride :
  - Fond cosmique (canvas étoiles + nébuleuse + palmier SVG) via st.components.v1.html()
  - Formulaire natif Streamlit superposé via CSS (fiable pour la communication)
"""

import streamlit as st
import streamlit.components.v1 as components


# ═══════════════════════════════════════════════════════════════
# COSMIC BACKGROUND HTML
# ═══════════════════════════════════════════════════════════════

COSMIC_BG_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Outfit:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
    --bg-deep: #030712;
    --emerald: #34D399;
    --emerald-deep: #059669;
    --teal: #2DD4BF;
    --gold: #FBBF24;
    --nebula-1: rgba(59, 130, 246, 0.07);
    --nebula-2: rgba(139, 92, 246, 0.05);
    --nebula-3: rgba(45, 212, 191, 0.04);
}

html, body {
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: var(--bg-deep);
}

.universe {
    position: relative;
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    background: var(--bg-deep);
}

/* ─── STARFIELD ─── */
#starfield {
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    z-index: 0;
}

/* ─── NEBULA ─── */
.nebula {
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    z-index: 1;
    background:
        radial-gradient(ellipse at 18% 52%, var(--nebula-1) 0%, transparent 58%),
        radial-gradient(ellipse at 82% 18%, var(--nebula-2) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 85%, var(--nebula-3) 0%, transparent 55%);
    animation: nebulaDrift 35s ease-in-out infinite alternate;
    pointer-events: none;
}

@keyframes nebulaDrift {
    0%   { transform: scale(1) translate(0, 0); opacity: 1; }
    50%  { transform: scale(1.04) translate(-1.5%, 1%); opacity: 0.85; }
    100% { transform: scale(1) translate(0.8%, -0.8%); opacity: 1; }
}

/* ─── GRID OVERLAY ─── */
.grid-overlay {
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 200%;
    z-index: 1;
    background-image:
        linear-gradient(rgba(52, 211, 153, 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(52, 211, 153, 0.025) 1px, transparent 1px);
    background-size: 60px 60px;
    transform: rotateX(55deg) translateY(-15%);
    transform-origin: center bottom;
    pointer-events: none;
}

/* ─── RAVINALA PALM ─── */
.palm-container {
    position: absolute;
    bottom: -10px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 2;
    opacity: 0.28;
    pointer-events: none;
    filter: drop-shadow(0 0 40px rgba(52, 211, 153, 0.08));
}

.ravinala-tree {
    width: 520px;
    height: 580px;
}

/* Animations feuilles */
.leaf-1 { animation: sw1 5.5s ease-in-out infinite; transform-origin: 50% 100%; }
.leaf-2 { animation: sw2 6.3s ease-in-out infinite; transform-origin: 50% 100%; }
.leaf-3 { animation: sw3 4.9s ease-in-out infinite; transform-origin: 50% 100%; }
.leaf-4 { animation: sw4 7.1s ease-in-out infinite; transform-origin: 50% 100%; }
.leaf-5 { animation: sw5 5.2s ease-in-out infinite; transform-origin: 50% 100%; }
.leaf-6 { animation: sw6 6.6s ease-in-out infinite; transform-origin: 50% 100%; }
.leaf-7 { animation: sw7 5.9s ease-in-out infinite; transform-origin: 50% 100%; }
.leaf-8 { animation: sw8 6.8s ease-in-out infinite; transform-origin: 50% 100%; }

@keyframes sw1 { 0%,100% { transform: rotate(-2.5deg); } 50% { transform: rotate(3deg); } }
@keyframes sw2 { 0%,100% { transform: rotate(1.5deg); } 50% { transform: rotate(-4deg); } }
@keyframes sw3 { 0%,100% { transform: rotate(-3deg); } 50% { transform: rotate(2.5deg); } }
@keyframes sw4 { 0%,100% { transform: rotate(2deg); } 50% { transform: rotate(-3.5deg); } }
@keyframes sw5 { 0%,100% { transform: rotate(-1.5deg); } 50% { transform: rotate(3.5deg); } }
@keyframes sw6 { 0%,100% { transform: rotate(3deg); } 50% { transform: rotate(-2deg); } }
@keyframes sw7 { 0%,100% { transform: rotate(-2deg); } 50% { transform: rotate(2.5deg); } }
@keyframes sw8 { 0%,100% { transform: rotate(1deg); } 50% { transform: rotate(-3deg); } }

/* ─── FLOATING PARTICLES ─── */
.particles { position: absolute; top:0; left:0; width:100%; height:100%; z-index:3; pointer-events:none; }
.particle {
    position: absolute;
    width: 2px; height: 2px;
    background: var(--gold);
    border-radius: 50%;
    opacity: 0;
    animation: floatUp linear infinite;
    box-shadow: 0 0 5px var(--gold), 0 0 10px rgba(251,191,36,0.3);
}

@keyframes floatUp {
    0%   { opacity: 0; transform: translateY(0) scale(0.5); }
    8%   { opacity: 0.9; }
    92%  { opacity: 0.7; }
    100% { opacity: 0; transform: translateY(-95vh) scale(1.3); }
}

/* Individuel particles */
.p1  { left: 8%;  animation-duration: 12s; animation-delay: 0s;    width:3px; height:3px; }
.p2  { left: 15%; animation-duration: 9s;  animation-delay: 2.5s; }
.p3  { left: 23%; animation-duration: 14s; animation-delay: 1s; }
.p4  { left: 31%; animation-duration: 10s; animation-delay: 4s; background: var(--emerald); box-shadow: 0 0 5px var(--emerald); }
.p5  { left: 40%; animation-duration: 11s; animation-delay: 0.5s;  width:3px; height:3px; }
.p6  { left: 48%; animation-duration: 8s;  animation-delay: 3s; }
.p7  { left: 56%; animation-duration: 13s; animation-delay: 1.5s; background: var(--teal); box-shadow: 0 0 5px var(--teal); }
.p8  { left: 63%; animation-duration: 10s; animation-delay: 5s; }
.p9  { left: 72%; animation-duration: 9s;  animation-delay: 2s;    width:3px; height:3px; }
.p10 { left: 80%; animation-duration: 15s; animation-delay: 0.8s; }
.p11 { left: 88%; animation-duration: 11s; animation-delay: 3.5s; }
.p12 { left: 5%;  animation-duration: 12s; animation-delay: 6s; background: var(--emerald); box-shadow: 0 0 5px var(--emerald); }
.p13 { left: 20%; animation-duration: 8s;  animation-delay: 7s; }
.p14 { left: 70%; animation-duration: 14s; animation-delay: 4.5s;  width:3px; height:3px; }
.p15 { left: 93%; animation-duration: 10s; animation-delay: 1.8s; }

/* ─── TITLE OVERLAY (top) ─── */
.title-overlay {
    position: absolute;
    top: 6%;
    left: 50%;
    transform: translateX(-50%);
    z-index: 10;
    text-align: center;
    pointer-events: none;
    animation: titleAppear 1.2s cubic-bezier(0.16,1,0.3,1) 0.3s both;
}

@keyframes titleAppear {
    from { opacity: 0; transform: translateX(-50%) translateY(-20px); }
    to   { opacity: 1; transform: translateX(-50%) translateY(0); }
}

.title-icon {
    font-size: 52px;
    display: block;
    margin-bottom: 10px;
    filter: drop-shadow(0 0 20px rgba(52,211,153,0.4));
    animation: iconPulse 3s ease-in-out infinite;
}

@keyframes iconPulse {
    0%,100% { filter: drop-shadow(0 0 12px rgba(52,211,153,0.35)); }
    50%      { filter: drop-shadow(0 0 28px rgba(52,211,153,0.6)); }
}

.app-title {
    font-family: 'Orbitron', sans-serif;
    font-weight: 900;
    font-size: clamp(28px, 4vw, 44px);
    letter-spacing: 10px;
    background: linear-gradient(135deg, #34D399 0%, #2DD4BF 45%, #FBBF24 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    display: block;
    margin-bottom: 6px;
}

.app-subtitle {
    font-family: 'Outfit', sans-serif;
    font-weight: 300;
    font-size: clamp(10px, 1.2vw, 13px);
    color: rgba(148,163,184,0.8);
    letter-spacing: 3px;
    text-transform: uppercase;
}

.title-line {
    width: 60px;
    height: 1.5px;
    background: linear-gradient(90deg, transparent, #34D399, transparent);
    margin: 12px auto 0;
}

/* ─── VERSION FOOTER ─── */
.version-bar {
    position: absolute;
    bottom: 14px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 10;
    text-align: center;
    pointer-events: none;
}

.version-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: rgba(71,85,105,0.7);
    letter-spacing: 1px;
}

.footer-note {
    font-family: 'Outfit', sans-serif;
    font-size: 10px;
    color: rgba(71,85,105,0.5);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 2px;
}
</style>
</head>
<body>
<div class="universe">
    <canvas id="starfield"></canvas>
    <div class="nebula"></div>
    <div class="grid-overlay"></div>

    <!-- RAVINALA PALM TREE SVG -->
    <div class="palm-container">
        <svg class="ravinala-tree" viewBox="0 0 520 580" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <!-- Gradient feuilles -->
                <linearGradient id="leafGrad1" x1="0%" y1="100%" x2="100%" y2="0%">
                    <stop offset="0%"   stop-color="#059669"/>
                    <stop offset="45%"  stop-color="#34D399"/>
                    <stop offset="100%" stop-color="#6EE7B7"/>
                </linearGradient>
                <linearGradient id="leafGrad2" x1="0%" y1="100%" x2="100%" y2="0%">
                    <stop offset="0%"   stop-color="#047857"/>
                    <stop offset="50%"  stop-color="#10B981"/>
                    <stop offset="100%" stop-color="#A7F3D0"/>
                </linearGradient>
                <!-- Gradient tronc -->
                <linearGradient id="trunkGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%"   stop-color="#6B5B3E"/>
                    <stop offset="40%"  stop-color="#8B7355"/>
                    <stop offset="70%"  stop-color="#A0926B"/>
                    <stop offset="100%" stop-color="#7A6548"/>
                </linearGradient>
                <!-- Glow filter -->
                <filter id="cosmicGlow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="4" result="blur"/>
                    <feComposite in="SourceGraphic" in2="blur" operator="over"/>
                </filter>
                <filter id="leafGlow">
                    <feGaussianBlur stdDeviation="2" result="blur"/>
                    <feComposite in="SourceGraphic" in2="blur" operator="over"/>
                </filter>
            </defs>

            <!-- TRONC -->
            <g transform="translate(260, 580)">
                <!-- Corps principal du tronc -->
                <rect x="-18" y="-210" width="36" height="210"
                      fill="url(#trunkGrad)" rx="4"/>
                <!-- Anneaux cicatriciels -->
                <line x1="-16" y1="-180" x2="16" y2="-180" stroke="#5C4A2E" stroke-width="1.5" opacity="0.6"/>
                <line x1="-16" y1="-150" x2="16" y2="-150" stroke="#5C4A2E" stroke-width="1.5" opacity="0.5"/>
                <line x1="-16" y1="-120" x2="16" y2="-120" stroke="#5C4A2E" stroke-width="1.5" opacity="0.6"/>
                <line x1="-16" y1="-90"  x2="16" y2="-90"  stroke="#5C4A2E" stroke-width="1.5" opacity="0.5"/>
                <line x1="-16" y1="-60"  x2="16" y2="-60"  stroke="#5C4A2E" stroke-width="1.5" opacity="0.6"/>
                <line x1="-16" y1="-30"  x2="16" y2="-30"  stroke="#5C4A2E" stroke-width="1.5" opacity="0.5"/>
                <!-- Base évasée -->
                <ellipse cx="0" cy="-2" rx="22" ry="8" fill="#6B5B3E" opacity="0.8"/>
            </g>

            <!-- ═══ FEUILLES EN ÉVENTAIL (partent toutes du sommet du tronc) ═══ -->
            <!-- Point d'origine : (260, 370) = sommet du tronc -->

            <!-- FEUILLE 1 — extrême gauche -->
            <g class="leaf-1" transform="translate(260, 370)">
                <path d="M 0,0 C -60,-30 -120,-50 -175,-40 C -155,-55 -110,-75 -55,-60 C -30,-30 0,0 0,0 Z"
                      fill="url(#leafGrad2)" filter="url(#leafGlow)"/>
                <line x1="0" y1="0" x2="-175" y2="-40" stroke="#FBBF24" stroke-width="0.8" opacity="0.25"/>
            </g>

            <!-- FEUILLE 2 — gauche large -->
            <g class="leaf-2" transform="translate(260, 370)">
                <path d="M 0,0 C -40,-50 -90,-110 -140,-150 C -118,-165 -75,-120 -45,-80 C -20,-45 0,0 0,0 Z"
                      fill="url(#leafGrad1)" filter="url(#leafGlow)"/>
                <line x1="0" y1="0" x2="-140" y2="-150" stroke="#FBBF24" stroke-width="0.8" opacity="0.25"/>
            </g>

            <!-- FEUILLE 3 — gauche centre -->
            <g class="leaf-3" transform="translate(260, 370)">
                <path d="M 0,0 C -15,-60 -30,-130 -35,-190 C -12,-195 0,-135 5,-75 C 5,-35 0,0 0,0 Z"
                      fill="url(#leafGrad1)" filter="url(#cosmicGlow)"/>
                <line x1="0" y1="0" x2="-35" y2="-190" stroke="#FBBF24" stroke-width="0.8" opacity="0.3"/>
            </g>

            <!-- FEUILLE 4 — centre gauche -->
            <g class="leaf-4" transform="translate(260, 370)">
                <path d="M 0,0 C -5,-65 5,-140 20,-195 C 38,-195 35,-135 28,-75 C 18,-35 0,0 0,0 Z"
                      fill="url(#leafGrad2)" filter="url(#cosmicGlow)"/>
                <line x1="0" y1="0" x2="20" y2="-195" stroke="#FBBF24" stroke-width="0.9" opacity="0.35"/>
            </g>

            <!-- FEUILLE 5 — centre (principale) -->
            <g class="leaf-5" transform="translate(260, 370)">
                <path d="M 0,0 C 10,-70 25,-150 45,-205 C 65,-200 55,-135 40,-80 C 25,-38 0,0 0,0 Z"
                      fill="url(#leafGrad1)" filter="url(#cosmicGlow)"/>
                <line x1="0" y1="0" x2="45" y2="-205" stroke="#FBBF24" stroke-width="1" opacity="0.35"/>
            </g>

            <!-- FEUILLE 6 — droite centre -->
            <g class="leaf-6" transform="translate(260, 370)">
                <path d="M 0,0 C 30,-55 75,-115 120,-155 C 140,-145 110,-100 75,-68 C 45,-40 0,0 0,0 Z"
                      fill="url(#leafGrad2)" filter="url(#leafGlow)"/>
                <line x1="0" y1="0" x2="120" y2="-155" stroke="#FBBF24" stroke-width="0.8" opacity="0.25"/>
            </g>

            <!-- FEUILLE 7 — droite large -->
            <g class="leaf-7" transform="translate(260, 370)">
                <path d="M 0,0 C 55,-40 115,-70 170,-60 C 155,-75 115,-95 60,-75 C 30,-45 0,0 0,0 Z"
                      fill="url(#leafGrad1)" filter="url(#leafGlow)"/>
                <line x1="0" y1="0" x2="170" y2="-60" stroke="#FBBF24" stroke-width="0.8" opacity="0.25"/>
            </g>

            <!-- FEUILLE 8 — extrême droite basse -->
            <g class="leaf-8" transform="translate(260, 370)">
                <path d="M 0,0 C 70,-15 145,-10 195,10 C 185,-10 150,-35 85,-30 C 45,-15 0,0 0,0 Z"
                      fill="url(#leafGrad2)" filter="url(#leafGlow)"/>
                <line x1="0" y1="0" x2="195" y2="10" stroke="#FBBF24" stroke-width="0.8" opacity="0.2"/>
            </g>

            <!-- PETITES TOUFFES à la base des feuilles -->
            <circle cx="260" cy="368" r="12" fill="#059669" opacity="0.5"/>
            <circle cx="260" cy="368" r="7"  fill="#34D399" opacity="0.6"/>
            <circle cx="260" cy="368" r="3"  fill="#6EE7B7" opacity="0.8"/>
        </svg>
    </div>

    <!-- PARTICULES -->
    <div class="particles">
        <div class="particle p1"></div>
        <div class="particle p2"></div>
        <div class="particle p3"></div>
        <div class="particle p4"></div>
        <div class="particle p5"></div>
        <div class="particle p6"></div>
        <div class="particle p7"></div>
        <div class="particle p8"></div>
        <div class="particle p9"></div>
        <div class="particle p10"></div>
        <div class="particle p11"></div>
        <div class="particle p12"></div>
        <div class="particle p13"></div>
        <div class="particle p14"></div>
        <div class="particle p15"></div>
    </div>

    <!-- TITRE -->
    <div class="title-overlay">
        <span class="title-icon">🌴</span>
        <span class="app-title">RAVINALA</span>
        <p class="app-subtitle">The Cross-Asset Quantum Structuring Lab</p>
        <div class="title-line"></div>
    </div>

    <!-- VERSION -->
    <div class="version-bar">
        <p class="version-text">v2.0 — © 2026 TSIVAHINY Matthias</p>
        <p class="footer-note">Authorized access only</p>
    </div>
</div>

<script>
// ═══ STARFIELD CANVAS ═══
const canvas = document.getElementById('starfield');
const ctx = canvas.getContext('2d');

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

// 200 étoiles avec propriétés aléatoires
const stars = Array.from({ length: 200 }, () => ({
    x: Math.random() * window.innerWidth,
    y: Math.random() * window.innerHeight,
    radius: Math.random() * 1.4 + 0.2,
    opacity: Math.random() * 0.7 + 0.2,
    speed: Math.random() * 0.02 + 0.004,
    phase: Math.random() * Math.PI * 2,
    color: Math.random() > 0.9 ? '#FBBF24' : Math.random() > 0.8 ? '#2DD4BF' : '#FFFFFF'
}));

let shootingStars = [];

function spawnShootingStar() {
    if (Math.random() < 0.004) {
        shootingStars.push({
            x: Math.random() * canvas.width * 0.8,
            y: Math.random() * canvas.height * 0.4,
            length: Math.random() * 90 + 40,
            speed: Math.random() * 9 + 4,
            angle: Math.PI / 4 + (Math.random() - 0.5) * 0.4,
            life: 1.0
        });
    }
}

function drawStars(t) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    stars.forEach(s => {
        const twinkle = Math.sin(t * s.speed * 8 + s.phase);
        const alpha = s.opacity * (0.5 + twinkle * 0.5);
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.radius, 0, Math.PI * 2);
        ctx.fillStyle = s.color.replace(')', `,${alpha})`).replace('rgb', 'rgba').replace('#', '');

        // Simple fillStyle with alpha
        if (s.color === '#FFFFFF') {
            ctx.fillStyle = `rgba(255,255,255,${alpha})`;
        } else if (s.color === '#FBBF24') {
            ctx.fillStyle = `rgba(251,191,36,${alpha})`;
        } else {
            ctx.fillStyle = `rgba(45,212,191,${alpha})`;
        }
        ctx.fill();

        if (s.radius > 1.1) {
            ctx.beginPath();
            ctx.arc(s.x, s.y, s.radius * 2.5, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255,255,255,${alpha * 0.07})`;
            ctx.fill();
        }
    });

    spawnShootingStar();
    shootingStars = shootingStars.filter(ss => {
        ss.x += Math.cos(ss.angle) * ss.speed;
        ss.y += Math.sin(ss.angle) * ss.speed;
        ss.life -= 0.014;
        if (ss.life <= 0) return false;

        const grad = ctx.createLinearGradient(
            ss.x, ss.y,
            ss.x - Math.cos(ss.angle) * ss.length,
            ss.y - Math.sin(ss.angle) * ss.length
        );
        grad.addColorStop(0, `rgba(255,255,255,${ss.life})`);
        grad.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.beginPath();
        ctx.moveTo(ss.x, ss.y);
        ctx.lineTo(ss.x - Math.cos(ss.angle)*ss.length, ss.y - Math.sin(ss.angle)*ss.length);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 1.5;
        ctx.stroke();
        return true;
    });
}

let last = 0;
function loop(ts) {
    const t = ts * 0.001;
    if (ts - last > 16) { // ~60fps cap
        drawStars(t);
        last = ts;
    }
    requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
</script>
</body>
</html>
"""


# ═══════════════════════════════════════════════════════════════
# STREAMLIT LOGIN FORM CSS
# ═══════════════════════════════════════════════════════════════

LOGIN_FORM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Outfit:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── MASQUER TOUT LE CHROME STREAMLIT ── */
#MainMenu, header, footer,
.stDeployButton, .stToolbar,
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stStatusWidget"],
.viewerBadge_container__r5tak,
.styles_viewerBadge__CvC9N {
    display: none !important;
}

/* ── MAIN BLOCK RESET ── */
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
    min-height: 100vh;
}

/* Fond transparent pour que le canvas HTML soit visible */
.stApp {
    background: transparent !important;
}

[data-testid="stAppViewContainer"] {
    background: transparent !important;
}

/* ── CARD DE LOGIN ── */
.login-card-wrapper {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: min(420px, 92vw);
    z-index: 100;
    background: rgba(15, 23, 42, 0.72);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(52, 211, 153, 0.28);
    border-radius: 24px;
    padding: 40px 36px;
    box-shadow:
        0 0 50px rgba(52, 211, 153, 0.06),
        0 30px 60px rgba(0, 0, 0, 0.55),
        inset 0 1px 0 rgba(255, 255, 255, 0.04);
    animation: cardIn 0.9s cubic-bezier(0.16,1,0.3,1) 0.6s both;
}

@keyframes cardIn {
    from { opacity: 0; transform: translate(-50%, calc(-50% + 28px)); }
    to   { opacity: 1; transform: translate(-50%, -50%); }
}

/* ── LABELS ── */
.stTextInput label {
    font-family: 'Outfit', sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    color: #94A3B8 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
}

/* ── INPUTS ── */
.stTextInput input {
    background: rgba(10, 18, 35, 0.85) !important;
    border: 1px solid rgba(148, 163, 184, 0.18) !important;
    border-radius: 12px !important;
    color: #F1F5F9 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 14px !important;
    padding: 14px 18px !important;
    transition: all 0.3s ease !important;
    caret-color: #34D399 !important;
}

.stTextInput input:focus {
    border-color: #34D399 !important;
    box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.14), 0 0 18px rgba(52,211,153,0.08) !important;
    background: rgba(15, 25, 45, 0.9) !important;
}

.stTextInput input::placeholder {
    color: #475569 !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 13px !important;
}

/* ── BOUTON PRINCIPAL ── */
.stButton > button[kind="primary"],
.stButton > button {
    background: linear-gradient(135deg, #059669 0%, #34D399 100%) !important;
    color: #030712 !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    letter-spacing: 1.5px !important;
    padding: 14px 24px !important;
    width: 100% !important;
    transition: all 0.25s ease !important;
    text-transform: uppercase !important;
    position: relative;
    overflow: hidden;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 30px rgba(52, 211, 153, 0.35) !important;
    background: linear-gradient(135deg, #047857 0%, #10B981 100%) !important;
}

.stButton > button:active {
    transform: translateY(0) !important;
}

/* ── ALERT / ERROR ── */
.stAlert {
    background: rgba(248, 113, 113, 0.10) !important;
    border: 1px solid rgba(248, 113, 113, 0.28) !important;
    border-radius: 10px !important;
    color: #FCA5A5 !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 13px !important;
}

/* ── SPINNER ── */
.stSpinner > div {
    border-top-color: #34D399 !important;
}

/* ── MASQUER labels vides ── */
.stTextInput > div > div > label:empty { display: none; }

/* ── RESPONSIVE mobile ── */
@media (max-width: 480px) {
    .login-card-wrapper {
        padding: 28px 20px !important;
    }
}
</style>
"""


# ═══════════════════════════════════════════════════════════════
# RENDER FUNCTION
# ═══════════════════════════════════════════════════════════════

def render_login_page() -> dict | None:
    """
    Affiche la page de connexion complète.
    Retourne {'username': str, 'password': str} si soumis, None sinon.
    """
    # 1. Masquer le chrome Streamlit + injecter les styles
    st.markdown(LOGIN_FORM_CSS, unsafe_allow_html=True)

    # 2. Fond cosmique plein écran via iframe
    components.html(COSMIC_BG_HTML, height=0, scrolling=False)

    # Injecter le CSS pour rendre le composant plein écran
    st.markdown("""
        <style>
        iframe[title="streamlit_components_v1_html"] {
            position: fixed !important;
            top: 0 !important; left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            z-index: 0 !important;
            pointer-events: none !important;
            border: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 3. Card de login en HTML (container)
    st.markdown('<div class="login-card-wrapper">', unsafe_allow_html=True)

    # Header de la card (titre dans le HTML)
    st.markdown("""
        <div style="text-align:center; margin-bottom:28px;">
            <div style="font-size:44px; margin-bottom:10px; filter: drop-shadow(0 0 16px rgba(52,211,153,0.45));">🌴</div>
            <div style="font-family:'Orbitron',sans-serif; font-weight:900; font-size:28px;
                        letter-spacing:8px;
                        background: linear-gradient(135deg,#34D399,#2DD4BF 50%,#FBBF24);
                        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                        background-clip:text; margin-bottom:6px;">
                RAVINALA
            </div>
            <div style="font-family:'Outfit',sans-serif; font-weight:300; font-size:11px;
                        color:#64748B; letter-spacing:3px; text-transform:uppercase;">
                The Cross-Asset Quantum Structuring Lab
            </div>
            <div style="width:50px; height:1.5px;
                        background: linear-gradient(90deg, transparent, #34D399, transparent);
                        margin: 14px auto 0;"></div>
        </div>
    """, unsafe_allow_html=True)

    # 4. Formulaire natif Streamlit
    username = st.text_input(
        "Identifier",
        placeholder="Enter your username",
        key="login_username"
    )
    password = st.text_input(
        "Password",
        type="password",
        placeholder="Enter your password",
        key="login_password"
    )

    # Espacement
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    login_clicked = st.button(
        "⟶  Access Ravinala",
        type="primary",
        use_container_width=True,
        key="login_button"
    )

    # Afficher l'erreur précédente si elle existe
    if st.session_state.get('login_error'):
        st.error(f"⚠️  {st.session_state.login_error}")
        st.session_state.login_error = None

    st.markdown('</div>', unsafe_allow_html=True)

    # 5. Retourner les credentials si le bouton est cliqué
    if login_clicked and username and password:
        return {'username': username.strip(), 'password': password}

    if login_clicked and (not username or not password):
        st.session_state.login_error = "Please enter both username and password."
        st.rerun()

    return None


def render_logout_button(auth_manager, user: dict) -> bool:
    """
    Affiche un bouton de déconnexion dans le header.
    Retourne True si l'utilisateur vient de se déconnecter.
    """
    col1, col2, col3 = st.columns([5, 3, 2])
    with col2:
        st.markdown(
            f"<div style='font-family:Outfit,sans-serif; font-size:13px; "
            f"color:#94A3B8; text-align:right; padding-top:8px;'>"
            f"👤 <b style='color:#34D399'>{user.get('display_name', user.get('username'))}</b>"
            f" <span style='color:#475569'>({user.get('role', 'user')})</span>"
            f"</div>",
            unsafe_allow_html=True
        )
    with col3:
        if st.button("🚪 Logout", key="logout_btn"):
            session_id = st.session_state.get('session_id')
            if session_id:
                auth_manager.logout(session_id)
            st.session_state.authenticated = False
            st.session_state.pop('session_id', None)
            st.session_state.pop('user', None)
            st.rerun()

    return False
