import os
import json
import aiohttp
import asyncio

def load_sites(file_path="sites.json"):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
import aiohttp
import asyncio

async def fetch_profile(session, site_name, site_data, username, found_profiles):
    url = site_data.get("url").format(username)
    error_type = site_data.get("errorType")
    error_msg = site_data.get("errorMsg")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        async with session.get(url, headers=headers, timeout=10) as response:
            if error_type == "status_code":
                if response.status == 200:
                    found_profiles[site_name] = url
            elif error_type == "message":
                if response.status == 200:
                    text = await response.text()
                    if error_msg not in text:
                        found_profiles[site_name] = url
    except Exception:
        pass  # Timeout or connection error, skip

async def _run_search_async(username, sites):
    found_profiles = {}
    print(f"[*] Buscando rastro del usuario '{username}' en {len(sites)} plataformas de forma concurrente...")
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for site_name, site_data in sites.items():
            tasks.append(
                fetch_profile(session, site_name, site_data, username, found_profiles)
            )
        await asyncio.gather(*tasks)
        
    return found_profiles

def search_username(username: str, sites: dict) -> dict:
    """
    Searches for a username across defined websites asynchronously.
    Returns a dictionary of site names and the profile URL if found.
    """
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    return asyncio.run(_run_search_async(username, sites))
