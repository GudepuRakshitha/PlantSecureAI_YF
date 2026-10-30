-- ---------------------------------------------------------------------------
-- SAFEGUARD industrial safety monitoring — SQLite export schema
--
-- This is a portable export of the CSV dataset, not the analytical source of
-- truth.  The CSVs in ``data/`` remain authoritative.  Timestamps are stored
-- as ISO-like text in the project's naive local time (Asia/Kolkata).
-- ---------------------------------------------------------------------------

PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS vw_ack_compliance;
DROP VIEW  IF EXISTS vw_open_incidents;
DROP VIEW  IF EXISTS vw_action_pipeline;

DROP TABLE IF EXISTS analysis_exceptions;
DROP TABLE IF EXISTS sla_breaches;
DROP TABLE IF EXISTS corrective_actions;
DROP TABLE IF EXISTS incidents;
DROP TABLE IF EXISTS acknowledgements;
DROP TABLE IF EXISTS operator_shifts;
DROP TABLE IF EXISTS alarm_events;
DROP TABLE IF EXISTS alarm_definitions;
DROP TABLE IF EXISTS interlocks;
DROP TABLE IF EXISTS machines;
DROP TABLE IF EXISTS safety_zones;
DROP TABLE IF EXISTS plants;

-- ---------------------------------------------------------------------------
-- Master data
-- ---------------------------------------------------------------------------

