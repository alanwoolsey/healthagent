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

def lambda_handler(event, context):
    """
    Lambda entry point.

    Expects event["message"] to contain user input string.
    """

    # Load system prompt
    with open("systemprompt.txt", "r") as prompt_file:
        system_prompt = prompt_file.read().strip()

    # Start MCP client and agent
    params = StdioServerParameters(command="python", args=["getPatient.py"])
    with MCPClient(lambda: stdio_client(params)) as mcp_client:
        tools = mcp_client.list_tools_sync()
        agent = Agent(tools=tools, system_prompt=system_prompt)

        user_message = event.get("message", "Hello, what can you do?")
        prompt = f"System: {system_prompt}\nUser: {user_message}"
        result = agent(prompt)

        return {
            "statusCode": 200,
            "response": getattr(result, "text", str(result))
        }
