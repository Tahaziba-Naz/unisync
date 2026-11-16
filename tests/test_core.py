import json
from app.services.scraper import fetch_url, validate_public_url, RawPage
from app.services.comparison_service import content_hash
from app.ai.schemas import DiscoveryOutput, ReviewOutput
from app.ai.discovery_agent import discover

def test_beautifulsoup_extraction(monkeypatch):
    class Resp:
        url="https://example.org/"; headers={"Content-Type":"text/html"}; status_code=200; text='<html><body><h1>Opportunity</h1><script>bad()</script><a href="/apply">Apply</a></body></html>'
        def raise_for_status(self): pass
    class Session:
        headers={}
        def get(self,url,**kw): return Resp()
        def __init__(self): self.headers={}
    monkeypatch.setattr("app.services.scraper.requests.Session",Session)
    monkeypatch.setattr("app.services.scraper.validate_public_url",lambda u:True)
    page=fetch_url("https://example.org/")
    assert "Opportunity" in page.text and "bad()" not in page.text
    assert page.links[0]["url"]=="https://example.org/apply"

def test_url_validation_private_and_scheme(monkeypatch):
    import socket
    monkeypatch.setattr(socket,"getaddrinfo",lambda *a:[(None,None,None,None,("127.0.0.1",0))])
    assert not validate_public_url("http://localhost/")
    assert not validate_public_url("file:///etc/passwd")

def test_schema_validation():
    assert DiscoveryOutput.model_validate({"records":[]}).records==[]
    assert ReviewOutput.model_validate({"verdict":"FLAG","reason":"Needs check","confidence":.2}).verdict=="FLAG"

def test_malformed_llm_response_fails(monkeypatch):
    monkeypatch.setattr("app.ai.discovery_agent.complete",lambda *a:"not json")
    try: discover(RawPage("https://x.test","some text",[]))
    except RuntimeError as e: assert "failed validation" in str(e)
    else: assert False, "malformed response must fail"

def test_review_agent_rejects_invalid_json(monkeypatch):
    from app.ai.review_agent import review
    monkeypatch.setattr("app.ai.review_agent.complete",lambda *a:"{broken")
    try: review({"proposed":{}})
    except Exception: pass
    else: assert False, "malformed Review Agent output must not validate"

def test_verification_flags_bad_application_url():
    from app.services.verification_service import verify
    result=verify({"title":"Internship listing","source_url":"https://example.org","apply_url":"javascript:alert(1)","evidence":[{"quote":"Listing"}]},"https://example.org")
    assert not result["valid"] and any("Application URL" in x for x in result["concerns"])

def test_content_hash_change():
    a={"title":"A","category":"notice","description":"one"}; b={**a,"description":"two"}
    assert content_hash(a)!=content_hash(b)

def test_duplicate_detection_and_changed_record(app):
    from app.extensions import db
    from app.models import Record
    from app.services.comparison_service import find_match
    with app.app_context():
        data={"title":"Summer Research Internship","category":"internship","source_url":"https://example.org/intern","apply_url":None,"deadline":None,"eligibility":None,"description":"Research students"}
        rec=Record(**{k:v for k,v in data.items() if k not in ("deadline",)},deadline=None,content_hash=content_hash(data),status="current")
        db.session.add(rec); db.session.commit()
        match,kind=find_match(data)
        assert match.id==rec.id and kind=="exact_hash"
        changed={**data,"description":"Research students with stipend"}
        match,kind=find_match(changed)
        assert match.id==rec.id and kind in ("likely_duplicate","possible_duplicate")

def test_explicit_expiry_is_recorded_for_review(app):
    from datetime import date, timedelta
    from app.extensions import db
    from app.models import Source, Record, Proposal
    from app.services.maintenance_engine import expire_deadlines
    with app.app_context():
        src=Source(name="Configured source",source_url="https://example.org",source_type="web",default_category="internship")
        db.session.add(src); db.session.flush()
        rec=Record(title="Internship with explicit date",category="internship",source_id=src.id,source_url=src.source_url,content_hash="a"*64,deadline=date.today()-timedelta(days=1),status="current")
        db.session.add(rec); db.session.commit()
        assert expire_deadlines()==1
        assert rec.status=="expired"
        assert Proposal.query.filter_by(record_id=rec.id,action="archive").count()==1

def test_public_empty_and_admin_protected(client):
    assert client.get("/").status_code==200
    assert client.get("/api/records").json["total"]==0
    assert client.get("/admin/").status_code in (302,401)
    assert client.get("/favicon.ico").status_code==404

def test_missing_secret_key_fails_clearly(monkeypatch):
    from app import create_app
    monkeypatch.setattr("app.Config.SECRET_KEY", None)
    try: create_app()
    except RuntimeError as exc: assert "SECRET_KEY is required" in str(exc)
    else: assert False, "startup must reject an empty secret key"

def test_public_api_search_and_pagination(app, client):
    from app.extensions import db
    from app.models import Record
    with app.app_context():
        db.session.add_all([
            Record(title="Scholarship Alpha",category="scholarship",source_url="https://example.org/a",content_hash="1"*64,description="Merit support",status="current"),
            Record(title="Campus Notice",category="notice",source_url="https://example.org/b",content_hash="2"*64,description="Library hours",status="current")])
        db.session.commit()
    data=client.get("/api/records?q=scholarship&per_page=1").json
    assert data["total"]==1 and data["items"][0]["title"]=="Scholarship Alpha"
    assert client.get("/api/records?category=notice").json["total"]==1

def test_proposal_decisions(app):
    from app.models import Admin, Source, Proposal, Record
    from app.services.proposal_service import decide
    with app.app_context():
        user=Admin(username="reviewer",password_hash="x"); src=Source(name="Test",source_url="https://example.org",source_type="web",default_category="notice"); dbs=app.extensions["sqlalchemy"]
        from app.extensions import db
        db.session.add_all([user,src]); db.session.flush()
        data={"title":"Actual Notice","category":"notice","source_url":"https://example.org","apply_url":None,"deadline":None,"eligibility":None,"description":"Text","published_date":None}
        p=Proposal(source_id=src.id,action="add",proposed_data=data,status="pending"); db.session.add(p); db.session.commit()
        decide(p.id,"accepted",user.id); assert Record.query.count()==1
        p2=Proposal(source_id=src.id,action="add",proposed_data=data,status="pending"); db.session.add(p2); db.session.commit(); decide(p2.id,"rejected",user.id); assert p2.status=="rejected"
        p3=Proposal(source_id=src.id,action="add",proposed_data=data,status="pending"); db.session.add(p3); db.session.commit(); decide(p3.id,"flagged",user.id); assert p3.status=="flagged"

def test_scheduler_prevents_overlapping_local_cycle():
    from app.services import maintenance_engine
    assert maintenance_engine._lock.acquire(blocking=False)
    try: assert maintenance_engine.run_cycle()["status"]=="skipped"
    finally: maintenance_engine._lock.release()