CREATE TABLE plants (
    plant_id    TEXT PRIMARY KEY,
    plant_name  TEXT NOT NULL,
    location    TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

CREATE TABLE safety_zones (
    zone_id     TEXT PRIMARY KEY,
    plant_id    TEXT NOT NULL REFERENCES plants (plant_id),
    zone_name   TEXT NOT NULL,
    risk_level  TEXT NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH'))
);

CREATE TABLE machines (
    machine_id   TEXT PRIMARY KEY,
    plant_id     TEXT NOT NULL REFERENCES plants (plant_id),
    zone_id      TEXT NOT NULL REFERENCES safety_zones (zone_id),
    machine_name TEXT NOT NULL,
    machine_type TEXT NOT NULL CHECK (
        machine_type IN ('CONVEYOR', 'ROBOT', 'PRESS', 'MOTOR', 'PUMP')
    ),
    status       TEXT NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

CREATE TABLE interlocks (
    interlock_id   TEXT PRIMARY KEY,
    machine_id     TEXT NOT NULL REFERENCES machines (machine_id),
    interlock_name TEXT NOT NULL,
    required_state TEXT NOT NULL CHECK (required_state IN ('OPEN', 'CLOSED')),
    current_state  TEXT NOT NULL CHECK (current_state IN ('OPEN', 'CLOSED'))
);

CREATE TABLE alarm_definitions (
    alarm_definition_id            TEXT PRIMARY KEY,
    machine_id                     TEXT NOT NULL REFERENCES machines (machine_id),
    alarm_name                     TEXT NOT NULL,
    severity                       TEXT NOT NULL CHECK (
        severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
    ),
    acknowledgement_required       INTEGER NOT NULL CHECK (
        acknowledgement_required IN (0, 1)
    ),
    acknowledgement_limit_minutes  INTEGER NOT NULL CHECK (
        acknowledgement_limit_minutes > 0
    )
);

-- ---------------------------------------------------------------------------
-- Transaction data
-- ---------------------------------------------------------------------------

CREATE TABLE operator_shifts (
    shift_id   TEXT PRIMARY KEY,
    plant_id   TEXT NOT NULL REFERENCES plants (plant_id),
    operator_id TEXT NOT NULL,
    shift_start TEXT NOT NULL,
    shift_end   TEXT NOT NULL,
    CHECK (shift_end > shift_start)
);

CREATE TABLE alarm_events (
    alarm_event_id      TEXT PRIMARY KEY,
    machine_id          TEXT NOT NULL REFERENCES machines (machine_id),
    alarm_definition_id TEXT NOT NULL REFERENCES alarm_definitions (alarm_definition_id),
    severity            TEXT NOT NULL CHECK (
        severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
    ),
    event_timestamp     TEXT NOT NULL,
    machine_state       TEXT NOT NULL CHECK (
        machine_state IN ('RUNNING', 'STOPPED', 'WARNING')
    ),
    alarm_status        TEXT NOT NULL CHECK (
        alarm_status IN ('ACTIVE', 'ACKNOWLEDGED', 'CLEARED', 'UNACKNOWLEDGED')
    ),
    acknowledged        INTEGER NOT NULL CHECK (acknowledged IN (0, 1)),
    acknowledged_at     TEXT,
    cleared_at          TEXT,
    state_transition    TEXT NOT NULL,
    issue_type          TEXT NOT NULL DEFAULT 'NONE'
);

CREATE TABLE acknowledgements (
    acknowledgement_id TEXT PRIMARY KEY,
    alarm_event_id     TEXT NOT NULL REFERENCES alarm_events (alarm_event_id),
    operator_id        TEXT NOT NULL,
    shift_id           TEXT NOT NULL REFERENCES operator_shifts (shift_id),
    ack_timestamp      TEXT NOT NULL,
    response_minutes   INTEGER NOT NULL CHECK (response_minutes >= 0),
    status             TEXT NOT NULL CHECK (status IN ('ON_TIME', 'DELAYED'))
);

CREATE TABLE incidents (
    incident_id    TEXT PRIMARY KEY,
    alarm_event_id TEXT NOT NULL REFERENCES alarm_events (alarm_event_id),
    machine_id     TEXT NOT NULL REFERENCES machines (machine_id),
    plant_id       TEXT NOT NULL REFERENCES plants (plant_id),
    incident_type  TEXT NOT NULL,
    severity       TEXT NOT NULL CHECK (
        severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
    ),
    created_at     TEXT NOT NULL,
    closed_at      TEXT,
    status         TEXT NOT NULL CHECK (
        status IN ('OPEN', 'INVESTIGATING', 'CLOSED')
    )
);

CREATE TABLE corrective_actions (
    action_id            TEXT PRIMARY KEY,
    incident_id          TEXT NOT NULL REFERENCES incidents (incident_id),
    action_description   TEXT NOT NULL,
    assigned_to          TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    closed_at            TEXT,
    verified_at          TEXT,
    status               TEXT NOT NULL CHECK (
        status IN ('OPEN', 'IN_PROGRESS', 'PENDING_VERIFICATION', 'CLOSED')
    ),
    verification_status  TEXT NOT NULL CHECK (
        verification_status IN ('PENDING', 'VERIFIED', 'NOT_VERIFIED')
    ),
    effectiveness_status TEXT NOT NULL CHECK (
        effectiveness_status IN (
            'PENDING', 'EFFECTIVE', 'PARTIALLY_EFFECTIVE', 'NOT_EFFECTIVE'
        )
    )
);

-- ---------------------------------------------------------------------------
-- Analytical outputs (regenerated by src/safety_analyzer.py)
-- ---------------------------------------------------------------------------

CREATE TABLE sla_breaches (
    record_id                     TEXT PRIMARY KEY,
    alarm_event_id                TEXT NOT NULL,
    acknowledgement_id            TEXT NOT NULL,
    plant_id                      TEXT,
    machine_id                    TEXT,
    alarm_definition_id           TEXT,
    severity                      TEXT NOT NULL,
    event_timestamp               TEXT NOT NULL,
    acknowledged_at               TEXT NOT NULL,
    response_minutes              REAL NOT NULL,
    acknowledgement_limit_minutes REAL NOT NULL,
    overdue_minutes               REAL NOT NULL,
    is_routine_sla                INTEGER NOT NULL CHECK (is_routine_sla IN (0, 1))
);

CREATE TABLE analysis_exceptions (
    exception_type TEXT NOT NULL,
    entity         TEXT NOT NULL,
    record_id      TEXT NOT NULL,
    severity       TEXT NOT NULL,
    plant_id       TEXT,
    machine_id     TEXT,
    case_id        TEXT,
    is_routine_sla INTEGER NOT NULL CHECK (is_routine_sla IN (0, 1)),
    description    TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

CREATE INDEX idx_machines_plant        ON machines (plant_id);
CREATE INDEX idx_definitions_machine   ON alarm_definitions (machine_id);
CREATE INDEX idx_events_machine_time   ON alarm_events (machine_id, event_timestamp);
CREATE INDEX idx_events_definition     ON alarm_events (alarm_definition_id);
CREATE INDEX idx_events_status         ON alarm_events (alarm_status);
CREATE INDEX idx_ack_event             ON acknowledgements (alarm_event_id);
CREATE INDEX idx_ack_shift             ON acknowledgements (shift_id);
CREATE INDEX idx_incidents_event       ON incidents (alarm_event_id);
CREATE INDEX idx_incidents_status      ON incidents (status);
CREATE INDEX idx_actions_incident      ON corrective_actions (incident_id);
CREATE INDEX idx_sla_event             ON sla_breaches (alarm_event_id);
CREATE INDEX idx_exceptions_type       ON analysis_exceptions (exception_type);

-- ---------------------------------------------------------------------------
-- Convenience views
-- ---------------------------------------------------------------------------

-- Activation-level acknowledgement compliance.  The denominator is every
-- alarm event, so unacknowledged alarms are counted as non-compliant rather
-- than being dropped from the population.
CREATE VIEW vw_ack_compliance AS
SELECT
    e.alarm_event_id,
    e.machine_id,
    m.plant_id,
    e.alarm_definition_id,
    e.severity,
    e.event_timestamp,
    a.acknowledgement_id,
    a.ack_timestamp,
    a.response_minutes,
    d.acknowledgement_limit_minutes,
    CASE WHEN a.alarm_event_id IS NULL THEN 1 ELSE 0 END AS is_unacknowledged,
    CASE
        WHEN a.alarm_event_id IS NOT NULL
         AND a.response_minutes <= d.acknowledgement_limit_minutes
        THEN 1 ELSE 0
    END AS is_on_time,
    CASE
        WHEN a.alarm_event_id IS NOT NULL
         AND a.response_minutes > d.acknowledgement_limit_minutes
        THEN 1 ELSE 0
    END AS is_late
FROM alarm_events AS e
LEFT JOIN acknowledgements AS a
       ON a.alarm_event_id = e.alarm_event_id
JOIN machines AS m
       ON m.machine_id = e.machine_id
JOIN alarm_definitions AS d
       ON d.alarm_definition_id = e.alarm_definition_id;

CREATE VIEW vw_open_incidents AS
SELECT *
FROM incidents
WHERE status IN ('OPEN', 'INVESTIGATING');

CREATE VIEW vw_action_pipeline AS
SELECT
    status,
    verification_status,
    effectiveness_status,
    COUNT(*) AS actions
FROM corrective_actions
GROUP BY status, verification_status, effectiveness_status;
