-- Unified AI Portal Database Schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Platform agents registry
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(20),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

-- CUR reports
CREATE TABLE IF NOT EXISTS cur_reports (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    filename VARCHAR(255) NOT NULL,
    file_content TEXT,
    period_start DATE,
    period_end DATE,
    row_count INTEGER DEFAULT 0,
    file_size BIGINT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'ready',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Alert reports
CREATE TABLE IF NOT EXISTS alert_reports (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    filename VARCHAR(255) NOT NULL,
    file_content TEXT,
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    total_alerts INTEGER DEFAULT 0,
    genuine_count INTEGER DEFAULT 0,
    noise_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'ready',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Shared chat sessions
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    session_id UUID DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Shared chat messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(session_id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    chart_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Shared agent settings
CREATE TABLE IF NOT EXISTS agent_settings (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id) UNIQUE,
    data_source VARCHAR(50) DEFAULT 'file',
    api_key TEXT,
    api_url TEXT,
    webhook_url TEXT,
    webhook_type VARCHAR(50),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Seed default agents
INSERT INTO agents (name, slug, description, icon, status) VALUES
    ('CUR Analyser', 'cur', 'Analyse AWS Cost & Usage Reports with AI-powered insights', '💰', 'active'),
    ('Alert Analyser', 'alerts', 'OpsGenie alert noise detection and signal analysis', '🚨', 'active')
ON CONFLICT (slug) DO NOTHING;

-- Seed default settings
INSERT INTO agent_settings (agent_id, data_source)
SELECT id, 'file' FROM agents WHERE slug IN ('cur', 'alerts')
ON CONFLICT (agent_id) DO NOTHING;
