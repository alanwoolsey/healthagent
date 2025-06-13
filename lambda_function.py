# lambda_function.py

import os
import json
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient
from mcp import stdio_client, StdioServerParameters

def lambda_handler(event, context):
    try:
        # Load system prompt
        system_prompt = os.environ.get("SYSTEM_PROMPT", "")
        if not system_prompt:
            with open("systemprompt.txt", "r") as f:
                system_prompt = f.read().strip()

        # Parse user input
        if "body" in event:
            body = json.loads(event["body"])
        else:
            body = event
        user_message = body.get("message", "Hello!")
        params = StdioServerParameters(command="python", args=["getPatient.py"])
        mcp_client = MCPClient(lambda: stdio_client(params))
        mcp_client.__enter__()
        # Instantiate agent with tools
        tools = mcp_client.list_tools_sync()
        agent = Agent(tools=tools, system_prompt=system_prompt)
        result = agent(user_message)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({ "response": getattr(result, "text", str(result)) })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({ "error": str(e) })
        }
