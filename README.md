# Deep Think - Multi-Agent Framework

A simple experimental framework that uses multiple AI agents to work on problems in parallel. Agents communicate through Redis and can execute code, search the web, and collaborate on solutions.

## Overview

This is a basic multi-agent system where 4 agents work together to solve problems. Each agent can contribute different approaches, and the system tries to find the best solution through collaboration.

## How it works

- **Orchestrator**: Manages the workflow and coordinates agents via Redis
- **4 Agents**: Work independently on the same problem (agent_a, agent_b, agent_c, agent_d)  
- **Redis**: Handles message passing between components
- **Docker**: Everything runs in containers

Each agent can:
- Call LLM APIs to generate solutions
- Execute Python code 
- Read/write files
- Search the web
- Run basic shell commands

## Getting Started

### What you need

- Docker and Docker Compose
- An API key for LLM access

### Setup

1. Clone this repo
   ```bash
   git clone git@github.com:unixsysdev/llmtalks.git
   cd llmtalks
   ```

2. Create a `.env` file with your API credentials (see below)

3. Run the deployment script
   ```bash
   ./deploy.sh
   ```

### Configuration

Create a `.env` file with your API settings:

```env
CHUTES_API_TOKEN=your_api_token_here
CHUTES_API_URL=https://openrouter.ai/api/v1/chat/completions
MODEL_NAME=@preset/free
# Add other settings as needed
```

## Usage

### Try it out

```bash
# Test with a simple problem
docker-compose exec orchestrator python3 redis_orchestrator.py "Write a Python script that prints hello world" -d
```

### Check if it's working

```bash
# See what containers are running
docker-compose ps

# Look at the logs
docker-compose logs -f orchestrator
```

## Project Structure

```
deep_think/
├── agent_a/           # Agent A workspace 
├── agent_b/           # Agent B workspace
├── agent_c/           # Agent C workspace  
├── agent_d/           # Agent D workspace
├── orchestrator/      # Main coordination logic
├── shared/            # Shared files between agents
├── agent_base.py      # Common agent functionality
├── redis_orchestrator.py  # Main orchestrator
├── redis_agent_worker.py  # Agent worker implementation
├── docker-compose.yml     # Container setup
└── deploy.sh             # Deployment script
```

## Notes

- This is experimental software
- Not recommended for production use
- Agents may produce inconsistent results
- API costs can add up quickly with multiple agents

## Contributing

Feel free to submit issues or pull requests. This is a learning project so all feedback is welcome.