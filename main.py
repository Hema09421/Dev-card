import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from google.adk import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.genai.types import Content, Part
from agent import github_card_agent
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

app = FastAPI(title="GitHub Dev Card Generator API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Services
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()
app_name = "GithubCardApp"

# Initialize ADK Runner
runner = Runner(
    agent=github_card_agent,
    session_service=session_service,
    memory_service=memory_service,
    app_name=app_name
)

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/generate")
async def generate_card(payload: dict = Body(...)):
    username = payload.get("username")
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    
    user_id = "default_user"
    session_id = f"session_{username}"
    
    # Ensure session exists
    try:
        await session_service.get_session(user_id=user_id, session_id=session_id, app_name=app_name)
    except Exception:
        await session_service.create_session(user_id=user_id, session_id=session_id, app_name=app_name)

    user_msg = Content(role="user", parts=[Part(text=f"Generate a dev card for {username}")])
    
    full_response = ""
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_msg
        ):
            if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                for part in event.content.parts:
                    if hasattr(part, 'text'):
                        full_response += part.text
        
        card_path = Path(f"static/cards/{username}.html")
        if not card_path.exists():
            raise HTTPException(status_code=500, detail="Card generation failed to save file")
            
        with open(card_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        return {
            "username": username,
            "status": "success",
            "card_url": f"/card/{username}",
            "html": html_content,
            "agent_response": full_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/card/{username}")
async def get_card(username: str):
    card_path = Path(f"static/cards/{username}.html")
    if not card_path.exists():
        raise HTTPException(status_code=404, detail="Card not found")
    return FileResponse(card_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
