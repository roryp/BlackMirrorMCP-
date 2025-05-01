# black_mirror_mcp_agents.py
"""
MCP agent definitions for Black Mirror Season 7 plus helper utilities.

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
from pathlib import Path
import traceback

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

def write_agent_files(base: Path | str = ".") -> None:
    """Explode AGENT_MANIFESTS_YAML into <agent-id>/agent.yaml files."""
    import yaml
    base_dir = Path(base)
    try:
        for i, block in enumerate(AGENT_MANIFESTS_YAML.split('---')):
            block = block.strip()
            if not block:
                continue
            
            # Parse the block to get the agent_id
            try:
                print(f"Processing block {i+1}...")
                yaml_data = yaml.safe_load(block)
                if not yaml_data or 'agent' not in yaml_data or 'id' not in yaml_data['agent']:
                    print(f"Skipping block {i+1} - missing agent id")
                    continue
                agent_id = yaml_data['agent']['id']
                
                # Create agent directory and write the file
                agent_path = base_dir / "agents" / agent_id
                agent_path.mkdir(parents=True, exist_ok=True)
                
                # Write the properly formatted YAML
                with open(agent_path / 'agent.yaml', 'w', encoding='utf-8') as f:
                    yaml.dump(yaml_data, f, default_flow_style=False)
                
                print(f"✔︎ wrote {agent_path / 'agent.yaml'}")
            except Exception as e:
                print(f"Error processing block {i+1}: {e}")
                print(f"Block content: {block[:100]}...")
                continue
    except Exception as e:
        print(f"General error in write_agent_files: {e}")
        traceback.print_exc()

def _load_yaml_docs():
    import yaml
    return list(yaml.safe_load_all(AGENT_MANIFESTS_YAML))
