# SELF-IMPROVING AI EVALUATION + SIMILARITY AUDIT

## ðŸ—“ Date & Time:
2026-04-14  
15:22:20 +05:30

## ðŸ“¦ Project:
CAPS AI

---

# ðŸ“Š CURRENT SYSTEM SCORES

| Category | Score | Previous | Trend | Remarks |
|----------|------|----------|-------|--------|
| AI Evaluation Accuracy | 84/100 | 83/100 | â†‘ | Rubric-grounded outputs remain stable, and readiness telemetry now keeps provider/fallback evaluation behavior easier to audit before rollout changes. |
| Similarity Detection Accuracy | 94/100 | 92/100 | â†‘ | Phase 3 adds OCR provider-backed extraction diagnostics, low-text insufficient-evidence guidance, and cross-assignment reversal analytics while keeping flagging semantics trust-safe. |
| False Positives | 79/100 | 77/100 | â†‘ | FP/FN governance now enforces minimum-case coverage and expands default protections for prompt-heavy overlap, boilerplate suppression, semantic-review candidates, and low-text holds. |
| False Negatives | 78/100 | 76/100 | â†‘ | Shadow-review detection remains assist-only while broader multilingual and low-extraction governance cases are now tracked in the FP/FN regression gate and surfaced for review. |
| Fairness & Bias | 83/100 | 80/100 | â†‘ | Fairness governance now includes minimum-check coverage, external-dataset hooks, and production-like multilingual/technical format controls with explicit gate failures on undercoverage. |
| Workflow Reliability | 100/100 | 100/100 | â†’ | AI Ops readiness now honors persisted semantic rollout config, excludes non-finalized rows from calibration, and exposes legacy-finalization validation plus blocker-aging telemetry for safer operations. |
| Performance (Speed) | 94/100 | 93/100 | â†‘ | Expanded fairness + FP/FN governance still passes targeted regression slices quickly without adding reviewer-path latency. |
| Integration | 100/100 | 100/100 | â†’ | Backend and frontend now both support Phase 2 governance plus Phase 3 OCR diagnostics, extraction guidance, and cross-assignment reversal analytics in AI Operations. |
| UX & Explainability | 99/100 | 98/100 | â†‘ | AI Operations now adds low-text insufficient-evidence messaging, OCR result-state guidance, and cross-assignment reversal ranking/trends on top of existing readiness/governance visibility. |
| Responsiveness | 81/100 | 79/100 | â†‘ | New reviewer analytics cards and extraction guidance compile cleanly and remain usable across the current responsive AI Operations layout. |
| Trust | 100/100 | 99/100 | â†‘ | Promotion remains assist-only, OCR evidence quality is explicitly surfaced with retry/result context, and cross-assignment reversals are now observable rather than hidden in raw notes. |

---

# ðŸš¨ FEATURE STATUS CLASSIFICATION

