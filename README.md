# Black Mirror Agents - MCP Enabled

This project hosts Black Mirror-inspired AI agents using the Model Context Protocol (MCP), making them compatible with VS Code and other MCP clients.

## Building the Agents

### Local Development

1. Set up your environment:
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Generate agent files (if needed)
   python -c "from black_mirror_mcp_agents import write_agent_files; write_agent_files()"
   
   # Edit .env file to add your GitHub token
   # GITHUB_TOKEN=your_github_token_here
   ```

2. Run the server locally:
   ```bash
   python server.py
   ```

### Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t black-mirror-agents .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 -e GITHUB_TOKEN=your_github_token black-mirror-agents
   ```

## Using with VS Code MCP Client

### Setup VS Code

1. Install the MCP Extension:
   - Open VS Code
   - Go to Extensions (Ctrl+Shift+X)
   - Search for "Model Context Protocol"
   - Install the extension

2. Configure MCP Connection:
   - Open VS Code Settings (Ctrl+,)
   - Search for "MCP"
   - Add a new endpoint with these settings:
     ```json
     {
       "name": "Black Mirror Agents",
       "url": "http://localhost:8000/agent/{agent_id}/mcp",
       "authType": "none"
     }
     ```

3. Connect to an Agent:
   - Open the MCP sidebar in VS Code
   - Select "Black Mirror Agents" from the dropdown
   - Replace "{agent_id}" with one of the available agent IDs (e.g., "common_people_assistant")

### Available Agents

- **common_people_assistant**: Tiered healthcare advice assistant
- **bete_noire_reality_simulator**: Generates alternate-timeline narratives
- **hotel_reverie_film_remixer**: Rewrites classic film scripts
- **plaything_ethics_trainer**: Ethics reflection assistant
- **eulogy_memory_narrator**: Transforms memories into narratives
- **uss_callister_infinity_clone**: Digital starship clone roleplay

### Agent Usage Examples

#### Common People Assistant
When using this agent, include the tier in your message:
```
tier=free I've been having headaches lately, what should I do?
```

#### Bête Noire Reality Simulator
Provide a scenario and get three alternate realities:
```
What if I decided to skip college and travel the world instead?
```

#### Hotel Reverie Film Remixer
Provide a film excerpt and the style to remix it in:
```
Remix the "Here's looking at you, kid" scene from Casablanca in a cyberpunk style
```

## API Endpoints

- **GET /** - List all available agents
- **GET /agents** - Get detailed information about all agents
- **POST /agent/{agent_id}/mcp** - MCP endpoint for agent interaction

## Troubleshooting

- If you get authentication errors, ensure your GitHub token is correctly set
- For local development, check that your `.env` file contains the proper token
- For Docker, verify you're passing the token via the environment variable