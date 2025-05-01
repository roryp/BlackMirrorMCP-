FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app/

# Install dependencies
RUN pip install -r requirements.txt

# Port for the Flask application
EXPOSE 8000

# Set environment variables (will be overridden at runtime)
ENV GITHUB_TOKEN=""

# Run the Flask server
CMD ["python", "/app/server.py"]