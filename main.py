import asyncio
import warnings
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from strands import Agent
from mcp import stdio_client, StdioServerParameters
from strands.tools.mcp.mcp_client import MCPClient
from fastapi.middleware.gzip import GZipMiddleware
from strands.models import BedrockModel

# Suppress Windows asyncio pipe warnings (optional)
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

# Load system prompt from file
with open("systemprompt.txt", "r") as prompt_file:
    system_prompt = prompt_file.read().strip()

# Initialize MCP client (tools can be shared)
params = StdioServerParameters(command="python", args=["getPatient.py"])
mcp_client = MCPClient(lambda: stdio_client(params))
mcp_client.__enter__()  # Keep session alive across requests

tools = mcp_client.list_tools_sync()

# Define FastAPI app
app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)
print("✅ FastAPI app initialized.")

# Request model
class AskRequest(BaseModel):
    message: str

# POST endpoint for agent
@app.post("/ask")
async def ask_agent(request: AskRequest):
    try:
        # Create a fresh Bedrock model per request to avoid shared token limits
        agent_model = BedrockModel(
            model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            temperature=0,
            max_tokens_to_sample=200,
            top_p=0.1,
            streaming=True
        )

        # Instantiate a new Agent per request
        agent = Agent(
            tools=tools,
            system_prompt=system_prompt,
            model=agent_model
        )

        response = agent(request.message)
        return {"response": getattr(response, "text", str(response))}
    except Exception as e:
        return {"error": str(e)}

# GET endpoint for health check
@app.get("/health", response_class=PlainTextResponse)
def health_check():
    return "OK"

# Graceful shutdown: clean up MCP client
@app.on_event("shutdown")
async def shutdown_event():
    mcp_client.__exit__(None, None, None)
    print("👋 MCP client closed gracefully.")

# Run with Uvicorn when executed directly
if __name__ == "__main__":
    print("🚀 Starting FastAPI server on 0.0.0.0:80")
    uvicorn.run("main:app", host="0.0.0.0", port=80)
