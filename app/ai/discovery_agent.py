import json
from .client import complete
from .prompts import DISCOVERY
from .schemas import DiscoveryOutput

def discover(raw_page):
    remaining=30000; pages=[]
    for page in (raw_page.pages or [{"url":raw_page.url,"text":raw_page.text}]):
        if remaining<=0: break
        text=page["text"][:remaining]; remaining-=len(text)
        pages.append({"url":page["url"],"text":text})
    content = json.dumps({"url": raw_page.url, "pages": pages, "text": raw_page.text[:30000], "links": raw_page.links[:30]}, ensure_ascii=False)
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
