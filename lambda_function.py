import os
import asyncio
from strands import Agent
from getPatient import tools  # This includes async @tool(s)
import json

def lambda_handler(event, context):
    """
    AWS Lambda entry point.

    Expects:
        event["message"]: the user prompt to send to the agent
    """

    # Load system prompt from env var or fallback to file
    system_prompt = os.environ.get("SYSTEM_PROMPT", "")

    if not system_prompt:
        try:
            with open("systemprompt.txt", "r") as prompt_file:
                system_prompt = prompt_file.read().strip()
        except FileNotFoundError:
            return {
                "statusCode": 500,
                "body": "Missing system prompt"
            }

    try:
        agent = Agent(tools=tools, system_prompt=system_prompt)

        user_message = event.get("message", "Hello, what can you do?")
        prompt = f"System: {system_prompt}\nUser: {user_message}"

        # Force async agent execution synchronously
        result = asyncio.run(agent.achat(prompt))  # `achat` = async chat (if available)

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
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({ "error": str(e) })
        }
