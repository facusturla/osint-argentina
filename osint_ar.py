import argparse
import sys
import os

from core.cuit_validator import analyze_cuit
from core.username_search import load_sites, search_username
from core.email_search import search_email
from core.email_harvester import harvest_emails
from core.domain_info import get_domain_info

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    # Fallback if colorama is not installed yet
    class FakeColor:
        def __getattr__(self, name):
            return ""
    Fore = Style = FakeColor()

BANNER = fr"""
{Fore.LIGHTBLUE_EX}================================================================={Style.RESET_ALL}
{Fore.WHITE}      _   _ ___ _____ _          _    ____   ____  {Style.RESET_ALL}
{Fore.WHITE}     | | | |_ _|  ___/ \        / \  |  _ \ / ___| {Style.RESET_ALL}
{Fore.LIGHTBLUE_EX}     | |_| || || |_ / _ \      / _ \ | |_) | |  _  {Style.RESET_ALL}
{Fore.WHITE}     |  _  || ||  _/ ___ \    / ___ \|  _ <| |_| | {Style.RESET_ALL}
{Fore.WHITE}     |_| |_|___|_|/_/   \_\  /_/   \_\_| \_\\____| {Style.RESET_ALL}
{Fore.LIGHTBLUE_EX}================================================================={Style.RESET_ALL}
{Fore.YELLOW}  >> Herramienta de Inteligencia de Fuentes Abiertas - Argentina <<{Style.RESET_ALL}
"""

def main():
    parser = argparse.ArgumentParser(description="OSINT Argentina - Toolkit v1.0")
    
    # Define arguments
    parser.add_argument("-c", "--cuit", help="Analizar y validar un CUIT o CUIL argentino", type=str)
    parser.add_argument("-u", "--username", help="Buscar perfiles asociados a un nombre de usuario", type=str)
    parser.add_argument("-e", "--email", help="Buscar cuentas registradas con una dirección de correo electrónico", type=str)
    parser.add_argument("-H", "--harvest", help="Cosechar emails expuestos de un dominio y verificar existencia", type=str)
    parser.add_argument("-d", "--domain", help="Obtener información WHOIS básica de un dominio (ej: sitio.com.ar)", type=str)

    args = parser.parse_args()

    print(BANNER)

    if not len(sys.argv) > 1:
        parser.print_help()
        sys.exit(1)

    # Logic Routing
    if args.cuit:
        print(f"{Fore.CYAN}[*] Iniciando módulo de Análisis CUIT/CUIL...{Style.RESET_ALL}")
        result = analyze_cuit(args.cuit)
        if result.get("valid"):
            print(f"  {Fore.GREEN}[+] CUIT/CUIL Válido:{Style.RESET_ALL} {result['formatted']}")
            print(f"  {Fore.GREEN}[+] Tipo de Persona:{Style.RESET_ALL} {result['tipo_persona']}")
            print(f"  {Fore.GREEN}[+] Género Inferido:{Style.RESET_ALL} {result['genero_inf']}")
        else:
            print(f"  {Fore.RED}[-] Error:{Style.RESET_ALL} {result.get('error')}")
            
    if args.username:
        print(f"\n{Fore.CYAN}[*] Iniciando módulo de Búsqueda de Usuario...{Style.RESET_ALL}")
        sites_file = os.path.join(os.path.dirname(__file__), 'sites.json')
        sites = load_sites(sites_file)
        
        if not sites:
            print(f"  {Fore.RED}[-] Error: No se encontró el archivo sites.json o está vacío.{Style.RESET_ALL}")
        else:
            results = search_username(args.username, sites)
            if results:
                print(f"  {Fore.GREEN}[+] Perfiles encontrados para '{args.username}':{Style.RESET_ALL}")
                for site, url in results.items():
                    print(f"      - {Fore.YELLOW}{site}:{Style.RESET_ALL} {url}")
            else:
                 print(f"  {Fore.RED}[-] No se encontraron perfiles públicos en los {len(sites)} sitios registrados.{Style.RESET_ALL}")

    if args.email:
        print(f"\n{Fore.CYAN}[*] Iniciando módulo de Búsqueda de Email...{Style.RESET_ALL}")
        results = search_email(args.email)
        
        if results:
            print(f"  {Fore.GREEN}[+] Cuentas encontradas registradas con '{args.email}':{Style.RESET_ALL}")
            for site in results:
                print(f"      - {Fore.YELLOW}{site}{Style.RESET_ALL}")
        elif results is not None:
             print(f"  {Fore.RED}[-] No se encontraron cuentas asociadas a este correo.{Style.RESET_ALL}")

    if args.domain:
        print(f"\n{Fore.CYAN}[*] Iniciando módulo de Información de Dominio...{Style.RESET_ALL}")
        info = get_domain_info(args.domain)
        print(f"  {Fore.GREEN}[+] Dominio:{Style.RESET_ALL} {info['domain']}")
        print(f"  {Fore.GREEN}[+] Dirección IP Resoluble:{Style.RESET_ALL} {info['ip']}")
        
        if "nic_ar_info" in info:
            nic = info["nic_ar_info"]
            if nic.get("registered"):
                 print(f"  {Fore.RED}[!] Estado NIC.ar:{Style.RESET_ALL} {nic['status']} - Probablemente registrado por un tercero.")
            else:
                 print(f"  {Fore.GREEN}[!] Estado NIC.ar:{Style.RESET_ALL} {nic['status']} - Podría estar disponible.")

    if args.harvest:
        print(f"\n{Fore.CYAN}[*] Iniciando módulo de Recolección Perimetral de Emails para '{args.harvest}'...{Style.RESET_ALL}")
        results = harvest_emails(args.harvest)
        
        print(f"  {Fore.GREEN}[+] Verificación de Dominio (MX):{Style.RESET_ALL}")
        if results["mx_valid"]:
             print(f"      - El dominio {Fore.GREEN}PUEDE RECIBIR CORREOS{Style.RESET_ALL} (Registros MX válidos encontrados).")
        else:
             print(f"      - El dominio {Fore.RED}NO PARECE RECIBIR CORREOS{Style.RESET_ALL} (Sin registros MX). Los emails podrían ser falsos positivos.")
             
        if results["emails"]:
            print(f"  {Fore.GREEN}[+] Emails Expuestos Encontrados ({len(results['emails'])}):{Style.RESET_ALL}")
            for email in results["emails"]:
                print(f"      - {Fore.YELLOW}{email}{Style.RESET_ALL}")
        else:
             print(f"  {Fore.RED}[-] No se encontraron emails expuestos públicamente para este dominio.{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