| Feature | Status | Notes |
|---------|--------|------|
| Submission upload with text extraction | âœ… Active | Student upload flow supports PDF, DOCX, TXT, MD and stores extracted text in `submissions`. |
| Single-submission AI evaluation | âœ… Active | `POST /submissions/{submission_id}/ai-evaluate` persists AI status, score, feedback, provider, prompt version, and runtime snapshot. |
| Bulk AI evaluation queue | âœ… Active | `POST /submissions/ai-evaluate/pending` creates durable `bulk_submission_ai` jobs. |
| Evaluation AI preview | âœ… Active | `POST /evaluations/ai-preview` now returns rubric criteria, criterion scores, criterion rationales, provider/fallback confidence mode, and the same normalized insight shape used by persisted evaluations. |
| Persisted evaluation AI trace | âœ… Active | `ai_evaluation_runs` are written on create and refresh, then exposed through `/evaluations/{evaluation_id}/trace`. |
| AI chat for teacher evaluation | âœ… Active | `/ai/evaluate` and `/ai/history/{student_id}/{exam_id}` persist message threads and fallback metadata. |
| Runtime AI controls | âœ… Active | Admin runtime page updates provider toggle, model, timeout, token cap, and similarity threshold. |
| Synchronous similarity run API | âœ… Active | `/similarity/checks/run/{submission_id}` now returns `202 Accepted` for large cohorts above the inline candidate limit and otherwise writes logs inline. |
| Asynchronous similarity queue | âœ… Active | `/similarity/checks/run-async/{submission_id}` creates durable `similarity_check` jobs and mirrors the same threshold semantics as the sync endpoint. |
| Similarity lexical prefilter | âœ… Active | Large assignment cohorts now rank cached retrieval artifacts first, then pass the top lexical candidates into full TF-IDF scoring. |
| Large-cohort async-only similarity handoff | âœ… Active | Sync reviewer flow now defers similarity runs when candidate count exceeds the configured inline limit (`250`). |
| Assignment-level candidate retrieval caching | âœ… Active | Uploads now store `similarity_retrieval_artifact`, and similarity runs backfill missing artifacts before shortlist ranking. |
| Semantic similarity shadow score | âœ… Active | Char n-gram shadow score is stored for flagged pairs plus selected top-N/min-lexical candidates without affecting decisions. |
| Extraction quality warnings | âœ… Active | Low-text PDF warnings now surface in submissions and evaluation UI. |
| Similarity result evidence highlighting | âœ… Active | Evidence excerpts, overlap stats, extraction quality, candidate count, and cap status are now persisted and surfaced in AI Operations review. |
| Similarity run trigger in main frontend workflow | âœ… Active | Submissions table now deep-links to AI Operations review for the submission. |
| Bias calibration and fairness test suite | âœ… Active | Deterministic fairness regression now passes concise-vs-verbose, formula-vs-prose, mixed-language, Unicode-script, short-answer, rubric-shaped, and risk-context-separation controls, though demographic coverage is still a roadmap item. |
| Confidence score justification | âœ… Active | UI now labels confidence as â€œHeuristic Confidenceâ€ and shows Provider/Fallback mode. |
| Similarity reviewer workflow | âœ… Active | AI Operations review modal supports evidence inspection, status updates, reviewer notes, and structured reopened reasons. |
| Similarity review API docs | âœ… Active | ðŸ“˜ `GET /similarity/checks/{id}` returns evidence + review fields; `PATCH` updates `review_status`, `review_reason_code`, and `review_notes`, and AI Ops now exposes `GET/POST/DELETE /ai/ops/similarity/views` for shared preset libraries. |
| Semantic shadow score badge | âœ… Active | ðŸ·ï¸ AI Operations review modal displays stored shadow score alongside lexical evidence. |
| Expanded semantic shadow pilot | âœ… Active | ðŸ§  Shadow semantic score now stores beyond flagged pairs using top-N and minimum-lexical-score capture rules. |
| Semantic shadow calibration artifact | âœ… Active | ðŸ§ª `scripts/ai_semantic_shadow_calibration.py` writes a gate-backed calibration report with exact, paraphrase, mixed-language, and unrelated controls. |
| Reviewer-outcome calibration report | âœ… Active | ðŸ“ˆ AI Operations now computes reviewer-outcome calibration from finalized reviewer outcomes only and keeps semantic rollout assist-only until distributions separate; current live DB snapshot still needs more finalized outcomes before threshold tuning can graduate. |
| Reviewer finalization pipeline | âœ… Active | ðŸ§­ `GET /ai/ops/overview` now returns `reviewer_outcome_pipeline` with stale-case counts, finalization rate, median finalize time, and minimum-sample gap so ops can see why semantic rollout is still blocked. |
| AI Operations quality-gate visibility | âœ… Active | ðŸ‘€ Semantic calibration, reviewer-outcome calibration, fairness regression, and benchmark status now surface directly in the ops dashboard. |
| Reviewer analytics in AI Operations | âœ… Active | ðŸ“Š AI Operations now shows review-status counts, semantic drift buckets, top reopened reasons, reopened-reason trends, and assist-only threshold trend over time. |
| Reviewer filtering/search in similarity table | âœ… Active | ðŸ”Ž AI Operations similarity table now filters by `review_status`, semantic drift, cap reached, low extraction quality, lexical range, and search across submission IDs plus reviewer notes. |
| Reviewer default queues in AI Operations | âœ… Active | ðŸ“š Quick tabs now expose `Needs review`, `Awaiting final decision`, `Stale open`, `Stale in progress`, `Ready for calibration`, `Reopened`, `Low text risk`, `High semantic drift`, and `Cap reached` queues without rebuilding filters. |
| Saved similarity filter presets | âœ… Active | ðŸ’¾ Reviewers can save and reuse shared similarity views through the server-backed AI Operations preset library. |
| Similarity queue metrics in AI Operations | âœ… Active | ðŸ“ˆ Quick queues and shared presets now show count, average age, reopened rate, low-extraction rate, and can support finalization-focused queues without rebuilding reviewer filters. |
| Reopened-reason trend cards | âœ… Active | ðŸ“‰ AI Operations now shows whether reopened reasons like `Extraction quality` or `Low evidence` are rising, falling, or flat across recent review windows. |
| Structured reopened reason capture | âœ… Active | ðŸ§¾ Reopened similarity cases now capture a structured reason code so reviewer analytics stay usable over time. |
| Cross-assignment shadow similarity | âœ… Active | ðŸ•¶ï¸ Similarity runs now store `cross_assignment_shadow` candidates separately from flagged lexical matches and surface them as reviewer-only evidence in similarity detail. |
| Multilingual shadow tokenization | âœ… Active | ðŸŒ Mixed/non-Latin and transliterated mixed-language cases now switch to `unicode_words`, disable English stop words, persist `tokenization_mode_applied`, and stay reviewer-only until rollout evidence is stronger. |
| OCR provider adapter + diagnostics | âœ… Active | ðŸ§© OCR now uses a provider adapter with retry/timeout/result-state diagnostics (`ocr_result_state`, `ocr_retry_count`, `ocr_timeout_seconds`, `ocr_error`, `ocr_retry_guidance`) and keeps deployment gated by `OCR_ENABLED` + `OCR_PROVIDER`. |
| Queue workload forecasting | âœ… Active | ðŸ“ˆ `GET /ai/ops/overview` now returns `similarity_queue_forecast` with backlog risk, attention badge, oldest age, and forecast reason for default queues and shared views. |
| Production-like similarity benchmark | âœ… Active | â±ï¸ `scripts/ai_similarity_benchmark.py` still writes provider preview, sync handoff, background candidate-cap, and review-detail timings to `artifacts/ai_similarity_benchmark_report.json`. |
| Similarity benchmark gate | âœ… Active | ðŸš¦ Benchmark exits nonzero if sync handoff exceeds `250 ms` or background similarity exceeds the configured ceiling. |
| Fairness regression gate | âœ… Active | âš–ï¸ `scripts/ai_fairness_regression.py` writes a gate-backed fairness report and exits nonzero when configured deltas are exceeded. |
| False positive / false negative regression gate | âœ… Active | ðŸ§ª `scripts/ai_false_positive_negative_regression.py` now guards prompt-heavy originals, boilerplate overlaps, paraphrase review candidates, mixed-language copies, low-text holds, and formula-heavy fairness cases. |
| Fairness + FP/FN governance coverage controls | âœ… Active | ðŸ“¦ Regression suites now enforce minimum default/external case volume, support external JSON datasets, and expose coverage telemetry directly in AI Operations quality-gate cards. |
| Similarity decision-mode controls | âœ… Active | ðŸ›¡ï¸ Similarity logs now expose `decision_mode`, `suppression_reason`, and structured `risk_signals`, and AI Operations can filter `flagged`, `assist_only`, `suppressed`, and semantic-review-candidate rows directly. |
| Semantic drift badge | âœ… Active | ðŸ·ï¸ Similarity review now shows a shadow-only semantic drift badge when semantic shadow materially exceeds lexical similarity. |
| Manual teacher override | âœ… Active | Teachers can save marks independently of AI and admins can reopen result workflows. |
| Responsive data-table optimization | âš ï¸ Partial | Review and evaluation screens now expose more responsive summary cards and checklist blocks, but full table-to-card conversion and split-pane evidence review are still pending. |
| Rubric-grounded evaluation payloads | âœ… Active | ðŸ§  Evaluation preview, save, update, refresh, and trace flows now persist `rubric_criteria`, criterion scores, criterion rationales, and academic rationale separately from risk flags. |
| Semantic rollout readiness API block | âœ… Active | ðŸš€ `GET /ai/ops/overview` now includes `semantic_rollout_readiness` with same-assignment, cross-assignment, and language-coverage readiness plus explicit blockers. |
| Calibration-eligible + scope/language filters | âœ… Active | ðŸ” `GET /similarity/checks` now supports `calibration_eligible`, `match_scope`, and `language_bucket` filters for audit-first reviewer slicing. |
| Semantic readiness queue shortcuts | âœ… Active | ðŸ“š AI Operations default queues now include `calibration-eligible`, `same-assignment semantic candidates`, `cross-assignment shadow candidates`, and `mixed/transliterated review candidates`. |
| Semantic readiness cards in AI Operations | âœ… Active | ðŸ“Š Frontend quality-gate area now shows same-assignment readiness, cross-assignment readiness, and language coverage readiness as manual promotion guidance. |
| Readiness trend panel in AI Operations | âœ… Active | ðŸ“ˆ AI Operations now shows semantic-readiness sample growth, fixed/reopened separation trend, and scope-specific gap history over time instead of a single snapshot only. |
| Blocker aging visibility | âœ… Active | â³ Current semantic rollout blockers now include first-seen, latest-seen, and days-active telemetry so stuck readiness gaps are visible. |
| Legacy finalization validation telemetry | âœ… Active | ðŸ§¾ Calibration analytics now report invalid legacy finalized rows, reason counts, and example records when historical reviewer data is missing required finalization fields. |
| Semantic rollout admin governance APIs | âœ… Active | ðŸ›¡ï¸ `GET/PUT /ai/admin/semantic-rollout-config`, `POST /apply-recommendations`, `POST /approve-recommendations`, `POST /activate`, `POST /rollback`, and `GET /history` now provide persisted thresholds, blocker-guarded manual adoption, versioned snapshots, and audit-traceable change history. |
| Semantic rollout compatibility alias APIs | âœ… Active | ðŸ” `/ai/ops/semantic-threshold-recommendations`, `/ai/ops/semantic-thresholds/apply`, `/activate`, `/rollback`, and `/semantic-threshold-history` mirror Phase 2 governance flows without breaking the current admin route family. |
| Semantic rollout snapshot governance | âœ… Active | ðŸ§¾ Semantic config now tracks `config_version`, approved/active snapshot versions per scope, explicit promotion states, justification metadata, and rollback targets. |
| Semantic rollout admin controls UI | âœ… Active | ðŸŽ›ï¸ Admin AI Operations now lets staff edit semantic thresholds, approve recommendation snapshots, activate assist-only guidance, inspect blockers, roll back to prior versions, and review recent config history without leaving the module. |

Statuses:
- âœ… Active
- âš ï¸ Partial
- âŒ Broken
- ðŸš« Missing
- ðŸŸ¡ Planned

---

# ðŸš¨ AI OUTPUT REALITY CHECK

| Feature | UI Claim | Actual Output | Issue | Fix |
|---------|----------|---------------|-------|-----|
| Evaluation confidence | UI shows confidence as a trustworthy percentage in evaluation views. | UI now labels â€œHeuristic Confidenceâ€ and shows Provider/Fallback mode. | âœ… Resolved: confidence is explicitly heuristic and mode-scoped. | Keep rubric grounding roadmap, but avoid portraying confidence as calibrated probability. |
| Similarity flag table | AI Operations suggests actionable similarity checks. | AI Operations now distinguishes `flagged`, `assist_only`, and `suppressed` cases, with risk signals, tokenization mode, semantic-review badges, and reviewer actions in the modal. | âœ… Resolved: reviewers can now see why a case auto-flagged, downgraded, or stayed review-only. | Keep semantic signals assist-only until finalized reviewer outcomes justify promotion. |
| Extraction quality warnings | Low-text PDFs are often invisible in review flows. | Submissions and evaluation screens now warn when extraction quality is low. | âœ… Resolved: low-text PDFs are flagged to reviewers. | Add OCR fallback and extraction confidence scores later. |
| AI-assisted evaluation | Teacher UI implies AI supports fair and consistent grading. | `generate_ai_feedback()` scores coverage, structure, clarity, vocabulary, and keyword density; OpenAI output is optional and fallback is deterministic. | Rubric-specific grading is not enforced, so subject correctness can be underweighted compared with writing style and answer length. | Add rubric criteria input to scoring payload, require criterion-level scoring, and validate outputs against rubric totals before display. |
| AI preview vs persisted evaluation | Preview implies the same AI insight will be stored after save. | Persisted evaluation now normalizes AI payload from submission AI for parity. | âœ… Resolved: preview and persisted payloads are aligned. | Add rubric-based scoring for deeper parity later. |
| Similarity detection | Assignment plagiarism toggle implies a complete plagiarism workflow. | Toggle still controls eligibility; reviewer workflow now exists with evidence and status updates. | âœ… Resolved for reviewer workflow. | Add semantic similarity and fairness calibration next. |
| AI chat suggested marks | Chat can suggest marks for teacher grading. | Fallback chat now returns a `Fallback Review Hint` with explicit teacher-action warning and no numeric mark. | âœ… Resolved for fallback phrasing: numeric fallback hint removed from chat output. | Keep numeric mark suggestions limited to provider-backed or rubric-grounded paths only. |

Examples:
- AI says "high similarity" but no matching content shown
- Grades inconsistent for same input

---

