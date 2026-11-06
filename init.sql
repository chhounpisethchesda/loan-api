-- Schema and initial seed data for Loan Service Database

CREATE TABLE IF NOT EXISTS borrowers (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    province VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS loan_applications (
    id SERIAL PRIMARY KEY,
    borrower_id INTEGER NOT NULL REFERENCES borrowers(id) ON DELETE CASCADE,
    amount_usd INTEGER NOT NULL CHECK (amount_usd >= 100 AND amount_usd <= 5000),
    term_months INTEGER NOT NULL CHECK (term_months IN (3, 6, 12, 18, 24)),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    purpose VARCHAR(255) NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    application_id INTEGER REFERENCES loan_applications(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    actor VARCHAR(50) NOT NULL,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed Initial Data
INSERT INTO borrowers (id, full_name, phone, province) VALUES
(1, 'Sok Dara', '012345678', 'Battambang'),
(2, 'Chan Chhaya', '098765432', 'Kampot'),
(3, 'Kim Vuthy', '011223344', 'Battambang'),
(4, 'Heng Malis', '015998877', 'Kampot'),
(5, 'Meas Bopha', '088112233', 'Siem Reap')
ON CONFLICT (id) DO NOTHING;

INSERT INTO loan_applications (id, borrower_id, amount_usd, term_months, status, purpose) VALUES
(101, 1, 1500, 12, 'pending', 'Fertilizer and seeds'),
(102, 2, 2500, 24, 'approved', 'Water pump purchase'),
(103, 3, 3200, 18, 'pending', 'Shop expansion'),
(104, 4, 1600, 12, 'pending', 'Motorcycle repair'),
(105, 5, 800, 6, 'approved', 'Irrigation equipment'),
(106, 4, 1200, 12, 'pending', 'Rice harvesting machinery')
ON CONFLICT (id) DO NOTHING;

INSERT INTO audit_log (application_id, action, actor) VALUES
(102, 'approved', 'officer_07'),
(105, 'approved', 'officer_03')
ON CONFLICT DO NOTHING;
