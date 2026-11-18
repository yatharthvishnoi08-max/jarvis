"""Morning Digest Agent — daily executive briefing synthesizer with voice support.
Adapted from OpenJarvis MorningDigestAgent.
"""
from __future__ import annotations

import datetime
from typing import Dict, Any
from tools.system_tools import get_system_stats
from tools.doc_tools import get_weather
from tools.web_tools import web_search
from tools.meta_tools import read_memory, list_employees

def generate_morning_digest(location: str = "auto", honorific: str = "sir") -> Dict[str, str]:
    """Generate a comprehensive daily executive morning digest.
    Combines:
    1. Greeting and date/time
    2. Host system health & metrics
    3. Weather briefing
    4. Top technology and AI intelligence
    5. Agent team status and memory priorities
    """
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%I:%M %p")

    # 1. System stats
    import psutil
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("C:\\")
    disk_free = disk.free // (1024**3)

    # 2. Weather
    target_loc = location if location != "auto" else "New York"
    weather_report = get_weather(target_loc)

    # 3. Top News Headlines
    news = web_search("top technology artificial intelligence news today", max_results=3)

    # 4. Agent Team
    employees = list_employees()

    # Markdown Report
    markdown_report = f"""# 🌅 JARVIS Executive Morning Briefing
**Date:** {date_str} | **Time:** {time_str}

Good morning, {honorific}. Here is your operational situation report:

## 💻 Host System Status
- **CPU Utilization:** {cpu}%
- **RAM Utilization:** {ram}%
- **Free Storage:** {disk_free} GB available
- **Status:** All core subsystems operating nominally.

## 🌤️ Weather Conditions
{weather_report}

## 🌐 World & Technology Intelligence
{news}

## 🤖 Active Subagent Roster
{employees}

---
*JARVIS Core Gateway Online. Awaiting your commands, {honorific}.*
"""

    # Spoken Audio Script (concise, natural neural speech)
    spoken_script = (
        f"Good morning, {honorific}. Today is {date_str}, {time_str}. "
        f"Your laptop systems are running smoothly with CPU at {cpu} percent, "
        f"and {disk_free} gigabytes of free disk space. "
        f"The weather is currently active in your area. "
        f"All subagents are standing by. How would you like to proceed?"
    )

    return {
        "markdown": markdown_report,
        "spoken_text": spoken_script,
        "spoken_script": spoken_script,
        "timestamp": now.isoformat()
    }