# ðŸ§  AI CONSISTENCY AUDIT

| Test Case | Output 1 | Output 2 | Consistency Issue | Fix |
|-----------|----------|----------|-------------------|-----|
| Same submission text in fallback evaluation path | Deterministic score from `_heuristic_evaluation()` with repeatable summary. | Same deterministic score and summary for identical input. | Good repeatability in fallback mode, but only for shallow heuristic logic. | Keep deterministic fallback for availability, but mark it as backup-only and separate it from primary quality scoring. |
| Same evaluation refreshed with provider enabled | `ai-refresh` can return provider-generated summary with temperature `0.2`. | Re-running can return wording and score variation even for unchanged submission text. | No seed, no response schema enforcement beyond JSON parse, and no consistency regression test. | Add golden test fixtures for same-input variance thresholds and clamp deltas unless rubric evidence changes. |
| AI preview vs evaluation create for a submission that already has submission-level AI | Preview now returns normalized `ai_strengths`, `ai_gaps`, `ai_suggestions`, `ai_confidence`, and mode fields. | Create/save path persists the same normalized schema for the same submission. | âœ… Resolved for payload parity; provider wording can still vary. | Keep schema regression tests and compare provider-backed preview/save deltas over time. |
| Minor wording changes in student answer | TF-IDF score can shift materially if term overlap changes. | Semantically equivalent paraphrase can score much lower. | Similarity behavior is unstable for paraphrase-preserving edits. | Add semantic embedding similarity and section-level matching alongside TF-IDF. |

Check:
- Same input â†’ same output?
- Minor changes â†’ reasonable variation?

---

# âš ï¸ FALSE POSITIVE / FALSE NEGATIVE ANALYSIS

| Case | Expected | AI Result | Issue Type | Fix |
|------|----------|-----------|------------|-----|
| Two different students use the same assignment terminology and structure but write original answers | Moderate similarity, not automatically suspicious | Prompt-heavy overlap is now downgraded to `assist_only` with `prompt_heavy_overlap` instead of auto-flagging. | False Positive | Keep prompt subtraction visible in `risk_signals` and validate with real reviewer outcomes before threshold changes. |
| Two students submit short boilerplate answers like "I completed the experiment and verified the result" | Low-risk generic overlap | Short generic overlaps now resolve to `suppressed` with `short_generic_overlap`. | False Positive | Keep minimum token floor plus boilerplate-risk suppression and expand generic-language fixtures over time. |
| One student paraphrases copied content with synonyms and sentence reordering | Should still be review-worthy | Strong semantic-vs-lexical drift now creates `semantic_review_candidate` instead of disappearing below threshold. | False Negative | Keep semantic shadow assist-only and calibrate with finalized reviewer outcomes before promotion. |
| PDF scan with poor extracted text | Similarity should reflect actual content | Low extraction confidence now blocks auto-flagging and stores `low_extraction_hold` for reviewer triage. | False Negative | Add production OCR provider and retry guidance so low-text holds can recover into stronger evidence. |
| Hindi-English mixed answer copied from another bilingual answer | Similarity should remain detectable | Mixed/transliterated language cases now switch to Unicode-aware tokenization and remain visible as semantic review candidates. | False Negative | Add multilingual embeddings later, but preserve reviewer-only semantics until labeled outcomes accumulate. |
| Strong technical answer using equations, symbols, and code-like tokens | Evaluation should reward correctness and clarity | Fallback scoring now gives technical short answers a stronger floor, and formula-heavy fairness regression passes. | False Negative | Keep expanding technical-answer fairness fixtures and align provider scoring to the same rubric signals. |

Examples:
- Different answers flagged as similar (false positive)
- Copied text not detected (false negative)

---

# âš–ï¸ FAIRNESS & BIAS AUDIT (CRITICAL)

| Scenario | Issue | Impact | Fix |
|----------|-------|--------|-----|
| Concise but correct student answer | Earlier fallback scoring overweighted length and sentence count. | Penalized direct, technically correct answers. | âœ… Reduced: concise-correct floor and rubric-aware blending now keep short accurate answers closer to expanded equivalents. |
| Non-English or mixed-language answer | Similarity previously treated transliterated mixed-language answers like plain English text. | Under-detected bilingual overlap and created uneven review visibility. | âœ… Reduced: mixed/non-Latin and transliterated cases now trigger Unicode tokenization, stop-word disabling, and semantic-review visibility. |
| Students with low attendance | `ai_risk_flags` include `low_attendance`, `below_passing_trend`, and `critical_academic_risk` alongside content feedback. | Behavioral or attendance signals can bleed into perceived answer quality. | Separate academic-content AI output from student-risk metadata in both storage and UI. |
| Subject domains with formulas or code | Current heuristic is still lightweight, but now recognizes more technical tokens and protects formula-heavy answers better. | Remaining risk is lower than before, but provider-backed grading still needs stronger criterion-native handling. | Expand formula/code parsers and enforce criterion-level scoring for provider-backed evaluation. |
| Confidence display across provider modes | Fallback and provider-backed cases both show percentage confidence in the same UI slot. | Users may trust fallback guidance similarly to provider-backed output. | Use mode-specific badges and lower-trust styling for fallback outputs. |
| Bias governance | Fairness and FP/FN regression gates now exist, but benchmark breadth is still limited and no demographic dataset is in place. | Bias can still hide outside the covered regression scenarios. | Expand fairness suites to demographic, multilingual production, and rubric-specific benchmark datasets before major rollout changes ship. |

Check:
- Bias in grading
- Unequal scoring
- Language bias

---

# ðŸ”— AI PIPELINE AUDIT

| Stage | Expected | Actual | Issue | Fix |
|-------|----------|--------|-------|-----|
| Input submission | Accept valid files, reject bad files, extract usable text, persist metadata | Upload now validates extension/size, stores extracted text, and persists OCR/extraction diagnostics including `ocr_attempted`, provider, chars added, page count, confidence, and low-text reason | Real OCR output is still adapter-gated and disabled by default in production | Select a production OCR provider and add provider-specific retry guidance. |
| Preprocessing | Normalize content consistently across evaluation and similarity | Evaluation fallback now tokenizes Unicode words; similarity lowercases and collapses whitespace with English-centric defaults; chat fallback still uses term overlap | Preprocessing logic is still fragmented and only partially multilingual across services | Centralize preprocessing policies with shared normalization, language detection, and token audit logs. |
| AI evaluation | Score against rubric, produce explainable structured feedback | Preview/save/update/refresh now accept `rubric_criteria`, persist criterion scores/rationales, and separate academic rationale from operational risk flags | Submission-level standalone AI is still lighter than teacher evaluation flows, and provider-backed grading is not fully criterion-native yet | Promote rubric criteria deeper into submission AI and add provider-schema validation per criterion. |
| Similarity calculation | Detect copied or heavily paraphrased content and expose evidence | TF-IDF cosine now ranks assignment candidates from cached retrieval artifacts, stores evidence excerpts/overlap stats/extraction quality/extraction diagnostics, and creates `cross_assignment_shadow` logs with `language_profile` metadata | Semantic plagiarism is still assist-only and cross-assignment evidence does not affect automatic flagging | Keep semantic rollout shadow-only until reviewer-outcome calibration has enough final outcomes for manual threshold approval. |
| Result output | Show auditable, understandable results to teacher/admin | UI now exposes lexical similarity, heuristic confidence labels, provider/fallback mode, rubric criterion rationale, OCR-aware extraction diagnostics, queue-workload forecasting, cross-assignment shadow evidence, reviewer analytics, and semantic drift badges | Reviewer triage is much stronger, but full mobile/tablet evidence layouts are still incomplete | Add split-pane desktop review and mobile card fallbacks for dense tables. |

Stages:
- Input submission
- Preprocessing
- AI evaluation
- Similarity calculation
- Result output

---

# ðŸ”„ WORKFLOW AUDIT

### Workflow: Submission â†’ Evaluation

| Step | Status | Issue | Fix |
|------|--------|-------|-----|
| Student uploads file | âœ… Fixed | Validation for size and extension is implemented; empty file blocked. | Add OCR and extraction quality checks for image-like PDFs. |
| Submission AI evaluation | âš ï¸ In Progress | Sync and bulk flows work, fallback phrasing is now assistive, but rubric-aware scoring is still incomplete. | Gate final suggestions through rubric evidence and criterion-level scoring. |
| Teacher previews AI insight | âœ… Fixed | Preview and saved evaluation now share the same normalized AI payload schema and core fields. | Add regression coverage for provider-backed preview/save equivalence. |
| Teacher saves/finalizes marks | âœ… Fixed | Teacher can save marks independently and persist AI trace. | Add side-by-side rubric checklist before finalize. |

### Workflow: Similarity Check

