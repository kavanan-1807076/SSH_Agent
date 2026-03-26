# SSH Agent

[![Python](https://img.shields.io/badge/Python-3.12-yellow)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-0.12.0-white)](https://ollama.com/)
[![LangChain](https://img.shields.io/badge/LangChain-Latest-green)](https://www.langchain.com/)
[![Docker](https://img.shields.io/badge/Docker-29.2.1-blue)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Closed%20Source-red)]()

**SSH (Secure Shell) Agent** is an AI-powered remote command execution tool that interprets natural language instructions, generates Linux shell commands using an LLM, and executes them on remote hosts (Docker containers) via SSH, returning unaltered command output with an explaination.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Architecture Diagram](#architecture-diagram)
- [Key Components](#key-components)
- [Setup & Installation](#setup--installation)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Overview

SSH AI Agent automates remote Linux command execution through a combination of:

- Accepting **Natural Language** input from the user describing what to do on a remote system
- Using a configured **LLM** (Ollama/OpenAI/Gemini) to convert user intent into valid Linux shell commands.
- Connecting to target **Docker containers** (Ubuntu, Debian) over SSH using **Paramiko**
- Executing the generated command on the chosen remote host and capturing **Output**
- Orchestrating the full workflow using **LangGraph** and **LangChain** agent tooling
- Supporting **NVIDIA GPU acceleration** via Ollama 0.12.0 for local LLM inference

---

## Tech Stack

| Layer              | Technology                        |
|-------------------|-----------------------------------|
| Agent Framework    | LangGraph, LangChain              |
| LLM Backend        | Ollama (local), OpenAI, Gemini    |
| SSH Execution      | Paramiko                          |
| Target Hosts       | Docker (Ubuntu, Debian)|
| Containerization   | Docker            |
| Language           | Python 3.12                       |
| Development IDE    | VS Code                           |

---

## Project Structure

```
SSH_Agent/
│
├── agent.py                  # Core AI agent - LLM selection, SSH tool, LangGraph workflow
├── docker-compose.yml        # Multi-container setup: ubuntu-target, debian-target, agent
├── Dockerfile                # Builds the agent container with Python dependencies
├── requirements.txt          # Python package dependencies
├── venv/                     # Local Python virtual environment (development only)
└── README.md
```

---

## Architecture Diagram

```
+-------------------+      +-------------------+      +-------------------+
|                   |      |                   |      |                   |
|    User Input     | ---> |    LangGraph      | ---> |       LLM         |
|(Natural Language) |      |      Agent        |      | (Ollama/OpenAI    |
|                   |      |                   |      |    /Gemini)       |
+-------------------+      +-------------------+      +-------------------+
                                                              |
                                                              v
+-------------------+      +-------------------+      +-------------------+
|                   |      |                   |      |                   |
|  Command's Output | <--- |     SSH Tool      | <--- |   Shell Command   |
|  is returned with |      |    (Paramiko)     |      |  (LLM generated)  |
|  additional notes |      |                   |      |                   |
+-------------------+      +-------------------+      +-------------------+
                                   |
                  +----------------+----------------+
                  |                                 |
                  v                                 v
   +-------------------------+       +-------------------------+
   |                         |       |                         |
   |     ubuntu-target       |       |     debian-target       |
   |   (Docker container     |       |   (Docker container     |
   |    SSH on port 22)      |       |    SSH on port 22)      |
   |                         |       |                         |
   +-------------------------+       +-------------------------+
```

- **User Input:** Natural language instruction describing the desired action on a remote host (e.g. *"show disk usage on ubuntu"*).
- **LangGraph Agent Loop:** Orchestrates the multi-step reasoning and tool invocation cycle which decides when to call the LLM and when to invoke the SSH tool.
- **LLM (Ollama / OpenAI / Gemini):** Receives the user instruction and generates the appropriate Linux shell command. If API keys for OpenAI or Gemini are set, they take priority over Ollama.
- **Shell Command:** The raw Linux command produced by the LLM (e.g. `df -h`, `ps aux`, `free -m`).
- **SSH Tool (Paramiko):** Establishes an SSH connection to the target container and executes the generated command. Username: `root`, Password: `root`, Port: `22`.
- **ubuntu-target / debian-target:** SSH-enabled Docker containers that act as the remote Linux systems. Commands are executed directly inside these containers.
- **Real Command Output:** The actual stdout/stderr captured from the container is returned as-is to the user. No simulation or hallucination occurs.

---

## Key Components

- **agent.py:**
  The heart of the project. Implements LLM selection logic (Ollama, OpenAI, Gemini), defines the SSH execution tool using Paramiko and builds the full LangGraph agent workflow. Handles multi-turn reasoning and routes tool calls based on LLM decisions.

- **Docker Compose Setup:**
  Provides an isolated, reproducible multi-container environment. The `ubuntu-target` and `debian-target` containers simulate real remote Linux servers. The `agent` container runs the Python agent code and connects to the targets over the shared Docker network.

- **Dockerfile:**
  Builds the agent runtime container. Installs all Python dependencies from `requirements.txt` and configures the working environment for `agent.py` to run inside Docker.

---

## Setup & Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/kavanan-1807076/SSH_Agent.git
   cd SSH_Agent
   ```

2. **Create and activate the virtual environment:**

   Python 3.12 is required.

   ```sh
   python -m venv venv
   ```
   ```sh
   # Windows
   venv\Scripts\activate

   # Linux / macOS
   source venv/bin/activate
   ```

3. **Install Python dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Start target containers:**

   These containers simulate the remote Linux hosts the agent will SSH into. Start them in detached mode and keep them running.
   ```sh
   docker compose up -d ubuntu-target debian-target
   ```

   Verify they are running:
   ```sh
   docker ps
   ```

   Inspect logs if needed:
   ```sh
   docker logs ubuntu-target
   docker logs debian-target
   ```

5. **Setup Ollama (local LLM):**

   > **NOTE:** Ollama **0.12.0** is specifically recommended for NVIDIA GPU support. Newer versions of Ollama may not function correctly with certain NVIDIA GPU configurations. Running on CPU is fully supported with no impact on functionality.

   Get the required model:
   ```sh
   ollama run llama3.1:8b
   ```

   Start the Ollama server:
   ```sh
   ollama serve
   ```

   Environment variables used by the agent (set in `.env` or shell):
   ```
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   OLLAMA_MODEL=llama3.1:8b
   ```

   **Alternative LLM providers** — if API keys are set they will take priority over Ollama:
   ```
   OPENAI_API_KEY=<your-key>       # enables OpenAI
   GEMINI_API_KEY=<your-key>       # enables Gemini
   ```

6. **Build the agent container:**
   ```sh
   docker compose build
   ```

7. **Run the agent:**
   ```sh
   docker compose run --rm agent
   ```

   Restart containers if required at any point:
   ```sh
   docker compose restart ubuntu-target debian-target
   ```

---

## Typical Execution Flow

```sh
# 1. Activate virtual environment (local development)
venv\Scripts\activate

# 2. Install dependencies (first time only)
pip install -r requirements.txt

# 3. Start target containers — keep running
docker compose up -d ubuntu-target debian-target

# 4. Start Ollama server — keep running in a separate terminal
ollama serve

# 5. Build the agent image
docker compose build

# 6. Run the agent
docker compose run --rm agent
```

---

## Example Commands

Once the agent is running, interact with it using plain English:

```
> Show disk usage on ubuntu
> List all running processes on debian
> Check memory usage on ubuntu
> Create a file called hello.txt on debian
> Show logged-in users on ubuntu
> Check CPU info on debian
> Display network interfaces on ubuntu
```

**Available target hosts:**

| Host     | Container        | SSH Port |
|---------|-----------------|----------|
| ubuntu  | ubuntu-target   | 22       |
| debian  | debian-target   | 22       |

SSH credentials for both: `root` / `root`

---

## Troubleshooting

- **Agent cannot connect to target containers via SSH**
  - Run `docker ps` and confirm `ubuntu-target` and `debian-target` are listed as running.
  - Inspect container logs: `docker logs ubuntu-target` / `docker logs debian-target`
  - Ensure SSH service is active inside the containers.

- **LLM returns no response or agent hangs**
  - Confirm `ollama serve` is running in a separate terminal window.
  - Verify the required model is available: `ollama list`
  - Check `OLLAMA_BASE_URL` is correctly set (use `host.docker.internal` when running agent inside Docker).

- **NVIDIA GPU not being used by Ollama**
  - Ensure Ollama version is exactly **0.12.0** — newer versions may drop NVIDIA support.
  - Verify GPU drivers are functional: `nvidia-smi` (For NVIDIA GPUs only).
  - Running on CPU is a fully supported fallback with no functional difference but performance is lowered.

- **Command produces no visible output**
  - Some Linux commands produce no stdout when they succeed (e.g. `touch`, `mkdir`).
  - This is expected behaviour — the agent returns only real output and nothing else, an explaination will be given by the agent.

- **Docker image build errors**
  - Ensure Docker Desktop (Windows) or Docker Engine (Linux) is running before any `docker compose` commands.
  - Confirm `requirements.txt` is present in the project root or has been imported previously.

- **Module import errors when running locally**
  - Ensure the virtual environment is activated before running `pip install`.
  - Verify Python version is 3.12: `python --version`

---

## License

© 2026. All rights reserved.

This project is **closed source** and may not be redistributed or modified without explicit permission from the maintainers.

For inquiries regarding usage, contribution, or licensing please contact the project maintainers.
