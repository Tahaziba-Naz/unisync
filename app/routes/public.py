from flask import Blueprint, render_template, request
from ..models import Record

bp=Blueprint("public",__name__)

@bp.get("/")
def home():
    latest=Record.query.filter_by(status="current").order_by(Record.created_at.desc()).limit(6).all()
    return render_template("index.html", latest=latest)

@bp.get("/resources")
def resources(): return render_template("listing.html", title="Study resources", categories=["study_resource"])
@bp.get("/opportunities")
def opportunities(): return render_template("listing.html", title="Opportunities", categories=["internship","job","hackathon","scholarship"])
@bp.get("/notices")
def notices(): return render_template("listing.html", title="Campus updates", categories=["notice","event"])
@bp.get("/record/<int:record_id>")
def detail(record_id):
    record=Record.query.filter_by(id=record_id,status="current").first_or_404()
    return render_template("record_detail.html", record=record)
