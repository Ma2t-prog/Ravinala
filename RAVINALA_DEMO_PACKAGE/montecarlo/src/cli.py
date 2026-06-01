#!/usr/bin/env python
"""
Ravinala CLI Launcher
Starts the Ravinala Streamlit application as an installed command-line tool.
"""

import sys
import os
import subprocess
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def main():
    """
    Main entry point for the Ravinala CLI.
    Launches the Streamlit application.
    """
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    
    # The Streamlit app file
    app_file = script_dir / "app.py"
    
    if not app_file.exists():
        print(f"Error: app.py not found at {app_file}")
        sys.exit(1)
    
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║                                                                ║
    ║  RAVINALA by TSIVAHINY Matthias                              ║
    ║  The Cross-Asset Quantum Structuring Lab                     ║
    ║                                                                ║
    ║  Version 2.0 | Professional Derivatives Pricing Platform     ║
    ║                                                                ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    print("Launching application...")
    print(f"App location: {app_file}\n")
    
    # Launch Streamlit
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(app_file)],
            cwd=str(script_dir),
            check=False
        )
    except KeyboardInterrupt:
        print("\n\nRavinala closed by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"Error launching Ravinala: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
