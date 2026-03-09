import os
import json
import requests
from requests.exceptions import RequestException

def load_sites(file_path="sites.json"):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def search_username(username: str, sites: dict) -> dict:
    """
    Searches for a username across defined websites.
    Returns a dictionary of site names and the profile URL if found.
    """
    found_profiles = {}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print(f"[*] Buscando rastro del usuario '{username}' en {len(sites)} plataformas...")
    
    for site_name, site_data in sites.items():
        url = site_data.get("url").format(username)
        # Some sites use specific strings to check if user doesn't exist, apart from 404
        error_type = site_data.get("errorType")
        error_msg = site_data.get("errorMsg")

        try:
            # We use timeout so it doesn't hang forever
            response = requests.get(url, headers=headers, timeout=10)
            
            if error_type == "status_code":
                if response.status_code == 200:
                    found_profiles[site_name] = url
            elif error_type == "message":
                if response.status_code == 200 and error_msg not in response.text:
                   found_profiles[site_name] = url
                   
        except RequestException as e:
             # Timeout or connection error, skip and continue
             pass
             
    return found_profiles
