FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app/

# Install dependencies
RUN pip install -r requirements.txt && \
    pip install flask openai

# Create a simple Flask server to serve the agents
RUN echo 'import os\nimport yaml\nimport json\nfrom flask import Flask, request, jsonify\nfrom openai import OpenAI\n\napp = Flask(__name__)\n\n# Load all agents\ndef load_agents():\n    agents = {}\n    agents_dir = os.path.join(os.getcwd(), "agents")\n    \n    for agent_dir in os.listdir(agents_dir):\n        agent_path = os.path.join(agents_dir, agent_dir, "agent.yaml")\n        if os.path.exists(agent_path):\n            with open(agent_path, "r") as f:\n                agent_data = yaml.safe_load(f)\n                agents[agent_dir] = agent_data\n    return agents\n\nagents = load_agents()\n\n@app.route("/", methods=["GET"])\ndef list_agents():\n    return jsonify({\n        "available_agents": list(agents.keys()),\n        "usage": "POST to /agent/<agent_id> with {\'message\': \'your message\'} to interact with an agent"\n    })\n\n@app.route("/agent/<agent_id>", methods=["POST"])\ndef query_agent(agent_id):\n    if agent_id not in agents:\n        return jsonify({"error": f"Agent {agent_id} not found"}), 404\n    \n    request_data = request.json\n    if not request_data or "message" not in request_data:\n        return jsonify({"error": "Message is required"}), 400\n    \n    message = request_data["message"]\n    agent_data = agents[agent_id]\n    \n    # Get system prompt\n    system_prompt = agent_data["agent"]["prompt"].split("(system)")[1].strip()\n    \n    # Configure OpenAI client\n    client = OpenAI(\n        api_key=os.environ.get("GITHUB_TOKEN") or os.environ.get("MCP_GITHUB_TOKEN"),\n        base_url="https://api.github.com/v1/"\n    )\n    \n    try:\n        response = client.chat.completions.create(\n            model=agent_data["agent"]["model"]["name"],\n            messages=[\n                {"role": "system", "content": system_prompt},\n                {"role": "user", "content": message}\n            ],\n            temperature=agent_data["agent"]["model"]["temperature"]\n        )\n        \n        return jsonify({\n            "agent": agent_data["agent"]["name"],\n            "response": response.choices[0].message.content\n        })\n    except Exception as e:\n        return jsonify({"error": str(e)}), 500\n\nif __name__ == "__main__":\n    app.run(host="0.0.0.0", port=8000)\n' > /app/server.py

# Port for the Flask application
EXPOSE 8000

# Set the GitHub token environment variable at runtime
ENV GITHUB_TOKEN=""

# Run the Flask server
CMD ["python", "/app/server.py"]