from datetime import datetime, date
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models import Proposal, Record, ReviewEvent, utcnow
from .comparison_service import content_hash

def build_proposal(draft, source_id, existing=None, verification=None, review=None):
    data = draft.model_dump(mode="json") if hasattr(draft, "model_dump") else dict(draft)
    action = "update" if existing and content_hash(data) != existing.content_hash else ("skip_duplicate" if existing else "add")
    duplicate_flag = bool(verification and verification.get("duplicate_match") in ("likely_duplicate", "possible_duplicate") and existing is None)
    if duplicate_flag: action = "skip_duplicate"
    prior = {k:getattr(existing,k) for k in ("title","category","source_url","apply_url","deadline","eligibility","description","published_date","status") } if existing else None
    for obj in (data, prior):
        if obj:
            for k,v in list(obj.items()):
                if isinstance(v,(date,datetime)): obj[k]=v.isoformat()
    p=Proposal(record_id=existing.id if existing else None, source_id=source_id, action=action, proposed_data=data, previous_data=prior, verification=verification or {}, review_verdict=review.verdict if review and not duplicate_flag else "FLAG", review_reason=review.reason if review and not duplicate_flag else ("Possible duplicate needs a human check." if duplicate_flag else "Review unavailable"), confidence=review.confidence if review and not duplicate_flag else 0, status="flagged" if duplicate_flag else "pending")
    db.session.add(p); db.session.flush(); return p

def decide(proposal_id, decision, reviewer_id, reason=None):
    if decision not in ("accepted", "rejected", "flagged"): raise ValueError("Decision must be accepted, rejected, or flagged")
    try:
        p=Proposal.query.filter_by(id=proposal_id).with_for_update().first_or_404()
        if p.status not in ("pending", "flagged"): raise ValueError("Proposal has already been decided")
        old=p.status
        if decision == "accepted":
            if p.action not in ("add","update","archive"): raise ValueError("This proposal action cannot be published")
            if p.action == "archive" and p.record_id:
                rec=db.session.get(Record,p.record_id); rec.status="archived"
            else:
                d=p.proposed_data
                def parse_date(v): return date.fromisoformat(v) if v else None
                if p.action == "add": rec=Record(source_id=p.source_id, source_url=d["source_url"], content_hash=content_hash(d), first_seen=utcnow())
                else:
                    rec=db.session.get(Record,p.record_id)
                    if rec is None: raise ValueError("Target record no longer exists")
                    rec.content_hash=content_hash(d)
                for k in ("title","category","source_url","apply_url","eligibility","description"):
                    setattr(rec,k,d.get(k))
                rec.deadline=parse_date(d.get("deadline")); rec.published_date=parse_date(d.get("published_date")); rec.status="current"; rec.last_checked=utcnow()
                db.session.add(rec)
            p.status="accepted"
        elif decision == "rejected": p.status="rejected"
        else: p.status="flagged"
        p.reviewed_at=utcnow(); p.reviewed_by=reviewer_id
        ev=ReviewEvent(proposal_id=p.id, reviewer_id=reviewer_id, decision=decision, reason=reason, changes={"from":old,"to":p.status})
        db.session.add(ev); db.session.commit(); return p
    except Exception:
        db.session.rollback(); raise
