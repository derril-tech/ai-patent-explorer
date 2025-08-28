# AI Patent Explorer — Delivery Plan (v0.1)
_Date: 2025-08-28 • Owner: PM/Tech Lead • Status: Draft_

## 0) One-liner
**“Find the most relevant prior art in seconds, align it to claim clauses, and quantify novelty—with traceable evidence and exportable claim charts.”**

## 1) Goals & Non-Goals (V1)
**Goals**
- Semantic + keyword prior-art search with hybrid retrieval.
- Clause-level comparison (alignment maps with overlap/gap/paraphrase/ambiguous).
- Novelty/obviousness scoring per claim and clause with rationale + confidence.
- Auto claim charts (DOCX/PDF/CSV/JSON bundles).
- Portfolio/family views with citation graph analytics and legal status timeline.
- Transparent retrieval & scoring; traceable evidence.

**Non-Goals**
- Legal judgment; system is **research support**, not legal advice.
- Drafting automation (claims/specification generation).

## 2) Scope
**In-scope**
- Ingest patents from USPTO/EPO/WIPO/Google datasets + national offices (where permitted).
- Normalize families, assignees, inventors, units; enrich with NER + CPC/IPC rollups.
- Index: keyword (OpenSearch) + dense embeddings (pgvector HNSW).
- RAG-style retrieval with rerank; clause alignment; novelty scoring.
- Claim charts + exports (DOCX, PDF, JSON).
- Portfolio dashboards (family/citation graphs).

**Out-of-scope**
- Litigation/prosecution workflows (filings, dockets, office actions).
- Non-patent literature (NPL); reserved for later.

## 3) Workstreams & Success Criteria
1. **Ingest & Normalize**  
   ✅ Parse XML/PDF; normalize entities/families; clauses segmented.  
2. **Search & Retrieval**  
   ✅ Hybrid retrieval (keyword + dense); reranking; top-20 results < 1.2s p95.  
3. **Clause Comparison**  
   ✅ Alignment maps with overlaps/gaps; explanations; precision/recall ≥ 0.75 vs human labels.  
4. **Novelty Scoring**  
   ✅ Clause & claim-level scores; calibration within CPC class; Brier score ≤ 0.18.  
5. **Claim Charts & Exports**  
   ✅ Generate DOCX/PDF in < 5s p95; charts accepted by ≥80% practitioners in pilot.  
6. **Portfolio & Graph**  
   ✅ Family tree; citation graph; novelty trends; alerts.  
7. **Observability & Governance**  
   ✅ Full OTel traces; SLO dashboards; audit log; RLS + signed URLs.

## 4) Milestones & Timeline (~12 weeks)
- **Phase 1 (Weeks 1–2)**: Infra setup, DB schema, connectors, basic ingest.  
- **Phase 2 (Weeks 3–4)**: Indexing pipelines (pgvector + OpenSearch), normalization.  
- **Phase 3 (Weeks 5–6)**: Retrieval & rerank; frontend search workspace.  
- **Phase 4 (Weeks 7–9)**: Clause alignment, novelty scoring, claim charts.  
- **Phase 5 (Weeks 10–12)**: Portfolio graphs, exports, QA, hardening, beta rollout.

## 5) Deliverables
- Running environments: dev/staging/prod.
- OpenAPI 3.1 spec (/v1); TypeScript SDK; Postman collection.
- Migration files; pilot benchmark datasets (gold TREC sets, human-labeled alignments).
- Playwright E2E tests.
- SRE dashboards, runbooks.

## 6) Risks & Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| Source API rate limits | High | Batch sync; retry w/backoff; caching; use public datasets |
| OCR fallback accuracy | Medium | Dual pipeline (Tesseract + commercial OCR); confidence flag |
| Alignment false positives | High | Ensemble aligners (soft-TFIDF + embedding DP); human eval loop |
| Latency spikes in OpenSearch | Medium | Caching; warm queries; tuned shards; replicas |
| Legal disclaimers ignored | Medium | UI banners; evidence cards; export disclaimers |

## 7) Acceptance Criteria
- Top-3 retrieval relevance ≥80% (practitioner judged).  
- Alignment recall ≥75% usable matches.  
- Novelty calibration within Brier ≤0.18.  
- Time-to-chart median <15 minutes.  
- p95 latencies within targets.  

## 8) Rollout
- Pilot with internal counsel + select firms.  
- Beta → feature-flag novelty → GA.  
- On-prem option (Docker/K8s) for confidential users.