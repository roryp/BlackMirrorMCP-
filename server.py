# server.py
import os
from pathlib import Path

import yaml
from flask import Flask, request, jsonify
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

# ✅ Modern MCP bindings (pip install "mcp[cli]")
from mcp.types import JSONRPCRequest, JSONRPCResponse

app = Flask(__name__)

# ---------------------------------------------------------------------
# Helper – load every agents/<name>/agent.yaml into a dict
# ---------------------------------------------------------------------
def load_agents() -> dict[str, dict]:
    agents_dir = Path(__file__).parent / "agents"
    agents: dict[str, dict] = {}
    for path in agents_dir.glob("*/agent.yaml"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                agents[path.parent.name] = yaml.safe_load(content)
        except Exception as e:
            print(f"Error loading agent from {path}: {e}")
            # Continue loading other agents even if one fails
            continue
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
def _to_chat_messages(system_prompt: str, rpc: JSONRPCRequest):
    """Convert MCP chat params → Azure AI Inference chat message format."""
    messages = [SystemMessage(system_prompt)]
    for m in (rpc.params or {}).get("messages", []):
        if m["role"] == "user":
            messages.append(UserMessage(m["content"]))
        elif m["role"] == "assistant":
            from azure.ai.inference.models import AssistantMessage
            messages.append(AssistantMessage(m["content"]))
    return messages

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
    model_name = agent_cfg["agent"]["model"]["name"]
    temperature = agent_cfg["agent"]["model"].get("temperature", 0.7)

    # GitHub hosted models client using Azure AI Inference SDK
    endpoint = "https://models.github.ai/inference"
    token = os.getenv("GITHUB_TOKEN")
    
    client = ChatCompletionsClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(token),
    )

    try:
        completion = client.complete(
            messages=_to_chat_messages(system_prompt, rpc),
            temperature=temperature,
            top_p=1.0,
            model=model_name
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
