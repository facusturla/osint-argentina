#!/usr/bin/env python3
"""
Script: company_lookup.py
Descripción: Busca el sitio web oficial y los contactos públicos de una lista
             de empresas mediante OSINT pasivo (DuckDuckGo Lite + scraping del
             sitio + extracción de emails y teléfonos).

Uso:
    python scripts/company_lookup.py input.txt output.csv
    python scripts/company_lookup.py input.txt output.csv --delay 3

Formato de input:  un nombre de empresa por línea.
Formato de output: CSV con columnas
    empresa, dominio, emails, telefonos, mx_valido, confianza, error

Sin API key requerida. Usa solo fuentes públicas.
"""

import argparse
import asyncio
import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, quote_plus

import aiohttp
from bs4 import BeautifulSoup

# Permitir importar desde core/ del proyecto (scripts/../core)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.email_harvester import harvest_emails  # noqa: E402

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}
TIMEOUT = aiohttp.ClientTimeout(total=15)

# Dominios a excluir cuando aparecen en los resultados de búsqueda
BLACKLIST_DOMAINS = {
    "linkedin.com", "facebook.com", "twitter.com", "x.com", "instagram.com",
    "youtube.com", "bloomberg.com", "dnb.com", "crunchbase.com",
    "wikipedia.org", "indeed.com", "glassdoor.com", "zoominfo.com",
    "rocketreach.co", "dun-bradstreet.com", "opencorporates.com",
    "yellowpages.com", "yelp.com", "tradewheel.com", "tradeford.com",
    "alibaba.com", "made-in-china.com", "europages.com", "kompass.com",
    "tofler.in", "pinterest.com", "tiktok.com", "amazon.com", "ebay.com",
    "google.com", "duckduckgo.com", "bing.com", "reddit.com",
    "pitchbook.com", "owler.com", "panjiva.com", "importgenius.com",
    "tradingeconomics.com",
}

# Páginas típicas de contacto a explorar luego de hallar el dominio
CONTACT_PATHS = [
    "/contact", "/contact-us", "/contacto", "/contactenos", "/contact.html",
    "/about", "/about-us", "/sobre-nosotros", "/quienes-somos", "/impressum",
    "/kontakt", "/contattaci", "/nous-contacter",
]

# Regex para teléfonos internacionales (formato laxo)
PHONE_REGEX = re.compile(
    r"(?:(?<=\D)|^)(\+?\d{1,3}[\s.\-]?\(?\d{2,4}\)?[\s.\-]?\d{3,4}[\s.\-]?\d{3,4}(?:[\s.\-]?\d{2,4})?)"
)
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def _normalize_domain(url: str) -> str | None:
    """Extrae el dominio raíz (sin www, sin path) de una URL."""
    try:
        parsed = urlparse(url if "://" in url else f"http://{url}")
        host = parsed.hostname or ""
        if host.startswith("www."):
            host = host[4:]
        return host or None
    except Exception:
        return None


