import os
import yaml
import json
from pathlib import Path
from flask import Flask, request, jsonify
from openai import OpenAI
from model_context_protocol import MCPRouter, MCPRequest, MCPResponse

app = Flask(__name__)
mcp_router = MCPRouter()

# Load all agents
def load_agents():
    agents = {}
    agents_dir = Path(os.getcwd()) / "agents"
    
    for agent_dir in os.listdir(agents_dir):
        agent_path = agents_dir / agent_dir / "agent.yaml"
        if agent_path.exists():
            with open(agent_path, "r") as f:
                agent_data = yaml.safe_load(f)
                agents[agent_dir] = agent_data
    return agents

agents = load_agents()

@app.route("/", methods=["GET"])
def list_agents():
    return jsonify({
        "available_agents": list(agents.keys()),
        "usage": "Send MCP format requests to /agent/<agent_id>/mcp to interact with an agent"
    })

@app.route("/agents", methods=["GET"])
def get_agents():
    """Return information about available agents"""
    agent_list = []
    for agent_id, agent_data in agents.items():
        agent_list.append({
            "id": agent_id,
            "name": agent_data["agent"]["name"],
            "description": agent_data["agent"]["description"]
        })
    return jsonify(agent_list)

@app.route("/agent/<agent_id>/mcp", methods=["POST"])
def mcp_endpoint(agent_id):
    """Handle MCP protocol requests"""
    if agent_id not in agents:
        return jsonify({"error": f"Agent {agent_id} not found"}), 404
    
    # Parse the MCP request
    try:
        request_data = request.json
        mcp_request = MCPRequest(**request_data)
    except Exception as e:
        return jsonify({"error": f"Invalid MCP request: {str(e)}"}), 400
    
    agent_data = agents[agent_id]
    system_prompt = agent_data["agent"]["prompt"].split("(system)")[1].strip()
    
    # Configure OpenAI client
    client = OpenAI(
        api_key=os.environ.get("GITHUB_TOKEN") or os.environ.get("MCP_GITHUB_TOKEN"),
        base_url="https://api.github.com/v1/"
    )
    
    try:
        # Convert MCP messages to OpenAI format
        messages = [{"role": "system", "content": system_prompt}]
        for msg in mcp_request.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        response = client.chat.completions.create(
            model=agent_data["agent"]["model"]["name"],
            messages=messages,
            temperature=agent_data["agent"]["model"]["temperature"]
        )
        
        # Create MCP response
        mcp_response = MCPResponse(
            message={
                "role": "assistant",
                "content": response.choices[0].message.content
            }
        )
        
        return jsonify(mcp_response.dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)