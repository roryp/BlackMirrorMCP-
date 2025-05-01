# Black Mirror Agents

This project hosts AI agents inspired by Black Mirror Season 7, compatible with VS Code through the Model Context Protocol (MCP).

## Quick Start

### Prerequisites
- Python 3.11+
- Docker (optional)
- GitHub token (for API access to GitHub-hosted models)
- VS Code with MCP extension (for testing)

### 1. Local Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/BlackMirrorMCP-.git
cd BlackMirrorMCP-

# Create and activate a virtual environment (recommended)
python -m venv venv
# On Windows
venv\Scripts\activate
# On Unix/MacOS
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create a .env file with your GitHub token
echo "GITHUB_TOKEN=your_github_token_here" > .env

# Generate agent YAML files (if not already present)
python -c "from black_mirror_mcp_agents import write_agent_files; write_agent_files()"

# Start the server
python server.py
```

### 2. Docker Setup

```bash
# Build the Docker image
docker build -t black-mirror-agents .

# Run the container
docker run -p 8000:8000 -e GITHUB_TOKEN=your_github_token black-mirror-agents
```

## Testing with VS Code

1. **Install the Model Context Protocol extension** in VS Code
2. **Configure a new MCP endpoint**:
   - Settings > Search "MCP" > Add endpoint:
   ```json
   {
     "name": "Black Mirror Agent",
     "url": "http://localhost:8000/agent/common_people_assistant/mcp",
     "authType": "none"
   }
   ```
3. **Open the MCP chat panel** and start interacting with the agent

## Available Agents

Replace the agent ID in the URL to use different agents:

- `common_people_assistant`: Healthcare advisor (use with `tier=free|plus|premium`)
- `bete_noire_reality_simulator`: Alternative reality generator
- `hotel_reverie_film_remixer`: Film script remixer
- `plaything_ethics_trainer`: Ethics reflection bot
- `eulogy_memory_narrator`: Memory to narrative converter
- `uss_callister_infinity_clone`: Sci-fi character roleplay

## API Access

If not using VS Code, you can access the API directly:

```bash
# List all agents
curl http://localhost:8000/

# Query an agent
curl -X POST http://localhost:8000/agent/common_people_assistant/mcp \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"tier=free What should I do about headaches?"}]}'
```

## Full Build Instructions from Scratch

### Setting up the Environment

1. **Create a project directory**:
   ```bash
   mkdir BlackMirrorMCP-
   cd BlackMirrorMCP-
   ```

2. **Download the project files**:
   - Clone the repository or download the source files:
     ```bash
     git clone https://github.com/yourusername/BlackMirrorMCP-.git .
     ```
   - Or download individual files as needed:
     - `black_mirror_mcp_agents.py`
     - `server.py`
     - `requirements.txt`
     - `Dockerfile` (optional)

3. **Set up Python environment**:
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate it
   # On Windows:
   venv\Scripts\activate
   # On Unix/MacOS: 
   # source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

4. **Generate Agent Files**:
   ```bash
   # Run this Python code to generate the agent YAML files
   python -c "from black_mirror_mcp_agents import write_agent_files; write_agent_files()"
   ```
   This will create the necessary YAML files in the `agents/` directory.

5. **Create a .env file**:
   ```bash
   # Create a .env file with your GitHub token
   echo "GITHUB_TOKEN=your_github_token_here" > .env
   ```
   You can get a GitHub token from [GitHub Settings > Developer Settings > Personal access tokens](https://github.com/settings/tokens).

### Running the Application

1. **Start the server**:
   ```bash
   python server.py
   ```
   The server will start on port 8000 by default.

2. **Verify it's working**:
   - Open a browser and go to http://localhost:8000/
   - You should see a list of available agents

### Troubleshooting

- **Authentication errors**: Verify your GitHub token is valid
- **Connection issues**: Ensure the server is running (http://localhost:8000)
- **Agent errors**: Check server logs for details
- **Missing modules**: Ensure all dependencies are installed with `pip install -r requirements.txt`
- **YAML generation errors**: Manually check the `agents/` directory structure
- **Port conflicts**: If port 8000 is already in use, modify the port in `server.py`