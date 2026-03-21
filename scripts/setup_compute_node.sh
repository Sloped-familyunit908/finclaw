#!/bin/bash
# ============================================================
# FinClaw Compute Node 一键部署脚本
# ============================================================
# 在新机器上跑这一个脚本就行:
#   curl -sSL <raw_url> | bash
#   或: bash setup_compute_node.sh
#
# 前提: Python 3.9+, git 已装好
# ============================================================

set -e

REPO_URL="https://github.com/NeuZhou/finclaw.git"
WORK_DIR="$HOME/finclaw"
RESULTS_REPO=""  # ← 填你的 private repo URL (见下方说明)

echo "============================================================"
echo "🦀 FinClaw Compute Node Setup"
echo "============================================================"

# Step 1: Clone finclaw
if [ -d "$WORK_DIR" ]; then
    echo "📂 finclaw already exists, pulling latest..."
    cd "$WORK_DIR"
    git pull
else
    echo "📥 Cloning finclaw..."
    git clone "$REPO_URL" "$WORK_DIR"
    cd "$WORK_DIR"
fi

# Step 2: Install Python dependencies
echo ""
echo "📦 Installing dependencies..."
pip install baostock numpy scipy pyyaml 2>/dev/null || pip3 install baostock numpy scipy pyyaml

# Step 3: Download A-share data
echo ""
echo "📊 Downloading A-share data (BaoStock, free, ~20-30 min)..."
python scripts/download_a_shares.py || python3 scripts/download_a_shares.py

# Step 4: Setup results repo (for git sync)
echo ""
if [ -n "$RESULTS_REPO" ]; then
    echo "🔗 Setting up results git sync..."
    cd evolution_results 2>/dev/null || mkdir -p evolution_results && cd evolution_results
    if [ ! -d ".git" ]; then
        git init
        git remote add origin "$RESULTS_REPO"
        # Pull existing results if any
        git pull origin main 2>/dev/null || true
    fi
    cd "$WORK_DIR"
    echo "✅ Git sync configured → $RESULTS_REPO"
else
    echo "⚠️  No RESULTS_REPO set. Edit this script or manually init:"
    echo "    cd $WORK_DIR/evolution_results"
    echo "    git init && git remote add origin <your-private-repo-url>"
fi

echo ""
echo "============================================================"
echo "✅ Setup complete!"
echo ""
echo "To start 24/7 evolution:"
echo ""
echo "  cd $WORK_DIR"
echo "  # Without git sync:"
echo "  nohup python -u scripts/run_evolve.py > evolve.log 2>&1 &"
echo ""
echo "  # With git sync (pushes results every 10 gens):"
echo "  nohup python -u scripts/run_evolve.py --git-sync > evolve.log 2>&1 &"
echo ""
echo "  # Or use tmux (recommended):"
echo "  tmux new -s evolve 'python scripts/run_evolve.py --git-sync'"
echo "============================================================"
