FROM python:3.11-slim

# Install dependencies
RUN pip install azure-mcp-cli

# Set the working directory
WORKDIR /app

# Copy the agent file
COPY agent.yaml /app/

# Set the GitHub token as an environment variable
ENV GITHUB_TOKEN=${GITHUB_TOKEN}

# Run the agent
CMD ["mcp", "run"]