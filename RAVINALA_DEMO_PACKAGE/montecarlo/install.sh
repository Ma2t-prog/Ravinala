#!/bin/bash

# Ravinala Installation Script for macOS & Linux
# This script sets up the Ravinala environment and installs the package

cat << "EOF"

╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║  🌴 RAVINALA INSTALLATION WIZARD                             ║
║  The Cross-Asset Quantum Structuring Lab                     ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

EOF

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ERROR: Python 3 is not installed"
    echo "Please install Python 3.10+ from https://www.python.org/"
    exit 1
fi

echo "✓ Python detected"
python3 --version
echo

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "⚠️  Virtual environment already exists. Skipping..."
else
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
fi
echo "✓ Virtual environment ready"

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi
echo "✓ Environment activated"

# Upgrade pip
echo "📥 Upgrading pip..."
python3 -m pip install --upgrade pip setuptools wheel > /dev/null 2>&1

# Install Ravinala in editable mode
echo "📥 Installing Ravinala..."
pip install -e .
if [ $? -ne 0 ]; then
    echo "❌ Installation failed"
    exit 1
fi
echo "✓ Ravinala installed successfully"

# Create a launch script
echo "🛠️  Creating launch script..."
cat > ravinala_run.sh << 'LAUNCHER'
#!/bin/bash
# Ravinala Launcher Script
source "$(dirname "$0")/.venv/bin/activate"
ravinala
LAUNCHER
chmod +x ravinala_run.sh

echo
echo "════════════════════════════════════════════════════════════════"
echo "✅ Installation Complete!"
echo "════════════════════════════════════════════════════════════════"
echo
echo "To launch Ravinala:"
echo
echo "  Option 1 (recommended):"
echo "    ./ravinala_run.sh"
echo
echo "  Option 2:"
echo "    source .venv/bin/activate"
echo "    ravinala"
echo
echo "  Option 3:"
echo "    python -m ravinala"
echo
echo "════════════════════════════════════════════════════════════════"
echo
