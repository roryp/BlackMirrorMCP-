# Black Mirror MCP Agents

This repository contains **six ready-to-run MCP agents** inspired by *Black Mirror* Season 7, wired for the lightweight **`gpt-4.1-nano`** model hosted from GitHub runners.

## 🗂 Repo layout
```
.
├── black_mirror_mcp_agents.py
├── <agent-id>/agent.yaml       # generated after running the helper
└── README.md
```

## ⚙️ Prerequisites

| Requirement            | Tested Version | Notes                                   |
|------------------------|---------------|-----------------------------------------|
| Python                 | 3.10 – 3.12   | `venv` or `pyenv` recommended           |
| GitHub Personal Token  | PAT with `packages:read` scope | Set via `GITHUB_TOKEN` or `MCP_GITHUB_TOKEN` |
| Azure Developer CLI    | ≥ 0.11        | (`azd`) for Azure MCP deployments       |
| GitHub MCP extension¹  | latest        | optional – run agents locally           |
| Docker (optional)      | ≥ 24.0        | required only for containerised runs    |

¹ Install with `azd extension add mcp`.

## 📦 Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
```

*requirements.txt*
```
azure-mcp-cli>=0.11
pytest>=8.2
pyyaml>=6.0
python-dotenv>=1.0
```

## 🚀 Quick Start
```bash
export GITHUB_TOKEN="ghp_XXXXXXXXXXXXXXXXXXXXXXXX"

python black_mirror_mcp_agents.py ./agents
pytest -q
cd agents/common_people_assistant
mcp run
```

## ☁️ Deploy to Azure MCP
```bash
az login
cd agents/bete_noire_reality_simulator
azd up
```