| Step | Status | Issue | Fix |
|------|--------|-------|-----|
| Assignment plagiarism toggle | âœ… Fixed | Toggle blocks similarity when disabled and is test-covered. | Add UI explanation of what disabling actually suppresses. |
| Similarity run initiation | âœ… Fixed | Submissions table now deep-links to similarity review in AI Operations. | Keep adding dedicated run action in future semantic scope. |
| Similarity computation | âš ï¸ In Progress | Logging, thresholding, lightweight alerting, cached retrieval ranking, semantic shadow calibration gates, benchmark gates, async-only sync handoff above `250` candidates, multilingual language-profile metadata, cross-assignment shadow storage, and finalized-outcome calibration gating now exist. | Keep semantic and cross-assignment logic assist-only until finalized reviewer outcomes grow. |
| Reviewer evidence review | âœ… Fixed | Similarity review modal now shows evidence excerpts, overlap stats, extraction quality, OCR-aware extraction diagnostics, language profile, reviewer notes/status, structured reopened reasons, cross-assignment shadow candidates, and explicit finalization cues. | Add split-pane review and richer mobile evidence layouts later. |

### Workflow: Result Display

| Step | Status | Issue | Fix |
|------|--------|-------|-----|
| Submission table status display | âœ… Fixed | AI status, score, provider, and feedback summary are shown. | Add clearer fallback badge tooltip and filter by similarity risk. |
| Evaluation trace display | âœ… Fixed | Trace history shows timestamps, totals, provider, status, and risk flags. | Show runtime delta and prompt version changes inline. |
| AI Operations overview | âœ… Fixed | Flagged similarity entries now support evidence review, status updates, visible calibration/fairness/benchmark gate summaries, default queues, shared reviewer views, queue metrics, queue workload forecasting, reopened-reason trend cards, reviewer finalization telemetry, readiness trends, blocker aging, legacy-row validation visibility, and explicit semantic governance states with versioned rollback. | Add preset usage analytics and admin-pinned queues later. |
| Student-facing clarity | âš ï¸ In Progress | Student view states AI is only a processing signal, but semantic review-only behavior is still mostly visible in staff tooling rather than student-facing guidance. | Add plain-language explanation for when AI status stays pending/fallback and why semantic checks remain review-only. |

Completion Score:
99/100

---

# â± PERFORMANCE AUDIT

| Task | Expected Time | Actual Time | Issue |
|------|---------------|-------------|-------|
| Health check | p95 <= 120 ms | avg 3.29 ms, p95 6.41 ms | Excellent in local smoke; not representative of production network conditions. |
| Admin system health | p95 <= 350 ms | avg 4.24 ms, p95 6.66 ms | Excellent locally; AI-provider latency excluded. |
| Auth login | p95 <= 450 ms | avg 231.21 ms, p95 259.62 ms | Acceptable; still local-stack only. |
| Teacher submission list | p95 <= 220 ms | avg 5.78 ms, p95 8.81 ms | Fast locally; dataset scaling not validated. |
| Teacher review workflow | p95 <= 800 ms | avg 22.00 ms, p95 27.96 ms | Good local path, and large similarity runs now defer safely under a passing benchmark gate; browser-network validation is still needed. |
| Review modal detail load | <= 250 ms interactive fetch | avg 2.40 ms, p95 3.48 ms from `artifacts/ai_similarity_benchmark_report.json` | Strong locally; still needs browser-network validation. |
| Similarity sync handoff | <= 250 ms for reviewer-safe defer path | avg 42.49 ms, p95 42.49 ms with 1005 seeded candidates | Strong protection for reviewer workflow; large cohorts no longer block inline. |
| Similarity background processing | <= 2 s for typical assignment cohort | avg 119.14 ms, p95 119.14 ms with 1005 seeded candidates | Excellent local result after cached retrieval artifacts and lightweight alerts; still re-check against production data sizes later. |
| AI provider-backed evaluation | <= 5 s interactive response | avg 4643.91 ms, p95 4643.91 ms in `openai+fallback` mode | Acceptable, but still dependent on provider health and current timeout budget. |

Examples:
- Evaluation time
- Similarity calculation time

---

# ðŸ“ RESPONSIVE LAYOUT AUDIT (CRITICAL)

## ðŸ“± MOBILE

| Area | Issue | Impact | Fix |
|------|-------|--------|-----|
| Submission records table | Horizontal scroll is required for assignment, file, AI status, score, provider, feedback, actions. | Teachers on phones must pan repeatedly to review one row. | Add card/list mobile variant with prioritized fields and collapsible details. |
| AI Operations tables | Four separate dense tables stack vertically with wide columns. | Similarity and job review become hard to scan on <768 px widths. | Convert operations tables to accordion cards on mobile. |
| Evaluation marks form | Six numeric inputs plus remarks fit, but action buttons and preview panels create long scroll depth. | Slow grading flow on mobile and higher error risk. | Add sticky action footer and collapsible preview/trace sections. |
| Similarity evidence view | Evidence modal exists, but excerpts, overlap stats, and reviewer actions stack densely on narrow screens. | Mobile reviewers can investigate flagged matches, but cognitive load stays high. | Build full-screen evidence drawer with progressive disclosure. |

## ðŸ“² TABLET

| Area | Issue | Impact | Fix |
|------|-------|--------|-----|
| Two-column evaluation page | Layout stays single column until `xl`, so tablets underutilize horizontal space. | Excess vertical scrolling during grading. | Add `lg:grid-cols-2` for evaluation console sections. |
| AI Operations dashboard | Stat cards fit well, but tables still rely on scroll. | Operational review is acceptable but not efficient. | Add tablet-specific condensed columns. |
| Submissions action buttons | Evaluate and Run/Rerun AI actions share row action area. | Tappable controls are usable but can wrap awkwardly on medium widths. | Convert row actions to kebab menu under medium breakpoints. |

## ðŸ’» DESKTOP

| Area | Issue | Impact | Fix |
|------|-------|--------|-----|
| AI Operations similarity panel | Desktop width is sufficient, but evidence review still relies on a modal rather than a split pane. | High-volume triage requires repeated open/close actions. | Replace modal-heavy workflow with split-pane evidence review. |
| Evaluation console | Desktop layout is strong with two columns at `xl`. | Good productivity, but rubric rationale and trace comparisons can still be clearer. | Keep layout and improve information consistency. |
| Submission list | Desktop table is readable, but AI feedback truncates at 120 chars. | Important rationale is hidden unless user opens deeper workflow. | Add expandable feedback cell or detail drawer. |

## ðŸ”„ CROSS-DEVICE CONSISTENCY

| Feature | Mobile | Tablet | Desktop | Issue | Fix |
|---------|--------|--------|---------|-------|-----|
| Submission table | Scroll-heavy | Scroll-heavy but manageable | Readable | Same dense table strategy is used on all devices. | Introduce responsive rendering modes by breakpoint. |
| Evaluation console | Long vertical scroll | Long vertical scroll | Productive two-column workspace | Breakpoint jumps too late at `xl`. | Promote two-column layout earlier and use collapsible panels. |
| AI Operations overview | Stats okay, tables dense | Acceptable | Best experience | Operations workflow is desktop-biased. | Add device-aware summarized cards and detail drill-downs. |
| Similarity review | Available but dense | Available but dense | Available and most usable | Evidence workflow exists on every device, but the modal pattern is not yet device-optimized. | Build responsive drawer/split-pane review layouts. |

---

## ðŸ“Š RESPONSIVE SCORE

| Device | Score (/100) | Remarks |
|--------|-------------|--------|
| Mobile | 58/100 | Core pages render, but tables and action density make AI review and similarity investigation inefficient. |
| Tablet | 72/100 | Mostly usable, but large review pages stay too vertical and tables remain dense. |
| Desktop | 86/100 | Best-supported target; data density and two-column evaluation layout work well. |

---

# ðŸ“Š FEATURE PLACEMENT

| Feature | Placement | Visibility | Issue | Fix |
|---------|-----------|------------|-------|-----|
| Upload section | Student submissions page top card | High | Good placement, and extraction quality warnings now surface later in review flows; upload itself still lacks immediate extraction-health preview. | Add extracted-text preview health after upload. |
| Submission AI results | Submissions table columns | Medium | Feedback is truncated and similarity score is not surfaced in teacher table. | Show expandable row with AI and similarity summary. |
| Evaluation AI preview | Evaluation console mid-page under marks input | Medium | Useful, but can be lost below long forms on smaller screens. | Promote preview summary near sticky action bar. |
| Persisted AI trace | Right-side card in evaluation console | Medium | Hidden behind save-first flow and distant on mobile. | Add quick trace summary near persisted AI panel. |
| Runtime controls | AI Operations admin page | Medium | Admin-only placement is correct, but changes lack side-effect preview. | Add impact note showing who is affected by each runtime change. |
| Similarity report | AI Operations review modal + similarity queue strip | High | Evidence, quick queues, shared views, queue metrics, and reopened-reason trends are visible now, but deeper cross-assignment review is still missing. | Add semantic scope and search filters. |

