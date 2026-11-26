CREATE TYPE data_mode AS ENUM ('SIMULATED','REAL');
CREATE TYPE claim_status AS ENUM ('VERIFIED','UNVERIFIED','PROHIBITED','NEEDS_REVIEW');
CREATE TYPE approval_status AS ENUM ('PENDING','APPROVED','REJECTED','NEEDS_CHANGES','BLOCKED');

CREATE TABLE workspace (
  workspace_id UUID PRIMARY KEY,
  owner_id TEXT NOT NULL,
  name TEXT NOT NULL,
  market CHAR(2) NOT NULL DEFAULT 'US',
  vertical TEXT NOT NULL DEFAULT 'beauty_skincare',
  data_mode data_mode NOT NULL DEFAULT 'SIMULATED',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE product (
  product_id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id),
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  currency CHAR(3) NOT NULL DEFAULT 'USD',
  price_cents BIGINT CHECK (price_cents IS NULL OR price_cents >= 0),
  facts JSONB NOT NULL DEFAULT '{}'::jsonb,
  landing_page_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE claim (
  claim_id UUID PRIMARY KEY,
  product_id UUID NOT NULL REFERENCES product(product_id),
  claim_text TEXT NOT NULL,
  claim_type TEXT NOT NULL,
  status claim_status NOT NULL DEFAULT 'UNVERIFIED',
  evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  risk_level TEXT NOT NULL DEFAULT 'MEDIUM',
  reviewer_id TEXT,
  reviewed_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE creative (
  creative_id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id),
  product_id UUID NOT NULL REFERENCES product(product_id),
  concept_name TEXT NOT NULL,
  angle TEXT,
  hook TEXT,
  narrative TEXT,
  cta TEXT,
  language TEXT NOT NULL DEFAULT 'en-US',
  format TEXT,
  hypothesis TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE asset_version (
  asset_version_id UUID PRIMARY KEY,
  creative_id UUID NOT NULL REFERENCES creative(creative_id),
  version_no INTEGER NOT NULL,
  asset_uri TEXT,
  asset_type TEXT NOT NULL,
  file_hash TEXT,
  prompt_text TEXT,
  model_provider TEXT,
  model_name TEXT,
  source_manifest JSONB NOT NULL DEFAULT '{}'::jsonb,
  approval_status approval_status NOT NULL DEFAULT 'PENDING',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (creative_id, version_no)
);

CREATE TABLE experiment (
  experiment_id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id),
  name TEXT NOT NULL,
  hypothesis TEXT NOT NULL,
  channel TEXT NOT NULL,
  data_mode data_mode NOT NULL,
  attribution_window TEXT,
  timezone TEXT NOT NULL DEFAULT 'America/Los_Angeles',
  budget_cap_cents BIGINT CHECK (budget_cap_cents IS NULL OR budget_cap_cents >= 0),
  currency CHAR(3) NOT NULL DEFAULT 'USD',
  preregistration JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE metric_daily (
  metric_daily_id UUID PRIMARY KEY,
  experiment_id UUID NOT NULL REFERENCES experiment(experiment_id),
  variant_id UUID NOT NULL,
  event_date DATE NOT NULL,
  source_mode data_mode NOT NULL,
  source_name TEXT NOT NULL,
  currency CHAR(3) NOT NULL DEFAULT 'USD',
  impressions BIGINT NOT NULL DEFAULT 0 CHECK (impressions >= 0),
  clicks BIGINT NOT NULL DEFAULT 0 CHECK (clicks >= 0),
  landing_page_views BIGINT NOT NULL DEFAULT 0 CHECK (landing_page_views >= 0),
  add_to_cart BIGINT NOT NULL DEFAULT 0 CHECK (add_to_cart >= 0),
  purchases BIGINT NOT NULL DEFAULT 0 CHECK (purchases >= 0),
  refunded_orders BIGINT NOT NULL DEFAULT 0 CHECK (refunded_orders >= 0),
  spend_cents BIGINT NOT NULL DEFAULT 0 CHECK (spend_cents >= 0),
  attributed_revenue_cents BIGINT NOT NULL DEFAULT 0 CHECK (attributed_revenue_cents >= 0),
  raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  imported_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE agent_run (
  agent_run_id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id),
  experiment_id UUID REFERENCES experiment(experiment_id),
  agent_name TEXT NOT NULL,
  status TEXT NOT NULL,
  model_provider TEXT,
  model_name TEXT,
  input_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  output_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  tool_trace JSONB NOT NULL DEFAULT '[]'::jsonb,
  error JSONB,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE review_record (
  review_id UUID PRIMARY KEY,
  asset_version_id UUID NOT NULL REFERENCES asset_version(asset_version_id),
  reviewer_id TEXT NOT NULL,
  decision approval_status NOT NULL,
  reason TEXT,
  findings JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
  audit_id BIGSERIAL PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id),
  actor_type TEXT NOT NULL,
  actor_id TEXT,
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  before_state JSONB,
  after_state JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_metric_daily_exp_date ON metric_daily(experiment_id, event_date);
CREATE INDEX idx_creative_workspace ON creative(workspace_id);
CREATE INDEX idx_agent_run_workspace ON agent_run(workspace_id, created_at DESC);
