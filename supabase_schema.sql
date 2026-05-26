CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    login_id TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT UNIQUE NOT NULL,
    encrypted_value TEXT NOT NULL,
    updated_by TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE machines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL
);

INSERT INTO machines (name)
VALUES ('Elekta'), ('Tomo');

CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_number TEXT UNIQUE NOT NULL,
    encrypted_name TEXT NOT NULL,
    encrypted_diagnosis TEXT,
    simulation_date TIMESTAMP,
    treatment_started BOOLEAN DEFAULT FALSE,
    treatment_start_date TIMESTAMP,
    contouring_done BOOLEAN DEFAULT FALSE,
    planning_done BOOLEAN DEFAULT FALSE,
    machine_id UUID REFERENCES machines(id)
);