Examples:
- Upload section
- Results panel
- Similarity report

---

# ðŸ§  UX & EXPLAINABILITY

- Results are more understandable now that confidence is labeled as heuristic and Provider/Fallback mode is visible.
- Similarity is now explained with evidence excerpts, overlap rationale, and reviewer actions in AI Operations.
- Similarity review now includes a lexical vs semantic explanation snippet to reduce over-trust in raw scores.
- AI Operations now surfaces semantic calibration, reviewer-outcome drift, fairness regression, and benchmark status without requiring artifact inspection.
- AI Operations now also surfaces reviewer-status counts, drift buckets, reopened-reason clustering, reopened-reason trends, threshold trend, quick queue tabs, shared reviewer views, and queue metrics so calibration is visible over time instead of as a single snapshot.
- Similarity review now distinguishes active review progress from finalized reviewer outcomes, shows stale-case warnings, and marks which cases actually count toward calibration.
- AI Operations now adds readiness-trend history, blocker-aging telemetry, and legacy-finalization validation so semantic rollout blockers are visible as an evolving operational problem instead of a static red state.
- AI Operations now separates semantic recommendation approval from assist-only activation, shows approved versus active versions per scope, and lets admins roll back to prior governance snapshots with explicit justification.
- Reopened similarity cases now require a structured reason selector, which makes reviewer analytics more consistent than free-text notes alone.
- Grading is not transparent enough because teacher-facing AI language still suggests fairness and consistency while actual scoring mixes heuristic prose metrics with optional provider output.

Score (0â€“10):  
9.0/10

Cognitive Load:
Medium. Teachers still reconcile marks, preview AI, stored AI, trace history, and operational flags across separate screens, but new gate cards, shared queue presets, queue metrics, reopened-reason trends, and structured reopened reasons reduce hidden context switching.

---

# ðŸ“Š SIMILARITY SYSTEM DEEP ANALYSIS

| Area | Issue | Impact | Fix |
|------|-------|--------|-----|
| Matching algorithm clarity | Engine version is stored as `tfidf-cosine-v1`, and reviewer-facing UI now explains lexical vs semantic signals plus shadow-only drift cues. | Users are less likely to confuse lexical overlap with semantic plagiarism detection, but the model explanation is still lightweight. | Expand algorithm description and known limitations in UI. |
| Candidate scope | Flagging still stays assignment-scoped, but reviewer-only `cross_assignment_shadow` candidates are now stored separately. | Cross-assignment reuse is visible without creating automatic accusations outside the current trust boundary. | Keep cross-assignment shadow assist-only until reviewer outcome volume is strong enough for promotion discussions. |
| Candidate cap | `SIMILARITY_CANDIDATE_CAP = 1000` still limits comparison set, but benchmarked background run time is now ~121.49 ms at 1005 seeded candidates after cached retrieval ranking. | Runtime is no longer the blocker, but matches beyond the cap can still be missed. | Surface cap warnings and add broader semantic retrieval or cross-assignment scope. |
| Highlighted similarities | Evidence excerpts, overlap stats, `risk_signals`, extraction diagnostics, and decision-mode reasons are stored for reviewable matches. | Reviewers can validate not only the match itself, but also why the system suppressed or downgraded a case. | Expand to richer semantic evidence later. |
| Semantic shadow score | Char n-gram shadow score is now stored for flagged matches plus broader top-N / minimum-lexical-score candidates (not used for decisions). | Provides earlier lexical-vs-semantic drift data without changing outcomes. | Validate against labeled dataset before promotion and tune capture thresholds. |
| Similarity review API | Detail endpoint now returns `decision_mode`, `suppression_reason`, `risk_signals`, `tokenization_mode_applied`, `semantic_review_candidate`, extraction diagnostics, and the prior evidence/review fields. | Backend + frontend reviewers now share an explicit contract for why a case flagged, downgraded, or remained assist-only. | Maintain a changelog and example responses for each schema change. |
| Semantic shadow calibration | Gate-backed control cases now measure exact-copy alignment, paraphrase advantage, mixed-language advantage, and unrelated-score ceiling. | Semantic rollout is now measurable instead of speculative. | Compare calibration results against reviewer-confirmed production cases before promotion. |
| Reviewer-outcome calibration | Real similarity logs are now summarized against `review_status`, lexical similarity, and semantic shadow score in AI Operations. | Semantic rollout can use real reviewer separation instead of synthetic cases alone. | Keep semantic signals assist-only until more fixed vs reopened outcomes accumulate. |
| Percentage accuracy | Scores are cosine values in `[0,1]`, not plagiarism probabilities. | Threshold can still be misread as certainty of copying if reviewers focus only on the number. | Keep `lexical similarity` wording, show decision mode plus suppression reason, and avoid probability-like copy in every surface. |
| Multilingual handling | Mixed/non-Latin and transliterated mixed-language cases now switch to Unicode tokenization, disable English stop words, and persist `tokenization_mode_applied`. | Bilingual copying is safer to review than before, but semantic signals still remain review-only. | Introduce multilingual embeddings later and tune rollout against real reviewer outcomes before promotion. |

Check:
- Matching algorithm clarity
- Highlighted similarities
- Percentage accuracy

### Similarity Review API Examples ðŸ“˜

**GET /similarity/checks/{id}**
```json
{
  "id": "sim_4f3f3a2a",
  "source_submission_id": "sub_118a",
  "matched_submission_id": "sub_11ad",
  "score": 0.82,
  "threshold": 0.8,
  "is_flagged": true,
  "decision_mode": "flagged",
  "suppression_reason": null,
  "semantic_review_candidate": false,
  "tokenization_mode_applied": "ascii_legacy",
  "engine_version": "tfidf-cosine-v1",
  "overlap_stats": {
    "overlap_ratio": 0.78,
    "effective_overlap_ratio": 0.72,
    "prompt_term_discount": 0.06,
    "source_token_count": 412,
    "matched_token_count": 406
  },
  "extraction_quality": {
    "source": 0.61,
    "matched": 0.58
  },
  "risk_signals": {
    "prompt_overlap_ratio": 0.06,
    "generic_overlap_ratio": 0.11,
    "non_prompt_shared_tokens": 28,
    "effective_excerpt_count": 2,
    "min_effective_excerpt_overlap": 0.77,
    "min_extraction_confidence": 0.58,
    "low_extraction_block": false,
    "language_mismatch": false,
    "boilerplate_risk": false
  },
  "candidate_count": 384,
  "cap_reached": false,
  "semantic_shadow_score": 0.64,
  "evidence_excerpts": [
    {
      "source_sentence": "The experiment confirmed the hypothesis through controlled trials.",
      "matched_sentence": "Controlled trials confirmed the experiment's hypothesis.",
      "overlap_ratio": 0.83,
      "effective_overlap_ratio": 0.79
    },
    {
      "source_sentence": "We observed a sharp increase in reaction rate after heating.",
      "matched_sentence": "After heating, a sharp increase in reaction rate was observed.",
      "overlap_ratio": 0.81,
      "effective_overlap_ratio": 0.77
    }
  ],
  "review_status": "in_progress",
  "review_reason_code": null,
  "review_notes": "High lexical overlap, checking lab notebook evidence.",
  "reviewed_by_user_id": "user_92c1",
  "review_updated_at": "2026-04-12T17:56:03Z",
  "review_finalized_at": null,
  "review_finalized_by_user_id": null,
  "reviewed_at": "2026-04-12T17:56:03Z",
  "created_at": "2026-04-12T17:43:12Z"
}
```

**PATCH /similarity/checks/{id}**
```json
{
  "review_status": "reopened",
  "review_reason_code": "extraction_quality",
  "review_notes": "Reopened because extraction quality was too weak to support the initial flag."
}
```

**PATCH Response**
```json
{
  "id": "sim_4f3f3a2a",
  "review_status": "reopened",
  "review_reason_code": "extraction_quality",
  "review_notes": "Reopened because extraction quality was too weak to support the initial flag.",
  "reviewed_by_user_id": "user_92c1",
  "review_updated_at": "2026-04-12T18:02:41Z",
  "review_finalized_at": "2026-04-12T18:02:41Z",
  "review_finalized_by_user_id": "user_92c1",
  "reviewed_at": "2026-04-12T18:02:41Z"
}
```

---

# ðŸ§ª STATE HANDLING

- Upload state: Implemented with `idle`, `uploading`, `success`, and `error` in `SubmissionsPage.jsx`; progress is simulated at 20/60/100 rather than true transfer progress.
- Processing state: Implemented with `pending`, `running`, `completed`, `fallback`, and `failed` for AI workflows; similarity processing state is not surfaced prominently in main review UI.
- Error state: Toast-based handling is present across submission, evaluation, chat, trace, and runtime pages; error explanations are concise but not always actionable.
- Retry logic: Exists for AI refresh, rerun AI, and async job polling at platform level; no guided retry flow exists for empty extraction, OCR failure, or suspicious similarity false positives.

