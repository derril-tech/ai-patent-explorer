AI Patent Explorer — semantic search across patents with clause comparison + novelty scoring 

 

1) Product Description & Presentation 

One-liner 

“Find the most relevant prior art in seconds, align it to claim clauses, and quantify novelty—with traceable evidence and exportable claim charts.” 

What it produces 

Semantic prior-art search with hybrid retrieval (keyword + dense) across global patent corpora. 

Clause-level comparison: aligns each claim clause to matching passages in prior art (color-coded overlaps/gaps). 

Novelty/obviousness scoring per claim & clause with confidence bands and rationale. 

Auto claim charts (102/103-style) citing passages, figures, and claim language. 

Portfolio & family views: legal status timeline, priority chain, citation graph analytics. 

Exports: DOCX/CSV/PDF claim charts, JSON bundle of searches/comparisons/scores. 

Scope/Safety 

Research support, not legal advice. All scores carry methods & evidence; final judgment left to practitioners. 

Transparent retrieval & scoring (why-picked evidence, weights, thresholds). 

Read-only ingestion; optional on-premise deployment for confidential drafting. 

 

2) Target User 

Patent attorneys & agents drafting, prosecuting, or litigating. 

IP analysts performing novelty, FTO, or landscape studies. 

R&D leads benchmarking novelty of internal disclosures. 

VC/Corp Dev assessing IP around investments/M&A. 

 

3) Features & Functionalities (Extensive) 

Ingestion & Connectors 

Sources: USPTO (XML/ST.36, Grants & Apps), EPO OPS/Espacenet, WIPO PATENTSCOPE, Google Patents Public Datasets (BigQuery), national offices (JPO/KIPO/CNIPA) where allowed. 

Artifacts: full text, claims, abstracts, descriptions, images, citations, CPC/IPC, legal events. 

Normalization: family resolution (DOCDB/INPADOC ids), priority mapping, assignee normalization, inventor entities, date harmonization, language tags. 

Versioning & dedup: hash per publication; retain latest corrected texts; OCR fallback for image-only. 

Enrichment 

Structure extraction: split claims (independent/dependent), clause segmentation (means-plus-function aware), sectionizer (Field, Background, Summary, Description, Examples). 

NER & Ontologies: chemicals, materials, devices, parameters, units; CPC/IPC rollups. 

Unit parsing with UCUM; value normalization (ranges, tolerances). 

Citation network: forward/backward graph, centrality metrics, age/decay features. 

Retrieval (RAG for Patents) 

Hybrid search: BM25/DFR keyword + dense embeddings (HNSW) + reranking (Cross-encoder). 

Field boosts (claims > abstract > description); date filters by priority date; CPC/IPC filters. 

Table/figure-aware passages: link claim terms to figure captions & numbered elements. 

Query planner: generates synonyms and expansion seeds from CPC definitions and spec language. 

Clause Comparison 

Alignment: token/phrase alignment (Monge-Elkan or soft-TF-IDF) + semantic DP (Smith-Waterman on embedding sims). 

Outputs: Overlap (green), Paraphrase (blue), Gap/New matter (red), Ambiguous (yellow). 

Explain: show matched text spans, similarity score, synonym substitutions, and figures referenced. 

Novelty & Obviousness Scoring 

Per-clause novelty: 1 - max_similarity_to_prior_art, adjusted by priority date & term rarity. 

Claim-level: weighted aggregate (independent weight > dependents; functional vs structural terms). 

Obviousness heuristic (103): multi-doc composition penalty + motivation-to-combine signals (co-citation, topic coherence). 

Confidence: bands from retrieval stability, alignment variance, and corpus coverage. 

Calibration: percentile within CPC class & decade (novelty band). 

Views & Reporting 

Search workspace: left (results), center (prior art passage), right (active claim with clause highlights). 

Claim charts: side-by-side clause ↔ evidence cells; one-click export. 

