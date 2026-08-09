import os
import re
import urllib.request
import urllib.parse
import json
import base64

def fetch_wakatime_stats(api_key):
    auth_string = base64.b64encode(api_key.encode('utf-8')).decode('utf-8')
    headers = {
        "Authorization": f"Basic {auth_string}",
        "User-Agent": "wakatime-markdown-generator"
    }
    
    url = "https://wakatime.com/api/v1/users/current/stats/last_7_days"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            stats = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching stats from WakaTime: {e}")
        return None

    ai_stats = None
    insights_url = "https://wakatime.com/api/v1/users/current/insights/stats/last_7_days"
    req_insights = urllib.request.Request(insights_url, headers=headers)
    try:
        with urllib.request.urlopen(req_insights, timeout=15) as response:
            ai_stats = json.loads(response.read().decode('utf-8'))
            print("Successfully fetched insights data.")
    except Exception as e:
        print(f"Could not fetch insights data (this is normal if not enabled or pro/team feature): {e}")

    return stats, ai_stats

def make_progress_bar(percent, width=20):
    filled = int(round((percent / 100.0) * width))
    return '█' * filled + '░' * (width - filled)

def generate_markdown(stats_payload, ai_payload):
    data = stats_payload.get("data", {})
    
    total_time = data.get("human_readable_total", "0 mins")
    daily_avg = data.get("human_readable_daily_average", "0 mins")
    best_day_info = data.get("best_day", {})
    best_day_str = "N/A"
    if isinstance(best_day_info, dict):
        best_day_date = best_day_info.get("date", "")
        best_day_text = best_day_info.get("text", "")
        if best_day_date and best_day_text:
            best_day_str = f"{best_day_date} ({best_day_text})"
        elif best_day_date:
            best_day_str = best_day_date

    markdown_lines = []
    
    markdown_lines.append("### ⚡ Activity & Insights Overview")
    markdown_lines.append("")
    markdown_lines.append("| 📅 Time Range | ⏳ Total Time | 📈 Daily Average | 🌟 Most Active Day |")
    markdown_lines.append("| :---: | :---: | :---: | :---: |")
    markdown_lines.append(f"| **Last 7 Days** | `{total_time}` | `{daily_avg}` | `{best_day_str}` |")
    markdown_lines.append("")

    ai_data = None
    if ai_payload and "data" in ai_payload:
        ai_data = ai_payload["data"]
    
    ai_percent = data.get("ai_percent") or (ai_data.get("ai_percent") if ai_data else None)
    ai_lines = data.get("ai_lines") or (ai_data.get("ai_lines") if ai_data else None)
    human_lines = data.get("human_lines") or (ai_data.get("human_lines") if ai_data else None)
    tokens = data.get("tokens") or (ai_data.get("tokens") if ai_data else 0)
    cost = data.get("cost") or (ai_data.get("cost") if ai_data else "$0")

    if ai_percent is not None or ai_lines is not None:
        ai_pct_val = ai_percent if ai_percent is not None else 0.0
        bar = make_progress_bar(ai_pct_val, width=15)
        markdown_lines.append("#### 🤖 AI Coding Performance")
        markdown_lines.append("")
        markdown_lines.append("| AI-Driven % | Lines Breakdown | Model Spend | Tokens |")
        markdown_lines.append("| :--- | :--- | :--- | :--- |")
        markdown_lines.append(f"| `{bar}` **{ai_pct_val:.1f}%** | 🤖 `{ai_lines or 0}` AI &nbsp;•&nbsp; 👤 `{human_lines or 0}` Human | `{cost}` | `{tokens}` |")
        markdown_lines.append("")

    languages = data.get("languages", [])
    models = data.get("models", [])
    
    if languages or models:
        markdown_lines.append("#### 🔤 Languages & 🤖 Models")
        markdown_lines.append("")
        markdown_lines.append("| Language / Model | Time / Lines | Visual Share | Share % |")
        markdown_lines.append("| :--- | :--- | :--- | :--- |")
        
        for item in languages[:5]:
            name = item.get("name", "Unknown")
            percent = item.get("percent", 0.0)
            text = item.get("text", "0 mins")
            bar = make_progress_bar(percent, width=12)
            markdown_lines.append(f"| 🔤 **{name}** | {text} | `{bar}` | {percent:.1f}% |")
            
        for item in models[:3]:
            name = item.get("name", "Unknown")
            percent = item.get("percent", 0.0)
            text = item.get("text", item.get("lines_text", "0 lines"))
            bar = make_progress_bar(percent, width=12)
            markdown_lines.append(f"| 🤖 **{name}** | {text} | `{bar}` | {percent:.1f}% |")
            
        markdown_lines.append("")

    editors = data.get("editors", [])
    os_items = data.get("operating_systems", [])
    machines = data.get("machines", [])

    if editors or os_items or machines:
        markdown_lines.append("#### 🛠️ Editors, OS & Machines")
        markdown_lines.append("")
        markdown_lines.append("| Category | Top Selection | Full Breakdown |")
        markdown_lines.append("| :--- | :--- | :--- |")
        
        def fmt_list(items):
            if not items:
                return "N/A"
            return ", ".join([f"{it.get('name')} ({it.get('percent', 0.0):.1f}%)" for it in items[:4]])

        if editors:
            markdown_lines.append(f"| 🛠️ **Editors** | **{editors[0].get('name')}** | {fmt_list(editors)} |")
        if os_items:
            markdown_lines.append(f"| 💻 **Operating System** | **{os_items[0].get('name')}** | {fmt_list(os_items)} |")
        if machines:
            markdown_lines.append(f"| 🖥️ **Machines** | **{machines[0].get('name')}** | {fmt_list(machines)} |")
            
        markdown_lines.append("")

    projects = data.get("projects", [])
    if projects:
        markdown_lines.append("#### 📁 Projects Activity")
        markdown_lines.append("")
        markdown_lines.append("| Project | Time Spent | Visual Share | Share % |")
        markdown_lines.append("| :--- | :--- | :--- | :--- |")
        for item in projects[:5]:
            name = item.get("name", "Unknown")
            percent = item.get("percent", 0.0)
            text = item.get("text", "0 mins")
            bar = make_progress_bar(percent, width=12)
            markdown_lines.append(f"| 📁 **{name}** | {text} | `{bar}` | {percent:.1f}% |")
        markdown_lines.append("")
        
    return "\n".join(markdown_lines)

def update_readme(new_content, filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return False
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = "<!--START_SECTION:waka-->"
    end_marker = "<!--END_SECTION:waka-->"
    
    pattern = re.compile(rf"{start_marker}.*?{end_marker}", re.DOTALL)
    
    if not pattern.search(content):
        print(f"Markers not found in {filepath}")
        return False
        
    updated_content = pattern.sub(f"{start_marker}\n{new_content}\n{end_marker}", content)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(updated_content)
        
    print(f"{filepath} updated successfully.")
    return True

if __name__ == "__main__":
    api_key = os.environ.get("WAKATIME_API_KEY")
    if not api_key:
        print("WAKATIME_API_KEY is not set.")
        exit(1)
        
    payloads = fetch_wakatime_stats(api_key)
    if payloads:
        stats_payload, ai_payload = payloads
        markdown_content = generate_markdown(stats_payload, ai_payload)
        
        # Update both profile/README.md and README.md if they exist and contain markers
        update_readme(markdown_content, "profile/README.md")
        update_readme(markdown_content, "README.md")
    else:
        print("Failed to fetch WakaTime stats.")
        exit(1)
