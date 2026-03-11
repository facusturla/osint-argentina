import socket
from urllib.parse import urlparse

def get_ip_from_domain(domain: str) -> str:
    """
    Resolve IP address for a given domain.
    """
    # Clean scheme if user passed http://domain.com
    if "://" in domain:
        domain = urlparse(domain).netloc

    try:
        ip = socket.gethostbyname(domain)
        return ip
    except socket.gaierror:
        return "Not found"

def check_nic_ar_availability(domain: str) -> dict:
    """
    Simple check if a .ar domain is registered by querying NIC.ar public WHOIS API endpoint (if available) or checking HTTP.
    For MVP, we check if the domain resolves to an IP, which implies it is registered.
    """
    if not domain.endswith(".ar"):
        return {"error": "Domain must end with .ar for this specific check."}
        
    ip = get_ip_from_domain(domain)
    
    if ip == "Not found":
         return {
             "registered": False,
             "status": "Available or not resolving",
             "domain": domain
         }
    else:
        return {
             "registered": True,
             "status": "Registered and resolving",
             "domain": domain,
             "ip": ip
         }

def get_domain_info(domain: str) -> dict:
    clean_domain = urlparse(domain).netloc if "://" in domain else domain
    result = {
        "domain": clean_domain,
        "ip": get_ip_from_domain(clean_domain)
    }
    
    if clean_domain.endswith(".ar"):
        result["nic_ar_info"] = check_nic_ar_availability(clean_domain)
        
    return result