Portfolio dashboards: family tree, legal status, citation heat, novelty trend vs art. 

Diff views: compare draft revisions and watch novelty deltas. 

Rules & Automations 

Alerts for new prior art in tracked CPC ranges. 

Auto-generate initial claim chart for top-k references. 

Weekly digest per project with new references and updated scores. 

Collaboration & Governance 

Workspaces (Owner/Admin/Member/Viewer); project folders. 

Read-only share links for claim charts (expiring tokens). 

Full audit log of searches, filters, exports, and edits. 

 

4) Backend Architecture (Extremely Detailed & Deployment-Ready) 

4.1 Topology 

Frontend/BFF: Next.js 14 (Vercel). Server Actions for signed uploads & exports; SSR for heavy viewers; ISR for share links. 

API Gateway: NestJS (Node 20) — REST /v1 (OpenAPI 3.1), Zod validation, Problem+JSON, RBAC (Casbin), RLS, Idempotency-Key, Request-ID (ULID). 

Workers (Python 3.11 + FastAPI control) 

patent-ingest (XML/PDF parse, OCR) 

normalize-worker (entities, families, units) 

embed-worker (text/claim/figure embeddings) 

retrieve-worker (hybrid search, rerank) 

align-worker (clause alignment) 

novelty-worker (scoring & calibration) 

chart-worker (claim chart build, DOCX/PDF) 

graph-worker (citation graph metrics) 

Event bus/queues: NATS (patent.ingest, patent.normalize, index.upsert, search.run, align.run, novelty.score, chart.make, graph.update) + Redis Streams; Celery/RQ orchestration. 

Datastores: 

Postgres 16 + pgvector (embeddings & metadata) 

OpenSearch/Elasticsearch (keyword & aggregations) 

S3/R2 (raw XML/PDF, exports) 

Redis (cache/session) 

Optional: Neo4j (citation/family graph), ClickHouse (analytics) 

Observability: OpenTelemetry traces/metrics/logs; Prometheus/Grafana; Sentry. 

Secrets: Cloud KMS; source API keys per connector; per-workspace encryption. 

4.2 Data Model (Postgres + pgvector) 

-- Tenancy 
CREATE TABLE orgs (id UUID PRIMARY KEY, name TEXT, plan TEXT DEFAULT 'free', created_at TIMESTAMPTZ DEFAULT now()); 
CREATE TABLE users (id UUID PRIMARY KEY, org_id UUID REFERENCES orgs(id) ON DELETE CASCADE, 
  email CITEXT UNIQUE NOT NULL, name TEXT, role TEXT DEFAULT 'member', tz TEXT, created_at TIMESTAMPTZ DEFAULT now()); 
CREATE TABLE workspaces (id UUID PRIMARY KEY, org_id UUID, name TEXT, created_by UUID, created_at TIMESTAMPTZ DEFAULT now()); 
CREATE TABLE memberships (user_id UUID, workspace_id UUID, role TEXT CHECK (role IN ('owner','admin','member','viewer')), 
  PRIMARY KEY(user_id, workspace_id)); 
 
-- Patents 
CREATE TABLE patents ( 
  id UUID PRIMARY KEY, workspace_id UUID, pub_number TEXT, kind TEXT, country TEXT, pub_date DATE, 
  app_number TEXT, prio_date DATE, family_id TEXT, title TEXT, abstract TEXT, assignee TEXT[], 
  inventors TEXT[], cpc TEXT[], ipc TEXT[], lang TEXT, s3_xml TEXT, s3_pdf TEXT, status TEXT, meta JSONB 
); 
 
-- Claims & Clauses 
CREATE TABLE claims (id UUID PRIMARY KEY, patent_id UUID, claim_num INT, is_independent BOOLEAN, text TEXT, embedding VECTOR(1536)); 
CREATE TABLE clauses (id UUID PRIMARY KEY, claim_id UUID, idx INT, text TEXT, type TEXT, embedding VECTOR(1536)); 
 
