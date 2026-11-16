from .scraper import validate_public_url

def verify(data, source_url, duplicate_kind="none"):
    concerns=[]
    if not data.get("title") or len(data["title"].strip()) < 4: concerns.append("Title is missing or too short")
    if data.get("source_url") != source_url: concerns.append("Source URL does not match fetched page")
    if not validate_public_url(source_url): concerns.append("Source URL is not a public HTTP URL")
    if data.get("apply_url") and not validate_public_url(data["apply_url"]): concerns.append("Application URL is invalid or non-public")
    if not data.get("evidence"): concerns.append("No source evidence provided")
    if duplicate_kind in ("likely_duplicate", "possible_duplicate"): concerns.append(f"Duplicate match: {duplicate_kind}")
    return {"valid": not concerns, "concerns": concerns, "duplicate_match": duplicate_kind}
