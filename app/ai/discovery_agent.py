import json
from .client import complete
from .prompts import DISCOVERY
from .schemas import DiscoveryOutput

def discover(raw_page):
    # Keep requests small enough for free-tier OpenAI-compatible services.
    # `raw_page.text` is an aggregate of these pages, so sending it as well
    # would duplicate the input and can cause a provider HTTP 413 response.
    remaining=12000; pages=[]
    for page in (raw_page.pages or [{"url":raw_page.url,"text":raw_page.text}]):
        if remaining<=0: break
        text=page["text"][:min(3000, remaining)]; remaining-=len(text)
        pages.append({"url":page["url"],"text":text})
    content = json.dumps({"url": raw_page.url, "pages": pages, "links": raw_page.links[:20]}, ensure_ascii=False)
    errors = []
    for _ in range(2):
        try:
            parsed = json.loads(complete(DISCOVERY, content))
            output = DiscoveryOutput.model_validate(parsed)
            for record in output.records:
                page_urls = {p["url"] for p in pages}
                if record.source_url not in page_urls:
                    raise ValueError("Record source URL was not one of the fetched source pages")
                for ev in record.evidence:
                    if ev.quote not in raw_page.text:
                        raise ValueError(f"Evidence for {ev.field} was not present in source text")
            return output.records
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError("Discovery extraction failed validation: " + "; ".join(errors))
