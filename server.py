# server.py
import os
from pathlib import Path
import time
import json
import uuid

import yaml
from flask import Flask, request, jsonify, Response
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

# ✅ Modern MCP bindings (pip install "mcp[cli]")
from mcp.types import JSONRPCRequest, JSONRPCResponse

app = Flask(__name__)

# Global message queue for SSE events
message_queue = []

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

# SSE Endpoint for VS Code MCP Client
@app.route("/sse", methods=["GET"])
def sse():
    def generate():
        # Send initial connection message
        yield "event: connection\ndata: {\"status\": \"connected\"}\n\n"
        
        # Send capabilities message to properly identify as MCP server
        yield "event: capabilities\ndata: {\"clientIds\": true, \"agents\": true, \"lsp\": true}\n\n"
        
        # Send agents available
        agent_list = [
            {
                "id": aid,
                "name": cfg["agent"]["name"],
                "description": cfg["agent"]["description"],
            }
            for aid, cfg in agents.items()
        ]
        yield f"event: agents\ndata: {json.dumps(agent_list)}\n\n"
        
        # Process any queued messages
        while len(message_queue) > 0:
            msg = message_queue.pop(0)
            yield f"event: message\ndata: {json.dumps(msg)}\n\n"
        
        # Keep connection alive with heartbeats and handle message queue
        last_id = 0
        try:
            while True:
                # Send any new messages that have been queued
                while len(message_queue) > 0:
                    msg = message_queue.pop(0)
                    yield f"event: message\ndata: {json.dumps(msg)}\n\n"
                
                time.sleep(1)
                yield "event: heartbeat\ndata: {}\n\n"
        except GeneratorExit:
            pass
    
    return Response(generate(), mimetype="text/event-stream", headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
    })

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

# MCP Language Server Protocol endpoint
@app.route("/mcp", methods=["POST"])
def handle_lsp():
    try:
        request_data = request.json
        print(f"Received LSP request: {request_data}")
        
        method = request_data.get("method")
        request_id = request_data.get("id")
        
        # Handle initialize request
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "capabilities": {
                        "textDocumentSync": 1,  # Full sync
                        "completionProvider": {
                            "resolveProvider": False,
                            "triggerCharacters": ["."]
                        },
                        "mcpAgentProvider": True
                    },
                    "serverInfo": {
                        "name": "BlackMirrorMCP",
                        "version": "1.0.0"
                    }
                }
            }
            message_queue.append(response)
            return jsonify(response)
        
        # Handle initialized notification
        elif method == "initialized":
            # No response needed for notifications
            return jsonify({"jsonrpc": "2.0", "result": None})
        
        # Handle mcp/getAgents request
        elif method == "mcp/getAgents":
            agent_list = [
                {
                    "id": aid,
                    "name": cfg["agent"]["name"],
                    "description": cfg["agent"]["description"],
                }
                for aid, cfg in agents.items()
            ]
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": agent_list
            }
            message_queue.append(response)
            return jsonify(response)
        
        # Handle mcp/chat request
        elif method == "mcp/chat":
            params = request_data.get("params", {})
            agent_id = params.get("agentId")
            
            if agent_id not in agents:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": f"Agent '{agent_id}' not found"
                    }
                }
                message_queue.append(error_response)
                return jsonify(error_response)
            
            # Process chat request
            try:
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
                
                # Convert messages to Azure AI Inference format
                messages = [SystemMessage(system_prompt)]
                for m in params.get("messages", []):
                    if m["role"] == "user":
                        messages.append(UserMessage(m["content"]))
                    elif m["role"] == "assistant":
                        from azure.ai.inference.models import AssistantMessage
                        messages.append(AssistantMessage(m["content"]))
                
                completion = client.complete(
                    messages=messages,
                    temperature=temperature,
                    top_p=1.0,
                    model=model_name
                )
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "role": "assistant",
                        "content": completion.choices[0].message.content,
                    }
                }
                message_queue.append(response)
                return jsonify(response)
            
            except Exception as exc:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"Error processing chat request: {str(exc)}"
                    }
                }
                message_queue.append(error_response)
                return jsonify(error_response)
        
        # Handle unknown methods
        else:
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found"
                }
            }
            message_queue.append(error_response)
            return jsonify(error_response)
    
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "id": request.json.get("id", None),
            "error": {
                "code": -32603,
                "message": f"Internal server error: {str(e)}"
            }
        }
        message_queue.append(error_response)
        return jsonify(error_response)

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