-- Passages (retrieval units) 
CREATE TABLE passages (id UUID PRIMARY KEY, patent_id UUID, section TEXT, start_pos INT, end_pos INT, 
  text TEXT, embedding VECTOR(1536), score NUMERIC, meta JSONB); 
CREATE INDEX ON passages USING hnsw (embedding vector_cosine_ops); 
 
-- Alignments & Novelty 
CREATE TABLE alignments (id UUID PRIMARY KEY, clause_id UUID, prior_patent_id UUID, passage_id UUID, 
  sim NUMERIC, overlap JSONB, explanation TEXT); 
CREATE TABLE novelty_scores (id UUID PRIMARY KEY, claim_id UUID, novelty NUMERIC, obviousness NUMERIC, 
  confidence NUMERIC, factors JSONB, created_at TIMESTAMPTZ DEFAULT now()); 
 
-- Searches & Charts 
CREATE TABLE search_sessions (id UUID PRIMARY KEY, workspace_id UUID, query TEXT, filters JSONB, created_by UUID, created_at TIMESTAMPTZ DEFAULT now()); 
CREATE TABLE claim_charts (id UUID PRIMARY KEY, workspace_id UUID, claim_id UUID, refs UUID[], s3_docx TEXT, s3_pdf TEXT, meta JSONB); 
 
-- Graph 
CREATE TABLE citations (id UUID PRIMARY KEY, from_patent TEXT, to_patent TEXT, relation TEXT, meta JSONB); 
 
-- Audit 
CREATE TABLE audit_log (id BIGSERIAL PRIMARY KEY, org_id UUID, user_id UUID, action TEXT, target TEXT, meta JSONB, created_at TIMESTAMPTZ DEFAULT now()); 
  

Invariants 

RLS by workspace_id; answers/charts require cited passages. 

Each clause has ≥1 embedding; novelty recomputed when alignments change. 

Family consistency: one family_id across jurisdictions; time-ordered priority chain. 

4.3 API Surface (REST /v1, OpenAPI) 

Auth/Users 

POST /auth/login, POST /auth/refresh, GET /me, GET /usage 

Corpus/Patents 

POST /patents/ingest (bulk or single; signed upload or source sync) 

GET /patents/:id, GET /patents?query&cpc&from&to 

GET /patents/:id/claims, GET /patents/:id/passages?section=claims|desc 

Search & Compare 

POST /search {query, filters, k, fieldBoosts} → results with hybrid scores 

POST /compare {patent_id, claim_num, refs:[pub_number...]} → alignments 

POST /novelty {patent_id, claim_num} → novelty/obviousness + confidence 

Charts & Exports 

POST /charts/claim {patent_id, claim_num, refs} → DOCX/PDF 

POST /exports/bundle {workspace_id, session_id} → JSON bundle 

Conventions 

Idempotency-Key; cursor pagination; Problem+JSON errors; SSE for long-running align/novelty jobs. 

4.4 Pipelines & Workers 

Ingest → parse XML/PDF, OCR if needed → normalize entities → sectionize → claims/clauses → passages. 

Index → embed claims/clauses/passages → upsert pgvector; keyword index (OpenSearch). 

Search → hybrid retrieve + rerank → explain features & scores. 

Align → per-clause semantic alignment to passages; produce overlap/gap maps. 

Score → novelty/obviousness with calibration; store confidence & factors. 

Chart → build claim chart artifacts (DOCX/PDF) → upload S3 → signed URL. 

4.5 Realtime 

WebSockets: ws:workspace:{id}:pipeline (ingest/index/align/score progress). 

SSE: streaming search results/reranks for interactive refinement. 

4.6 Caching & Performance 

Redis caches: query → top-k IDs; alignment memoization per clause/ref pair. 

Pre-compute nearest neighbors for popular CPC classes. 

