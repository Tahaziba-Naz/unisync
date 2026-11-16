import hashlib, re
from urllib.parse import urlsplit, urlunsplit
from rapidfuzz.fuzz import ratio
from ..extensions import db
from ..models import Record

def normalize_url(url):
    p = urlsplit(url.strip()); return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", ""))

def content_hash(data):
    keys = ("title", "category", "apply_url", "deadline", "eligibility", "description", "published_date")
    material = "|".join(str(data.get(k) or "").strip().lower() for k in keys)
    return hashlib.sha256(material.encode()).hexdigest()

def find_match(data):
    h = content_hash(data)
    exact = Record.query.filter_by(content_hash=h).first()
    if exact: return exact, "exact_hash"
    title = re.sub(r"\W+", " ", data["title"].lower()).strip()
    candidates = Record.query.filter_by(category=data["category"], status="current").all()
    matches = [(ratio(title, re.sub(r"\W+", " ", r.title.lower()).strip()), r) for r in candidates]
    if matches:
        score, rec = max(matches, key=lambda x:x[0])
        if score >= 92: return rec, "likely_duplicate"
        if score >= 82: return rec, "possible_duplicate"
    return None, "none"
