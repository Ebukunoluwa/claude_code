-- =============================================================================
-- Sizor Clinical Pathway Mapping System — Database Schema
-- =============================================================================
-- NOTE: This schema extends the existing Sizor database. Tables prefixed with
-- "pathway_" or new tables only. Existing tables (patients, calls etc.) are
-- managed by the main ORM / Alembic migrations.
-- =============================================================================

-- alembic_version is managed by Alembic automatically.
-- CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num));

-- -----------------------------------------------------------------------------
-- patient_pathways
-- Links a patient to a specific OPCS-coded clinical pathway with full schedule
-- and playbook stored as JSONB.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_pathways (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id          UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    opcs_code           VARCHAR(20) NOT NULL,
    pathway_slug        VARCHAR(100) NOT NULL,
    nice_ids            TEXT[] NOT NULL DEFAULT '{}',
    domains             TEXT[] NOT NULL DEFAULT '{}',
    risk_flags          TEXT[] NOT NULL DEFAULT '{}',
    discharge_date      DATE NOT NULL,
    monitoring_ends     DATE NOT NULL,
    -- call_schedule: [{"date": "YYYY-MM-DD", "day": N, "status": "scheduled|completed|missed"}]
    call_schedule       JSONB NOT NULL DEFAULT '[]',
    -- playbook: {day: {domain: {opening_question, clinical_question, score_guide, ...}}}
    playbook            JSONB,
    active              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT patient_pathways_patient_opcs_unique UNIQUE (patient_id, opcs_code)
);

CREATE INDEX IF NOT EXISTS idx_patient_pathways_patient_id ON patient_pathways(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_pathways_opcs_code ON patient_pathways(opcs_code);
CREATE INDEX IF NOT EXISTS idx_patient_pathways_active ON patient_pathways(active) WHERE active = TRUE;

-- -----------------------------------------------------------------------------
-- domain_scores and pathway_soap_notes — REMOVED 2026-04-24
-- Both tables were defined here historically but never written or read by any
-- Python code. Dropped via Alembic revision c2e4a6f801b3. Row count was zero
-- at drop time. See PLAN.md Sec 6 D2 for the rationale; the migration's
-- downgrade() block recreates the original definitions if needed.
-- -----------------------------------------------------------------------------

-- -----------------------------------------------------------------------------
-- patient_red_flags
-- Tracks active and resolved red flags at domain level across the monitoring window.
-- DEFERRED PROMOTION (PLAN.md Sec 6 D2): kept in schema pending Phase 4's
-- patient-facing red-flag probing work. urgency_flags (modelled as UrgencyFlag)
-- handles generic urgency today; this table's per-domain + resolution-tracking
-- shape is the likely home for Phase 4 once that work lands.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_red_flags (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id          UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    call_id             UUID REFERENCES call_records(call_id) ON DELETE SET NULL,
    domain              VARCHAR(100) NOT NULL,
    flag_code           VARCHAR(100) NOT NULL,
    score_at_trigger    SMALLINT NOT NULL,
    nice_basis          VARCHAR(50),
    escalation_tier     VARCHAR(20) NOT NULL,   -- 999/same_day/urgent_gp/next_call
    resolved            BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_call_id    UUID REFERENCES call_records(call_id) ON DELETE SET NULL,
    triggered_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_patient_red_flags_patient_id ON patient_red_flags(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_red_flags_unresolved ON patient_red_flags(patient_id, resolved) WHERE resolved = FALSE;

-- -----------------------------------------------------------------------------
-- domain_benchmarks
-- NICE-sourced expected and upper-bound scores per domain per day range per pathway.
-- Seeded from clinical/benchmarks.py via db/seed_benchmarks.py.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS domain_benchmarks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opcs_code           VARCHAR(20) NOT NULL,
    domain              VARCHAR(100) NOT NULL,
    day_range_start     INTEGER NOT NULL,
    day_range_end       INTEGER NOT NULL,
    expected_score      SMALLINT NOT NULL,
    upper_bound_score   SMALLINT NOT NULL,
    expected_state      TEXT,
    nice_source         VARCHAR(50),
    nice_quote          TEXT,
    urgency             VARCHAR(20) DEFAULT 'routine',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT domain_benchmarks_unique UNIQUE (opcs_code, domain, day_range_start)
);

CREATE INDEX IF NOT EXISTS idx_domain_benchmarks_opcs_domain ON domain_benchmarks(opcs_code, domain);
CREATE INDEX IF NOT EXISTS idx_domain_benchmarks_lookup ON domain_benchmarks(opcs_code, domain, day_range_start, day_range_end);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_domain_benchmarks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_domain_benchmarks_updated_at ON domain_benchmarks;
CREATE TRIGGER trg_domain_benchmarks_updated_at
    BEFORE UPDATE ON domain_benchmarks
    FOR EACH ROW EXECUTE FUNCTION update_domain_benchmarks_updated_at();
