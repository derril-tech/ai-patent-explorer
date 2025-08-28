-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create database schema for AI Patent Explorer
-- This will be replaced by proper migrations, but provides initial setup

-- Organizations
CREATE TABLE IF NOT EXISTS orgs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workspaces
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(org_id, slug)
);

-- Memberships
CREATE TABLE IF NOT EXISTS memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member', -- owner, admin, member, viewer
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, workspace_id)
);

-- Patents
CREATE TABLE IF NOT EXISTS patents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    pub_number VARCHAR(50) NOT NULL,
    app_number VARCHAR(50),
    prio_date DATE,
    family_id VARCHAR(100),
    title TEXT NOT NULL,
    abstract TEXT,
    assignees JSONB,
    inventors JSONB,
    cpc_codes JSONB,
    ipc_codes JSONB,
    lang VARCHAR(10) DEFAULT 'en',
    s3_xml_path VARCHAR(500),
    s3_pdf_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(workspace_id, pub_number)
);

-- Claims
CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patent_id UUID NOT NULL REFERENCES patents(id) ON DELETE CASCADE,
    claim_number INTEGER NOT NULL,
    is_independent BOOLEAN NOT NULL DEFAULT false,
    text TEXT NOT NULL,
    embedding vector(1536), -- OpenAI embedding dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(patent_id, claim_number)
);

-- Clauses
CREATE TABLE IF NOT EXISTS clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    clause_index INTEGER NOT NULL,
    clause_type VARCHAR(50), -- preamble, element, transition, etc.
    text TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(claim_id, clause_index)
);

-- Passages (for retrieval)
CREATE TABLE IF NOT EXISTS passages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patent_id UUID NOT NULL REFERENCES patents(id) ON DELETE CASCADE,
    passage_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(patent_id, passage_index)
);

-- Alignments
CREATE TABLE IF NOT EXISTS alignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    clause_id UUID NOT NULL REFERENCES clauses(id) ON DELETE CASCADE,
    passage_id UUID NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
    alignment_type VARCHAR(50) NOT NULL, -- overlap, gap, paraphrase, ambiguous
    similarity_score FLOAT NOT NULL,
    explanation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(clause_id, passage_id)
);

-- Novelty Scores
CREATE TABLE IF NOT EXISTS novelty_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    novelty_score FLOAT NOT NULL,
    obviousness_score FLOAT NOT NULL,
    confidence FLOAT NOT NULL,
    factors JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(claim_id)
);

-- Search Sessions
CREATE TABLE IF NOT EXISTS search_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    filters JSONB,
    results JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Claim Charts
CREATE TABLE IF NOT EXISTS claim_charts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patent_id UUID NOT NULL REFERENCES patents(id) ON DELETE CASCADE,
    chart_type VARCHAR(50) NOT NULL, -- claim_chart, novelty_report, etc.
    s3_docx_path VARCHAR(500),
    s3_pdf_path VARCHAR(500),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Citations
CREATE TABLE IF NOT EXISTS citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_patent_id UUID NOT NULL REFERENCES patents(id) ON DELETE CASCADE,
    to_patent_id UUID NOT NULL REFERENCES patents(id) ON DELETE CASCADE,
    citation_type VARCHAR(50), -- forward, backward, family
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(from_patent_id, to_patent_id)
);

-- Audit Log
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_patents_workspace_id ON patents(workspace_id);
CREATE INDEX IF NOT EXISTS idx_patents_family_id ON patents(family_id);
CREATE INDEX IF NOT EXISTS idx_claims_patent_id ON claims(patent_id);
CREATE INDEX IF NOT EXISTS idx_clauses_claim_id ON clauses(claim_id);
CREATE INDEX IF NOT EXISTS idx_passages_patent_id ON passages(patent_id);
CREATE INDEX IF NOT EXISTS idx_alignments_workspace_id ON alignments(workspace_id);
CREATE INDEX IF NOT EXISTS idx_novelty_scores_workspace_id ON novelty_scores(workspace_id);
CREATE INDEX IF NOT EXISTS idx_search_sessions_workspace_id ON search_sessions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_claim_charts_workspace_id ON claim_charts(workspace_id);
CREATE INDEX IF NOT EXISTS idx_citations_from_patent_id ON citations(from_patent_id);
CREATE INDEX IF NOT EXISTS idx_citations_to_patent_id ON citations(to_patent_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_workspace_id ON audit_log(workspace_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);

-- Create vector indexes for similarity search
CREATE INDEX IF NOT EXISTS idx_claims_embedding ON claims USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_clauses_embedding ON clauses USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_passages_embedding ON passages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Row Level Security (RLS) setup
ALTER TABLE patents ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE clauses ENABLE ROW LEVEL SECURITY;
ALTER TABLE passages ENABLE ROW LEVEL SECURITY;
ALTER TABLE alignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE novelty_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE claim_charts ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (basic - will be enhanced later)
CREATE POLICY "Users can view patents in their workspaces" ON patents
    FOR SELECT USING (
        workspace_id IN (
            SELECT workspace_id FROM memberships WHERE user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_patents_updated_at BEFORE UPDATE ON patents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_novelty_scores_updated_at BEFORE UPDATE ON novelty_scores FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