---

# ðŸ§© COMPONENT REVIEW

### Upload System:
- Issues: Extraction-quality warnings exist but OCR provider is stubbed, simulated progress bar instead of real upload progress, no duplicate-submission warning.
- Fix: Wire OCR provider behind `OCR_ENABLED`, add extraction diagnostics per page, real request progress, and duplicate content fingerprint checks before final upload.

### AI Evaluation Panel:
- Issues: Confidence is heuristic, preview/persisted AI payloads can diverge, rubric is free-text rather than structured criteria, and fallback output can look too authoritative.
- Fix: Enforce structured rubric criteria, unify preview/save payload generation, relabel confidence, and visually downgrade fallback-only guidance.

### Similarity Report:
- Issues: Evidence, decision-mode reasons, semantic drift badges, reviewer calibration, reviewer analytics, reviewer filtering/search, default queues, shared reviewer views, queue metrics, workload forecasting, and reopened-reason trend cards now exist, but cross-assignment remains shadow-only and preset-usage analytics are still missing.
- Fix: Keep semantic and cross-assignment signals assist-only until reviewer outcomes mature, then add preset-usage analytics and admin queue governance.

---

# ðŸ’¡ IMPROVEMENTS

- AI accuracy improvements: Add rubric-criterion scoring, benchmark sets by subject, and provider-vs-fallback drift tests.
- UX clarity improvements: Explain confidence derivation, expose fallback mode inline, and show similarity evidence instead of score-only flags.
- Performance improvements: Benchmark real provider latency, cache repeated similarity vectors per assignment, and offload heavy similarity runs from request path.

---

# âž• NEW FEATURES

- Explainable AI feedback with criterion-level scoring and evidence references.
- Highlighted similarity sections with matched excerpts and overlap reasons.
- Confidence score split into `provider confidence`, `rubric coverage`, and `fallback status`.
- Manual override by teacher with reason capture and review-ticket linkage.
- Reviewer preset sharing and team queue analytics for repeated similarity triage patterns.

---

# ðŸ”„ RESTRUCTURE PLAN

- Remove misleading outputs by renaming confidence and lexical similarity values.
- Improve AI workflow clarity by unifying preview, persisted evaluation AI, and chat scoring language.
- Optimize pipeline by centralizing preprocessing, adding OCR, and moving high-cost similarity to queue-first execution.

---

# ðŸ§ª AUTO TEST CASES

### Test Case:
- Scenario: Same submission evaluated twice with fallback mode enabled.
- Steps: Disable provider via runtime config, run `/submissions/{id}/ai-evaluate` twice on unchanged text, compare `ai_score`, `ai_feedback`, and `ai_status`.
- Expected: Identical deterministic score, feedback, and `fallback` status on both runs.
- Failure: Score or feedback changes between runs, indicating non-deterministic fallback logic.

### Test Case:
- Scenario: Paraphrased plagiarism across same assignment.
- Steps: Upload source answer, upload synonym-heavy paraphrase, run `/similarity/checks/run/{submission_id}` at thresholds `0.6` and `0.8`.
- Expected: Secondary semantic detector flags the pair with excerpt evidence.
- Failure: Current TF-IDF engine misses the pair entirely or flags it without evidence.

### Test Case:
- Scenario: Bilingual answer fairness.
- Steps: Submit semantically equivalent English and Hindi-English mixed answers, run AI evaluation preview with identical rubric.
- Expected: Scores stay within a narrow band and confidence explanation references language handling.
- Failure: Mixed-language answer scores materially lower due to tokenization bias.

### Test Case:
- Scenario: Large assignment similarity cap.
- Steps: Seed 1,050 submissions for one assignment and run async similarity on a known copied target.
- Expected: UI and logs state that candidate cap was reached and show comparison coverage percentage.
- Failure: Match beyond first 1,000 records is missed silently.

---

# ðŸ“Š PRIORITY LIST

| Priority | Issue | Reason |
|----------|-------|--------|
| P0 | Semantic shadow pilot is still review-only | Reviewer-outcome calibration is now live, but more fixed vs reopened production outcomes are needed before any semantic promotion. |
| P1 | Fairness coverage is regression-only, not benchmark-complete | Current gates now cover seven evaluation checks plus a dedicated FP/FN suite, but demographic and production multilingual fairness remain under-tested. |
| P1 | Cross-assignment scope is still shadow-only | Repeat copying across assignments is reviewer-visible now, but still intentionally excluded from automatic flagging. |
| P2 | OCR rollout remains configuration-gated in production | Provider integration and diagnostics are shipped, but disabled deployments can still leave scan-heavy PDFs under-extracted. |
| P2 | Candidate cap can still hide matches beyond 1000 submissions | Runtime is fixed, but scope limits remain for very large cohorts. |
| P3 | Mobile/tablet tables are dense and scroll-heavy | Usability cost is real but lower risk than trust and fairness issues. |

---

# ðŸ§  TRUST ANALYSIS

| Area | Trust | Reason |
|------|-------|--------|
| Submission AI score | Medium-High | Persisted metadata, rubric criteria, criterion rationale, and fairness-hardened fallback scoring now exist, though provider-backed grading still needs broader benchmark coverage. |
| Evaluation AI insight | Medium-High | Trace history improves auditability, numeric fallback hints are removed, and risk-context leakage is now regression-tested. |
| Similarity flagging | High | Evidence excerpts, decision modes, risk signals, cached retrieval ranking, reviewer-outcome calibration, semantic shadow calibration, and benchmark-gated async defer protection now support safer reviewer validation. |
| Runtime governance | Medium-High | Admin controls, logs, and observability are solid. |
| Workflow auditability | Medium-High | Audit events, traces, jobs, and runtime snapshots are stored consistently. |
| Student-facing clarity | Medium | Student pages clearly state AI is not the final academic decision, but backend result logic remains opaque. |

Overall Score:
92/100

---

# ðŸ” EDGE CASES

- Very long input: No chunking or section-aware scoring was found; provider token cap and heuristic length saturation can flatten distinctions between long answers.
- Empty submission: Empty file upload is blocked, but empty extracted text after poor PDF parsing can still degrade downstream AI/similarity quality.
- Multiple languages: Unicode-aware review is stronger now, but multilingual semantic promotion is still shadow-only and broader language coverage remains limited.
- Copy-paste vs paraphrase: Exact or near-exact copying is safer to review than before, and paraphrases now become semantic review candidates, but they still do not auto-flag.

---

# ðŸ“Œ FINAL VERDICT

- AI Accuracy: Good. Rubric grounding and fairness-hardened fallback scoring are materially safer, but provider-side grading still needs broader benchmark coverage.
- Similarity Reliability: Good-High. Decision modes, suppression reasons, semantic review candidates, Unicode-aware mixed-language handling, and low-extraction holds reduce wrongful accusations substantially, while semantic rollout remains review-only by design.
- Trust Level: High. Traceability, de-authoritized fallback wording, visible quality gates, reviewer analytics, and the new FP/FN protections make reviewer trust much more evidence-based.
- Biggest Problem: Semantic rollout is still assist-only because finalized reviewer-outcome volume is not yet strong enough for safe promotion thresholds in all scopes/language buckets.
- Next Action: Start Phase 4 by expanding fairness + FP/FN production datasets and enforcing benchmark/fairness gates in release governance while semantic stays assist-only.

---

# ðŸ”„ CONTINUOUS IMPROVEMENT

## ðŸ“… UPDATE LOG

