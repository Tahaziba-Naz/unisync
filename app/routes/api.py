from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from datetime import date
from datetime import datetime
from ..models import Record

bp=Blueprint("api",__name__)

@bp.get("/records")
def records():
    q=Record.query.filter_by(status="current")
    term=request.args.get("q","").strip()
    if term: q=q.filter(or_(Record.title.ilike(f"%{term}%"),Record.description.ilike(f"%{term}%"),Record.eligibility.ilike(f"%{term}%")))
    cats=request.args.getlist("category")
    if cats: q=q.filter(Record.category.in_(cats))
    if request.args.get("deadline") == "upcoming": q=q.filter(Record.deadline >= date.today())
    sort=request.args.get("sort","newest")
    q=q.order_by(Record.deadline.asc().nullslast() if sort=="deadline" else Record.created_at.desc())
    page=max(1,request.args.get("page",1,type=int)); per=min(50,max(1,request.args.get("per_page",12,type=int)))
    total=q.count(); items=q.offset((page-1)*per).limit(per).all()
    return jsonify(items=[serialize(r) for r in items],page=page,per_page=per,total=total,pages=(total+per-1)//per)

@bp.get("/records/<int:record_id>")
def record(record_id):
    r=Record.query.filter_by(id=record_id,status="current").first_or_404(); return jsonify(serialize(r))

@bp.get("/categories")
def categories():
    rows=Record.query.filter_by(status="current").with_entities(Record.category).all()
    from collections import Counter
    return jsonify(counts=dict(Counter(c for (c,) in rows)))

def serialize(r):
    result={}
    for k in ("id","title","category","source_id","source_url","apply_url","deadline","eligibility","description","published_date","status","first_seen","last_checked","created_at"):
        value=getattr(r,k)
        result[k]=value.isoformat() if isinstance(value,(date,datetime)) else value
    return result
