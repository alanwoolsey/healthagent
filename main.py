import asyncio
import time
import uvicorn
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from strands import Agent
from mcp import stdio_client, StdioServerParameters
from strands.tools.mcp.mcp_client import MCPClient
from strands.models import BedrockModel
import botocore.exceptions

# -------------------------------
# Suppress asyncio Windows pipe warning (optional)
# -------------------------------
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

# -------------------------------
# Load system prompt
# -------------------------------
with open("systemprompt.txt", "r") as prompt_file:
    system_prompt = prompt_file.read().strip()

# -------------------------------
# Initialize MCP client and tools
# -------------------------------
params = StdioServerParameters(command="python", args=["getPatient.py"])
mcp_client = MCPClient(lambda: stdio_client(params))
mcp_client.__enter__()
tools = mcp_client.list_tools_sync()

# -------------------------------
# FastAPI app setup
# -------------------------------
app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)
print("✅ FastAPI app initialized.")

# Limit to N concurrent model calls per Fargate task
semaphore = asyncio.Semaphore(2)  # Adjust based on throughput limits

# -------------------------------
# Request model
# -------------------------------
class AskRequest(BaseModel):
    message: str

# -------------------------------
# Agent invocation logic with retry
# -------------------------------
async def process_request(request: AskRequest):
    MAX_RETRIES = 3
    backoff = 2

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            agent_model = BedrockModel(
                model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                temperature=0,
                max_tokens_to_sample=200,
                top_p=0.1,
                streaming=True
            )

            agent = Agent(
                tools=tools,
                system_prompt=system_prompt,
                model=agent_model
            )

            response = agent(request.message)
            return {"response": getattr(response, "text", str(response))}

        except botocore.exceptions.ClientError as e:
            if "ThrottlingException" in str(e):
                if attempt < MAX_RETRIES:
                    print(f"⚠️ Throttled. Retrying in {backoff}s (attempt {attempt})...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                else:
                    return {"error": "❌ Too many requests. Please try again shortly."}
            else:
                return {"error": str(e)}

        except Exception as e:
            return {"error": str(e)}

# -------------------------------
# POST endpoint
# -------------------------------
@app.post("/ask")
async def ask_agent(request: AskRequest):
    async with semaphore:
        return await process_request(request)

# -------------------------------
# Health check endpoint
# -------------------------------
@app.get("/health", response_class=PlainTextResponse)
def health_check():
    return "OK"

# -------------------------------
# Shutdown cleanup
# -------------------------------
@app.on_event("shutdown")
async def shutdown_event():
    mcp_client.__exit__(None, None, None)
    print("👋 MCP client closed gracefully.")

# -------------------------------
# Run the app
# -------------------------------
if __name__ == "__main__":
    print("🚀 Starting FastAPI server on 0.0.0.0:80")
    uvicorn.run("main:app", host="0.0.0.0", port=80)
