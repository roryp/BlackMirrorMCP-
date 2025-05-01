# server.py
import os
from pathlib import Path

import yaml
from flask import Flask, request, jsonify
from openai import OpenAI

# ✅ Modern MCP bindings (pip install "mcp[cli]")
from mcp.types import JSONRPCRequest, JSONRPCResponse  # <— replaces the old MCPRequest/MCPResponse

app = Flask(__name__)

# ---------------------------------------------------------------------
# Helper – load every agents/<name>/agent.yaml into a dict
# ---------------------------------------------------------------------
def load_agents() -> dict[str, dict]:
    agents_dir = Path(__file__).parent / "agents"
    agents: dict[str, dict] = {}
    for path in agents_dir.glob("*/agent.yaml"):
        with open(path, "r", encoding="utf-8") as f:
            agents[path.parent.name] = yaml.safe_load(f)
    return agents

agents = load_agents()

# ---------------------------------------------------------------------
# Public end-points
# ---------------------------------------------------------------------
@app.route("/", methods=["GET"])
def root():
    return jsonify(
        {
            "available_agents": list(agents.keys()),
            "usage": "POST JSON-RPC 2.0 to /agent/<agent_id>/mcp",
        }
    )

@app.route("/agents", methods=["GET"])
def get_agents():
    return jsonify(
        [
            {
                "id": aid,
                "name": cfg["agent"]["name"],
                "description": cfg["agent"]["description"],
            }
            for aid, cfg in agents.items()
        ]
    )

# ---------------------------------------------------------------------
# Core: handle an MCP JSON-RPC request and proxy it to an LLM
# ---------------------------------------------------------------------
def _to_openai_messages(system_prompt: str, rpc: JSONRPCRequest) -> list[dict]:
    """Convert MCP chat params → OpenAI chat format."""
    msgs = [{"role": "system", "content": system_prompt}]
    for m in (rpc.params or {}).get("messages", []):
        msgs.append({"role": m["role"], "content": m["content"]})
    return msgs

@app.route("/agent/<agent_id>/mcp", methods=["POST"])
def handle_mcp(agent_id: str):
    if agent_id not in agents:
        return jsonify({"error": f"Agent '{agent_id}' not found"}), 404

    # Validate JSON-RPC 2.0 request
    try:
        rpc = JSONRPCRequest.model_validate(request.json)
    except Exception as exc:
        return jsonify({"error": f"Invalid JSON-RPC request: {exc}"}), 400

    agent_cfg = agents[agent_id]
    system_prompt = agent_cfg["agent"]["prompt"].split("(system)", 1)[-1].strip()

    # OpenAI-compatible client (GitHub-hosted LLMs, OpenRouter, Ollama proxy…)
    client = OpenAI(
        api_key=os.getenv("GITHUB_TOKEN") or os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.github.com/llm/v1"),
    )

    try:
        completion = client.chat.completions.create(
            model=agent_cfg["agent"]["model"]["name"],
            messages=_to_openai_messages(system_prompt, rpc),
            temperature=agent_cfg["agent"]["model"].get("temperature", 0.7),
        )

        result = JSONRPCResponse(
            jsonrpc="2.0",
            id=rpc.id,
            result={
                "role": "assistant",
                "content": completion.choices[0].message.content,
            },
        )
        return jsonify(result.model_dump())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    # Respect $PORT on PaaS platforms
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=True)
