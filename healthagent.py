import warnings
import asyncio
from strands import Agent
from mcp import stdio_client, StdioServerParameters
from strands.tools.mcp.mcp_client import MCPClient
from strands.models import BedrockModel

# MCP client and agent setup
params = StdioServerParameters(command="python", args=["getPatient.py"])
mcp_client = MCPClient(lambda: stdio_client(params))
mcp_client.__enter__()

with open("systemprompt.txt", "r") as prompt_file:
    system_prompt = prompt_file.read().strip()

try:
    tools = mcp_client.list_tools_sync()
    agent_model = BedrockModel(
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        temperature=0.3,
        max_tokens=2000,
        top_p=0.8,
    )
    agent = Agent(
        model=agent_model,
        tools=tools, 
        system_prompt=system_prompt)

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