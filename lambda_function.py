import os
from strands import Agent
from getPatient import tools  # Assume this is a list of @tool-decorated functions

def lambda_handler(event, context):
    """
    AWS Lambda entry point.

    Expects:
        event["message"]: the user prompt to send to the agent
    """

    # Load the system prompt from environment variable or fallback file
    system_prompt = os.environ.get("SYSTEM_PROMPT", "")

    if not system_prompt:
        try:
            with open("systemprompt.txt", "r") as prompt_file:
                system_prompt = prompt_file.read().strip()
        except FileNotFoundError:
            return {
                "statusCode": 500,
                "error": "Missing system prompt"
            }

    try:
        agent = Agent(tools=tools, system_prompt=system_prompt)

        user_message = event.get("message", "Hello, what can you do?")
        prompt = f"System: {system_prompt}\nUser: {user_message}"
        result = agent(prompt)

        return {
            "statusCode": 200,
            "response": getattr(result, "text", str(result))
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "error": str(e)
        }
