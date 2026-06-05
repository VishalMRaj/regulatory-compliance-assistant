DROP TABLE IF EXISTS compliance_sessions CASCADE;
DROP TABLE IF EXISTS compliance_users CASCADE;

CREATE TABLE compliance_users (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(30) NOT NULL CHECK (role IN ('COMPLIANCE_OFFICER', 'INTERNAL_AUDITOR', 'COMPLIANCE_HEAD')),
    email VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed mock personas
INSERT INTO compliance_users (user_id, username, full_name, role, email) VALUES
('USR-001', 'compliance_officer', 'Fiserv Compliance Officer', 'COMPLIANCE_OFFICER', 'compliance.officer@finserv.global'),
('USR-002', 'internal_auditor', 'Internal Auditor', 'INTERNAL_AUDITOR', 'internal.auditor@finserv.global'),
('USR-003', 'compliance_head', 'Compliance Head', 'COMPLIANCE_HEAD', 'compliance.head@finserv.global')
ON CONFLICT (user_id) DO NOTHING;

-- Session tracking layout linked directly to LangGraph thread_id mapping
CREATE TABLE compliance_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    initiated_by VARCHAR(50) REFERENCES compliance_users(user_id),
    transaction_amount NUMERIC(15, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    target_jurisdiction VARCHAR(50),
    status VARCHAR(20) DEFAULT 'SUSPENDED' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'APPROVED', 'FLAGGED_VIOLATION')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed active pending compliance rows
INSERT INTO compliance_sessions (session_id, initiated_by, transaction_amount, target_jurisdiction, status) VALUES
('TXN-2026-8891', 'USR-001', 2500000.00, 'High-Risk-A', 'SUSPENDED'),
('TXN-2026-9042', 'USR-001', 450000.00, 'EU', 'SUSPENDED')
ON CONFLICT (session_id) DO NOTHING;