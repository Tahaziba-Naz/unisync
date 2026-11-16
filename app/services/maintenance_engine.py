import logging, threading, time
from datetime import date
from sqlalchemy import text
from ..extensions import db
from ..models import Source, ScanRun, Record, Proposal, utcnow
from ..ai.discovery_agent import discover
from ..ai.review_agent import review
from .scraper import fetch_url
from .comparison_service import find_match
from .verification_service import verify
from .proposal_service import build_proposal

log=logging.getLogger(__name__); _lock=threading.Lock()

def fetch_source(source):
    raw=fetch_url(source.source_url, source.css_selector)
    pages=raw.pages or [{"url":raw.url,"text":raw.text}]
    relevant=[]
    words=("intern", "career", "job", "scholar", "hackathon", "event", "notice", "resource", "apply", "deadline", "fellowship", "competition")
    for link in raw.links:
        label=(link.get("text","")+" "+link.get("url","")).lower()
        if any(word in label for word in words) and link["url"].rstrip("/") != raw.url.rstrip("/"):
            relevant.append(link)
        if len(relevant)>=3: break
    for link in relevant:
        time.sleep(0.3)
        try:
            detail=fetch_url(link["url"])
            pages.extend(detail.pages or [{"url":detail.url,"text":detail.text}])
        except Exception as exc:
            log.info("Same-domain detail link skipped (%s): %s",link["url"],exc)
    raw.pages=pages
    raw.text="\n".join(p["text"] for p in pages)[:40000]
    return raw
def extract_records(raw_page): return discover(raw_page)
def build(draft, source, existing=None, verification=None, review_result=None): return build_proposal(draft, source.id, existing, verification, review_result)
def review_proposal(proposal): return review({"proposed":proposal.proposed_data,"previous":proposal.previous_data,"action":proposal.action,"verification":proposal.verification,"evidence":proposal.proposed_data.get("evidence")})

def expire_deadlines(today=None):
    today = today or date.today()
    expired=Record.query.filter(Record.deadline < today,Record.deadline.isnot(None),Record.status=="current").all()
    for rec in expired:
        has_proposal=Proposal.query.filter_by(record_id=rec.id,action="archive",status="pending").first()
        if not has_proposal:
            data={k:getattr(rec,k).isoformat() if hasattr(getattr(rec,k),"isoformat") else getattr(rec,k) for k in ("title","category","source_url","apply_url","deadline","eligibility","description","published_date","status")}
            db.session.add(Proposal(record_id=rec.id,source_id=rec.source_id,action="archive",proposed_data=data,previous_data=data,review_verdict="ACCEPT",review_reason="The source explicitly listed a deadline that has passed.",confidence=1.0,verification={"deadline_passed":True},status="pending"))
        rec.status="expired"
    return len(expired)

def run_cycle(source_id=None):
    if not _lock.acquire(blocking=False): return {"status":"skipped","error":"A maintenance cycle is already running."}
    acquired_db_lock=False
    total={"status":"success","sources":0,"pages_checked":0,"records_extracted":0,"proposals_created":0,"errors":[]}
    try:
        if db.engine.url.drivername.startswith("mysql"):
            acquired_db_lock = bool(db.session.execute(text("SELECT GET_LOCK('unisync-maintenance', 0)")).scalar())
            if not acquired_db_lock: return {"status":"skipped","error":"A maintenance cycle is already running in another process."}
        q=Source.query.filter_by(enabled=True)
        if source_id: q=q.filter_by(id=source_id)
        for src in q.all():
            run=ScanRun(source_id=src.id); db.session.add(run); db.session.commit(); total["sources"]+=1
            try:
                raw=fetch_source(src); run.pages_checked=len(raw.pages or [raw]); total["pages_checked"]+=run.pages_checked
                drafts=extract_records(raw); run.records_extracted=len(drafts); total["records_extracted"]+=len(drafts)
                for draft in drafts:
                    data=draft.model_dump(mode="json"); existing,kind=find_match(data); checks=verify(data,data["source_url"],kind)
                    if kind=="exact_hash": continue
                    same_source = existing and existing.source_url.rstrip("/") == data["source_url"].rstrip("/")
                    p=build_proposal(draft,src.id,existing if kind=="likely_duplicate" and same_source else None,checks,None)
                    try:
                        rr=review_proposal(p); p.review_verdict=rr.verdict; p.review_reason=rr.reason; p.confidence=rr.confidence
                    except Exception as exc:
                        p.review_verdict="FLAG"; p.review_reason=f"Review Agent unavailable: {exc}"; p.confidence=0
                    run.proposals_created+=1; total["proposals_created"]+=1
                src.last_checked=utcnow(); src.last_successful_check=utcnow(); run.status="success"; db.session.commit()
            except Exception as exc:
                db.session.rollback(); run=db.session.get(ScanRun,run.id); run.status="failed"; run.error_message=str(exc)[:4000]; run.completed_at=utcnow(); src=db.session.get(Source,src.id); src.last_checked=utcnow(); db.session.commit(); total["status"]="partial_failure"; total["errors"].append({"source":src.name,"error":str(exc)})
            else:
                run.completed_at=utcnow(); db.session.commit()
        expire_deadlines()
        db.session.commit()
    finally:
        if acquired_db_lock:
            try: db.session.execute(text("SELECT RELEASE_LOCK('unisync-maintenance')")); db.session.commit()
            except Exception: db.session.rollback(); log.exception("Could not release maintenance lock")
        _lock.release()
    return total
