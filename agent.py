import os
import asyncio
from google.adk import Agent, Runner
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams, StdioServerParameters
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai.types import Content, Part
from dotenv import load_dotenv

load_dotenv()

# Define the MCP Toolset
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="uv",
            args=["run", "python", "mcp_server.py"],
            env=os.environ.copy()
        )
    )
)

# Create the Agent: "github_card_agent"
github_card_agent = Agent(
    name="github_card_agent",
    model="gemini-1.5-flash",
    instruction=(
        "You are a GitHub profile analyst and dev card generator. "
        "When a user gives you a GitHub username, you ALWAYS follow this exact sequence: "
        "first call scrape_github, then analyze_profile with the result, "
        "then generate_card_html with all three inputs, then save_card. "
        "Never skip steps. Be enthusiastic about developers' work. "
        "If the profile is private or doesn't exist, say so clearly."
    ),
    tools=[mcp_toolset]
)

if __name__ == "__main__":
    async def main():
        session_service = InMemorySessionService()
        app_name = "GithubCardApp"
        # Pre-creating the session with app_name
        await session_service.create_session(
            user_id="test_user", 
            session_id="test_session", 
            app_name=app_name
        )
        
        runner = Runner(
            agent=github_card_agent, 
            session_service=session_service, 
            app_name=app_name
        )
        print("Testing agent with 'torvalds'...")
        
        user_msg = Content(role="user", parts=[Part(text="Generate a card for torvalds")])
        
        try:
            async for event in runner.run_async(
                user_id="test_user",
                session_id="test_session",
                new_message=user_msg
            ):
                if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text'):
                            print(part.text, end="", flush=True)
            print("\nTest complete.")
        except Exception as e:
            print(f"\nAgent execution failed: {e}")
            import traceback
            traceback.print_exc()
    
    asyncio.run(main())
