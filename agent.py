import os
import re
import paramiko
from pydantic import SecretStr
from typing import Annotated, TypedDict
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

HOSTS: dict[str, str] = {
    "ubuntu": "ubuntu-target",
    "debian": "debian-target",
}

SSH_USER     = "root"
SSH_PASSWORD = "root"
SSH_PORT     = 22

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")

def create_llm() -> BaseChatModel:
    if GEMINI_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI
        print("Using Gemini")
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0,
        )
    if OPENAI_API_KEY:
        print("Using OpenAI")
        return ChatOpenAI(model="gpt-4o-mini", api_key=SecretStr(OPENAI_API_KEY), temperature=0)
    from langchain_ollama import ChatOllama
    print(f"Using Ollama model={OLLAMA_MODEL} url={OLLAMA_BASE_URL}")
    return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)

class SSHExecutor:
    def run(self, host_alias: str, script: str) -> str:
        hostname = HOSTS.get(host_alias.lower())
        if not hostname:
            return f"Unknown host '{host_alias}'. Choose from: {list(HOSTS)}"
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            client.connect(
                hostname=hostname,
                port=SSH_PORT,
                username=SSH_USER,
                password=SSH_PASSWORD,
                timeout=15,
            )
            _, stdout, stderr = client.exec_command(script)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            return out or err or "(no output)"
        except Exception as exc:
            return f"SSH error: {exc}"
        finally:
            client.close()

_executor = SSHExecutor()

@tool
def run_script_on_host(host: str, script: str) -> str:
    """
    Executes a shell script on the specified host via SSH.
    Args:
        host: Target host (e.g., 'ubuntu' or 'debian')
        script: Shell command to execute
    Returns:
        Output of the executed command
    """
    print(f"\nExecuting on [{host}]:\n{'-'*40}\n{script}\n{'-'*40}")
    result = _executor.run(host, script)
    print(f"Output:\n{result}\n")
    return result

SYSTEM_PROMPT = f"""You are an SSH automation agent.
Available hosts : {list(HOSTS.keys())}
Rules:
- When a user asks about a system, generate a Linux shell command.
- Use the tool run_script_on_host to execute it.
- ALWAYS base your final answer ONLY on the tool output.
- NEVER invent or simulate command output.
- If the tool returns empty output, say "(no output)" and the appropriate message.
"""

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

class SSHAgent:
    def __init__(self):
        llm = create_llm()
        self._llm_with_tools = llm.bind_tools([run_script_on_host])
        self._graph = self._build_graph()

    def _llm_node(self, state: AgentState) -> AgentState:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = self._llm_with_tools.invoke(messages)
#        print("\nLLM response:", response, "\n")
        return {"messages": [response]}

    @staticmethod
    def _route(state: AgentState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    def _build_graph(self):
        tool_node = ToolNode(tools=[run_script_on_host])
        g = StateGraph(AgentState)
        g.add_node("llm",   self._llm_node)
        g.add_node("tools", tool_node)
        g.set_entry_point("llm")
        g.add_conditional_edges("llm", self._route, {"tools": "tools", END: END})
        g.add_edge("tools", "llm")
        return g.compile()

    def chat(self, user_input: str) -> str:
        result = self._graph.invoke(
            {"messages": [HumanMessage(content=user_input)]}
        )
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content if isinstance(msg.content, str) else str(msg.content)
        return "(no response)"

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║            SSH AI Agent  —  Type 'exit' to quit              ║
╠══════════════════════════════════════════════════════════════╣
║  Hosts   :  Ubuntu  |  Debian                                ║
║  Examples:                                                   ║
║    > Show disk usage on ubuntu                               ║
║    > List running processes on debian                        ║
║    > Show memory usage on ubuntu                             ║
║    > Create a file called hello.txt on debian                ║
║    > Check which users are logged in on ubuntu               ║
╚══════════════════════════════════════════════════════════════╝
"""

def main():
    print(BANNER)
    agent = SSHAgent()
    print("Agent ready\n")
    while True:
        try:
            user_input = input("User> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("Goodbye!")
            break
        print("Thinking...\n")
        reply = agent.chat(user_input)
        print(f"Agent> {reply}\n")
        print("─" * 60)
if __name__ == "__main__":
    main()