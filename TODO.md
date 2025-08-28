# AI Patent Explorer — TODO (V1, Phased)

> Owner tags: **[FE]**, **[BE]**, **[MLE]**, **[DE]**, **[SRE]**, **[QA]**, **[PM]**  
> ~5 phases max; tasks grouped logically; no task dropped.

---

## Phase 1: Foundations & Ingest
- [x] [PM][SRE] Monorepo structure (`/frontend`, `/api`, `/workers`, `/infra`, `/docs`).
- [x] [SRE] CI/CD via GitHub Actions: typecheck, lint, test, Docker build, scan, deploy.  
- [x] [SRE] Infra: Postgres 16 + pgvector, OpenSearch, Redis, NATS, S3/R2 buckets.  
- [x] [BE] Apply schema migrations (orgs, users, workspaces, memberships, patents, claims, clauses, passages, alignments, novelty_scores, search_sessions, claim_charts, citations, audit_log).  
- [x] [BE][DE] Patent ingest worker: XML/PDF parsing; OCR fallback; dedup/versioning.  
- [x] [DE] Normalize: family ids, assignees, inventors, dates, units; CPC/IPC rollups.  

---

## Phase 2: Indexing & Retrieval
- [x] [MLE] embed-worker: embeddings for claims, clauses, passages.  
- [x] [MLE][BE] Index to pgvector HNSW + keyword OpenSearch.  
- [x] [MLE] retrieve-worker: hybrid retrieval (BM25 + dense) + reranking (cross-encoder).  
- [x] [MLE] Query planner: synonyms, CPC expansions.  
- [x] [BE] API: `POST /patents/ingest`, `GET /patents`, `GET /patents/:id/claims`, `GET /patents/:id/passages`.  
- [x] [BE] API: `POST /search {query, filters, k}` returning hybrid results.  
- [x] [QA] Retrieval evaluation: recall@k, MRR vs gold TREC sets.

---

**Phase 2 Summary**: Completed indexing and retrieval pipeline with embed-worker (sentence-transformers), retrieve-worker (hybrid BM25+dense), query planner (synonyms+CPC), NestJS API endpoints, and evaluation metrics. All workers use NATS messaging and pgvector for similarity search.

## Phase 3: Clause Alignment & Novelty
- [x] [MLE] align-worker: per-clause alignment (soft-TFIDF + embedding DP).  
- [x] [MLE] Highlight overlaps/gaps/paraphrases with explanations.  
- [x] [MLE] novelty-worker: clause-level novelty = 1 - max_similarity; claim-level weighted aggregate.  
- [x] [MLE] Obviousness scoring: multi-doc penalty + co-citation + topic coherence.  
- [x] [MLE] Calibration by CPC/decade; output bands & confidence.  
- [x] [BE] API: `POST /compare {patent_id, claim_num, refs}`.  
- [x] [BE] API: `POST /novelty {patent_id, claim_num}`.  
- [x] [QA] Alignment/novelty benchmarks: human-labeled overlap/gap; Brier score.

---

**Phase 3 Summary**: Completed clause alignment and novelty analysis pipeline with align-worker (soft-TFIDF + embedding similarity), novelty-worker (clause-level novelty scoring with obviousness analysis), NestJS API endpoints for comparison and novelty calculation, and comprehensive evaluation framework with Brier scores and human-labeled benchmarks.  

---

## Phase 4: Charts, Exports & Portfolio, frontend
- [x] [BE] chart-worker: build DOCX/PDF claim charts.  
- [x] [BE] API: `POST /charts/claim`, `POST /exports/bundle`.  
- [x] [FE] ClaimViewer + AlignmentTable components.  
- [x] [FE] NoveltyCard with explain factors.  
- [x] [FE] ChartBuilder (editor/export).  
- [x] [FE] GraphView: citation/family network.  
- [x] [BE] graph-worker: citation graph metrics (centrality, decay).  
- [x] [QA] Chart export fidelity; portfolio views; citation graph tests.  
### Frontend (Next.js 14)
- [x] [FE] Routes: search, patent detail, compare, charts, portfolio, reports, settings.  
- [x] [FE] State: TanStack Query + Zustand stores; SSE + WS clients.  
- [x] [FE] Guardrails: disable novelty until refs aligned; disclaimers shown.  
- [x] [FE] Accessibility: ARIA for tables/graphs; high-contrast; keyboard nav.  
- [x] [FE] i18n: next-intl; localized numbers/dates.

**Phase 4 Summary**: Completed chart generation worker (DOCX/PDF), export bundle functionality, graph worker for citation analysis (centrality/decay metrics), and comprehensive Next.js frontend with search interface, patent viewer, chart builder, and graph visualization components. All components use modern React patterns with TypeScript and Tailwind CSS.


## Phase 5: ## Observability, Security, Testing
- [x] [SRE] OTel spans (`xml.parse`, `embed.upsert`, `search.hybrid`, `align.run`, `novelty.score`, `chart.render`).  
- [x] [SRE] Prometheus/Grafana dashboards; Sentry error tracking.  
- [x] [SRE] Load/chaos: concurrent searches; ANN rebuild fallback; DLQ runbooks.  
- [x] [BE] RLS enforcement; RBAC (Casbin).  
- [x] [BE] TLS/HSTS/CSP; signed URLs; KMS-wrapped secrets.  
- [x] [BE] Audit log (searches, aligns, scores, exports).  
- [x] [BE] DSR endpoints; configurable retention windows.  
- [x] [PM] Ensure "Not legal advice" banners in UI + exports.  
- [x] [QA] Unit: clause segmentation, unit parsing, CPC rollups.  
- [x] [QA][MLE] Retrieval, alignment, novelty benchmarks.  
- [x] [QA] Integration: ingest → index → search → compare → score → chart.  
- [x] [QA] E2E: query → pin refs → align → score → export chart.  
- [x] [QA] Security tests (RLS, signed URL scope, audit completeness).

**Phase 5 Summary**: Completed comprehensive observability system with OpenTelemetry tracing, Prometheus metrics, and Sentry error tracking. Implemented robust security framework with RBAC, JWT authentication, audit logging, and data protection. Created comprehensive test suite including unit tests, integration tests, and security tests. Added legal disclaimers and compliance features throughout the UI and exports.  
## Definition of Done
- [x] Feature delivered with API spec + tests, FE states (loading/empty/error), evidence of SLOs met, accessibility pass, legal disclaimer present, reproducible exports verified.