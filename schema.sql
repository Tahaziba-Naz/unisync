-- Empty MySQL schema for UniSync. Runtime initialization is also available via
-- `flask --app run.py init-db`; SQLAlchemy models in app/models.py are canonical.
CREATE TABLE admins (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE sources (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  source_url VARCHAR(500) NOT NULL UNIQUE,
  source_type VARCHAR(80) NOT NULL,
  default_category VARCHAR(40) NOT NULL,
  css_selector VARCHAR(500) NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  last_checked DATETIME NULL,
  last_successful_check DATETIME NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE records (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(500) NOT NULL,
  category VARCHAR(40) NOT NULL,
  source_id INT NULL,
  source_url VARCHAR(500) NOT NULL,
  apply_url VARCHAR(500) NULL,
  deadline DATE NULL,
  eligibility TEXT NULL,
  description TEXT NULL,
  published_date DATE NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'current',
  content_hash CHAR(64) NOT NULL,
  first_seen DATETIME NOT NULL,
  last_checked DATETIME NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uq_record_source_hash (source_url, content_hash),
  KEY ix_records_category (category), KEY ix_records_source_id (source_id),
  KEY ix_records_content_hash (content_hash), KEY ix_records_status (status),
  CONSTRAINT fk_records_source FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE proposals (
  id INT AUTO_INCREMENT PRIMARY KEY,
  record_id INT NULL,
  source_id INT NULL,
  action VARCHAR(24) NOT NULL,
  proposed_data JSON NOT NULL,
  previous_data JSON NULL,
  review_verdict VARCHAR(12) NULL,
  review_reason TEXT NULL,
  confidence FLOAT NULL,
  verification JSON NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  created_at DATETIME NOT NULL,
  reviewed_at DATETIME NULL,
  reviewed_by INT NULL,
  KEY ix_proposals_status (status),
  CONSTRAINT fk_proposals_record FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE SET NULL,
  CONSTRAINT fk_proposals_source FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE SET NULL,
  CONSTRAINT fk_proposals_admin FOREIGN KEY (reviewed_by) REFERENCES admins(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE scan_runs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  source_id INT NULL,
  started_at DATETIME NOT NULL,
  completed_at DATETIME NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'running',
  pages_checked INT NOT NULL DEFAULT 0,
  records_extracted INT NOT NULL DEFAULT 0,
  proposals_created INT NOT NULL DEFAULT 0,
  error_message TEXT NULL,
  KEY ix_scan_runs_source_id (source_id),
  CONSTRAINT fk_scan_runs_source FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE review_events (
  id INT AUTO_INCREMENT PRIMARY KEY,
  proposal_id INT NOT NULL,
  reviewer_id INT NULL,
  decision VARCHAR(16) NOT NULL,
  reason TEXT NULL,
  changes JSON NULL,
  created_at DATETIME NOT NULL,
  KEY ix_review_events_proposal_id (proposal_id),
  CONSTRAINT fk_review_events_proposal FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE,
  CONSTRAINT fk_review_events_admin FOREIGN KEY (reviewer_id) REFERENCES admins(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
