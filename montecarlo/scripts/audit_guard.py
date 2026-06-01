#!/usr/bin/env python3
"""
AUDIT GUARD — GENESIX Ω Suite
═══════════════════════════════════════════════════════════════════════
Script d'audit automatique du projet.
Exécute toutes les vérifications critiques et retourne un rapport.

Usage:
    python scripts/audit_guard.py              # Audit complet
    python scripts/audit_guard.py --quick      # Audit rapide (règles bloquantes uniquement)
    python scripts/audit_guard.py --fix-hints  # Audit + suggestions de correction
    python scripts/audit_guard.py --strict     # Audit strict (bloquant + qualité)
    python scripts/audit_guard.py --watch      # Mode watch (ré-exécute toutes les 30s)

Exit codes:
    0 = Tout est OK
    1 = Violations bloquantes détectées
    2 = Warnings qualité détectés (non-bloquant sauf en --strict)
═══════════════════════════════════════════════════════════════════════
"""

import os
import re
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import NamedTuple

# ── Configuration ─────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Répertoires à scanner
SCAN_DIRS = {
    "backend": PROJECT_ROOT / "backend",
    "src": PROJECT_ROOT / "src",
}

# Répertoires exclus du scan
EXCLUDE_DIRS = {
    ".venv", "venv", "__pycache__", ".git", "node_modules",
    ".ruff_cache", ".pytest_cache", ".mypy_cache", "ravinala.egg-info",
    ".streamlit", "tmp", "logs",
}

# ── Types ─────────────────────────────────────────────────────────────────────

class Violation(NamedTuple):
    rule: str
    severity: str  # "BLOCKER" | "WARNING"
    file: str
    line: int
    message: str
    fix_hint: str


# ── Utilitaires ──────────────────────────────────────────────────────────────

