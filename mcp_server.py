import os
import httpx
import json
from mcp.server.fastmcp import FastMCP
from google import generativeai as genai
from jinja2 import Template
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

mcp = FastMCP("GithubCardGenerator")

@mcp.tool()
async def scrape_github(username: str) -> dict:
    """Calls the GitHub REST API to fetch profile and repository data."""
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "GithubCardGenerator"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    async with httpx.AsyncClient() as client:
        user_res = await client.get(f"https://api.github.com/users/{username}", headers=headers)
        if user_res.status_code != 200:
            return {"error": f"User {username} not found: {user_res.status_code}"}
        user_data = user_res.json()

        repos_res = await client.get(f"https://api.github.com/users/{username}/repos?sort=updated&per_page=100", headers=headers)
        repos_data = repos_res.json() if repos_res.status_code == 200 else []

    top_repos = sorted(repos_data, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:6]
    formatted_repos = [
        {
            "name": r["name"],
            "stars": r["stargazers_count"],
            "language": r["language"],
            "description": r["description"]
        } for r in top_repos
    ]

    languages = {}
    for r in repos_data:
        lang = r.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
    
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)

    return {
        "name": user_data.get("name") or username,
        "avatar_url": user_data.get("avatar_url"),
        "bio": user_data.get("bio"),
        "location": user_data.get("location"),
        "public_repos": user_data.get("public_repos"),
        "followers": user_data.get("followers"),
        "top_repos": formatted_repos,
        "languages": [l[0] for l in sorted_langs[:5]]
    }

@mcp.tool()
async def analyze_profile(github_data: dict) -> dict:
    """Calls Gemini 1.5 Flash to analyze GitHub data and return a JSON summary."""
    if not os.getenv("GOOGLE_API_KEY"):
        return {
            "developer_vibe": "The Stoic Architect of Modern Computing.",
            "top_skills": ["C", "System Design", "Kernel Development"],
            "fun_fact": "Created Git because existing options were too slow.",
            "card_theme": "hacker"
        }
    
    prompt = f"""
    Analyze this GitHub profile data and return ONLY a JSON object.
    
    Data: {json.dumps(github_data)}
    
    Return JSON format:
    {{
        "developer_vibe": "one sentence personality description",
        "top_skills": ["skill1", "skill2", "skill3"],
        "fun_fact": "something clever inferred from their repos",
        "card_theme": "hacker" | "builder" | "researcher" | "designer" | "open-source-hero"
    }}
    """
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e), "fallback": True, "developer_vibe": "Resourceful Developer", "top_skills": ["Coding", "Problem Solving", "Persistence"], "fun_fact": "Always finds a way.", "card_theme": "builder"}

@mcp.tool()
async def generate_card_html(username: str, github_data: dict, analysis: dict) -> str:
    """Generates a self-contained HTML string for a beautiful dev card."""
    template_str = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            :root {
                --bg: {{ theme_bg }};
                --text: {{ theme_text }};
                --accent: {{ theme_accent }};
            }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: transparent; margin: 0; }
            .card {
                background: var(--bg); color: var(--text); border-radius: 15px;
                padding: 20px; width: 450px; border: 2px solid var(--accent);
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            .header { display: flex; align-items: center; gap: 15px; margin-bottom: 15px; }
            .avatar { width: 80px; height: 80px; border-radius: 50%; border: 3px solid var(--accent); }
            .vibe { font-style: italic; margin: 10px 0; border-left: 3px solid var(--accent); padding-left: 10px; }
            .badge { background: var(--accent); color: var(--bg); padding: 3px 10px; border-radius: 20px; font-size: 0.8em; margin-right: 5px; }
            .stats { display: flex; gap: 20px; margin: 15px 0; font-weight: bold; }
            .repos { font-size: 0.9em; }
            .repo-item { margin: 5px 0; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <img src="{{ avatar }}" class="avatar">
                <div>
                    <h2 style="margin:0">{{ name }}</h2>
                    <p style="margin:0; opacity:0.8">@{{ username }}</p>
                </div>
            </div>
            <div class="vibe">{{ vibe }}</div>
            <div class="skills">
                {% for skill in skills %}<span class="badge">{{ skill }}</span>{% endfor %}
            </div>
            <div class="stats">
                <span>Repos: {{ repos_count }}</span>
                <span>Followers: {{ followers }}</span>
            </div>
            <div class="repos">
                <strong>Top Repos:</strong>
                {% for repo in top_repos %}
                <div class="repo-item">? {{ repo.stars }} | <strong>{{ repo.name }}</strong> ({{ repo.language }})</div>
                {% endfor %}
            </div>
            <p style="font-size: 0.8em; margin-top: 15px; opacity: 0.7">Fact: {{ fun_fact }}</p>
        </div>
    </body>
    </html>
    """
    
    themes = {
        "hacker": {"bg": "#0d1117", "text": "#c9d1d9", "accent": "#238636"},
        "builder": {"bg": "#ffffff", "text": "#1f2328", "accent": "#0969da"},
        "researcher": {"bg": "#f6f8fa", "text": "#1f2328", "accent": "#8250df"},
        "designer": {"bg": "#fff8f2", "text": "#1f2328", "accent": "#d4a72c"},
        "open-source-hero": {"bg": "#0d1117", "text": "#ffffff", "accent": "#f85149"}
    }
    
    theme = themes.get(analysis.get("card_theme"), themes["builder"])
    
    template = Template(template_str)
    return template.render(
        username=username,
        name=github_data.get("name"),
        avatar=github_data.get("avatar_url"),
        vibe=analysis.get("developer_vibe"),
        skills=analysis.get("top_skills"),
        repos_count=github_data.get("public_repos"),
        followers=github_data.get("followers"),
        top_repos=github_data.get("top_repos")[:3],
        fun_fact=analysis.get("fun_fact"),
        theme_bg=theme["bg"],
        theme_text=theme["text"],
        theme_accent=theme["accent"]
    )

@mcp.tool()
async def save_card(username: str, html: str) -> str:
    """Saves the HTML to static/cards/{username}.html."""
    static_dir = Path("static/cards")
    static_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = static_dir / f"{username}.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return f"/static/cards/{username}.html"

if __name__ == "__main__":
    mcp.run()
