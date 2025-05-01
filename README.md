# Black Mirror Agents Docker Usage

This Dockerfile sets up a simple Flask server that serves all the Black Mirror-inspired agents through a REST API

## Building the Docker Image

```bash
docker build -t black-mirror-agents .
```

## Running the Container

Run the container with your GitHub token:

```bash
docker run -p 8000:8000 -e GITHUB_TOKEN=your_github_token black-mirror-agents
```

## Using the Agents

Once the container is running, you can:

1. **List all available agents**:
   ```
   GET http://localhost:8000/
   ```

2. **Interact with a specific agent**:
   ```
   POST http://localhost:8000/agent/common_people_assistant
   Content-Type: application/json
   
   {
     "message": "Your message to the agent"
   }
   ```

## Available Agents

- **common_people_assistant**: Tiered healthcare advice assistant
- **bete_noire_reality_simulator**: Generates alternate-timeline narratives
- **hotel_reverie_film_remixer**: Rewrites classic film scripts
- **plaything_ethics_trainer**: Ethics reflection assistant
- **eulogy_memory_narrator**: Transforms memories into narratives
- **uss_callister_infinity_clone**: Digital starship clone roleplay

Each agent provides unique responses based on its specialized prompt and character.