HNSW + ANN params tuned per section (claims tighter, desc looser). 

4.7 Observability 

OTel spans: xml.parse, embed.upsert, search.hybrid, align.run, novelty.score, chart.render. 

Metrics: parse latency, ANN recall@k, alignment precision audits, score stability, export p95. 

4.8 Security & Compliance 

TLS/HSTS/CSP; signed URLs; per-workspace encryption; KMS-wrapped secrets. 

Audit trail; DSR endpoints; export/delete APIs. 

On-prem option; configurable retention windows; role-based access to sensitive corpora. 

“Not legal advice” banner + method card on every score. 

 

5) Frontend Architecture (React 18 + Next.js 14) 

5.1 Tech Choices 

UI: PrimeReact + Tailwind (DataTable, Tree, Dialog, Splitter, FileUpload). 

Charts: Recharts for analytics; server-rendered SVGs for charts in exports. 

State/Data: TanStack Query; Zustand for panel/UI state; URL-synced filters. 

Realtime: WS + SSE clients. 

i18n/A11y: next-intl; keyboard-first; ARIA for diff/align tables. 

5.2 App Structure 

/app 
  /(marketing)/page.tsx 
  /(auth)/sign-in/page.tsx 
  /(app)/search/page.tsx 
  /(app)/patent/[id]/page.tsx 
  /(app)/compare/page.tsx 
  /(app)/charts/page.tsx 
  /(app)/portfolio/page.tsx 
  /(app)/reports/page.tsx 
  /(app)/settings/page.tsx 
