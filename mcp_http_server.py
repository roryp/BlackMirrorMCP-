#!/usr/bin/env python3
# mcp_http_server.py - HTTP-based MCP server for VS Code MCP extension
import json
import logging
import os
import uuid
from pathlib import Path
from threading import Thread

import yaml
import flask
from flask import Flask, request, jsonify, Response
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage
from azure.core.credentials import AzureKeyCredential

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global state
client_sessions = {}

# ---------------------------------------------------------------------
# Helper – load every agents/<n>/agent.yaml into a dict
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
            logger.error(f"Error loading agent from {path}: {e}")
            # Continue loading other agents even if one fails
            continue
    return agents

# Load agents
agents = load_agents()
logger.info(f"Loaded {len(agents)} agents: {', '.join(agents.keys())}")

# Chat completion function
async def get_completion(agent_id, messages):
    """Get a chat completion from the AI model."""
    try:
        agent_cfg = agents[agent_id]
        system_prompt = agent_cfg["agent"]["prompt"].split("(system)", 1)[-1].strip()
        model_name = agent_cfg["agent"]["model"]["name"]
        temperature = agent_cfg["agent"]["model"].get("temperature", 0.7)
        
        # GitHub hosted models client using Azure AI Inference SDK
        endpoint = "https://models.github.ai/inference"
        token = os.getenv("GITHUB_TOKEN")
        
        if not token:
            logger.error("GITHUB_TOKEN environment variable not set")
            return "Error: GITHUB_TOKEN environment variable not set. Please set it and try again."
        
        client = ChatCompletionsClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(token),
        )
        
        # Convert messages to Azure AI Inference format
        azure_messages = [SystemMessage(system_prompt)]
        for m in messages:
            if m["role"] == "user":
                azure_messages.append(UserMessage(m["content"]))
            elif m["role"] == "assistant":
                azure_messages.append(AssistantMessage(m["content"]))
        
        completion = client.complete(
            messages=azure_messages,
            temperature=temperature,
            top_p=1.0,
            model=model_name
        )
        
        return completion.choices[0].message.content
    except Exception as exc:
        logger.error(f"Error getting completion: {exc}")
        return f"Error: {str(exc)}"

# ---------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "running",
        "agents": list(agents.keys())
    })

# ---------------------------------------------------------------------
# SSE endpoint for connecting VS Code MCP client
# ---------------------------------------------------------------------
@app.route("/sse", methods=["GET"])
def sse():
    def generate():
        # Send initial connection message
        yield "event: connection\ndata: {\"status\": \"connected\"}\n\n"
        
        # Send capabilities message
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
        
        # Keep connection alive with heartbeats
        import time
        try:
            while True:
                time.sleep(10)
                yield "event: heartbeat\ndata: {}\n\n"
        except GeneratorExit:
            pass
    
    return Response(generate(), mimetype="text/event-stream", headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
    })

# ---------------------------------------------------------------------
# MCP Language Server Protocol endpoint
# ---------------------------------------------------------------------
@app.route("/mcp", methods=["POST"])
def handle_lsp():
    try:
        request_data = request.json
        logger.info(f"Received LSP request: {request_data}")
        
        method = request_data.get("method")
        request_id = request_data.get("id")
        params = request_data.get("params", {})
        
        # Handle initialize request
        if method == "initialize":
            logger.info(f"Processing initialize request with id: {request_id}")
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "capabilities": {
                        "textDocumentSync": 1,
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
            return jsonify(response)
        
        # Handle initialized notification
        elif method == "initialized":
            logger.info("Received initialized notification")
            return jsonify({"jsonrpc": "2.0", "result": None})
        
        # Handle shutdown request
        elif method == "shutdown":
            logger.info(f"Processing shutdown request with id: {request_id}")
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": None
            }
            return jsonify(response)
        
        # Handle exit notification
        elif method == "exit":
            logger.info("Received exit notification")
            return jsonify({"jsonrpc": "2.0", "result": None})
        
        # Handle mcp/getAgents request
        elif method == "mcp/getAgents":
            logger.info(f"Processing getAgents request with id: {request_id}")
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
            return jsonify(response)
        
        # Handle mcp/chat request
        elif method == "mcp/chat":
            agent_id = params.get("agentId")
            conversation_id = params.get("conversationId", str(uuid.uuid4()))
            messages = params.get("messages", [])
            
            logger.info(f"Processing chat request for agent: {agent_id}, conversation: {conversation_id}")
            
            if agent_id not in agents:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": f"Agent '{agent_id}' not found"
                    }
                }
                return jsonify(error_response)
            
            # Store conversation
            if conversation_id not in client_sessions:
                client_sessions[conversation_id] = {
                    "agent_id": agent_id,
                    "messages": []
                }
            
            # Update conversation with new messages
            client_sessions[conversation_id]["messages"] = messages
            
            # Get AI response
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                ai_response = loop.run_until_complete(get_completion(agent_id, messages))
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "role": "assistant",
                        "content": ai_response,
                    }
                }
                return jsonify(response)
            
            except Exception as e:
                logger.error(f"Error processing chat: {str(e)}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"Error processing chat request: {str(e)}"
                    }
                }
                return jsonify(error_response)
        
        # Handle unknown methods
        else:
            logger.warning(f"Unknown method received: {method}")
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found"
                }
            }
            return jsonify(error_response)
    
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": request.json.get("id") if request.json and "id" in request.json else None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
        return jsonify(error_response)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting HTTP MCP server on port {port}...")
    logger.info(f"Available endpoints:")
    logger.info(f"  - SSE: http://localhost:{port}/sse")
    logger.info(f"  - MCP: http://localhost:{port}/mcp")
    logger.info(f"Available agents: {', '.join(agents.keys())}")
    
    # Run the server
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)