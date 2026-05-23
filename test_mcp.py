import asyncio
import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()

async def test_mcp():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "mcp_server.py"],
        env=os.environ.copy()
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 1. Scrape GitHub
                print("1. Scraping torvalds...")
                scrape_res = await session.call_tool("scrape_github", {"username": "torvalds"})
                if not scrape_res.content or "error" in scrape_res.content[0].text:
                    print(f"FAILED scrape_github: {scrape_res.content}")
                    return
                github_data = json.loads(scrape_res.content[0].text)
                
                # 2. Analyze Profile
                print("2. Analyzing profile...")
                try:
                    analyze_res = await session.call_tool("analyze_profile", {"github_data": github_data})
                    if not analyze_res.content:
                        print("FAILED analyze_profile: No content")
                        return
                    analysis = json.loads(analyze_res.content[0].text)
                except Exception as inner_e:
                    print(f"FAILED analyze_profile with exception: {str(inner_e)}")
                    # Print stdout/stderr if possible or log more info
                    return
                
                # 3. Generate HTML
                print("3. Generating HTML card...")
                html_res = await session.call_tool("generate_card_html", {
                    "username": "torvalds",
                    "github_data": github_data,
                    "analysis": analysis
                })
                
                # 4. Save Card
                print("4. Saving card...")
                save_res = await session.call_tool("save_card", {
                    "username": "torvalds",
                    "html": html_res.content[0].text
                })
                
                print("\n--- TEST RESULTS ---")
                print(f"Card Theme: {analysis.get('card_theme')}")
                print(f"Developer Vibe: {analysis.get('developer_vibe')}")
                print(f"Saved to: {save_res.content[0].text}")

    except Exception as e:
        print(f"AN ERROR OCCURRED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp())
