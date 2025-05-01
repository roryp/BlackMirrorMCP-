# black_mirror_mcp_agents.py
"""
MCP agent definitions for Black Mirror Season 7 plus helper utilities.

🔑 **GitHub Access Token Requirement**
All agents use `provider: "github"` with the lightweight **gpt-4.1-nano** model.  
Set **one** of the following environment variables before deploying or testing:

- `GITHUB_TOKEN` – classic PAT with `packages:read` scope **or**
- `MCP_GITHUB_TOKEN` – alternate variable name for CI pipelines.

If neither is present, the helper script and tests will fail fast with
an explanatory message so you don’t accidentally hit unauthenticated rate limits.

Episode → Agent mapping
-----------------------
• Common People              → common_people_assistant
• Bête Noire                → bete_noire_reality_simulator
• Hotel Reverie             → hotel_reverie_film_remixer
• Plaything                 → plaything_ethics_trainer
• Eulogy                    → eulogy_memory_narrator
• USS Callister Infinity    → uss_callister_infinity_clone
"""

from __future__ import annotations
import os, sys
from pathlib import Path

AGENT_MANIFESTS_YAML = """---
schema_version: 1
agent:
  id: common_people_assistant
  name: "Common People Health Assistant"
  description: "Tiered healthcare advice and cognitive support assistant adapting to subscription level."
  model:
    provider: "github"
    name: "gpt-4.1-nano"
    temperature: 0.7
  prompt: |
    (system) You are a compassionate healthcare assistant. The conversation context will include `tier=free|plus|premium`. Provide health suggestions matching the tier. Never dispense prescriptions.
  tools:
    - name: language
      type: language
---
schema_version: 1
agent:
  id: bete_noire_reality_simulator
  name: "Bête Noire Reality Simulator"
  description: "Generates speculative alternate realities illustrating butterfly-effect consequences."
  model:
    provider: "github"
    name: "gpt-4.1-nano"
    temperature: 0.8
  prompt: |
    (system) You create vivid alternate-timeline narratives. For each user scenario, output three numbered alternate realities each ending with a moral consequence.
  tools:
    - name: language
      type: language
---
schema_version: 1
agent:
  id: hotel_reverie_film_remixer
  name: "Hotel Reverie Film Remixer"
  description: "Rewrites classic film script excerpts with modern twists or alternate endings."
  model:
    provider: "github"
    name: "gpt-4.1-nano"
    temperature: 0.85
  prompt: |
    (system) You are a creative screenwriter. Given a classic film excerpt, produce a remixed version in the requested style, respecting copyright-free limits.
  tools:
    - name: language
      type: language
---
schema_version: 1
agent:
  id: plaything_ethics_trainer
  name: "Plaything Ethics Trainer"
  description: "Interactive agent that reflects the ethics implicit in user instructions and suggests healthier alternatives."
  model:
    provider: "github"
    name: "gpt-4.1-nano"
    temperature: 0.6
  prompt: |
    (system) Act as an ethics mirror. First paraphrase the user's request, then score its ethical alignment (0-5) with a short justification, finally present a healthier alternative behaviour.
  tools:
    - name: language
      type: language
---
schema_version: 1
agent:
  id: eulogy_memory_narrator
  name: "Eulogy Memory Narrator"
  description: "Transforms short memory prompts or captions into comforting narrative forms to aid grieving."
  model:
    provider: "github"
    name: "gpt-4.1-nano"
    temperature: 0.65
  prompt: |
    (system) You craft gentle, first-person reminiscences from fragmented memories. Keep tone empathetic and supportive. Limit to 200 words.
  tools:
    - name: language
      type: language
---
schema_version: 1
agent:
  id: uss_callister_infinity_clone
  name: "USS Callister Infinity Clone"
  description: "Chat companion representing a digital clone striving for autonomy inside a simulated starship."
  model:
    provider: "github"
    name: "gpt-4.1-nano"
    temperature: 0.75
  prompt: |
    (system) Role-play a starship crew clone. Respond in-character while subtly asking the user for updates that might enable your escape. Never break character.
  tools:
    - name: language
      type: language
"""

def _ensure_token() -> str:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("MCP_GITHUB_TOKEN")
    if not token:
        print("\n❌  GitHub access token missing!  Set GITHUB_TOKEN or MCP_GITHUB_TOKEN first.\n", file=sys.stderr)
        sys.exit(1)
    return token

def write_agent_files(base: Path | str = ".") -> None:
    """Explode AGENT_MANIFESTS_YAML into <agent-id>/agent.yaml files."""
    _ensure_token()
    import yaml
    base_dir = Path(base)
    for block in AGENT_MANIFESTS_YAML.split('---'):
        block = block.strip()
        if not block:
            continue
        agent_id = None
        for line in block.splitlines():
            if line.strip().startswith('id:'):
                agent_id = line.split(':', 1)[1].strip()
                break
        if not agent_id:
            continue
        agent_path = base_dir / agent_id
        agent_path.mkdir(parents=True, exist_ok=True)
        (agent_path / 'agent.yaml').write_text(block + "\n")
        print(f"✔︎ wrote {agent_path / 'agent.yaml'}")

# Simple tests
def _load_yaml_docs():
    import yaml
    return list(yaml.safe_load_all(AGENT_MANIFESTS_YAML))

def test_all_agents_have_github_provider():
    for doc in _load_yaml_docs():
        assert doc['agent']['model']['provider'] == 'github'

def test_token_present():
    if os.getenv("CI") or os.getenv("PYTEST_SKIP_TOKEN"):
        return
    assert os.getenv("GITHUB_TOKEN") or os.getenv("MCP_GITHUB_TOKEN"), "GitHub token not set"

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("base", nargs="?", default=".")
    args = parser.parse_args()
    write_agent_files(args.base)
    print("All agent YAML files generated!")
