"""
protection.py — Mesures anti-copie et protection côté client pour Ravinala.
Ces protections sont côté client (JavaScript/CSS) et découragent fortement
la copie sans être bulletproof face à un développeur expérimenté.
"""

from datetime import datetime


class AppProtection:
    """
    Mesures de protection pour empêcher la copie de l'application.
    """

    @staticmethod
    def inject_anti_copy_js() -> str:
        """
        JavaScript de protection à injecter via st.components.v1.html().
        Désactive clic droit, raccourcis DevTools, sélection, impression.
        """
        return """
(function() {
    'use strict';

    // ─── 1. DÉSACTIVER LE CLIC DROIT ───────────────────────────
    document.addEventListener('contextmenu', function(e) {
        e.preventDefault();
        return false;
    });

    // ─── 2. DÉSACTIVER LES RACCOURCIS DEV TOOLS ────────────────
    document.addEventListener('keydown', function(e) {
        var blocked = false;

        // F12
        if (e.key === 'F12') blocked = true;

        // Ctrl+Shift+I / Ctrl+Shift+J / Ctrl+U
        if (e.ctrlKey && e.shiftKey && ['I', 'J', 'i', 'j'].includes(e.key)) blocked = true;
        if (e.ctrlKey && ['U', 'u'].includes(e.key)) blocked = true;

        // Ctrl+P (print)
        if (e.ctrlKey && ['P', 'p'].includes(e.key)) blocked = true;

        // Cmd+Option+I / Cmd+Option+J (Mac)
        if (e.metaKey && e.altKey && ['I', 'J', 'i', 'j'].includes(e.key)) blocked = true;
        if (e.metaKey && ['U', 'u'].includes(e.key)) blocked = true;

        // Cmd+P (Mac print)
        if (e.metaKey && ['P', 'p'].includes(e.key)) blocked = true;

        if (blocked) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    }, true);

    // ─── 3. DÉSACTIVER LA SÉLECTION DE TEXTE (ÉLÉMENTS SENSIBLES) ──
    var style = document.createElement('style');
    style.textContent = `
        .stApp, .main, [data-testid="stAppViewContainer"] {
            -webkit-user-select: none !important;
            -moz-user-select: none !important;
            -ms-user-select: none !important;
            user-select: none !important;
        }
        /* Autoriser la sélection dans les inputs */
        input, textarea, [contenteditable="true"] {
            -webkit-user-select: text !important;
            user-select: text !important;
        }
    `;
    document.head.appendChild(style);

    // ─── 4. DÉSACTIVER L'IMPRESSION ────────────────────────────
    var printStyle = document.createElement('style');
    printStyle.textContent = `
        @media print {
            body { display: none !important; }
        }
    `;
    document.head.appendChild(printStyle);

    window.addEventListener('beforeprint', function(e) {
        document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:#334;font-size:24px;">Printing is not allowed for this application.</div>';
        e.preventDefault();
    });

    // ─── 5. DÉTECTION DES DEVTOOLS ─────────────────────────────
    var devtoolsOpen = false;
    var overlay = null;

    function createOverlay() {
        if (overlay) return;
        overlay = document.createElement('div');
        overlay.id = 'devtools-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(3, 7, 18, 0.97);
            z-index: 10000;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-family: 'Outfit', -apple-system, sans-serif;
            color: #F1F5F9;
        `;
        overlay.innerHTML = `
            <div style="font-size:20px;font-weight:700;margin-bottom:24px;color:#94A3B8;letter-spacing:4px;">LOCKED</div>
            <h2 style="font-family:'Orbitron',sans-serif;font-size:20px;letter-spacing:4px;color:#34D399;margin-bottom:12px;">ACCESS RESTRICTED</h2>
            <p style="color:#94A3B8;font-size:14px;letter-spacing:2px;text-transform:uppercase;">Developer tools are not permitted</p>
            <p style="color:#475569;font-size:12px;margin-top:8px;">Please close DevTools to continue using Ravinala</p>
        `;
        document.body.appendChild(overlay);
    }

    function removeOverlay() {
        if (overlay) {
            overlay.remove();
            overlay = null;
        }
    }

    // Détection par taille de fenêtre (threshold > 160px)
    function checkDevTools() {
        var widthThreshold = window.outerWidth - window.innerWidth > 160;
        var heightThreshold = window.outerHeight - window.innerHeight > 160;
        var isOpen = widthThreshold || heightThreshold;

        if (isOpen && !devtoolsOpen) {
            devtoolsOpen = true;
            createOverlay();
        } else if (!isOpen && devtoolsOpen) {
            devtoolsOpen = false;
            removeOverlay();
        }
    }

    setInterval(checkDevTools, 1000);

    // ─── 6. DÉSACTIVER LE DRAG & DROP ──────────────────────────
    document.addEventListener('dragstart', function(e) {
        e.preventDefault();
        return false;
    });

    // ─── 7. BLOQUER CONSOLE.LOG (obscurcissement) ──────────────
    // (commenté — peut causer des problèmes avec Streamlit)
    // var noop = function() {};
    // if (window.console) {
    //     window.console.log = noop;
    //     window.console.warn = noop;
    //     window.console.error = noop;
    // }

})();
"""

    @staticmethod
    def inject_watermark(username: str) -> str:
        """
        CSS watermark semi-transparent avec le username.
        Quasi invisible à l'œil nu mais détectable si contraste augmenté.
        """
        today = datetime.utcnow().strftime('%Y-%m-%d')
        text = f"RAVINALA — Licensed to {username} — {today}"

        return f"""
/* ═══ WATERMARK RAVINALA ═══ */
.stApp::before {{
    content: "{text}\\A{text}\\A{text}\\A{text}\\A{text}\\A{text}\\A{text}\\A{text}\\A{text}\\A{text}";
    white-space: pre;
    position: fixed;
    top: 0; left: 0;
    width: 200%;
    height: 200%;
    font-size: 16px;
    color: rgba(52, 211, 153, 0.035);
    transform: rotate(-30deg) translate(-25%, -10%);
    pointer-events: none;
    z-index: 0;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 2px;
    line-height: 80px;
    user-select: none;
    -webkit-user-select: none;
}}
"""

    @staticmethod
    def inject_session_heartbeat(interval_seconds: int = 60) -> str:
        """
        CSS/JS pour forcer un rerun Streamlit périodique (vérification session).
        Dans Streamlit, on utilise st.empty() + time.sleep() côté serveur,
        ou on injecte un meta refresh en JS.
        """
        return f"""
(function() {{
    // Heartbeat : recharge légère toutes les {interval_seconds}s pour vérifier la session
    // En pratique, Streamlit rerun côté Python est plus fiable
    // Ce JS est un fallback si la page devient "stale"
    setTimeout(function heartbeat() {{
        try {{
            // Déclencher un événement pour forcer une interaction Streamlit
            var inputs = document.querySelectorAll('input[data-testid]');
            if (inputs.length > 0) {{
                inputs[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch(e) {{}}
        setTimeout(heartbeat, {interval_seconds * 1000});
    }}, {interval_seconds * 1000});
}})();
"""

    @staticmethod
    def add_source_obfuscation_note() -> str:
        """Recommandations pour la vraie protection du code source Python."""
        return """
╔══════════════════════════════════════════════════════════════════╗
║         PROTECTION DU CODE SOURCE — RECOMMANDATIONS             ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Les protections JS/CSS côté client arrêtent ~95% des           ║
║  utilisateurs non-techniques. Pour une vraie protection :        ║
║                                                                  ║
║  1. DÉPLOYER, ne pas distribuer le code                          ║
║     → Streamlit Cloud, Railway, Render, ou VPS                  ║
║     → Partager l'URL, pas le code                               ║
║                                                                  ║
║  2. Si distribution nécessaire → PyInstaller                    ║
║     → Compile en .exe / .app standalone                         ║
║     → Le code Python est dans un .pyc dans l'archive            ║
║                                                                  ║
║  3. Modules critiques → Cython                                   ║
║     → Compile auth.py, pricing logic en .so/.pyd                ║
║     → Pratiquement impossible à décompiler                      ║
║                                                                  ║
║  4. Ne JAMAIS partager le repo Git en accès direct              ║
║     → GitHub privé, pas de fork public                          ║
║                                                                  ║
║  5. Sessions avec expiration courte + IP binding                 ║
║     → Déjà implémenté dans AuthManager                          ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""

    @staticmethod
    def get_full_protection_html(username: str) -> str:
        """
        Retourne le HTML complet à injecter via st.components.v1.html() height=0.
        Combine JS anti-copy + CSS watermark.
        """
        js = AppProtection.inject_anti_copy_js()
        css = AppProtection.inject_watermark(username)
        return f"<script>{js}</script><style>{css}</style>"
