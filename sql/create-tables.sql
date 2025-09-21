-- LiquidRound Database Schema
-- Multi-Agent M&A and IPO Deal Flow System

-- Deals table - Core deal information
CREATE TABLE IF NOT EXISTS deals (
    id TEXT PRIMARY KEY,
    deal_type TEXT NOT NULL CHECK (deal_type IN ('buyer_ma', 'seller_ma', 'ipo')),
    company_name TEXT,
    industry TEXT,
    sector TEXT,
    deal_size_min INTEGER,
    deal_size_max INTEGER,
    deal_size_currency TEXT DEFAULT 'USD',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed', 'failed', 'cancelled')),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata TEXT -- JSON field for additional data
);

-- Workflows table - Workflow execution tracking
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    deal_id TEXT,
    user_query TEXT NOT NULL,
    workflow_type TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'routing', 'executing', 'completed', 'failed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (deal_id) REFERENCES deals (id)
);

-- Workflow results table - Agent execution results
CREATE TABLE IF NOT EXISTS workflow_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'in_progress', 'success', 'failed')),
    result_data TEXT, -- JSON field
    execution_time REAL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (workflow_id) REFERENCES workflows (id)
);

-- Messages table - Chat conversation history
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (workflow_id) REFERENCES workflows (id)
);

-- Companies table - Target companies and acquisition candidates
CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ticker_symbol TEXT,
    industry TEXT,
    sector TEXT,
    market_cap REAL,
    revenue REAL,
    ebitda REAL,
    employees INTEGER,
    founded_year INTEGER,
    headquarters TEXT,
    website TEXT,
    description TEXT,
    financial_data TEXT, -- JSON field for detailed financials
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Deal targets table - Links deals to target companies
CREATE TABLE IF NOT EXISTS deal_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK (target_type IN ('acquisition_target', 'buyer_candidate', 'competitor', 'comparable')),
    strategic_fit_score REAL CHECK (strategic_fit_score >= 0 AND strategic_fit_score <= 5),
    valuation_low REAL,
    valuation_high REAL,
    valuation_currency TEXT DEFAULT 'USD',
    notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (deal_id) REFERENCES deals (id),
    FOREIGN KEY (company_id) REFERENCES companies (id),
    UNIQUE(deal_id, company_id, target_type)
);

-- Valuations table - Financial valuations and analysis
CREATE TABLE IF NOT EXISTS valuations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    company_id TEXT,
    valuation_method TEXT NOT NULL CHECK (valuation_method IN ('dcf', 'comparable_companies', 'precedent_transactions', 'asset_based')),
    valuation_amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    assumptions TEXT, -- JSON field for valuation assumptions
    confidence_level TEXT CHECK (confidence_level IN ('low', 'medium', 'high')),
    created_by_agent TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (deal_id) REFERENCES deals (id),
    FOREIGN KEY (company_id) REFERENCES companies (id)
);

-- Market data table - Real-time and historical market data
CREATE TABLE IF NOT EXISTS market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('stock_price', 'financial_metrics', 'news', 'analyst_rating')),
    data_value REAL,
    data_text TEXT,
    data_json TEXT, -- JSON field for complex data
    source TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Deal activities table - Audit trail of deal activities
CREATE TABLE IF NOT EXISTS deal_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    description TEXT NOT NULL,
    performed_by TEXT, -- Agent name or user
    metadata TEXT, -- JSON field
    created_at TEXT NOT NULL,
    FOREIGN KEY (deal_id) REFERENCES deals (id)
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_deals_type_status ON deals (deal_type, status);
CREATE INDEX IF NOT EXISTS idx_deals_created_at ON deals (created_at);
CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows (status);
CREATE INDEX IF NOT EXISTS idx_workflows_created_at ON workflows (created_at);
CREATE INDEX IF NOT EXISTS idx_companies_industry ON companies (industry);
CREATE INDEX IF NOT EXISTS idx_companies_market_cap ON companies (market_cap);
CREATE INDEX IF NOT EXISTS idx_deal_targets_deal_id ON deal_targets (deal_id);
CREATE INDEX IF NOT EXISTS idx_deal_targets_strategic_fit ON deal_targets (strategic_fit_score);
CREATE INDEX IF NOT EXISTS idx_valuations_deal_id ON valuations (deal_id);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data (symbol);
CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data (timestamp);

-- Views for common queries
CREATE VIEW IF NOT EXISTS active_deals AS
SELECT 
    d.*,
    COUNT(dt.id) as target_count,
    AVG(dt.strategic_fit_score) as avg_strategic_fit,
    MAX(v.valuation_amount) as max_valuation
FROM deals d
LEFT JOIN deal_targets dt ON d.id = dt.deal_id
LEFT JOIN valuations v ON d.id = v.deal_id
WHERE d.status IN ('pending', 'active')
GROUP BY d.id;

CREATE VIEW IF NOT EXISTS deal_summary AS
SELECT 
    d.id,
    d.deal_type,
    d.company_name,
    d.industry,
    d.status,
    d.created_at,
    COUNT(DISTINCT dt.company_id) as target_companies,
    COUNT(DISTINCT v.id) as valuations_count,
    AVG(dt.strategic_fit_score) as avg_strategic_fit,
    MIN(v.valuation_amount) as min_valuation,
    MAX(v.valuation_amount) as max_valuation
FROM deals d
LEFT JOIN deal_targets dt ON d.id = dt.deal_id
LEFT JOIN valuations v ON d.id = v.deal_id
GROUP BY d.id;