def _is_blacklisted(domain: str) -> bool:
    """True si el dominio o uno de sus padres está en la blacklist."""
    parts = domain.split(".")
    for i in range(len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in BLACKLIST_DOMAINS:
            return True
    return False


async def find_company_domain(session: aiohttp.ClientSession, empresa: str) -> tuple[str | None, int]:
    """
    Busca el sitio web oficial de una empresa en DuckDuckGo Lite.
    Retorna (dominio, confianza 0-100).
    """
    query = f'"{empresa}" official site contact'
    url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"

    try:
        async with session.get(url, headers=HEADERS, timeout=TIMEOUT) as resp:
            html = await resp.text()
    except Exception:
        return None, 0

    soup = BeautifulSoup(html, "html.parser")
    # En la versión lite, los resultados son <a class="result-link"> (o <a> dentro de <td>)
    candidates: list[str] = []
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if not href.startswith(("http://", "https://")):
            continue
        domain = _normalize_domain(href)
        if not domain or _is_blacklisted(domain):
            continue
        if domain in candidates:
            continue
        candidates.append(domain)
        if len(candidates) >= 5:
            break

    if not candidates:
        return None, 0

    # Heurística simple de confianza:
    # - dominio que contiene una palabra del nombre de la empresa = más confianza
    # - posición en los resultados también importa
    empresa_tokens = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", empresa)]
    best_domain = candidates[0]
    best_score = 30

    for idx, dom in enumerate(candidates):
        score = max(50 - idx * 10, 10)
        for token in empresa_tokens:
            if token in dom.lower():
                score += 25
                break
        if score > best_score:
            best_score = score
            best_domain = dom

    return best_domain, min(best_score, 100)


async def scrape_contact_pages(session: aiohttp.ClientSession, domain: str) -> tuple[set[str], set[str]]:
    """Scrapea homepage + páginas de contacto típicas. Retorna (emails, teléfonos)."""
    emails: set[str] = set()
    phones: set[str] = set()

    paths_to_try = [""] + CONTACT_PATHS
    for path in paths_to_try:
        url = f"https://{domain}{path}"
        try:
            async with session.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True) as resp:
                if resp.status != 200:
                    continue
                text = await resp.text(errors="ignore")
        except Exception:
            continue

        for match in EMAIL_REGEX.findall(text):
            # Filtrar emails genéricos de plantillas/wordpress/imágenes
            if any(skip in match.lower() for skip in ("@example.", "@sentry.", "@wixpress.", ".png", ".jpg")):
                continue
            emails.add(match.lower())

        for match in PHONE_REGEX.findall(text):
            cleaned = re.sub(r"\s+", " ", match).strip()
            # Filtrar matches muy cortos o numéricos sin sentido
            if len(re.sub(r"\D", "", cleaned)) >= 8:
                phones.add(cleaned)

    return emails, phones


async def lookup_company(session: aiohttp.ClientSession, empresa: str, delay: float) -> dict:
    """Pipeline completo para una empresa."""
    result = {
        "empresa": empresa,
        "dominio": "",
        "emails": "",
        "telefonos": "",
        "mx_valido": "",
        "confianza": 0,
        "error": "",
    }

    try:
        domain, confianza = await find_company_domain(session, empresa)
        result["confianza"] = confianza

        if not domain:
            result["error"] = "Sin coincidencias confiables"
            return result

        result["dominio"] = domain

        # harvest_emails es síncrono internamente — lo corremos en thread pool
        loop = asyncio.get_event_loop()
        harvest_result = await loop.run_in_executor(None, harvest_emails, domain)

        emails_set = set(harvest_result.get("emails", []))
        phones_set: set[str] = set()

        # Enriquecer con scraping de páginas de contacto
        extra_emails, extra_phones = await scrape_contact_pages(session, domain)
        emails_set.update(extra_emails)
        phones_set.update(extra_phones)

        result["emails"] = "; ".join(sorted(emails_set)[:10])
        result["telefonos"] = "; ".join(sorted(phones_set)[:5])
        result["mx_valido"] = "si" if harvest_result.get("mx_valid") else "no"

    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    finally:
        # Rate limit cortés con DuckDuckGo y los servidores de las empresas
        await asyncio.sleep(delay)

    return result


async def run(input_path: Path, output_path: Path, delay: float) -> None:
    empresas = [line.strip() for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    total = len(empresas)
    print(f"[*] Procesando {total} empresas (delay {delay}s entre cada una)...")

    fieldnames = ["empresa", "dominio", "emails", "telefonos", "mx_valido", "confianza", "error"]

    async with aiohttp.ClientSession() as session:
        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for idx, empresa in enumerate(empresas, 1):
                started = time.time()
                row = await lookup_company(session, empresa, delay)
                elapsed = time.time() - started
                status = "OK" if row["dominio"] else "MISS"
                print(f"  [{idx}/{total}] {status:4} {empresa[:50]:50} -> {row['dominio'] or '-'} ({elapsed:.1f}s)")
                writer.writerow(row)
                f.flush()

    print(f"\n[+] Reporte guardado en: {output_path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Busca sitio web y contactos públicos de una lista de empresas (OSINT pasivo)."
    )
    parser.add_argument("input", type=Path, help="Archivo de texto con un nombre de empresa por línea.")
    parser.add_argument("output", type=Path, help="Archivo CSV de salida.")
    parser.add_argument(
        "--delay", type=float, default=3.0,
        help="Segundos de espera entre consultas (default: 3.0)."
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"[-] No existe el archivo de entrada: {args.input}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(run(args.input, args.output, args.delay))


if __name__ == "__main__":
    main()
