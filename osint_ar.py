import argparse
import sys
import os

from core.cuit_validator import analyze_cuit
from core.username_search import load_sites, search_username
from core.email_search import search_email
from core.email_harvester import harvest_emails
from core.domain_info import get_domain_info
from core.ddjj_lookup import lookup_ddjj
from core.bcra_lookup import lookup_bcra_deudores
from core.georef import normalize_address
from core.report_generator import generate_report

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
    parser = argparse.ArgumentParser(description="OSINT Argentina - Toolkit v1.1")

    # Módulos originales
    parser.add_argument("-c", "--cuit", help="Analizar y validar un CUIT o CUIL argentino", type=str)
    parser.add_argument("-u", "--username", help="Buscar perfiles asociados a un nombre de usuario", type=str)
    parser.add_argument("-e", "--email", help="Buscar cuentas registradas con una dirección de correo electrónico", type=str)
    parser.add_argument("-H", "--harvest", help="Cosechar emails expuestos de un dominio y verificar existencia", type=str)
    parser.add_argument("-d", "--domain", help="Obtener información WHOIS básica de un dominio (ej: sitio.com.ar)", type=str)

    # Nuevos módulos
    parser.add_argument("-j", "--ddjj", help="Buscar declaraciones juradas patrimoniales de funcionarios públicos (ej: \"Juan Perez\")", type=str)
    parser.add_argument("-b", "--bcra", help="Consultar el historial crediticio en la Central de Deudores del BCRA por CUIT", type=str)
    parser.add_argument("-g", "--georef", help="Normalizar un domicilio argentino contra el padrón oficial del IGN (ej: \"Av. Corrientes 1234\")", type=str)

    # Reporte
    parser.add_argument("--report", help="Exportar todos los resultados en un reporte (json o html)", type=str, choices=["json", "html"], metavar="FORMAT")

    args = parser.parse_args()

    print(BANNER)

    if not len(sys.argv) > 1:
        parser.print_help()
        sys.exit(1)

    # Acumular resultados para reporte si se solicitó
    report_results = {}
    target_for_report = (
        args.cuit or args.username or args.email or args.harvest
        or args.domain or args.ddjj or args.bcra or args.georef or "osint"
    )

    # --- Módulo CUIT/CUIL ---
    if args.cuit:
        print(f"{Fore.CYAN}[*] Iniciando módulo de Análisis CUIT/CUIL...{Style.RESET_ALL}")
        result = analyze_cuit(args.cuit)
        if result.get("valid"):
            print(f"  {Fore.GREEN}[+] CUIT/CUIL Válido:{Style.RESET_ALL} {result['formatted']}")
            print(f"  {Fore.GREEN}[+] Tipo de Persona:{Style.RESET_ALL} {result['tipo_persona']}")
            print(f"  {Fore.GREEN}[+] Género Inferido:{Style.RESET_ALL} {result['genero_inf']}")
        else:
            print(f"  {Fore.RED}[-] Error:{Style.RESET_ALL} {result.get('error')}")
        report_results["cuit"] = result

    # --- Módulo Username ---
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
            report_results["username"] = results

    # --- Módulo Email ---
    if args.email:
        print(f"\n{Fore.CYAN}[*] Iniciando módulo de Búsqueda de Email...{Style.RESET_ALL}")
        results = search_email(args.email)

        if results:
            print(f"  {Fore.GREEN}[+] Cuentas encontradas registradas con '{args.email}':{Style.RESET_ALL}")
            for site in results:
                print(f"      - {Fore.YELLOW}{site}{Style.RESET_ALL}")
        elif results is not None:
            print(f"  {Fore.RED}[-] No se encontraron cuentas asociadas a este correo.{Style.RESET_ALL}")
        report_results["email"] = results

    # --- Módulo Dominio ---
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
        report_results["domain"] = info

    # --- Módulo Harvest ---
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
        report_results["harvest"] = results

    # --- Módulo DDJJ ---
    if args.ddjj:
        print(f"\n{Fore.CYAN}[*] Iniciando módulo de Declaraciones Juradas (DDJJ)...{Style.RESET_ALL}")
        result = lookup_ddjj(args.ddjj)

        if result.get("error"):
            print(f"  {Fore.RED}[-] {result['error']}{Style.RESET_ALL}")
        elif result.get("found"):
            print(f"  {Fore.GREEN}[+] Declaraciones encontradas para '{args.ddjj}':{Style.RESET_ALL}")
            for rec in result["results"]:
                print(f"\n      {Fore.YELLOW}Funcionario:{Style.RESET_ALL} {rec['nombre']}")
                print(f"      {Fore.YELLOW}Cargo:{Style.RESET_ALL} {rec['cargo']}")
                print(f"      {Fore.YELLOW}Jurisdicción:{Style.RESET_ALL} {rec['jurisdiccion']}")
                print(f"      {Fore.YELLOW}Año:{Style.RESET_ALL} {rec['año']}")
                print(f"      {Fore.YELLOW}Tipo:{Style.RESET_ALL} {rec['tipo']}")
                print(f"      {Fore.YELLOW}Fuente:{Style.RESET_ALL} {rec['fuente_recurso']}")
        else:
            print(f"  {Fore.RED}[-] No se encontraron declaraciones juradas para '{args.ddjj}'.{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}[i] Verificar manualmente en:{Style.RESET_ALL} {result['fuente']}")
        report_results["ddjj"] = result

    # --- Módulo BCRA ---
    if args.bcra:
        print(f"\n{Fore.CYAN}[*] Iniciando módulo de Central de Deudores BCRA...{Style.RESET_ALL}")
        result = lookup_bcra_deudores(args.bcra)

        if result.get("error"):
            print(f"  {Fore.RED}[-] {result['error']}{Style.RESET_ALL}")
        elif result.get("found"):
            sit = result.get("situacion_maxima", 1)
            color = Fore.GREEN if sit == 1 else Fore.YELLOW if sit <= 2 else Fore.RED
            print(f"  {Fore.GREEN}[+] CUIT:{Style.RESET_ALL} {result['cuit']}")
            print(f"  {Fore.GREEN}[+] Período:{Style.RESET_ALL} {result['periodo']}")
            print(f"  {color}[!] Situación máxima:{Style.RESET_ALL} {sit} — {result.get('situacion_descripcion', '')}")
            if result["entidades"]:
                print(f"  {Fore.GREEN}[+] Entidades reportantes:{Style.RESET_ALL}")
                for ent in result["entidades"]:
                    print(f"      - {Fore.YELLOW}{ent['entidad']}:{Style.RESET_ALL} Situación {ent['situacion']} ({ent['situacion_descripcion']})")
        else:
            print(f"  {Fore.GREEN}[+] CUIT {result['cuit']}:{Style.RESET_ALL} Sin deudas registradas en el BCRA.")
            print(f"  {Fore.YELLOW}[i] Verificar manualmente en:{Style.RESET_ALL} {result['fuente']}")
        report_results["bcra"] = result

    # --- Módulo GeoRef ---
    if args.georef:
        print(f"\n{Fore.CYAN}[*] Iniciando módulo de Normalización de Domicilio (GeoRef)...{Style.RESET_ALL}")
        result = normalize_address(args.georef)

        if result.get("error"):
            print(f"  {Fore.RED}[-] {result['error']}{Style.RESET_ALL}")
        elif result.get("found"):
            print(f"  {Fore.GREEN}[+] Dirección normalizada:{Style.RESET_ALL} {result['direccion_normalizada']}")
            print(f"  {Fore.GREEN}[+] Calle oficial:{Style.RESET_ALL} {result['calle']} {result['altura'] or ''}")
            print(f"  {Fore.GREEN}[+] Localidad:{Style.RESET_ALL} {result['localidad']}")
            print(f"  {Fore.GREEN}[+] Municipio:{Style.RESET_ALL} {result['municipio']}")
            print(f"  {Fore.GREEN}[+] Provincia:{Style.RESET_ALL} {result['provincia']}")
            if result.get("coordenadas"):
                lat = result["coordenadas"]["lat"]
                lon = result["coordenadas"]["lon"]
                print(f"  {Fore.GREEN}[+] Coordenadas:{Style.RESET_ALL} {lat}, {lon}")
            print(f"  {Fore.GREEN}[+] Confianza:{Style.RESET_ALL} {result['confianza']}%")
        else:
            print(f"  {Fore.RED}[-] No se pudo normalizar el domicilio '{args.georef}'.{Style.RESET_ALL}")
        report_results["georef"] = result

    # --- Generar Reporte ---
    if args.report and report_results:
        print(f"\n{Fore.CYAN}[*] Generando reporte {args.report.upper()}...{Style.RESET_ALL}")
        ruta = generate_report(target_for_report, report_results, args.report)
        print(f"  {Fore.GREEN}[+] Reporte guardado en:{Style.RESET_ALL} {ruta}")


if __name__ == "__main__":
    main()
