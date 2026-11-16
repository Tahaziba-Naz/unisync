from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

def utcnow(): return datetime.now(timezone.utc).replace(tzinfo=None)

class Admin(UserMixin, db.Model):
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Source(db.Model):
    __tablename__ = "sources"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    source_url = db.Column(db.String(500), nullable=False, unique=True)
    source_type = db.Column(db.String(80), nullable=False)
    default_category = db.Column(db.String(40), nullable=False)
    css_selector = db.Column(db.String(500))
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    last_checked = db.Column(db.DateTime)
    last_successful_check = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

class Record(db.Model):
    __tablename__ = "records"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(40), nullable=False, index=True)
    source_id = db.Column(db.Integer, db.ForeignKey("sources.id", ondelete="SET NULL"), index=True)
    source_url = db.Column(db.String(500), nullable=False)
    apply_url = db.Column(db.String(500))
    deadline = db.Column(db.Date)
    eligibility = db.Column(db.Text)
    description = db.Column(db.Text)
    published_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, default="current", index=True)
    content_hash = db.Column(db.String(64), nullable=False, index=True)
    first_seen = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_checked = db.Column(db.DateTime, nullable=False, default=utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    __table_args__ = (db.UniqueConstraint("source_url", "content_hash", name="uq_record_source_hash"),)

class Proposal(db.Model):
    __tablename__ = "proposals"
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey("records.id", ondelete="SET NULL"))
    source_id = db.Column(db.Integer, db.ForeignKey("sources.id", ondelete="SET NULL"))
    action = db.Column(db.String(24), nullable=False)
    proposed_data = db.Column(db.JSON, nullable=False)
    previous_data = db.Column(db.JSON)
    review_verdict = db.Column(db.String(12))
    review_reason = db.Column(db.Text)
    confidence = db.Column(db.Float)
    verification = db.Column(db.JSON)
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"))

class ScanRun(db.Model):
    __tablename__ = "scan_runs"
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("sources.id", ondelete="SET NULL"), index=True)
    started_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default="running")
    pages_checked = db.Column(db.Integer, nullable=False, default=0)
    records_extracted = db.Column(db.Integer, nullable=False, default=0)
    proposals_created = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text)

class ReviewEvent(db.Model):
    __tablename__ = "review_events"
    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"))
    decision = db.Column(db.String(16), nullable=False)
    reason = db.Column(db.Text)
    changes = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