def find_python_files(root: Path) -> list[Path]:
    """Trouve tous les fichiers .py en excluant les répertoires non pertinents."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Exclure les répertoires non pertinents
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                files.append(Path(dirpath) / f)
    return files


def is_test_file(filepath: Path) -> bool:
    """Vérifie si un fichier est un fichier de test."""
    parts = str(filepath).lower()
    return ("test" in parts or "tests" in parts or
            filepath.name.startswith("test_") or
            filepath.name.endswith("_test.py"))


def relative_path(filepath: Path) -> str:
    """Retourne le chemin relatif depuis la racine du projet."""
    try:
        return str(filepath.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(filepath)


# ── Règles bloquantes (R1-R7) ───────────────────────────────────────────────

def check_r1_no_random_in_ml(files: list[Path]) -> list[Violation]:
    """R1 — Pas de np.random dans le code ML/signal/prediction."""
    violations = []
    ml_dirs = {"ml", "intelligence", "signals", "prediction"}

    for f in files:
        if is_test_file(f):
            continue

        # Vérifie si le fichier est dans un répertoire ML/signal
        parts = set(f.parts)
        is_ml_file = bool(parts & ml_dirs) or "predict" in f.name or "signal" in f.name

        if not is_ml_file:
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(content.splitlines(), 1):
            if re.search(r"np\.random\.", line) and not line.strip().startswith("#"):
                violations.append(Violation(
                    rule="R1",
                    severity="BLOCKER",
                    file=relative_path(f),
                    line=i,
                    message=f"np.random trouvé dans code ML/signal: {line.strip()[:80]}",
                    fix_hint="Remplacer par un retour structuré {'status': 'unavailable', 'reason': '...', 'prediction': None}"
                ))

    return violations


def check_r2_risk_free_rate(files: list[Path]) -> list[Violation]:
    """R2 — risk_free_rate doit être importé depuis constants.py, jamais hardcodé."""
    violations = []
    # Pattern: risk_free_rate = 0.XX ou rf = 0.XX ou risk_free = 0.XX
    patterns = [
        r"risk_free_rate\s*=\s*0\.\d+",
        r"\brf\s*=\s*0\.0[2-9]\b",
        r"risk_free\s*=\s*0\.\d+",
    ]

    for f in files:
        if is_test_file(f) or f.name == "constants.py":
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(content.splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            for pattern in patterns:
                if re.search(pattern, line):
                    violations.append(Violation(
                        rule="R2",
                        severity="BLOCKER",
                        file=relative_path(f),
                        line=i,
                        message=f"risk_free_rate hardcodé: {line.strip()[:80]}",
                        fix_hint="Importer RISK_FREE_RATE depuis constants.py"
                    ))

    return violations


def check_r3_no_direct_yfinance(files: list[Path]) -> list[Violation]:
    """R3 — Pas d'appel yfinance direct dans services/."""
    violations = []
    patterns = [r"yf\.download", r"yf\.Ticker", r"yfinance\.download", r"yfinance\.Ticker"]

    for f in files:
        if is_test_file(f):
            continue

        # Ne vérifie que dans services/ et routes/ (pas dans providers/)
        rel = relative_path(f)
        if "providers" in rel or "adapter" in f.name:
            continue
        if "services" not in rel and "routes" not in rel:
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(content.splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            for pattern in patterns:
                if re.search(pattern, line):
                    violations.append(Violation(
                        rule="R3",
                        severity="BLOCKER",
                        file=relative_path(f),
                        line=i,
                        message=f"Appel yfinance direct dans services/routes: {line.strip()[:80]}",
                        fix_hint="Utiliser self._provider.fetch_*() via YFinanceProvider"
                    ))

    return violations


def check_r4_schema_sync() -> list[Violation]:
    """R4 — BacktestRun doit avoir le même schéma dans src/ et backend/."""
    violations = []

    src_models = PROJECT_ROOT / "src" / "db" / "models.py"
    backend_models = PROJECT_ROOT / "backend" / "app" / "db" / "models.py"

    if not src_models.exists() or not backend_models.exists():
        return violations

    def count_columns(filepath: Path, class_name: str) -> int:
        """Compte approximativement les colonnes d'un modèle SQLAlchemy."""
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return -1

        in_class = False
        col_count = 0
        indent_level = None

        for line in content.splitlines():
            if f"class {class_name}" in line:
                in_class = True
                continue
            if in_class:
                stripped = line.strip()
                if not stripped:
                    continue
                # Nouvelle classe = fin
                if stripped.startswith("class ") and not stripped.startswith("class_"):
                    break
                # Compter les colonnes
                if "Column(" in line or "Mapped[" in line or "mapped_column" in line.lower():
                    col_count += 1

        return col_count

    for model_name in ["BacktestRun", "BacktestTrade"]:
        src_cols = count_columns(src_models, model_name)
        backend_cols = count_columns(backend_models, model_name)

        if src_cols > 0 and backend_cols > 0 and src_cols != backend_cols:
            violations.append(Violation(
                rule="R4",
                severity="BLOCKER",
                file=f"src/db/models.py vs backend/app/db/models.py",
                line=0,
                message=f"{model_name}: {src_cols} colonnes (src) vs {backend_cols} colonnes (backend)",
                fix_hint=f"Aligner {model_name} sur le schéma le plus complet (backend = {backend_cols} cols)"
            ))

    return violations


def check_r5_persistence(files: list[Path]) -> list[Violation]:
    """R5 — Pas de stockage in-memory seul pour les résultats."""
    violations = []

    # Cherche des patterns de stockage in-memory global
    patterns = [
        (r"_store\s*[=:]\s*\{\}", "Dict global in-memory comme store"),
        (r"_cache\s*[=:]\s*\{\}", "Dict global in-memory comme cache"),
        (r"_results\s*[=:]\s*\[\]", "Liste globale in-memory comme résultats"),
    ]

    for f in files:
        if is_test_file(f):
            continue

        rel = relative_path(f)
        # Ne vérifie que dans routes/ et services/
        if "routes" not in rel and "services" not in rel:
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(content.splitlines(), 1):
            for pattern, desc in patterns:
                if re.search(pattern, line):
                    violations.append(Violation(
                        rule="R5",
                        severity="BLOCKER",
                        file=relative_path(f),
                        line=i,
                        message=f"Stockage in-memory détecté: {desc}",
                        fix_hint="Persister en DB via le modèle SQLAlchemy approprié"
                    ))

    return violations


def check_r6_no_secrets(files: list[Path]) -> list[Violation]:
    """R6 — Pas de secrets hardcodés."""
    violations = []
    patterns = [
        (r"""(?:api_key|apikey|api_secret|secret_key|password|passwd|token|auth_token)\s*=\s*['"][^'"]{8,}['"]""",
         "Secret potentiellement hardcodé"),
        (r"""['"]sk-[a-zA-Z0-9]{20,}['"]""", "Clé API OpenAI/Anthropic"),
        (r"""['"]ghp_[a-zA-Z0-9]{30,}['"]""", "Token GitHub"),
        (r"""['"]Bearer\s+[a-zA-Z0-9._-]{20,}['"]""", "Bearer token hardcodé"),
    ]

    for f in files:
        if is_test_file(f) or "example" in f.name or "config" in f.name:
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(content.splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            for pattern, desc in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(Violation(
                        rule="R6",
                        severity="BLOCKER",
                        file=relative_path(f),
                        line=i,
                        message=f"{desc}: {line.strip()[:60]}...",
                        fix_hint="Utiliser os.environ['...'] ou un fichier .env"
                    ))

    return violations


def check_r7_dead_code(files: list[Path]) -> list[Violation]:
    """R7 — Pas de code mort actif (pas marqué dans feature_flags)."""
    violations = []

    # Cherche les modèles/classes définis mais jamais importés
    defined_classes = {}
    imported_names = set()

    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(content.splitlines(), 1):
            # Classes définies dans models.py
            if f.name == "models.py":
                match = re.match(r"class (\w+)\(", line)
                if match:
                    cls_name = match.group(1)
                    if cls_name not in defined_classes:
                        defined_classes[cls_name] = (relative_path(f), i)

            # Imports
            import_match = re.search(r"from .+ import (.+)", line)
            if import_match:
                names = [n.strip() for n in import_match.group(1).split(",")]
                imported_names.update(names)

            # Usage directe
            for cls_name in list(defined_classes.keys()):
                if cls_name in line and "class " not in line:
                    imported_names.add(cls_name)

    # Vérifie les classes jamais importées
    for cls_name, (filepath, line) in defined_classes.items():
        if cls_name not in imported_names and cls_name not in ("Base", "BaseModel"):
            violations.append(Violation(
                rule="R7",
                severity="WARNING",
                file=filepath,
                line=line,
                message=f"Classe '{cls_name}' définie mais potentiellement jamais utilisée",
                fix_hint=f"Implémenter l'utilisation de {cls_name} ou le supprimer"
            ))

    return violations


# ── Règles qualité (Q1-Q7) ──────────────────────────────────────────────────

def check_q1_response_models(files: list[Path]) -> list[Violation]:
    """Q1 — Chaque endpoint doit avoir un response_model."""
    violations = []

    for f in files:
        rel = relative_path(f)
        if "routes" not in rel:
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(content.splitlines(), 1):
            # Cherche les décorateurs de route sans response_model
            if re.search(r"@router\.(get|post|put|delete|patch)\(", line):
                # Vérifie les 3 lignes suivantes pour response_model
                context = "\n".join(content.splitlines()[i-1:i+3])
                if "response_model" not in context:
                    violations.append(Violation(
                        rule="Q1",
                        severity="WARNING",
                        file=relative_path(f),
                        line=i,
                        message=f"Endpoint sans response_model: {line.strip()[:60]}",
                        fix_hint="Ajouter response_model=ApiResponse[...] au décorateur"
                    ))

    return violations


def check_q2_celery_limits(files: list[Path]) -> list[Violation]:
    """Q2 — Chaque tâche Celery a soft/hard time limit."""
    violations = []

    for f in files:
        rel = relative_path(f)
        if "tasks" not in rel and "worker" not in rel:
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(content.splitlines(), 1):
            if "@" in line and "shared_task" in line or "app.task" in line:
                context = "\n".join(content.splitlines()[max(0,i-1):i+5])
                if "soft_time_limit" not in context:
                    violations.append(Violation(
                        rule="Q2",
                        severity="WARNING",
                        file=relative_path(f),
                        line=i,
                        message="Tâche Celery sans soft_time_limit",
                        fix_hint="Ajouter soft_time_limit=X, time_limit=Y au décorateur"
                    ))

    return violations


def check_q6_docstrings(files: list[Path]) -> list[Violation]:
    """Q6 — Docstrings sur les modules et fonctions publiques."""
    violations = []

    for f in files:
        if is_test_file(f):
            continue

        rel = relative_path(f)
        # Ne vérifie que les fichiers importants
        if "routes" not in rel and "services" not in rel and "ml" not in rel:
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        lines = content.splitlines()

        # Module docstring
        if lines and not (lines[0].startswith('"""') or lines[0].startswith("'''")):
            if len(lines) > 1 and not (lines[1].startswith('"""') or lines[1].startswith("'''")):
                violations.append(Violation(
                    rule="Q6",
                    severity="WARNING",
                    file=relative_path(f),
                    line=1,
                    message="Module sans docstring",
                    fix_hint="Ajouter une docstring en haut du fichier"
                ))

    return violations


# ── Rapport ──────────────────────────────────────────────────────────────────

def print_report(violations: list[Violation], show_hints: bool = False) -> tuple[int, int]:
    """Affiche le rapport d'audit et retourne (blockers, warnings)."""

    blockers = [v for v in violations if v.severity == "BLOCKER"]
    warnings = [v for v in violations if v.severity == "WARNING"]

    print()
    print("═" * 70)
    print("  AUDIT GUARD — GENESIX Ω Suite")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 70)

    if not violations:
        print()
        print("  ✅ AUCUNE VIOLATION DÉTECTÉE")
        print("  Le code respecte toutes les règles du projet.")
        print()
        print("═" * 70)
        return 0, 0

    # Grouper par règle
    by_rule: dict[str, list[Violation]] = {}
    for v in violations:
        by_rule.setdefault(v.rule, []).append(v)

    # Afficher les blockers d'abord
    if blockers:
        print()
        print(f"  🔴 {len(blockers)} VIOLATION(S) BLOQUANTE(S)")
        print("  ─" * 35)

        for rule, rule_violations in sorted(by_rule.items()):
            rule_blockers = [v for v in rule_violations if v.severity == "BLOCKER"]
            if not rule_blockers:
                continue

            print(f"\n  [{rule}] ({len(rule_blockers)} violation(s))")
            for v in rule_blockers:
                loc = f"{v.file}:{v.line}" if v.line > 0 else v.file
                print(f"    ✗ {loc}")
                print(f"      {v.message}")
                if show_hints:
                    print(f"      💡 {v.fix_hint}")

    # Afficher les warnings
    if warnings:
        print()
        print(f"  ⚠️  {len(warnings)} WARNING(S) QUALITÉ")
        print("  ─" * 35)

        for rule, rule_violations in sorted(by_rule.items()):
            rule_warnings = [v for v in rule_violations if v.severity == "WARNING"]
            if not rule_warnings:
                continue

            print(f"\n  [{rule}] ({len(rule_warnings)} warning(s))")
            for v in rule_warnings[:5]:  # Max 5 par règle pour lisibilité
                loc = f"{v.file}:{v.line}" if v.line > 0 else v.file
                print(f"    ⚠ {loc}")
                print(f"      {v.message}")
                if show_hints:
                    print(f"      💡 {v.fix_hint}")
            if len(rule_warnings) > 5:
                print(f"    ... et {len(rule_warnings) - 5} autre(s)")

    # Résumé
    print()
    print("  ─" * 35)
    print(f"  RÉSUMÉ: {len(blockers)} blocker(s) | {len(warnings)} warning(s)")
    if blockers:
        print("  ❌ AUDIT ÉCHOUÉ — Corrige les violations bloquantes")
    else:
        print("  ✅ AUDIT PASSÉ (avec warnings)")
    print("═" * 70)
    print()

    return len(blockers), len(warnings)


# ── Score global ─────────────────────────────────────────────────────────────

def compute_score(blockers: int, warnings: int) -> float:
    """Calcule un score sur 10."""
    score = 10.0
    score -= blockers * 1.5  # Chaque blocker coûte 1.5 point
    score -= warnings * 0.3  # Chaque warning coûte 0.3 point
    return max(0.0, min(10.0, round(score, 1)))


# ── Main ─────────────────────────────────────────────────────────────────────

def run_audit(strict: bool = False, show_hints: bool = False) -> int:
    """Exécute l'audit complet. Retourne le code de sortie."""

    # Collecter tous les fichiers Python
    all_files: list[Path] = []
    for name, root in SCAN_DIRS.items():
        if root.exists():
            all_files.extend(find_python_files(root))

    if not all_files:
        print("⚠️  Aucun fichier Python trouvé dans le projet")
        return 0

    print(f"\n  Scanning {len(all_files)} fichiers Python...")

    # Exécuter toutes les règles bloquantes
    violations: list[Violation] = []
    violations.extend(check_r1_no_random_in_ml(all_files))
    violations.extend(check_r2_risk_free_rate(all_files))
    violations.extend(check_r3_no_direct_yfinance(all_files))
    violations.extend(check_r4_schema_sync())
    violations.extend(check_r5_persistence(all_files))
    violations.extend(check_r6_no_secrets(all_files))
    violations.extend(check_r7_dead_code(all_files))

    # Règles qualité
    violations.extend(check_q1_response_models(all_files))
    violations.extend(check_q2_celery_limits(all_files))
    violations.extend(check_q6_docstrings(all_files))

    # Rapport
    blockers, warnings = print_report(violations, show_hints=show_hints)

    # Score
    score = compute_score(blockers, warnings)
    print(f"  📊 SCORE: {score}/10")
    print()

    # Code de sortie
    if blockers > 0:
        return 1
    if warnings > 0 and strict:
        return 2
    return 0


def main():
    parser = argparse.ArgumentParser(description="AUDIT GUARD — GENESIX Ω Suite")
    parser.add_argument("--quick", action="store_true", help="Audit rapide (bloquantes uniquement)")
    parser.add_argument("--strict", action="store_true", help="Traite les warnings comme des erreurs")
    parser.add_argument("--fix-hints", action="store_true", help="Affiche les suggestions de correction")
    parser.add_argument("--watch", action="store_true", help="Mode watch (ré-exécute toutes les 30s)")
    args = parser.parse_args()

    if args.watch:
        print("  🔄 Mode watch activé — Ctrl+C pour arrêter")
        while True:
            os.system("cls" if os.name == "nt" else "clear")
            run_audit(strict=args.strict, show_hints=args.fix_hints)
            time.sleep(30)
    else:
        exit_code = run_audit(strict=args.strict, show_hints=args.fix_hints)
        sys.exit(exit_code)


if __name__ == "__main__":
    # Fix Windows encoding
    import io
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    main()
