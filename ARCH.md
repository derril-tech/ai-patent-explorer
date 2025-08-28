# AI Patent Explorer — Architecture (V1)

## 1) System Overview
**Frontend/BFF:** Next.js 14 (Vercel).  
**API Gateway:** NestJS (Node 20) REST /v1 with OpenAPI 3.1, Zod validation, Problem+JSON, Casbin RBAC, Idempotency-Key + Request-ID.  
**Workers (Python 3.11 + FastAPI control):**
- patent-ingest (XML/PDF parsing, OCR)
- normalize-worker (entities, families, units)
- embed-worker (embeddings for text/claims/figures)
- retrieve-worker (hybrid search + rerank)
- align-worker (clause alignment)
- novelty-worker (scoring & calibration)
- chart-worker (DOCX/PDF claim charts)
- graph-worker (citation metrics)

**Event Bus:** NATS (`patent.ingest`, `patent.normalize`, `index.upsert`, `search.run`, `align.run`, `novelty.score`, `chart.make`, `graph.update`) + Redis Streams DLQ.  
**Datastores:** Postgres 16 + pgvector (embeddings/metadata), OpenSearch (keyword), S3/R2 (artifacts/exports), Redis (cache/session), optional Neo4j (graphs), ClickHouse (analytics).  
**Observability:** OTel + Prometheus/Grafana; Sentry.  
**Security:** TLS/HSTS/CSP, Cloud KMS, per-workspace encryption, RLS in Postgres; audit log.  

## 2) Data Model (summary)
- **Tenancy:** orgs, users, workspaces, memberships (RLS by workspace_id).  
- **Patents:** `patents` table: pub_number, app_number, prio_date, family_id, title, abstract, assignee[], inventors[], cpc[], ipc[], lang, s3_xml/pdf.  
- **Claims & Clauses:** `claims` (is_independent, embedding), `clauses` (idx, type, embedding).  
- **Passages:** retrieval units; HNSW index on embedding.  
- **Alignments & Novelty:** per clause alignment to prior art passages; novelty_scores per claim.  
- **Search & Charts:** search_sessions, claim_charts (s3_docx/pdf).  
- **Graph:** citations (from_patent → to_patent).  
- **Audit:** audit_log.  

**Invariants**
- RLS enforced; each clause has ≥1 embedding.  
- Novelty recomputed when alignments change.  
- Family consistency (priority chain).  
- Exports reproducible; evidence always cited.

## 3) Key Flows

### 3.1 Ingest & Normalize
- Fetch/upload XML/PDF → patent-ingest worker parses; OCR fallback.  
- normalize-worker resolves families, assignees, inventors, units.  
- Claims segmented into clauses; passages extracted.  
- Embeddings computed (embed-worker); indexes updated (pgvector + OpenSearch).

### 3.2 Search & Retrieve
- API `POST /search {query,filters}` → retrieve-worker does BM25 + dense HNSW → rerank (cross-encoder).  
- Facets: CPC, dates, jurisdictions.  
- Evidence scored & returned with why-picked info.

### 3.3 Clause Comparison
- API `POST /compare` → align-worker aligns each clause to passages (soft-TFIDF + semantic DP).  
- Outputs overlap/gap/paraphrase/ambiguous with explanations.  
- UI highlights color-coded matches.

### 3.4 Novelty & Obviousness
- novelty-worker computes novelty per clause & claim, adjusted by rarity + priority date.  
- Obviousness heuristic across multiple docs (composition penalty + co-citation).  
- Confidence from stability of retrieval + alignment.  
- API `POST /novelty` returns novelty/obviousness + factors.

### 3.5 Charts & Exports
- chart-worker builds DOCX/PDF claim charts.  
- API `POST /charts/claim` returns signed URL; `POST /exports/bundle` builds JSON bundle.  
- Bundle includes patents, claims, clauses, passages, alignments, novelty_scores, charts, citations.

### 3.6 Portfolio & Graphs
- graph-worker builds family/citation graph metrics.  
- UI portfolio shows family timeline, legal status, novelty trends, citation heatmap.

## 4) API Surface (REST /v1)
- **Auth:** login, refresh, me, usage.  
- **Patents:** ingest, list/query, detail, claims, passages.  
- **Search:** `POST /search`.  
- **Compare:** `POST /compare`.  
- **Novelty:** `POST /novelty`.  
- **Charts:** `POST /charts/claim`.  
- **Exports:** `POST /exports/bundle`.  

Conventions: Idempotency-Key; cursor pagination; Problem+JSON; SSE for align/novelty jobs.

## 5) Observability & SLOs
- OTel spans: xml.parse, embed.upsert, search.hybrid, align.run, novelty.score, chart.render.  
- Metrics: ingest latency, recall@k, alignment precision, score stability, chart export p95.  
- SLOs: ingest <6s p95, search <1.2s p95, alignment <3.5s p95, chart <5s p95, pipeline success ≥99%.

## 6) Security & Governance
- RLS by workspace_id; RBAC (Casbin).  
- Signed URLs; per-workspace encryption keys.  
- Audit logs for searches, alignments, exports.  
- DSR endpoints; retention windows; on-prem deployment option.  
- “Not legal advice” disclaimers in UI & exports.

## 7) Performance & Scaling
- pgvector HNSW tuned per section (claims tighter thresholds).  
- Redis caches for queries, alignment memoization.  
- Precompute NN for popular CPC classes.  
- Horizontal scaling of workers; DLQ for failures.  
- OpenSearch shards tuned; replicas for read-heavy workloads.

## 8) Threat Model (summary)
- **Abuse:** Oversized XML/PDFs → size limits + streaming parse.  
- **Poisoning:** Malformed docs → sandbox parse, schema validation.  
- **Exfiltration:** strict RLS + signed URLs.  
- **Prompt injection:** limited since no generative free-text, but ensure retrieval-only + explanations.  

## 9) Accessibility & i18n
- ARIA roles for tables/graphs.  
- High-contrast mode; keyboard nav.  
- next-intl for localization of numbers/dates.