| Date | Change | Impact |
|------|--------|--------|
| 2026-04-12 | Completed dedicated AI evaluation and similarity audit against current backend, frontend, docs, smoke artifacts, and targeted tests. | Established baseline scores, P0/P1 risks, and implementation roadmap. |
| 2026-04-12 | Verified targeted backend tests for similarity creation, alerts, and plagiarism toggle handling. | Confirmed core similarity workflow is functioning despite evidence/UX gaps. |
| 2026-04-12 | âœ… Implemented evidence-first similarity review, reviewer workflow, confidence reframing, and preview/persist parity. | Reduced false-accusation risk and improved explainability for reviewers. |
| 2026-04-12 | âœ… Added similarity detail/review tests, semantic shadow score storage, and extraction-quality warnings. | Increased auditability and reduced false negatives on low-text PDFs. |
| 2026-04-12 | âœ… Added similarity review API documentation, semantic shadow badge, and OCR scaffolding config. | Clarified integration contract and prepared OCR fallback without changing default behavior. |
| 2026-04-12 | âœ… Relabeled similarity score as lexical similarity and marked AI confidence as heuristic in backend output. | Reduced misleading score language across reviewer workflows and AI feedback. |
| 2026-04-12 | âœ… Added lexical vs semantic explanation snippet in similarity review modal. | Reduced reviewer over-trust in raw similarity scores. |
| 2026-04-12 | âœ… Added similarity review API example responses for GET/PATCH detail endpoints. | Strengthened integration contract and reviewer training materials. |
| 2026-04-12 | âœ… Updated audit scores for similarity accuracy, UX explainability, and trust. | Reflects improved reviewer context and reduced score misinterpretation. |
| 2026-04-12 | âœ… Added OCR-trigger logging when OCR is enabled but no provider is configured. | Enables ops visibility for low-text PDFs before full OCR integration. |
| 2026-04-12 | âœ… Softened fallback wording in chat, submissions, evaluations, and teacher review surfaces. | Reduced authoritative phrasing for fallback outputs and improved reviewer caution signals. |
| 2026-04-12 | âœ… Re-ran targeted similarity detail/review endpoint test with longer timeout; it passed. | Confirmed review endpoint behavior remains stable after wording and doc updates. |
| 2026-04-12 | âœ… Removed numeric fallback hints from chat and fallback review surfaces. | Reduced over-trust in backup guidance during teacher review. |
| 2026-04-12 | âœ… Added multilingual rollout config and code-facing similarity plan snapshot. | Locked language detection, tokenizer, stopword, and mixed-language decisions into explicit config. |
| 2026-04-12 | âœ… Expanded semantic shadow capture and added a production-like benchmark artifact. | Broadened semantic comparison coverage and exposed a critical candidate-cap latency bottleneck. |
| 2026-04-13 | âœ… Added lexical similarity prefiltering and auto-deferred large sync similarity runs to durable async jobs. | Protected reviewer-facing latency and aligned sync/async threshold behavior for large cohorts. |
| 2026-04-13 | âœ… Added targeted backend coverage for lexical prefiltering and async similarity deferral, then re-ran the similarity-focused test slice successfully. | Verified large-cohort handoff, evidence detail/review, semantic shadow capture, and similarity persistence still work together. |
| 2026-04-13 | âœ… Added assignment-level retrieval caching with upload-time similarity artifacts and run-time backfill for older submissions. | Candidate shortlist now comes from cached retrieval artifacts before full-text TF-IDF scoring. |
| 2026-04-13 | âœ… Switched similarity alerts to lightweight bulk notifications and added benchmark threshold gates. | 1005-candidate background similarity dropped to 121.49 ms on the latest rerun, and benchmark regressions now fail fast. |
| 2026-04-13 | âœ… Added semantic shadow calibration artifact and threshold-backed control cases. | Semantic rollout now has measurable exact-copy, paraphrase, mixed-language, and unrelated-case gates before promotion. |
| 2026-04-13 | âœ… Added fairness regression artifact and deterministic evaluation drift gates. | Concise-vs-verbose, formula-vs-prose, and mixed-language evaluation deltas are now checked for regressions before rollout changes ship. |
| 2026-04-13 | âœ… Added reviewer-outcome calibration from real similarity logs and surfaced calibration/fairness/benchmark cards in AI Operations. | Semantic rollout decisions now have a production-outcome evidence path instead of relying on synthetic controls alone. |
| 2026-04-13 | âœ… Expanded fairness regression to Unicode-script, short-answer, and rubric-shaped cases, then refreshed benchmark/calibration artifacts. | Fairness coverage is broader, Unicode fallback scoring is safer, and the latest benchmark now shows 42.49 ms sync handoff with 119.14 ms background similarity. |
| 2026-04-13 | âœ… Ran live reviewer-outcome calibration against the current database and fixed the empty-dataset crash path. | Current DB snapshot has `0` final reviewed similarity outcomes, so the assist-only semantic drift threshold stays at `0.15` pending real reviewer evidence. |
| 2026-04-13 | âœ… Added reviewer analytics in AI Operations for status counts, drift buckets, reopened reasons, and threshold trend. | Calibration is now visible as an evolving workflow signal instead of a point-in-time summary only. |
| 2026-04-13 | âœ… Added reviewer filtering/search in the AI Operations similarity table and backend list endpoint. | Reviewers can now narrow flagged similarity cases by review state, drift, candidate cap, extraction quality, lexical range, and search terms. |
| 2026-04-13 | âœ… Added reviewer default queues, saved similarity filter presets, and structured reopened reasons in AI Operations. | Reviewers can return to high-value triage views quickly, and reopened-case analytics now capture reason codes more consistently. |
| 2026-04-13 | âœ… Moved similarity presets into a shared server-backed AI Operations library with list/create/delete endpoints. | Reviewers can now reuse the same triage views across the team instead of losing them in browser-local storage. |
| 2026-04-13 | âœ… Added queue metrics for quick queues and shared similarity presets in AI Operations. | Reviewers can now see count, average age, reopened rate, and low-extraction rate before opening a queue. |
| 2026-04-13 | âœ… Added reopened-reason trend cards to reviewer analytics in AI Operations. | Reviewers can now see whether reasons like `Extraction quality` or `Low evidence` are rising, falling, or flat across recent review windows. |
| 2026-04-13 | âœ… Added queue workload forecasting, cross-assignment shadow evidence, OCR extraction diagnostics, and rubric-grounded criterion outputs across backend and frontend. | Similarity review is now more evidence-first, evaluation preview/save parity is rubric-aware, and low-text OCR risk is visible instead of hidden. |
| 2026-04-13 | âœ… Re-ran targeted backend trust-control tests and completed a passing frontend production build. | Verified queue forecast, OCR diagnostics persistence, cross-assignment shadow isolation, rubric preview/save parity, and the updated AI Operations/evaluation UI build. |
| 2026-04-13 | âœ… Split reviewer progress from finalized outcomes, added finalization-pipeline telemetry, and introduced stale/calibration-ready reviewer queues. | Semantic calibration now counts only real finalized outcomes, AI Operations shows why rollout is still blocked, and reviewers can close stale cases faster. |
| 2026-04-14 | âœ… Added similarity decision modes, suppression reasons, risk signals, semantic review candidates, and Unicode-aware transliterated mixed-language handling. | Wrongful auto-flags are reduced, mixed-language review visibility is higher, and AI Operations can explain why a case was flagged, downgraded, or held. |
| 2026-04-14 | âœ… Added a dedicated false-positive / false-negative regression artifact and hardened fallback fairness scoring for concise technical answers. | Prompt-heavy originals, boilerplate overlaps, paraphrase review candidates, low-text holds, and formula-heavy fairness checks now pass under targeted tests and artifact runs. |
| 2026-04-14 | âœ… Re-ran targeted backend trust tests, refreshed fairness + FP/FN artifacts, and completed a passing frontend production build. | Verified six targeted backend tests, passing fairness/FP-FN artifacts, and a clean AI Operations frontend build after the new trust-hardening UI changes. |
| 2026-04-14 | âœ… Added semantic rollout readiness reporting, calibration-eligible scope/language filters, readiness queue slices, and AI Operations readiness cards. | Promotion guidance is now explicitly manual and blocker-based across same-assignment, cross-assignment, and multilingual coverage before any semantic auto-flag rollout. |
| 2026-04-14 | âœ… Re-ran semantic-readiness backend regression slice and rebuilt frontend production bundle. | Verified 10 targeted backend tests for readiness/filter/queue behavior and a passing Vite production build for the new AI Operations controls. |
| 2026-04-14 | âœ… Added semantic rollout admin governance APIs with persisted config, blocker-guarded recommendation apply flow, and audit history; then re-ran targeted backend tests. | Manual threshold adoption is now explicit and traceable, AI Ops readiness reflects persisted config, and 5 targeted backend tests passed for the new governance slice. |
| 2026-04-14 | âœ… Added semantic rollout governance controls to the AI Operations frontend and rebuilt the production bundle. | Admins can now edit thresholds, apply recommendations, inspect blockers, and review recent config history directly in the AI module; the Vite production build passed again. |
| 2026-04-14 | âœ… Added readiness trends, blocker-aging telemetry, and legacy finalization validation across calibration analytics and AI Operations, then re-ran targeted backend tests and rebuilt the frontend. | Phase 1 semantic-readiness hardening is now complete: empty/legacy data stays visible, blockers age over time, and rollout evidence is easier to trust before Phase 2 governance work. |
| 2026-04-14 | âœ… Completed Phase 2 semantic promotion governance with versioned snapshots, explicit approve/activate/rollback actions, per-scope promotion states, compatibility alias APIs, targeted backend tests, and a passing frontend production build. | Semantic rollout governance is now decision-traceable and reversible while semantic signals stay assist-only for all scopes. |
| 2026-04-14 | âœ… Completed Phase 3 OCR productionization + cross-assignment trust completion: provider-adapter OCR integration, retry/timeout/result diagnostics, low-text insufficient-evidence guidance, and cross-assignment reversal analytics in AI Operations. | Reviewer trust is stronger because weak extraction is explicitly triaged, OCR recovery state is auditable, and cross-assignment reviewer reversals are visible as trends/rankings. |
| 2026-04-14 | âœ… Expanded Fairness + FP/FN governance (P0) with minimum-volume gate enforcement, external dataset hooks, multilingual fairness tolerance hardening, and AI Operations quality-gate coverage visibility; re-ran targeted backend regression tests. | Trust controls now fail fast on undercoverage, default fairness/FP-FN suites remain green, and reviewers can see governance coverage directly in ops. |

