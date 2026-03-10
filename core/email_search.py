import trio
import httpx
from holehe.core import *
from colorama import Fore, Style

class DummyArgs:
    def __init__(self):
        self.onlyused = False
        self.nopasswordrecovery = False

async def _run_holehe(email, out):
    import holehe.core
    
    modules = holehe.core.import_submodules("holehe.modules")
    websites = holehe.core.get_functions(modules, DummyArgs())
    
    client = httpx.AsyncClient()
    
    async with trio.open_nursery() as nursery:
        for website in websites:
            nursery.start_soon(
                holehe.core.launch_module, website, email, client, out
            )
            
    await client.aclose()
    
import re

def search_email(email):
    out = []
    
    # Validamos que el input sea realmente un formato de correo
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        print(f"{Fore.RED}[-] Error: '{email}' no parece ser una dirección de correo válida.{Style.RESET_ALL}")
        return None

    print(f"{Fore.CYAN}[*] Iniciando búsqueda con holehe para {email}... Esto puede tardar unos momentos.{Style.RESET_ALL}")
    
    # We run the async holehe main function usig trio
    try:
         trio.run(_run_holehe, email, out)
    except Exception as e:
         print(f"{Fore.RED}[-] Error durante la ejecución de holehe: {e}{Style.RESET_ALL}")
         return None
         
    # Parse the output
    # out is a list of dicts: {'name': 'SiteName', 'exists': True/False, 'rateLimit': True/False, ...}
    registered_sites = [site['name'] for site in out if site.get('exists') is True]
    
    return registered_sites
