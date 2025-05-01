#!/usr/bin/env python3
# mcp_socket_server.py - WebSocket-based MCP server for VS Code MCP extension
import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path

import yaml
import websockets
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

# Global state
connected_clients = set()
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

# Load agents
agents = load_agents()
logger.info(f"Loaded {len(agents)} agents: {', '.join(agents.keys())}")

async def handle_request(websocket, path):
    """Handle a WebSocket connection for JSON-RPC requests."""
    client_id = str(uuid.uuid4())
    connected_clients.add(websocket)
    client_sessions[client_id] = {"websocket": websocket, "conversations": {}}
    logger.info(f"Client {client_id} connected")
    
    try:
        async for message in websocket:
            try:
                request = json.loads(message)
                logger.info(f"Received request: {request}")
                
                if "id" not in request:
                    logger.warning("Received request without id")
                    continue
                
                request_id = request.get("id")
                method = request.get("method")
                params = request.get("params", {})
                
                # Handle initialize request
                if method == "initialize":
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
                    await websocket.send(json.dumps(response))
                
                # Handle initialized notification
                elif method == "initialized":
                    # No response needed for notifications
                    pass
                
                # Handle shutdown request
                elif method == "shutdown":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": None
                    }
                    await websocket.send(json.dumps(response))
                
                # Handle exit notification
                elif method == "exit":
                    # No response needed for notifications
                    break
                
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
                    await websocket.send(json.dumps(response))
                
                # Handle mcp/chat request
                elif method == "mcp/chat":
                    agent_id = params.get("agentId")
                    conversation_id = params.get("conversationId", str(uuid.uuid4()))
                    messages = params.get("messages", [])
                    
                    if agent_id not in agents:
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32602,
                                "message": f"Agent '{agent_id}' not found"
                            }
                        }
                        await websocket.send(json.dumps(error_response))
                        continue
                    
                    # Store conversation
                    if conversation_id not in client_sessions[client_id]["conversations"]:
                        client_sessions[client_id]["conversations"][conversation_id] = {
                            "agent_id": agent_id,
                            "messages": []
                        }
                    
                    # Update conversation with new messages
                    client_sessions[client_id]["conversations"][conversation_id]["messages"] = messages
                    
                    # Get AI response
                    try:
                        ai_response = await get_completion(agent_id, messages)
                        
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "role": "assistant",
                                "content": ai_response,
                            }
                        }
                        await websocket.send(json.dumps(response))
                    except Exception as e:
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32603,
                                "message": f"Error processing chat request: {str(e)}"
                            }
                        }
                        await websocket.send(json.dumps(error_response))
                
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
                    await websocket.send(json.dumps(error_response))
            
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {message}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                await websocket.send(json.dumps(error_response))
            
            except Exception as e:
                logger.error(f"Error handling request: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if isinstance(request, dict) else None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                await websocket.send(json.dumps(error_response))
    
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Connection closed for client {client_id}")
    
    finally:
        connected_clients.remove(websocket)
        del client_sessions[client_id]
        logger.info(f"Client {client_id} disconnected")

async def main():
    """Start the WebSocket server."""
    port = int(os.getenv("PORT", "8765"))
    server = await websockets.serve(handle_request, "0.0.0.0", port)
    logger.info(f"MCP WebSocket server started on port {port}")
    logger.info(f"Available agents: {', '.join(agents.keys())}")
    await server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)