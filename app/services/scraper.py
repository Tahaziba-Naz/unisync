from dataclasses import dataclass
from urllib.parse import urlparse, urljoin
import ipaddress, socket, requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser

UA = "UniSyncAcademicInfoBot/1.0 (respectful, contact site administrator)"

def validate_public_url(url):
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password: return False
        host = p.hostname.lower()
        if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"): return False
        for item in socket.getaddrinfo(host, None):
            addr = ipaddress.ip_address(item[4][0])
            if not addr.is_global: return False
        return True
    except (ValueError, OSError): return False

@dataclass
class RawPage:
    url: str
    text: str
    links: list
    pages: list = None

def fetch_url(url, selector=None):
    if not validate_public_url(url): raise ValueError("URL must resolve to a public HTTP/HTTPS address.")
    session = requests.Session(); session.headers.update({"User-Agent": UA})
    robots_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}/robots.txt"
    try:
        robots_resp = session.get(robots_url, timeout=8, allow_redirects=False)
        if robots_resp.status_code < 400:
            rp = RobotFileParser(); rp.parse(robots_resp.text.splitlines())
            if not rp.can_fetch(UA, url): raise PermissionError("robots.txt disallows this URL.")
    except requests.RequestException:
        pass
    response = session.get(url, timeout=15, allow_redirects=True)
    response.raise_for_status()
    if not validate_public_url(response.url): raise ValueError("Redirect resolved to a non-public URL.")
    if urlparse(response.url).hostname != urlparse(url).hostname: raise ValueError("Source redirected to a different domain.")
    if "html" not in response.headers.get("Content-Type", "").lower(): raise ValueError("Source did not return an HTML page.")
    soup = BeautifulSoup(response.text, "html.parser")
    for x in soup(["script", "style", "noscript", "svg"]): x.decompose()
    scope = soup.select_one(selector) if selector else soup.body or soup
    if scope is None: scope = soup
    text = " ".join(scope.stripped_strings)[:40000]
    base_domain = urlparse(response.url).hostname
    links = []
    for a in scope.find_all("a", href=True):
        href = urljoin(response.url, a["href"])
        if urlparse(href).hostname == base_domain and len(links) < 30:
            links.append({"text": a.get_text(" ", strip=True)[:250], "url": href})
    return RawPage(response.url, text, links, [{"url":response.url,"text":text}])