/components 
  SearchBar/*            // Query + filters (CPC/date/jurisdiction) 
  ResultsList/*          // Hybrid scores, facets, quick-add to compare 
  ClaimViewer/*          // Claims with clause segmentation & highlights 
  AlignmentTable/*       // Clause ↔ passage matches with color legend 
  NoveltyCard/*          // Score, band, confidence, factors 
  ChartBuilder/*         // Claim chart editor/export 
  GraphView/*            // Citation/family graph 
  UploadWizard/*         // Bulk XML/PDF 
/lib 
  api-client.ts 
  sse-client.ts 
  zod-schemas.ts 
  rbac.ts 
/store 
  useSearchStore.ts 
  useCompareStore.ts 
  usePortfolioStore.ts 
  

5.3 Key Pages & UX Flows 

Search: enter query → live hybrid results with facets → preview passages → pin refs to comparison. 

Compare: pick patent & claim → see clause list → each clause shows best-matching passages across refs with overlap/gap coloring. 

Novelty: run scoring → view explanation (nearest match table, rarity weights, date effects) → confidence band. 

Charts: build/export DOCX/PDF claim charts; template styles (litigation, prosecution, internal). 

Portfolio: family timeline, legal status, citation heatmap; track alerts. 

5.4 Component Breakdown (Selected) 

AlignmentTable/Row.tsx 

 Props: { clause, candidates[] } — renders top matches with similarity, highlights, figure refs; toggle paraphrase/overlap/gap filters. 

NoveltyCard/Explain.tsx 

 Props: { score, factors } — shows contribution breakdown (clause rarity, age, composition penalty) + confidence. 

GraphView/Citation.tsx 

 Props: { patentId } — citation network, centrality metrics, filter by year/CPC. 

5.5 Data Fetching & Caching 

Server components for heavy read pages; client queries for live search and alignment. 

Prefetch sequence: patent → claims → clauses → passages → alignments. 

5.6 Validation & Error Handling 

Zod schemas for filters and query; inline Problem+JSON renderer with remediation (e.g., filter conflicts). 

Guard: scoring disabled until ≥1 prior art reference aligned. 

5.7 Accessibility & i18n 

Keyboard navigation across results/clauses; high-contrast mode; tooltips with ARIA labels; localized dates & numbers. 

 

6) SDKs & Integration Contracts 

Search 

POST /v1/search 
{ 
  "query": "lithium-ion electrolyte additive for SEI stability", 
  "filters": {"cpc":["H01M 10/052"], "from":"2015-01-01", "to":"2025-08-28", "jurisdiction":["US","EP"]}, 
  "k": 50 
} 
  

Compare a claim against references 

POST /v1/compare 
{ 
  "patent_id": "UUID", 
  "claim_num": 1, 
  "refs": ["US2019xxxxA1","EP3456xxxA1"] 
} 
  

Compute novelty 

POST /v1/novelty 
{ "patent_id": "UUID", "claim_num": 1 } 
  

Generate claim chart 

POST /v1/charts/claim 
{ "patent_id":"UUID", "claim_num":1, "refs":["US2019...","WO2020..."], "template":"prosecution" } 
  

Bundle export 

POST /v1/exports/bundle 
{ "workspace_id":"UUID", "session_id":"UUID" } 
  

JSON bundle keys: patents[], claims[], clauses[], passages[], alignments[], novelty_scores[], charts[], citations[]. 

 

7) DevOps & Deployment 

FE: Vercel (Next.js). 

APIs/Workers: Render/Fly/GKE; separate pools for ingest/index/search/align/score/chart. 

DB: Managed Postgres + pgvector; PITR; read replicas for search. 

Search: Managed OpenSearch/Elasticsearch with snapshots. 

Cache/Bus: Redis + NATS; DLQ with exponential backoff/jitter. 

Storage: S3/R2 for artifacts & exports. 

CI/CD: GitHub Actions (lint/typecheck/unit/integration, Docker, scan, sign, deploy); blue/green; migration approvals. 

IaC: Terraform modules for DB/Search/Redis/NATS/buckets/CDN/secrets/DNS. 

Envs: dev/staging/prod; region pinning; error budgets & paging. 

Operational SLOs 

Ingest normalize (single grant) < 6 s p95. 

Top-20 search results < 1.2 s p95. 

Clause alignment (indep. claim vs 5 refs) < 3.5 s p95. 

Claim chart render < 5 s p95. 

 

8) Testing 

Unit: clause segmentation accuracy; unit parsing; CPC rollups; embedding generation. 

Retrieval: TREC-style gold sets; recall@k, MRR; ablations (keyword vs hybrid vs rerank). 

Alignment: human-labeled overlap/gap sets; precision/recall; error taxonomy. 

Novelty: calibration curves; stability across ref subsets; time-shift tests. 

Integration: ingest → index → search → compare → score → chart. 

E2E (Playwright): query → pin refs → align → score → export chart. 

Load: concurrent searches; burst alignment jobs. 

Chaos: search node loss, ANN index rebuild, OCR fallback; ensure retries/backoff. 

Security: RLS coverage; signed URL scope; audit completeness. 

 

9) Success Criteria 

Product KPIs 

Practitioner acceptance: ≥ 80% of top-3 results deemed relevant in pilot tests. 

Alignment usefulness: ≥ 75% of clauses have at least one “usable” prior art passage. 

Novelty calibration: Brier score ≤ 0.18 on blinded benchmarks. 

Time-to-chart: median < 15 min from query to export. 

Engineering SLOs 

Pipeline success ≥ 99%; search error rate < 0.5%; p95 latencies within targets. 

 

10) Visual/Logical Flows 

A) Ingest & Normalize 

 Fetch/Upload → parse XML/PDF → entity & family normalization → claims/clauses → passages → indexes (keyword + vector). 

B) Search & Filter 

 User query + CPC/date filters → hybrid retrieve → rerank → preview passages → pin references. 

C) Clause Comparison 

 Select patent & claim → per-clause alignment to pinned refs → overlap/paraphrase/gap map → rationale. 

D) Novelty & Chart 

 Compute novelty/obviousness with confidence → inspect factor breakdown → generate DOCX/PDF claim chart → share/export. 

 

 