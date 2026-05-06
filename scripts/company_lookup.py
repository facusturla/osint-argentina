#!/usr/bin/env python3
"""
Script: company_lookup.py
Descripción: Busca el sitio web oficial y los contactos públicos de una lista
             de empresas mediante OSINT pasivo. Usa múltiples motores de búsqueda
             como fallback (DDG Lite → Bing), scraping de páginas de contacto,
             extracción de emails y teléfonos, e inferencia de país por TLD.

Uso:
    python scripts/company_lookup.py input.txt output.csv
    python scripts/company_lookup.py input.txt output.csv --delay 3 --concurrency 4

Formato de input:  un nombre de empresa por línea.
Formato de output: CSV con columnas:
    empresa, dominio, pais_inferido, emails, telefonos, mx_valido, confianza, fuente_busqueda, error

Features:
    - Fallback DDG Lite → Bing si un motor está bloqueado
    - Resume automático: si el CSV de salida ya existe, saltea empresas ya procesadas
    - Inferencia de país desde el TLD del dominio encontrado
    - Detección de Cloudflare / WAF challenge (no scrappea en vano)
    - Filtro de redirects: si el dominio final es un directorio, lo descarta
    - Concurrencia configurable con rate-limit por motor de búsqueda
    - Validación MX del dominio vía DNS

Sin API key requerida. Solo fuentes públicas.
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.email_harvester import harvest_emails  # noqa: E402

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = aiohttp.ClientTimeout(total=20)

BLACKLIST_DOMAINS = {
    # Directorios de empresas
    "linkedin.com", "facebook.com", "twitter.com", "x.com", "instagram.com",
    "youtube.com", "bloomberg.com", "dnb.com", "crunchbase.com",
    "wikipedia.org", "indeed.com", "glassdoor.com", "zoominfo.com",
    "rocketreach.co", "dun-bradstreet.com", "opencorporates.com",
    "yellowpages.com", "yelp.com", "tradewheel.com", "tradeford.com",
    "alibaba.com", "made-in-china.com", "europages.com", "kompass.com",
    "tofler.in", "pinterest.com", "tiktok.com", "amazon.com", "ebay.com",
    "google.com", "google.es", "google.co", "duckduckgo.com", "bing.com",
    "reddit.com", "pitchbook.com", "owler.com", "panjiva.com",
    "importgenius.com", "tradingeconomics.com", "manta.com", "bizapedia.com",
    "corporationwiki.com", "sec.gov", "companieshouse.gov.uk",
    "registreoficiant.cat", "infoempresa.com", "einforma.com",
    "empresia.es", "axesor.es", "infocif.es", "sabi.bvdinfo.com",
    "whois.domaintools.com", "peekyou.com", "spokeo.com",
    "globaltradepoint.com", "importkey.com", "tradesparq.com",
}

# Palabras en el HTML que indican Cloudflare/WAF challenge — no scrappear
CHALLENGE_MARKERS = [
    "cloudflare", "cf-browser-verification", "checking your browser",
    "enable javascript", "ddos-guard", "please wait", "just a moment",
    "security check", "access denied", "403 forbidden",
]

CONTACT_PATHS = [
    "/contact", "/contact-us", "/contacto", "/contactenos",
    "/contact.html", "/contact.php",
    "/about", "/about-us", "/sobre-nosotros", "/quienes-somos",
    "/impressum", "/legal-notice",
    "/kontakt", "/kontakt.html",
    "/contattaci", "/nous-contacter",
    "/reach-us", "/get-in-touch",
]

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(
    r"(\+?(?:\d[\s.\-()]?){7,15}\d)"
)

# TLD → país (los más comunes en la lista)
TLD_COUNTRY = {
    "ar": "Argentina", "br": "Brasil", "de": "Alemania", "es": "España",
    "nl": "Países Bajos", "be": "Bélgica", "sa": "Arabia Saudita",
    "ae": "Emiratos Árabes", "qa": "Qatar", "om": "Omán", "kw": "Kuwait",
    "jo": "Jordania", "lb": "Líbano", "dz": "Argelia", "ma": "Marruecos",
    "pt": "Portugal", "it": "Italia", "fr": "Francia", "se": "Suecia",
    "dk": "Dinamarca", "no": "Noruega", "fi": "Finlandia",
    "uk": "Reino Unido", "ie": "Irlanda", "us": "Estados Unidos",
    "ca": "Canadá", "au": "Australia", "nz": "Nueva Zelanda",
    "sg": "Singapur", "ph": "Filipinas", "cn": "China",
    "tr": "Turquía", "ru": "Rusia", "pl": "Polonia", "at": "Austria",
    "ch": "Suiza", "mx": "México", "cl": "Chile", "co": "Colombia",
    "pe": "Perú", "ve": "Venezuela", "uy": "Uruguay", "py": "Paraguay",
    "bo": "Bolivia", "ec": "Ecuador",
}

FIELDNAMES = [
    "empresa", "dominio", "pais_inferido",
    "emails", "telefonos", "mx_valido",
    "confianza", "fuente_busqueda", "error",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_domain(url: str) -> str | None:
    try:
        parsed = urlparse(url if "://" in url else f"http://{url}")
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host or None
    except Exception:
        return None


def _is_blacklisted(domain: str) -> bool:
    parts = domain.split(".")
    for i in range(len(parts) - 1):
        if ".".join(parts[i:]) in BLACKLIST_DOMAINS:
            return True
    return False


def _infer_country(domain: str) -> str:
    """Infiere país a partir del TLD del dominio."""
    parts = domain.rsplit(".", 1)
    if len(parts) == 2:
        tld = parts[1].lower()
        if tld in TLD_COUNTRY:
            return TLD_COUNTRY[tld]
        # Casos especiales de segundo nivel (.co.uk, .com.ar, etc.)
        sub_parts = domain.rsplit(".", 2)
        if len(sub_parts) == 3:
            second_tld = sub_parts[1].lower()
            if second_tld in TLD_COUNTRY:
                return TLD_COUNTRY[second_tld]
    return ""


def _is_challenge_page(html: str) -> bool:
    lower = html.lower()
    return any(marker in lower for marker in CHALLENGE_MARKERS)


def _clean_emails(raw: list[str], domain: str) -> list[str]:
    """Filtra y deduplica emails. Prioriza los del propio dominio."""
    skip = {"@example.", "@sentry.", "@wixpress.", "@yoursite.", "@domain.",
            ".png", ".jpg", ".gif", ".svg", "@schema.", "@w3.org"}
    seen: set[str] = set()
    own: list[str] = []
    other: list[str] = []
    for e in raw:
        e = e.lower().strip()
        if any(s in e for s in skip):
            continue
        if e in seen:
            continue
        seen.add(e)
        if domain and domain in e:
            own.append(e)
        else:
            other.append(e)
    return (own + other)[:10]


def _clean_phones(raw: list[str]) -> list[str]:
    """Filtra teléfonos: mínimo 8 dígitos, máximo 15 (ITU-T E.164)."""
    seen: set[str] = set()
    result: list[str] = []
    for p in raw:
        digits = re.sub(r"\D", "", p)
        if not (8 <= len(digits) <= 15):
            continue
        # Evitar strings tipo "20240101" (fechas) o "123456789" (repetitivo)
        if len(set(digits)) < 4:
            continue
        normalized = p.strip()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result[:5]


# ---------------------------------------------------------------------------
# Búsqueda de dominio: múltiples backends
# ---------------------------------------------------------------------------

async def _search_ddg(session: aiohttp.ClientSession, query: str) -> list[str]:
    """Busca en DuckDuckGo Lite. Retorna lista de dominios candidatos."""
    url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
    try:
        async with session.get(url, headers=HEADERS, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                return []
            html = await resp.text()
    except Exception:
        return []

    soup = BeautifulSoup(html, "html.parser")
    domains: list[str] = []
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if not href.startswith(("http://", "https://")):
            continue
        d = _normalize_domain(href)
        if d and not _is_blacklisted(d) and d not in domains:
            domains.append(d)
        if len(domains) >= 6:
            break
    return domains


async def _search_bing(session: aiohttp.ClientSession, query: str) -> list[str]:
    """Busca en Bing HTML como fallback. Retorna lista de dominios candidatos."""
    url = f"https://www.bing.com/search?q={quote_plus(query)}&count=10"
    try:
        async with session.get(url, headers=HEADERS, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                return []
            html = await resp.text()
    except Exception:
        return []

    soup = BeautifulSoup(html, "html.parser")
    domains: list[str] = []
    # Bing: resultados en <li class="b_algo"> → <h2><a href="...">
    for a in soup.select("li.b_algo h2 a, li.b_algo a.tilk"):
        href = a.get("href", "")
        if not href.startswith(("http://", "https://")):
            continue
        d = _normalize_domain(href)
        if d and not _is_blacklisted(d) and d not in domains:
            domains.append(d)
        if len(domains) >= 6:
            break
    return domains


def _score_candidates(candidates: list[str], empresa: str) -> tuple[str | None, int]:
    """Selecciona el mejor candidato y calcula un score de confianza 0–100."""
    if not candidates:
        return None, 0

    tokens = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", empresa)]
    best_domain = candidates[0]
    best_score = 0

    for idx, dom in enumerate(candidates):
        # Penalización por posición
        score = max(55 - idx * 10, 5)
        # Bonus si algún token del nombre está en el dominio
        for tok in tokens:
            if tok in dom.lower():
                score += 30
                break
        # Bonus pequeño si el TLD coincide con la zona geográfica inferida del nombre
        # (ej: nombre con "CANARIAS" → bonus para .es)
        if any(w in empresa.lower() for w in ("canarias", "españa", "spain")) and dom.endswith(".es"):
            score += 10
        if any(w in empresa.lower() for w in ("gmbh", "deutschland", "german")) and dom.endswith(".de"):
            score += 10
        if any(w in empresa.lower() for w in ("bv", "netherlands", "holland")) and dom.endswith(".nl"):
            score += 10
        if any(w in empresa.lower() for w in ("sarl", "france", "francaise")) and dom.endswith(".fr"):
            score += 10
        if score > best_score:
            best_score = score
            best_domain = dom

    return best_domain, min(best_score, 100)


async def find_company_domain(
    session: aiohttp.ClientSession, empresa: str
) -> tuple[str | None, int, str]:
    """
    Busca el dominio oficial de una empresa intentando DDG → Bing.
    Retorna (dominio, confianza, fuente_usada).
    """
    query = f'"{empresa}" official website contact'

    candidates = await _search_ddg(session, query)
    source = "DDG"

    if not candidates:
        await asyncio.sleep(1)
        candidates = await _search_bing(session, query)
        source = "Bing"

    if not candidates:
        # Último intento: query más simple sin comillas
        await asyncio.sleep(1)
        simple_query = f"{empresa} contact official"
        candidates = await _search_ddg(session, simple_query)
        source = "DDG-simple"

    domain, score = _score_candidates(candidates, empresa)
    return domain, score, source if domain else ""


# ---------------------------------------------------------------------------
# Scraping del sitio encontrado
# ---------------------------------------------------------------------------

async def scrape_contact_pages(
    session: aiohttp.ClientSession, domain: str
) -> tuple[list[str], list[str]]:
    """
    Scrapea homepage + páginas de contacto típicas.
    Retorna (emails, teléfonos) ya filtrados.
    """
    raw_emails: list[str] = []
    raw_phones: list[str] = []
    pages_scraped = 0

    paths_to_try = [""] + CONTACT_PATHS

    for path in paths_to_try:
        if pages_scraped >= 5:
            break
        url = f"https://{domain}{path}"
        try:
            async with session.get(
                url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True
            ) as resp:
                if resp.status not in (200, 201):
                    continue
                # Verificar que el redirect no nos llevó a un directorio
                final_host = _normalize_domain(str(resp.url))
                if final_host and final_host != domain and _is_blacklisted(final_host):
                    continue
                text = await resp.text(errors="ignore")
        except Exception:
            continue

        if _is_challenge_page(text):
            continue

        pages_scraped += 1
        raw_emails.extend(EMAIL_REGEX.findall(text))
        raw_phones.extend(PHONE_REGEX.findall(text))

    return _clean_emails(raw_emails, domain), _clean_phones(raw_phones)


# ---------------------------------------------------------------------------
# Pipeline por empresa
# ---------------------------------------------------------------------------

async def lookup_company(
    session: aiohttp.ClientSession,
    empresa: str,
    delay: float,
    sem: asyncio.Semaphore,
) -> dict:
    result = {
        "empresa": empresa,
        "dominio": "",
        "pais_inferido": "",
        "emails": "",
        "telefonos": "",
        "mx_valido": "",
        "confianza": 0,
        "fuente_busqueda": "",
        "error": "",
    }

    async with sem:
        try:
            domain, confianza, source = await find_company_domain(session, empresa)
            result["confianza"] = confianza
            result["fuente_busqueda"] = source

            if not domain:
                result["error"] = "Sin coincidencias"
                return result

            result["dominio"] = domain
            result["pais_inferido"] = _infer_country(domain)

            # harvest_emails es síncrono → correr en thread pool
            loop = asyncio.get_event_loop()
            harvest_result = await loop.run_in_executor(None, harvest_emails, domain)

            emails_set = set(harvest_result.get("emails", []))
            result["mx_valido"] = "si" if harvest_result.get("mx_valid") else "no"

            # Enriquecer con scraping de páginas de contacto
            extra_emails, phones = await scrape_contact_pages(session, domain)
            emails_set.update(extra_emails)

            result["emails"] = "; ".join(_clean_emails(list(emails_set), domain))
            result["telefonos"] = "; ".join(phones)

        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"

        finally:
            await asyncio.sleep(delay)

    return result


# ---------------------------------------------------------------------------
# Entrada/salida y resumen
# ---------------------------------------------------------------------------

def _load_already_done(output_path: Path) -> set[str]:
    """Lee el CSV existente y retorna el set de empresas ya procesadas."""
    done: set[str] = set()
    if not output_path.exists():
        return done
    try:
        with output_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("empresa"):
                    done.add(row["empresa"].strip())
    except Exception:
        pass
    return done


async def run(input_path: Path, output_path: Path, delay: float, concurrency: int) -> None:
    all_empresas = [
        line.strip()
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    already_done = _load_already_done(output_path)
    empresas = [e for e in all_empresas if e not in already_done]
    skipped = len(all_empresas) - len(empresas)

    total = len(empresas)
    if skipped:
        print(f"[*] Retomando: {skipped} empresas ya procesadas, {total} pendientes.")
    else:
        print(f"[*] Procesando {total} empresas (concurrencia {concurrency}, delay {delay}s)...")

    # Si el archivo ya existe, abrir en append; si no, crear con header
    write_mode = "a" if already_done else "w"

    sem = asyncio.Semaphore(concurrency)
    ok_count = 0
    miss_count = 0
    start_total = time.time()

    connector = aiohttp.TCPConnector(limit=concurrency * 2)
    async with aiohttp.ClientSession(connector=connector) as session:
        with output_path.open(write_mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if write_mode == "w":
                writer.writeheader()

            tasks = [
                lookup_company(session, empresa, delay, sem)
                for empresa in empresas
            ]

            for idx, coro in enumerate(asyncio.as_completed(tasks), 1):
                t0 = time.time()
                row = await coro
                elapsed = time.time() - t0

                if row["dominio"]:
                    ok_count += 1
                    status = "OK  "
                else:
                    miss_count += 1
                    status = "MISS"

                hit_rate = ok_count / (ok_count + miss_count) * 100
                print(
                    f"  [{idx:>3}/{total}] {status} "
                    f"{row['empresa'][:45]:45} -> "
                    f"{row['dominio'] or '-':30} "
                    f"[{row['pais_inferido']:12}] "
                    f"conf:{row['confianza']:>3} "
                    f"({elapsed:.1f}s) hit:{hit_rate:.0f}%"
                )
                writer.writerow(row)
                f.flush()

    elapsed_total = time.time() - start_total
    print(f"\n[+] Listo en {elapsed_total:.0f}s  —  OK: {ok_count}  MISS: {miss_count}  "
          f"Hit rate: {ok_count/(ok_count+miss_count)*100:.1f}%")
    print(f"[+] Reporte guardado en: {output_path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Busca sitio web y contactos públicos de una lista de empresas (OSINT pasivo).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python scripts/company_lookup.py empresas.txt resultados.csv\n"
            "  python scripts/company_lookup.py empresas.txt resultados.csv --delay 2 --concurrency 5\n"
            "  # Si se interrumpe, retomá con el mismo comando — saltea lo ya procesado"
        ),
    )
    parser.add_argument("input", type=Path, help="Archivo TXT con un nombre de empresa por línea.")
    parser.add_argument("output", type=Path, help="Archivo CSV de salida (se reanuda si ya existe).")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="Segundos de espera entre queries (default: 3.0).")
    parser.add_argument("--concurrency", type=int, default=3,
                        help="Empresas procesadas en paralelo (default: 3). No subir de 5 para evitar bloqueos.")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"[-] No existe el archivo de entrada: {args.input}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(run(args.input, args.output, args.delay, args.concurrency))


if __name__ == "__main__":
    main()