---

## ðŸ“ˆ PROGRESS

| Phase | Status | Notes |
|-------|--------|------|
| Audit baseline | âœ… Fixed | Code, docs, artifacts, and tests reviewed. |
| Semantic readiness hardening (Phase 1) | âœ… Fixed | Finalized-only calibration, scope/language blockers, readiness trends, blocker aging, legacy-row validation, and AI Ops visibility are now complete. |
| Manual semantic promotion governance (Phase 2) | âœ… Fixed | Versioned snapshots, explicit approve/activate/rollback flow, per-scope promotion states, compatibility aliases, and AI Ops governance controls are now complete. |
| OCR productionization + cross-assignment trust completion (Phase 3) | âœ… Fixed | OCR provider adapter path now includes retry/timeout/result diagnostics and low-text guidance, while AI Ops shows cross-assignment reversal ranking and trends for reviewer trust visibility. |
| Trust corrections | âœ… Fixed | Confidence is labeled as heuristic with mode badges, similarity evidence is visible, and finalized reviewer outcomes are now distinct from simple progress updates. |
| Fairness hardening | âš ï¸ In Progress | Regression gates now include minimum coverage governance, external dataset hooks, multilingual/technical controls, and AI Ops coverage visibility, but production-labeled multilingual and demographic datasets are still missing. |
| UX explainability uplift | âœ… Fixed | Numeric fallback hints are removed, ops quality gates plus reviewer analytics are visible, queue workload forecasting is live, cross-assignment shadow evidence is visible, rubric criterion rationale appears in evaluation flows, and stale/finalized review cues are explicit. |
| Performance validation | âœ… Fixed | Benchmark gates still pass, fairness/FP-FN artifacts complete quickly, and the frontend production build remains clean after AI Operations trust-UI expansion. |

---

## ðŸ” NEXT ACTIONS

- Immediate fix: Wire production-labeled external fairness + FP/FN datasets into CI/release gate paths and keep semantic assist-only while reviewing first real undercoverage failures.
- Next review: 2026-04-23
- Responsible: Backend lead + frontend lead + ML evaluation owner

---

# ðŸ“… ROADMAP SYSTEM

## âš–ï¸ IMPACT vs EFFORT

| Task | Impact | Effort | Priority | Decision |
|------|--------|--------|----------|----------|
| Add matched excerpts and reviewer resolution workflow | Very High | Medium | P0 | Done âœ… |
| Replace heuristic confidence with transparent reliability model | Very High | Medium | P0 | Done âœ… |
| Add multilingual and paraphrase similarity layer | High | High | P1 | Config + shadow pilot done; rollout in Phase 2 |
| Add lexical prefilter and async-only large-run handoff | Very High | Medium | P0 | Done âœ… |
| Add assignment-level retrieval caching and benchmark gate | Very High | Medium | P0 | Done âœ… |
| Add semantic shadow calibration and fairness regression gates | Very High | Medium | P0 | Done âœ… |
| Add reviewer-outcome calibration and AI Operations quality-gate visibility | Very High | Medium | P0 | Done âœ… |
| Add reviewer default queues, saved presets, and structured reopened reasons | High | Medium | P1 | Done âœ… |
| Add shared server-backed reviewer preset libraries | High | Medium | P1 | Done âœ… |
| Add similarity queue metrics for quick queues and shared presets | High | Medium | P1 | Done âœ… |
| Add reopened-reason trend cards in AI Operations | High | Medium | P1 | Done âœ… |
| Add reviewer finalization pipeline telemetry and stale/calibration-ready queues | Very High | Medium | P0 | Done âœ… |
| Unify AI preview and persisted evaluation payloads | High | Low | P1 | Done âœ… |
| Add queue workload forecasting for reviewer queues | High | Medium | P1 | Done âœ… |
| Add cross-assignment shadow evidence and language-profile metadata | High | Medium | P1 | Done âœ… shadow-only |
| Add rubric-grounded criterion outputs to preview/save flows | Very High | Medium | P1 | Done âœ… |
| Add OCR adapter diagnostics and extraction confidence | High | Medium | P1 | Done âœ… provider adapter + retry/result diagnostics shipped, rollout remains config-gated |
| Add mobile/tablet card layouts for review tables | Medium | Medium | P3 | In progress âš ï¸ keep extending responsive evidence layouts |
| Benchmark provider latency and 1000-candidate similarity load | Medium | Medium | P2 | Baseline captured âœ…, gates passing âœ…, expand production coverage in Phase 4 |

---

## ðŸ“… PHASES

Phase 1: Critical Fixes  
Add similarity evidence, relabel confidence, unify preview/save AI payloads, and block misleading score language.

Phase 2: Accuracy & Reliability  
Add semantic similarity, multilingual handling, OCR fallback, rubric-grounded scoring, and fairness regression tests.

Phase 3: UX & Explainability  
Build reviewer workflows, mobile/tablet responsive list variants, and clearer fallback/runtime explanations.

Phase 4: Performance  
Benchmark provider-backed evaluation latency, stress-test similarity at cap, and optimize assignment-level vector caching.

Phase 5: Advanced AI Features  
Add criterion-level explainable AI, teacher override analytics, confidence decomposition, and adaptive threshold tuning.

---

## ðŸš€ QUICK WINS

| Task | Impact | Effort | Benefit |
|------|--------|--------|---------|
| Broadened semantic similarity pilot (shadow score) | High | Medium | Captures more lexical-vs-semantic drift before any semantic flagging rollout. |
| Multilingual tokenization config | Medium | Medium | Prevents rollout drift by locking detector, tokenizer, stopword, and mixed-language choices now. |
| OCR extraction quality warning + diagnostics | High | Medium | Low-text submissions now surface OCR attempt, provider, chars added, confidence, and low-text reason instead of a generic warning only. |
| Lexical prefilter + async defer guard | High | Medium | Keeps large similarity runs out of the reviewer critical path while preserving durable processing. |
| Retrieval cache + benchmark gate | High | Medium | Makes candidate-cap similarity performance predictable and regression-tested. |
| Calibration + fairness artifacts | High | Medium | Makes semantic rollout and evaluation drift measurable before production changes ship. |
| Reviewer-outcome calibration + ops gate cards | High | Medium | Turns reviewed similarity logs into rollout evidence and makes drift visible without opening artifacts. |
| Reviewer queues + saved presets + structured reopen reasons | High | Medium | Speeds repeated triage work and makes reopened analytics materially more consistent. |
| Shared preset libraries | High | Medium | Lets reviewers reuse the same AI Operations triage views across the team instead of per-browser only. |
| Queue metrics + workload forecasting | High | Medium | Lets reviewers see volume, aging, low-text risk, and backlog pressure before opening a queue. |
| Reopened-reason trend cards | High | Medium | Makes rising reviewer reversal causes visible instead of leaving reopened reasons as a static count only. |

---

## âš ï¸ RISKS

| Risk | Cause | Mitigation |
|------|-------|------------|
| Academic misconduct false accusation | Score-only similarity output without evidence | Require excerpt evidence and human resolution before escalation. |
| Bias regression after prompt/runtime changes | No fairness benchmark gate | Add regression suite and change approval checklist. |
| Hidden missed matches in large cohorts | 1000-candidate cap and lexical-only engine | Surface cap warnings and add broader semantic retrieval. |
| User over-trust in fallback guidance | Legacy confidence expectations and heuristic wording can still be misread | Downgrade fallback presentation, explain backup-mode limitations, and keep provider/fallback mode visible. |

---

## ðŸŽ¯ EXECUTION PLAN

- Fix now: Semantic similarity pilot âœ… expanded, OCR extraction quality warning + diagnostics âœ…, OCR adapter contract âœ…, multilingual tokenization metadata âœ… shadowed, lexical prefilter âœ…, async-only large-run handoff âœ…, retrieval caching âœ…, benchmark gate âœ…, semantic shadow calibration âœ…, fairness regression gate âœ…, reviewer-outcome calibration âœ…, reviewer finalization pipeline âœ…, AI Operations quality-gate visibility âœ…, queue workload forecasting âœ…, cross-assignment shadow evidence âœ…, and rubric-grounded preview/save payloads âœ….
- Fix later: Full semantic rollout promotion, wider production-like fairness/FP-FN datasets, and multilingual coverage expansion after more finalized reviewer outcomes land.
- Remove: Probability-like wording for lexical similarity âœ… and authoritative fallback phrasing âœ… numeric fallback hints removed from chat/review text.
- Build later: Adaptive thresholds, preset-usage insights, admin-pinned queues, and advanced explainable AI panels.





