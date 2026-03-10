import aiohttp
import asyncio
import re
import dns.resolver
import os

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

async def fetch_html(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            return await response.text()
    except Exception:
        return ""

async def scrape_domain(session, domain):
    html = await fetch_html(session, f"http://{domain}")
    emails = set(re.findall(EMAIL_REGEX, html))
    # Filter to only emails belonging to the domain to avoid false positives
    return {e.lower() for e in emails if e.lower().endswith(f"@{domain}")}

async def search_duckduckgo(session, domain):
    # lite.duckduckgo.com doesn't use JS, easier to scrape
    url = "https://lite.duckduckgo.com/lite/"
    data = {"q": f'"{domain}" email'}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    emails = set()
    try:
        async with session.post(url, data=data, headers=headers, timeout=10) as response:
            html = await response.text()
            found = set(re.findall(EMAIL_REGEX, html))
            emails.update({e.lower() for e in found if e.lower().endswith(f"@{domain}")})
    except Exception:
        pass
    return emails

def verify_email_domain(domain):
    try:
        records = dns.resolver.resolve(domain, 'MX')
        return True, [str(r.exchange) for r in records]
    except Exception:
        return False, []

async def _run_harvest_async(domain):
    emails = set()
    async with aiohttp.ClientSession() as session:
        domain_emails, ddg_emails = await asyncio.gather(
            scrape_domain(session, domain),
            search_duckduckgo(session, domain)
        )
        emails.update(domain_emails)
        emails.update(ddg_emails)
    
    # Verification
    mx_valid, mx_records = verify_email_domain(domain)
    
    return {
        "domain": domain,
        "emails": list(emails),
        "mx_valid": mx_valid,
        "mx_records": mx_records
    }

def harvest_emails(domain: str) -> dict:
    """
    Harvests emails associated with a domain using public search and crawling.
    Checks MX records to confirm the domain can actually receive emails.
    """
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    return asyncio.run(_run_harvest_async(domain))
