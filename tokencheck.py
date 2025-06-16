import warnings
import asyncio
from strands import Agent
from mcp import stdio_client, StdioServerParameters
from strands.tools.mcp.mcp_client import MCPClient
from strands.models import BedrockModel

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
agent_model = BedrockModel(
    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    temperature=0,
    max_tokens_to_sample=200,
    top_p=0.1,
    streaming=True
)
try:
    tools = mcp_client.list_tools_sync()
    agent = Agent(
        model=agent_model,
        tools=tools, 
        system_prompt=system_prompt,
        load_tools_from_directory=False
    )

    print("✅ HealthAgent CLI is ready. Type your message (or type 'exit' to quit).")

    while True:
        user_message = input("\nYou: ").strip()
        if user_message.lower() in {"exit", "quit"}:
            break

        prompt = f"System: {system_prompt}\nUser: {user_message}"
        result = agent(prompt)

        # Print the agent response
        if hasattr(result, "metrics"):
            usage = result.metrics.accumulated_usage
            print("\n🔍 Token Usage:")
            print(f"  Prompt tokens: {usage.get('inputTokens')}")
            print(f"  Completion tokens: {usage.get('outputTokens')}")
            print(f"  Total tokens: {usage.get('totalTokens')}")

            latency = result.metrics.accumulated_metrics.get("latencyMs", None)
            if latency is not None:
                print(f"  Latency: {latency} ms")
        else:
            print("⚠️ No metrics data available.")



finally:
    mcp_client.__exit__(None, None, None)
    print("👋 Agent session ended.")
