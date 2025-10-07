#!/bin/bash

# Pico Setup Script for Mac (using Conda)
# This script sets up Pico on a fresh Mac installation

set -e  # Exit on error

echo "🚀 Setting up Pico - AI-Powered Personal Assistant"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if conda is installed
echo "📦 Checking prerequisites..."
if ! command -v conda &> /dev/null; then
    echo -e "${YELLOW}⚠️  Conda not found. Installing Miniconda...${NC}"
    echo ""
    
    # Detect architecture (Apple Silicon vs Intel)
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        INSTALLER_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh"
        echo "Detected: Apple Silicon (M1/M2/M3)"
    else
        INSTALLER_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
        echo "Detected: Intel Mac"
    fi
    
    echo "Downloading Miniconda installer..."
    mkdir -p ~/miniconda3
    curl -L $INSTALLER_URL -o ~/miniconda3/miniconda.sh
    
    echo "Installing Miniconda..."
    bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
    
    echo "Cleaning up installer..."
    rm ~/miniconda3/miniconda.sh
    
    echo "Initializing conda for bash and zsh..."
    ~/miniconda3/bin/conda init bash
    ~/miniconda3/bin/conda init zsh
    
    echo -e "${GREEN}✅ Miniconda installed successfully${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Please restart your terminal and run this script again.${NC}"
    echo "After restart, you should see (base) in your terminal prompt."
    exit 0
fi
echo -e "${GREEN}✅ Conda found ($(conda --version))${NC}"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠️  Node.js not found. Installing via Homebrew...${NC}"
    echo ""
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew first..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH based on architecture
        ARCH=$(uname -m)
        if [ "$ARCH" = "arm64" ]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        else
            echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/usr/local/bin/brew shellenv)"
        fi
        echo -e "${GREEN}✅ Homebrew installed${NC}"
    fi
    
    echo "Installing Node.js..."
    brew install node
    
    echo -e "${GREEN}✅ Node.js installed successfully${NC}"
fi
echo -e "${GREEN}✅ Node.js found ($(node --version))${NC}"
echo ""

# Get Anthropic API key
echo "🔑 Setting up Anthropic API key..."
if [ -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file already exists. Keeping existing configuration.${NC}"
else
    echo "Please enter your Anthropic API key:"
    read -r api_key
    if [ -z "$api_key" ]; then
        echo -e "${RED}❌ API key cannot be empty${NC}"
        exit 1
    fi
    echo "ANTHROPIC_API_KEY=$api_key" > .env
    echo -e "${GREEN}✅ API key saved to .env${NC}"
fi
echo ""

# Create conda environment
echo "🐍 Setting up Python environment with Conda..."
ENV_NAME="pico"
if conda env list | grep -q "^$ENV_NAME "; then
    echo -e "${YELLOW}⚠️  Conda environment '$ENV_NAME' already exists.${NC}"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing environment..."
        conda env remove -n $ENV_NAME -y
        echo "Creating new environment..."
        conda create -n $ENV_NAME python=3.11 -y
    else
        echo "Using existing environment..."
    fi
else
    echo "Creating conda environment '$ENV_NAME' with Python 3.11..."
    conda create -n $ENV_NAME python=3.11 -y
fi
echo -e "${GREEN}✅ Conda environment ready${NC}"
echo ""

# Activate conda environment and install Python dependencies
echo "📚 Installing Python dependencies..."
eval "$(conda shell.bash hook)"
conda activate $ENV_NAME

if [ -f requirements.txt ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Python dependencies installed${NC}"
else
    echo -e "${RED}❌ requirements.txt not found${NC}"
    exit 1
fi
echo ""

# Install frontend dependencies
echo "🎨 Installing frontend dependencies..."
cd frontend
if [ -f package.json ]; then
    npm install
    echo -e "${GREEN}✅ Frontend dependencies installed${NC}"
else
    echo -e "${RED}❌ package.json not found${NC}"
    exit 1
fi
cd ..
echo ""

# Create data directories
echo "📁 Setting up data directories..."
mkdir -p backend/data/notes
mkdir -p data/notes
echo -e "${GREEN}✅ Data directories created${NC}"
echo ""

# Setup complete
echo "=================================================="
echo -e "${GREEN}✨ Setup complete!${NC}"
echo ""
echo "To start Pico, run:"
echo ""
echo -e "  ${YELLOW}./start.sh${NC}"
echo ""
echo "Or manually:"
echo -e "  ${YELLOW}1. Terminal 1:${NC} conda activate pico && python backend/main.py"
echo -e "  ${YELLOW}2. Terminal 2:${NC} cd frontend && npm start"
echo ""
echo "The app will open at http://localhost:4000"
echo "=================================================="
