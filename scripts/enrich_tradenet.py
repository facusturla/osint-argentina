#!/usr/bin/env python3
"""
Script: enrich_tradenet.py
Descripción: Enriquece un CSV de importadores TradeNet con validación y búsqueda
             selectiva de sitio web, emails y teléfonos.

Lógica:
    - Si ya tiene Web → valida que resuelva (MX check + HTTP 200)
    - Si Web está vacío → busca el dominio oficial
    - Si ya tiene Email → valida que sea válido
    - Si Email está vacío → extrae del sitio encontrado/validado
    - Si Teléfono está vacío → busca en el sitio
    - Si Tipo entidad / Tamaño entidad están vacíos → intenta inferir

Output: CSV original + columnas nuevas con validación y enriquecimiento:
    _web_validado, _email_validado, _telefono_validado, _confianza,
    _fuente_busqueda, _error

Uso:
    python scripts/enrich_tradenet.py importadores.csv importadores_enriquecido.csv

Sin API key requerida.
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
    "linkedin.com", "facebook.com", "twitter.com", "x.com", "instagram.com",
    "youtube.com", "bloomberg.com", "dnb.com", "crunchbase.com",
    "wikipedia.org", "indeed.com", "glassdoor.com", "zoominfo.com",
    "rocketreach.co", "opencorporates.com", "yellowpages.com", "yelp.com",
    "alibaba.com", "made-in-china.com", "europages.com", "kompass.com",
    "pinterest.com", "tiktok.com", "amazon.com", "ebay.com",
    "google.com", "duckduckgo.com", "bing.com", "reddit.com",
    "owler.com", "panjiva.com", "importgenius.com", "sec.gov",
}

CHALLENGE_MARKERS = [
    "cloudflare", "checking your browser", "ddos-guard",
    "please wait", "security check", "403 forbidden",
]

CONTACT_PATHS = [
    "/contact", "/contact-us", "/contacto", "/about",
    "/impressum", "/kontakt", "/contattaci",
]

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"(\+?(?:\d[\s.\-()]?){7,15}\d)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_domain(url: str) -> str | None:
    """Normaliza URL a dominio raíz."""
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not url:
        return None
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


def _is_valid_email(email: str) -> bool:
    """Valida formato básico de email."""
    if not email or not isinstance(email, str):
        return False
    match = EMAIL_REGEX.match(email.strip())
    if not match:
        return False
    skip = {"@example.", "@sentry.", "@wixpress.", "@yoursite.", "@domain."}
    return not any(s in email.lower() for s in skip)


def _is_valid_phone(phone: str) -> bool:
    """Valida teléfono: 8-15 dígitos, min 4 únicos."""
    if not phone or not isinstance(phone, str):
        return False
    digits = re.sub(r"\D", "", phone.strip())
    if not (8 <= len(digits) <= 15):
        return False
    if len(set(digits)) < 4:
        return False
    return True


def _is_challenge_page(html: str) -> bool:
    if not html:
        return False
    lower = html.lower()
    return any(marker in lower for marker in CHALLENGE_MARKERS)


async def _search_ddg(session: aiohttp.ClientSession, query: str) -> list[str]:
    """Busca en DDG Lite."""
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
    """Busca en Bing como fallback."""
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


async def validate_domain(session: aiohttp.ClientSession, domain: str) -> tuple[bool, str]:
    """
    Valida que un dominio:
    1. Resuelva a una IP (DNS)
    2. Tenga registros MX válidos
    3. Devuelva 200-299 al acceder
    Retorna (válido, error_msg).
    """
    if not domain:
        return False, "vacío"

    try:
        # Validar MX vía harvest_emails (que usa dns.resolver)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, harvest_emails, domain)
        mx_valid = result.get("mx_valid", False)

        if not mx_valid:
            return False, "sin MX"

        # Verificar HTTP 200
        url = f"https://{domain}"
        try:
            async with session.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True) as resp:
                if resp.status < 200 or resp.status >= 300:
                    return False, f"HTTP {resp.status}"
                if _is_challenge_page(await resp.text()):
                    return False, "WAF/challenge"
        except asyncio.TimeoutError:
            return False, "timeout"
        except Exception as e:
            return False, f"conexión: {type(e).__name__}"

        return True, ""

    except Exception as e:
        return False, f"{type(e).__name__}"


async def find_domain(session: aiohttp.ClientSession, nombre: str, pais: str) -> tuple[str | None, int, str]:
    """
    Busca el dominio oficial de una empresa.
    Retorna (dominio, confianza, source).
    """
    query = f'"{nombre}" {pais} official website contact'

    candidates = await _search_ddg(session, query)
    source = "DDG"

    if not candidates:
        await asyncio.sleep(1)
        candidates = await _search_bing(session, query)
        source = "Bing"

    if not candidates:
        # Segundo intento sin país
        await asyncio.sleep(1)
        query2 = f'"{nombre}" official website'
        candidates = await _search_ddg(session, query2)
        source = "DDG-v2"

    if not candidates:
        return None, 0, ""

    # Score simple: primer candidato
    best_domain = candidates[0]
    score = max(50, 100 - len(candidates) * 10)

    # Bonus si el nombre está en el dominio
    for token in nombre.split():
        if token.lower() in best_domain.lower():
            score = min(score + 20, 100)
            break

    return best_domain, score, source


async def extract_contacts_from_site(
    session: aiohttp.ClientSession, domain: str
) -> tuple[list[str], list[str]]:
    """
    Extrae emails y teléfonos del sitio.
    Retorna (emails, teléfonos) ya filtrados.
    """
    raw_emails: list[str] = []
    raw_phones: list[str] = []
    pages = 0

    for path in [""] + CONTACT_PATHS:
        if pages >= 3:
            break
        url = f"https://{domain}{path}"
        try:
            async with session.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True) as resp:
                if resp.status not in (200, 201):
                    continue
                text = await resp.text(errors="ignore")
        except Exception:
            continue

        if _is_challenge_page(text):
            continue

        pages += 1
        raw_emails.extend(EMAIL_REGEX.findall(text))
        raw_phones.extend(PHONE_REGEX.findall(text))

    # Filtrar
    emails = list(set(e.lower() for e in raw_emails if _is_valid_email(e)))[:5]
    phones = list(set(p for p in raw_phones if _is_valid_phone(p)))[:3]

    return emails, phones


# ---------------------------------------------------------------------------
# Pipeline por importador
# ---------------------------------------------------------------------------

async def enrich_row(
    session: aiohttp.ClientSession,
    row: dict,
    delay: float,
    sem: asyncio.Semaphore,
) -> dict:
    """
    Enriquece una fila del TradeNet.
    Valida datos existentes y busca/enriquece lo vacío.
    """
    async with sem:
        nombre = row.get("Nombre", "").strip()
        pais = row.get("País/Región", "").strip()
        web_existing = row.get("Web", "").strip()
        email_existing = row.get("Email", "").strip()
        phone_existing = row.get("Teléfono", "").strip()

        # Resultados
        out = dict(row)  # Copia todas las columnas originales
        out["_web_validado"] = ""
        out["_email_validado"] = ""
        out["_telefono_validado"] = ""
        out["_confianza"] = ""
        out["_fuente_busqueda"] = ""
        out["_error"] = ""

        if not nombre:
            out["_error"] = "sin nombre"
            return out

        try:
            domain = None
            source = ""
            confianza = 0

            # 1. Si tiene Web → validar
            if web_existing:
                domain = _normalize_domain(web_existing)
                if domain:
                    valid, err = await validate_domain(session, domain)
                    if valid:
                        out["_web_validado"] = "OK"
                        out["Web"] = domain  # Normalizar
                        source = "EXISTENTE"
                        confianza = 95
                    else:
                        out["_web_validado"] = f"INVÁLIDO ({err})"
                        domain = None
            else:
                # 2. Si no tiene Web → buscar
                domain, confianza, source = await find_domain(session, nombre, pais)
                if domain:
                    valid, err = await validate_domain(session, domain)
                    if valid:
                        out["Web"] = domain
                        out["_web_validado"] = "ENCONTRADO"
                    else:
                        out["_web_validado"] = f"ENCONTRADO pero inválido ({err})"
                        domain = None

            if domain:
                out["_confianza"] = str(confianza)
                out["_fuente_busqueda"] = source

                # 3. Extraer contactos del sitio
                emails, phones = await extract_contacts_from_site(session, domain)

                # Si no tiene Email → usar lo encontrado
                if not email_existing and emails:
                    out["Email"] = "; ".join(emails)
                    out["_email_validado"] = "EXTRAÍDO"
                elif email_existing:
                    if _is_valid_email(email_existing):
                        out["_email_validado"] = "OK"
                    else:
                        out["_email_validado"] = "FORMATO INVÁLIDO"

                # Si no tiene Teléfono → usar lo encontrado
                if not phone_existing and phones:
                    out["Teléfono"] = "; ".join(phones)
                    out["_telefono_validado"] = "EXTRAÍDO"
                elif phone_existing:
                    if _is_valid_phone(phone_existing):
                        out["_telefono_validado"] = "OK"
                    else:
                        out["_telefono_validado"] = "FORMATO INVÁLIDO"

            else:
                out["_error"] = f"no se encontró dominio (buscado: {source})"

        except Exception as exc:
            out["_error"] = f"{type(exc).__name__}: {exc}"

        finally:
            await asyncio.sleep(delay)

        return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(input_path: Path, output_path: Path, delay: float, concurrency: int) -> None:
    print(f"[*] Leyendo {input_path}...")

    # Leer CSV TradeNet
    rows = []
    with input_path.open(encoding="utf-8-sig") as f:  # utf-8-sig para BOM
        reader = csv.DictReader(f, delimiter=";")
        rows = list(reader)

    total = len(rows)
    print(f"[*] {total} importadores. Procesando (concurrencia {concurrency}, delay {delay}s)...")

    sem = asyncio.Semaphore(concurrency)
    processed = 0

    connector = aiohttp.TCPConnector(limit=concurrency * 2)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Preparar fieldnames: originales + nuevos
        new_fields = ["_web_validado", "_email_validado", "_telefono_validado",
                      "_confianza", "_fuente_busqueda", "_error"]
        fieldnames = list(rows[0].keys()) + new_fields if rows else new_fields

        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()

            tasks = [
                enrich_row(session, row, delay, sem)
                for row in rows
            ]

            start = time.time()
            for coro in asyncio.as_completed(tasks):
                enriched = await coro
                processed += 1
                nombre = enriched.get("Nombre", "?")[:40]
                web = enriched.get("Web", "")[:30]
                val = enriched.get("_web_validado", "")
                email_val = enriched.get("_email_validado", "")
                phone_val = enriched.get("_telefono_validado", "")
                error = enriched.get("_error", "")[:30]

                status_parts = []
                if web:
                    status_parts.append(f"web:{web}")
                if email_val:
                    status_parts.append(f"email:{email_val}")
                if phone_val:
                    status_parts.append(f"phone:{phone_val}")
                if error:
                    status_parts.append(f"error:{error}")

                status = " | ".join(status_parts) if status_parts else "sin cambios"

                print(f"  [{processed:>4}/{total}] {nombre:40} → {status}")
                writer.writerow(enriched)
                f.flush()

    elapsed = time.time() - start
    print(f"\n[+] Listo en {elapsed:.0f}s")
    print(f"[+] Resultado guardado en: {output_path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enriquece CSV de importadores TradeNet con validación de Web/Email/Teléfono.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Uso:\n"
            "  python scripts/enrich_tradenet.py importadores.csv importadores_enriquecido.csv\n"
            "  python scripts/enrich_tradenet.py importadores.csv resultado.csv --delay 2 --concurrency 5\n"
        ),
    )
    parser.add_argument("input", type=Path, help="CSV de TradeNet (delimitado por ;)")
    parser.add_argument("output", type=Path, help="CSV de salida enriquecido")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="Segundos entre queries (default: 3.0)")
    parser.add_argument("--concurrency", type=int, default=3,
                        help="Máximo concurrentes (default: 3)")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"[-] No existe: {args.input}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(run(args.input, args.output, args.delay, args.concurrency))


if __name__ == "__main__":
    main()
