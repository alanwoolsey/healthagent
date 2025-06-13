import warnings
import asyncio
from strands import Agent
from mcp import stdio_client, StdioServerParameters
from strands.tools.mcp.mcp_client import MCPClient

# Suppress Windows asyncio pipe warnings
def suppress_windows_asyncio_pipe_warning():
    if hasattr(asyncio, 'windows_utils'):
        original_fileno = asyncio.windows_utils.PipeHandle.fileno
        def safe_fileno(self):
            try:
                return original_fileno(self)
            except ValueError:
                return -1
        asyncio.windows_utils.PipeHandle.fileno = safe_fileno

suppress_windows_asyncio_pipe_warning()

# Load system prompt
with open("systemprompt.txt", "r") as prompt_file:
    system_prompt = prompt_file.read().strip()

# MCP client and agent setup
params = StdioServerParameters(command="python", args=["getPatient.py"])
mcp_client = MCPClient(lambda: stdio_client(params))
mcp_client.__enter__()

try:
    tools = mcp_client.list_tools_sync()
    agent = Agent(tools=tools, system_prompt=system_prompt)

    print("✅ HealthAgent CLI is ready. Type your message (or type 'exit' to quit).")

    while True:
        user_message = input("\nYou: ").strip()
        if user_message.lower() in {"exit", "quit"}:
            break

        prompt = f"System: {system_prompt}\nUser: {user_message}"
        result = agent(prompt)

        try:
            print(f"Agent: {result.text}")
        except AttributeError:
            print(f"Agent: {str(result)}")

finally:
    mcp_client.__exit__(None, None, None)
    print("👋 Agent session ended.")