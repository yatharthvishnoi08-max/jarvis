"""Document analysis (PDF) and weather lookup tools inspired by OpenJarvis.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import httpx
from pypdf import PdfReader

def read_pdf(file_path: str, max_pages: int = 10) -> str:
    """Read and extract text from a PDF file.
    Parameters
    ----------
    file_path:
        Absolute or relative path to the PDF document.
    max_pages:
        Maximum number of pages to read (default 10).
    """
    path = Path(file_path).resolve()
    if not path.exists():
        return f"Error: PDF file not found at '{file_path}'."
    if not path.is_file():
        return f"Error: '{file_path}' is a directory, not a file."

    try:
        reader = PdfReader(str(path))
        num_pages = len(reader.pages)
        pages_to_read = min(num_pages, max_pages)

        extracted = []
        for i in range(pages_to_read):
            page_text = reader.pages[i].extract_text() or ""
            extracted.append(f"--- Page {i+1} ---\n{page_text.strip()}")

        text_content = "\n\n".join(extracted)
        summary = f"**Document:** {path.name} ({num_pages} total pages, read {pages_to_read})\n\n{text_content}"
        return summary
    except Exception as e:
        return f"PDF Extraction Error: {str(e)}"


def get_weather(location: str, units: str = "metric") -> str:
    """Look up current weather conditions and forecast for any city or location.
    Works keylessly via global weather meteorological endpoints.
    """
    loc = location.strip()
    if not loc:
        return "Location cannot be empty."

    # Use wttr.in JSON API (keyless, fast, comprehensive)
    try:
        url = f"https://wttr.in/{urllib_quote(loc)}?format=j1"
        resp = httpx.get(
            url,
            headers={"User-Agent": "JARVIS-Weather/3.0"},
            timeout=10.0
        )
        if resp.status_code == 200:
            data = resp.json()
            curr = data.get("current_condition", [{}])[0]
            area = data.get("nearest_area", [{}])[0]

            city = area.get("areaName", [{}])[0].get("value", loc)
            country = area.get("country", [{}])[0].get("value", "")

            temp_c = curr.get("temp_C")
            temp_f = curr.get("temp_F")
            feels_c = curr.get("FeelsLikeC")
            feels_f = curr.get("FeelsLikeF")
            desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear")
            humidity = curr.get("humidity")
            wind_kmh = curr.get("windspeedKmph")
            wind_mph = curr.get("windspeedMiles")

            if units.lower() == "imperial":
                temp_str = f"{temp_f}°F (Feels like {feels_f}°F)"
                wind_str = f"{wind_mph} mph"
            else:
                temp_str = f"{temp_c}°C (Feels like {feels_c}°C)"
                wind_str = f"{wind_kmh} km/h"

            return (
                f"### Weather in {city}, {country}\n"
                f"- **Condition:** {desc}\n"
                f"- **Temperature:** {temp_str}\n"
                f"- **Humidity:** {humidity}%\n"
                f"- **Wind:** {wind_str}\n"
            )
    except Exception as e:
        return f"Weather Lookup Error for '{location}': {str(e)}"

def urllib_quote(text: str) -> str:
    import urllib.parse
    return urllib.parse.quote(text)
