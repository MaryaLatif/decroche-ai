import io
import ipaddress
import re
import socket
import time
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from config import MAX_PAGES

UA = "Mozilla/5.0 (compatible; MerchantOnboardingBot/0.1)"
MAX_BYTES = 3_000_000
KEYWORDS = ("menu", "carte", "produit", "tarif", "prix", "restaurant", "horaire",
            "contact", "commande", "boutique", "shop", "food", "drink")


def assert_public_url(url: str) -> None:
    """Protection SSRF : refuse les URL pointant vers des adresses internes."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("URL invalide (http/https uniquement)")
    port = p.port or (443 if p.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(p.hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError(f"Domaine introuvable : {p.hostname}")
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValueError("Adresse non autorisée")


def safe_get(client: httpx.Client, url: str):
    redirects, retries = 0, 0
    while True:
        assert_public_url(url)
        with client.stream("GET", url, follow_redirects=False) as r:
            if r.is_redirect:
                redirects += 1
                if redirects > 3:
                    raise ValueError("Trop de redirections")
                url = urljoin(url, r.headers.get("location", ""))
                continue
            if r.status_code in (429, 503) and retries < 2:
                retries += 1
                retry_after = r.headers.get("retry-after", "")
                wait = float(retry_after) if retry_after.isdigit() else 5 * retries
                time.sleep(min(wait + 1, 70))
                continue
            if r.status_code == 429:
                raise ValueError(
                    "Le site limite les accès automatiques (429). "
                    f"Retry-After : {r.headers.get('retry-after', 'non indiqué')} s. "
                    "Réessaie dans une minute, ou colle le texte du site / importe un PDF."
                )
            r.raise_for_status()
            chunks, size = [], 0
            for chunk in r.iter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    break
                chunks.append(chunk)
            return url, r.headers.get("content-type", ""), b"".join(chunks)

def pdf_to_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages[:30])


def extract_upload(filename: str, data: bytes) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        text = pdf_to_text(data)
    elif ext in ("txt", "md"):
        text = data.decode("utf-8", "ignore")
    else:
        raise ValueError("Format non supporté (pdf, txt, md)")
    if len(text.strip()) < 20:
        raise ValueError("Aucun texte lisible (PDF scanné ?). Colle le menu en texte.")
    return text


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").removeprefix("www.")


def _html_to_text(soup: BeautifulSoup) -> str:
    ld = [s.get_text() for s in soup.find_all("script", type="application/ld+json")]
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    text = re.sub(r"\n\s*\n+", "\n", soup.get_text("\n", strip=True))
    if ld:
        text += "\n\n[Données structurées]\n" + "\n".join(ld)[:8000]
    return text[:20000]


def _load_robots(client: httpx.Client, url: str):
    p = urlparse(url)
    try:
        _, _, body = safe_get(client, f"{p.scheme}://{p.netloc}/robots.txt")
        rp = RobotFileParser()
        rp.parse(body.decode("utf-8", "ignore").splitlines())
        return rp
    except Exception:
        return None


def crawl(start_url: str, max_pages: int = MAX_PAGES):
    pages, errors, seen = [], [], set()
    queue = [start_url]
    host = _host(start_url)

    with httpx.Client(
        timeout=15,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.5",
        },
    ) as client:
        robots = _load_robots(client, start_url)
        time.sleep(1.5)
        while queue and len(pages) < max_pages:
            url = urldefrag(queue.pop(0))[0]
            if url in seen:
                continue
            seen.add(url)
            if robots and not robots.can_fetch(UA, url):
                errors.append(f"{url} : bloqué par robots.txt")
                continue
            try:
                final, ctype, body = safe_get(client, url)
                if "pdf" in ctype or final.lower().split("?")[0].endswith(".pdf"):
                    text, title, found = pdf_to_text(body), final, []
                else:
                    soup = BeautifulSoup(body, "html.parser")
                    title = soup.title.get_text(strip=True) if soup.title else final
                    found = []
                    for a in soup.find_all("a", href=True):
                        link = urldefrag(urljoin(final, a["href"]))[0]
                        if urlparse(link).scheme not in ("http", "https") or _host(link) != host:
                            continue
                        score = sum(k in (link + " " + a.get_text()).lower() for k in KEYWORDS)
                        if score:
                            found.append((score, link))
                    text = _html_to_text(soup)
                if len(text.strip()) < 200:
                    errors.append(f"{final} : très peu de texte (site rendu en JavaScript ?)")
                if text.strip():
                    pages.append({"url": final, "title": title, "text": text, "collected_at": time.time()})
                queue += [l for _, l in sorted(found, reverse=True) if l not in seen]
                time.sleep(1.5)
            except Exception as exc:
                errors.append(f"{url} : {exc}")
    return pages, errors