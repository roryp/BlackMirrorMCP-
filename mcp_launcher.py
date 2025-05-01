#!/usr/bin/env python3
# mcp_launcher.py - Launcher for WebSocket-based MCP server that ensures dependencies are installed
import os
import sys
import subprocess
import traceback

def main():
    """Ensure dependencies are installed and launch the MCP server."""
    # Install all required dependencies
    print("Checking and installing required dependencies...")
    requirements = ["websockets", "pyyaml", "azure-ai-inference==1.0.0b9", "azure-core>=1.29.0"]
    
    for package in requirements:
        try:
            __import__(package.split("==")[0].split(">=")[0])
            print(f"Package {package} is already installed.")
        except ImportError:
            print(f"Installing {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"Package {package} installed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Error installing {package}: {e}")
                return 1
    
    # Launch the MCP server
    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_socket_server.py")
    print(f"Launching MCP server from {server_path}")
    
    try:
        # Execute the server directly (don't use check_call which throws an error)
        process = subprocess.Popen(
            [sys.executable, server_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Print output in real-time
        print("Server starting...")
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"[SERVER] {output.strip()}")
                
        # Check for errors
        stderr = process.stderr.read()
        if stderr:
            print(f"ERROR: {stderr}")
            
        return process.poll()
    except Exception as e:
        print(f"Error launching MCP server: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())