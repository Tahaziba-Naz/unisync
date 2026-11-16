from datetime import datetime, timezone
from urllib.parse import urlparse
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func
from sqlalchemy import text
from ..extensions import db
from ..models import Admin, Source, Proposal, ScanRun, Record
from ..services.scraper import validate_public_url, fetch_url
from ..services.maintenance_engine import run_cycle
from ..services.proposal_service import decide
from ..ai.client import configured

bp=Blueprint("admin",__name__)

@bp.get("/login")
def login(): return render_template("login.html")
@bp.post("/login")
def do_login():
    user=Admin.query.filter_by(username=request.form.get("username","").strip()).first()
    if not user or not user.check_password(request.form.get("password","")): flash("Invalid username or password.","error"); return redirect(url_for("admin.login"))
    login_user(user); return redirect(url_for("admin.dashboard"))
@bp.post("/logout")
@login_required
def logout(): logout_user(); return redirect(url_for("public.home"))

@bp.get("/")
@login_required
def dashboard():
    return render_template("admin_dashboard.html", total=Record.query.count(), current=Record.query.filter_by(status="current").count(), expired=Record.query.filter_by(status="expired").count(), pending=Proposal.query.filter_by(status="pending").count(), flagged=Proposal.query.filter_by(status="flagged").count(), sources=Source.query.count(), last=ScanRun.query.filter_by(status="success").order_by(ScanRun.completed_at.desc()).first(), next_run=None, llm=configured(), db_status=database_status())

def database_status():
    try: db.session.execute(text("SELECT 1")); return "Connected"
    except Exception: db.session.rollback(); return "Unavailable"

@bp.get("/sources")
@login_required
def sources(): return render_template("sources.html", sources=Source.query.order_by(Source.created_at.desc()).all())
@bp.post("/sources")
@login_required
def add_source():
    url=request.form.get("source_url","").strip()
    if len(url)>500 or not validate_public_url(url): flash("URL must be a public HTTP/HTTPS URL no longer than 500 characters.","error"); return redirect(url_for("admin.sources"))
    if Source.query.filter_by(source_url=url).first(): flash("That source URL already exists.","error"); return redirect(url_for("admin.sources"))
    s=Source(name=request.form.get("name","").strip(),source_url=url,source_type=request.form.get("source_type","web").strip(),default_category=request.form.get("default_category","notice"),css_selector=request.form.get("css_selector") or None,enabled=bool(request.form.get("enabled")))
    if not s.name: flash("Source name is required.","error")
    else: db.session.add(s); db.session.commit(); flash("Source added.","success")
    return redirect(url_for("admin.sources"))
@bp.post("/sources/<int:source_id>/edit")
@login_required
def edit_source(source_id):
    s=db.get_or_404(Source,source_id); url=request.form.get("source_url","").strip()
    if len(url)>500 or not validate_public_url(url): flash("Invalid public URL (must be no longer than 500 characters).","error")
    else:
        s.name=request.form.get("name",s.name).strip(); s.source_url=url; s.source_type=request.form.get("source_type",s.source_type); s.default_category=request.form.get("default_category",s.default_category); s.css_selector=request.form.get("css_selector") or None; s.enabled=request.form.get("enabled")=="1"; db.session.commit(); flash("Source updated.","success")
    return redirect(url_for("admin.sources"))
@bp.post("/sources/<int:source_id>/delete")
@login_required
def delete_source(source_id):
    db.session.delete(db.get_or_404(Source,source_id)); db.session.commit(); flash("Source deleted.","success"); return redirect(url_for("admin.sources"))
@bp.post("/sources/<int:source_id>/test")
@login_required
def test_source(source_id):
    s=db.get_or_404(Source,source_id)
    try: page=fetch_url(s.source_url,s.css_selector); return jsonify(ok=True,title=page.text[:200],characters=len(page.text),links=len(page.links))
    except Exception as exc: return jsonify(ok=False,error=str(exc)),400
@bp.post("/sources/<int:source_id>/scan")
@login_required
def scan_source(source_id):
    if not Source.query.filter_by(id=source_id).first(): return jsonify(error="Source not found"),404
    return jsonify(run_cycle(source_id))
@bp.post("/maintenance/run")
@login_required
def manual_run():
    result=run_cycle()
    if result.get("status")=="skipped":
        flash(result.get("error", "Maintenance is already running."), "error")
    else:
        flash(f"Maintenance finished: {result.get('status', 'unknown')}; {result.get('proposals_created', 0)} proposals created.","success" if result.get("status")=="success" else "error")
        if result.get("errors"):
            first=result["errors"][0]
            flash(f"{first.get('source', 'Source')} failed: {first.get('error', 'Unknown scan error')}", "error")
    return redirect(url_for("admin.dashboard"))
@bp.get("/proposals")
@login_required
def proposals(): return render_template("review_queue.html", proposals=Proposal.query.order_by(Proposal.created_at.desc()).all())
@bp.post("/proposals/<int:proposal_id>/decision")
@login_required
def review_proposal(proposal_id):
    try: decide(proposal_id,request.form.get("decision"),current_user.id,request.form.get("reason")); flash("Review decision saved.","success")
    except Exception as exc: flash(f"Review failed: {exc}","error")
    return redirect(url_for("admin.proposals"))
@bp.get("/history")
@login_required
def history():
    runs=ScanRun.query.order_by(ScanRun.started_at.desc()).limit(200).all()
    source_names={s.id:s.name for s in Source.query.all()}
    return render_template("scan_history.html", runs=runs, source_names=source_names)
@bp.get("/settings")
@login_required
def settings(): return render_template("settings.html", llm=configured(), database=database_status(), interval=current_app.config["CHECK_INTERVAL_MINUTES"], timezone=current_app.config["TIMEZONE"])
