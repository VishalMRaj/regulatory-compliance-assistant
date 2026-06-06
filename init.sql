-- Schema is idempotent: safe to re-run without data loss.
-- Tables are only created if they do not already exist.
-- DROPs are intentionally removed to preserve live session data across restarts.

CREATE TABLE IF NOT EXISTS compliance_users (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(30) NOT NULL CHECK (role IN ('COMPLIANCE_OFFICER', 'INTERNAL_AUDITOR', 'COMPLIANCE_HEAD')),
    email VARCHAR(100),
    metadata JSONB,
    structural_roles VARCHAR(50)[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO compliance_users (user_id, username, full_name, role, email, metadata, structural_roles) VALUES
('USR-001', 'compliance_officer_sim', 'Fiserv Compliance Officer', 'COMPLIANCE_OFFICER', 'compliance.officer@finserv.global', '{}', '{"COMPLIANCE_OFFICER"}'),
('USR-002', 'internal_auditor_sim', 'Internal Auditor', 'INTERNAL_AUDITOR', 'internal.auditor@finserv.global', '{}', '{"INTERNAL_AUDITOR"}'),
('USR-003', 'compliance_head_sim', 'Compliance Head', 'COMPLIANCE_HEAD', 'compliance.head@finserv.global', '{}', '{"COMPLIANCE_HEAD"}')
ON CONFLICT (user_id) DO UPDATE
SET username = EXCLUDED.username, structural_roles = EXCLUDED.structural_roles;

CREATE TABLE IF NOT EXISTS compliance_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    initiated_by VARCHAR(50) REFERENCES compliance_users(user_id),
    transaction_amount NUMERIC(15, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    target_jurisdiction VARCHAR(50),
    status VARCHAR(20) DEFAULT 'SUSPENDED' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'APPROVED', 'FLAGGED_VIOLATION')),
    metadata JSONB DEFAULT '{}',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compliance_audit_log (
    event_id VARCHAR(50) PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(100) NOT NULL,
    details JSONB DEFAULT '{}'
);

INSERT INTO compliance_audit_log (event_id, timestamp, action, details) VALUES
('EVT-001', CURRENT_TIMESTAMP - INTERVAL '1 day', 'SCREEN_TRANSACTION', '{"session_id": "TXN-2026-8891", "risk_rating": "HIGH", "reason": "Jurisdiction listed as High-Risk-A"}'),
('EVT-002', CURRENT_TIMESTAMP - INTERVAL '2 days', 'SCREEN_TRANSACTION', '{"session_id": "TXN-2026-9042", "risk_rating": "MEDIUM", "reason": "Transaction exceeds standard daily threshold for EU"}')
ON CONFLICT (event_id) DO NOTHING;