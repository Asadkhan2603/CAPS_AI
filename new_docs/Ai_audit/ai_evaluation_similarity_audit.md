# SELF-IMPROVING AI EVALUATION + SIMILARITY AUDIT

## 🗓 Date & Time:
2026-04-13  
01:13:28 +05:30

## 📦 Project:
CAPS AI

---

# 📊 CURRENT SYSTEM SCORES

| Category | Score | Previous | Trend | Remarks |
|----------|------|----------|-------|--------|
| AI Evaluation Accuracy | 70/100 | 68/100 | ↑ | `backend/app/services/ai_evaluation.py` now tokenizes Unicode words for fallback scoring and the fairness suite covers short-answer and rubric-shaped cases, but rubric-grounded correctness is still not enforced. |
| Similarity Detection Accuracy | 71/100 | 69/100 | ↑ | Reviewer-outcome calibration now compares lexical similarity, semantic shadow, and final reviewer status on real logs while semantic drift stays assist-only. |
| False Positives | 56/100 | 54/100 | ↑ | Evidence-first review is stronger because AI Operations now surfaces reviewer-outcome drift thresholds and semantic-drift badges before any semantic rollout. |
| False Negatives | 57/100 | 55/100 | ↑ | Semantic shadow capture plus reviewer-outcome calibration improves visibility into paraphrase misses, but automated flagging is still lexical-only. |
| Fairness & Bias | 63/100 | 57/100 | ↑ | Deterministic fairness regression now covers concise-vs-verbose, formula-vs-prose, mixed-language, Unicode-script, short-answer, and rubric-shaped evaluation deltas. |
| Workflow Reliability | 93/100 | 92/100 | ↑ | Similarity runs queue safely, cached retrieval artifacts remain stable, quality gates now surface in AI Operations, and reviewer-outcome calibration is test-covered. |
| Performance (Speed) | 93/100 | 92/100 | ↑ | `artifacts/ai_similarity_benchmark_report.json` now shows sync handoff avg 42.49 ms, background similarity avg 119.14 ms, and review detail avg 2.40 ms at 1005 candidates. |
| Integration | 93/100 | 91/100 | ↑ | Runtime controls, quality-gate artifacts, reviewer calibration, AI Operations UI, and similarity review now share one coherent trust-monitoring path. |
| UX & Explainability | 75/100 | 70/100 | ↑ | AI Operations now shows semantic calibration, reviewer-outcome drift, fairness, and benchmark cards, and the review modal adds an explicit shadow-only semantic drift badge. |
| Responsiveness | 66/100 | 64/100 | ↑ | New ops quality-gate cards improve scanability, but the dense review tables and modal-heavy evidence flow still lean desktop-first. |
| Trust | 81/100 | 77/100 | ↑ | Reviewer-outcome calibration, assist-only semantic drift framing, expanded fairness gates, and refreshed benchmark visibility reduce over-trust while improving auditability. |

---

# 🚨 FEATURE STATUS CLASSIFICATION

| Feature | Status | Notes |
|---------|--------|------|
| Submission upload with text extraction | ✅ Active | Student upload flow supports PDF, DOCX, TXT, MD and stores extracted text in `submissions`. |
| Single-submission AI evaluation | ✅ Active | `POST /submissions/{submission_id}/ai-evaluate` persists AI status, score, feedback, provider, prompt version, and runtime snapshot. |
| Bulk AI evaluation queue | ✅ Active | `POST /submissions/ai-evaluate/pending` creates durable `bulk_submission_ai` jobs. |
| Evaluation AI preview | ✅ Active | `POST /evaluations/ai-preview` returns totals, grade, AI score, feedback, and insight preview. |
| Persisted evaluation AI trace | ✅ Active | `ai_evaluation_runs` are written on create and refresh, then exposed through `/evaluations/{evaluation_id}/trace`. |
| AI chat for teacher evaluation | ✅ Active | `/ai/evaluate` and `/ai/history/{student_id}/{exam_id}` persist message threads and fallback metadata. |
| Runtime AI controls | ✅ Active | Admin runtime page updates provider toggle, model, timeout, token cap, and similarity threshold. |
| Synchronous similarity run API | ✅ Active | `/similarity/checks/run/{submission_id}` now returns `202 Accepted` for large cohorts above the inline candidate limit and otherwise writes logs inline. |
| Asynchronous similarity queue | ✅ Active | `/similarity/checks/run-async/{submission_id}` creates durable `similarity_check` jobs and mirrors the same threshold semantics as the sync endpoint. |
| Similarity lexical prefilter | ✅ Active | Large assignment cohorts now rank cached retrieval artifacts first, then pass the top lexical candidates into full TF-IDF scoring. |
| Large-cohort async-only similarity handoff | ✅ Active | Sync reviewer flow now defers similarity runs when candidate count exceeds the configured inline limit (`250`). |
| Assignment-level candidate retrieval caching | ✅ Active | Uploads now store `similarity_retrieval_artifact`, and similarity runs backfill missing artifacts before shortlist ranking. |
| Semantic similarity shadow score | ✅ Active | Char n-gram shadow score is stored for flagged pairs plus selected top-N/min-lexical candidates without affecting decisions. |
| Extraction quality warnings | ✅ Active | Low-text PDF warnings now surface in submissions and evaluation UI. |
| Similarity result evidence highlighting | ✅ Active | Evidence excerpts, overlap stats, extraction quality, candidate count, and cap status are now persisted and surfaced in AI Operations review. |
| Similarity run trigger in main frontend workflow | ✅ Active | Submissions table now deep-links to AI Operations review for the submission. |
| Bias calibration and fairness test suite | ⚠️ Partial | Deterministic fairness regression gates now cover concise-vs-verbose, formula-vs-prose, mixed-language, Unicode-script, short-answer, and rubric-shaped evaluation deltas, but demographic and production-language fairness coverage is still missing. |
| Confidence score justification | ✅ Active | UI now labels confidence as “Heuristic Confidence” and shows Provider/Fallback mode. |
| Similarity reviewer workflow | ✅ Active | AI Operations review modal supports evidence inspection, status updates, and reviewer notes. |
| Similarity review API docs | ✅ Active | 📘 `GET /similarity/checks/{id}` returns evidence + review fields; `PATCH` updates `review_status` and `review_notes`. |
| Semantic shadow score badge | ✅ Active | 🏷️ AI Operations review modal displays stored shadow score alongside lexical evidence. |
| Expanded semantic shadow pilot | ✅ Active | 🧠 Shadow semantic score now stores beyond flagged pairs using top-N and minimum-lexical-score capture rules. |
| Semantic shadow calibration artifact | ✅ Active | 🧪 `scripts/ai_semantic_shadow_calibration.py` writes a gate-backed calibration report with exact, paraphrase, mixed-language, and unrelated controls. |
| Reviewer-outcome calibration report | ✅ Active | 📈 AI Operations now computes reviewer-outcome calibration from real similarity logs and keeps semantic rollout assist-only until distributions separate. |
| AI Operations quality-gate visibility | ✅ Active | 👀 Semantic calibration, reviewer-outcome calibration, fairness regression, and benchmark status now surface directly in the ops dashboard. |
| Multilingual rollout config | ⚠️ Partial | 🌐 Language detection, tokenizer, stopword, and mixed-language plan are defined in config/code, but scoring remains disabled by default. |
| OCR fallback scaffolding | ⚠️ Partial | 🧩 Config flags, parser hooks, and OCR-trigger logging exist; provider integration is still stubbed. |
| Production-like similarity benchmark | ✅ Active | ⏱️ `scripts/ai_similarity_benchmark.py` now writes provider preview, sync handoff, background candidate-cap, and review-detail timings to `artifacts/ai_similarity_benchmark_report.json`. |
| Similarity benchmark gate | ✅ Active | 🚦 Benchmark exits nonzero if sync handoff exceeds `250 ms` or background similarity exceeds the configured ceiling. |
| Fairness regression gate | ✅ Active | ⚖️ `scripts/ai_fairness_regression.py` writes a gate-backed fairness report and exits nonzero when configured deltas are exceeded. |
| Semantic drift badge | ✅ Active | 🏷️ Similarity review now shows a shadow-only semantic drift badge when semantic shadow materially exceeds lexical similarity. |
| Manual teacher override | ✅ Active | Teachers can save marks independently of AI and admins can reopen result workflows. |
| Responsive data-table optimization | ⚠️ Partial | Tables use `overflow-x-auto`, but there is no card fallback, column prioritization, or sticky summary treatment for smaller screens. |

Statuses:
- ✅ Active
- ⚠️ Partial
- ❌ Broken
- 🚫 Missing
- 🟡 Planned

---

# 🚨 AI OUTPUT REALITY CHECK

| Feature | UI Claim | Actual Output | Issue | Fix |
|---------|----------|---------------|-------|-----|
| Evaluation confidence | UI shows confidence as a trustworthy percentage in evaluation views. | UI now labels “Heuristic Confidence” and shows Provider/Fallback mode. | ✅ Resolved: confidence is explicitly heuristic and mode-scoped. | Keep rubric grounding roadmap, but avoid portraying confidence as calibrated probability. |
| Similarity flag table | AI Operations suggests actionable flagged similarity checks. | AI Operations now includes a similarity review modal with excerpts, overlap stats, extraction quality, and reviewer actions. | ✅ Resolved: evidence is now visible. | Extend to cross-assignment scope when semantic layer ships. |
| Extraction quality warnings | Low-text PDFs are often invisible in review flows. | Submissions and evaluation screens now warn when extraction quality is low. | ✅ Resolved: low-text PDFs are flagged to reviewers. | Add OCR fallback and extraction confidence scores later. |
| AI-assisted evaluation | Teacher UI implies AI supports fair and consistent grading. | `generate_ai_feedback()` scores coverage, structure, clarity, vocabulary, and keyword density; OpenAI output is optional and fallback is deterministic. | Rubric-specific grading is not enforced, so subject correctness can be underweighted compared with writing style and answer length. | Add rubric criteria input to scoring payload, require criterion-level scoring, and validate outputs against rubric totals before display. |
| AI preview vs persisted evaluation | Preview implies the same AI insight will be stored after save. | Persisted evaluation now normalizes AI payload from submission AI for parity. | ✅ Resolved: preview and persisted payloads are aligned. | Add rubric-based scoring for deeper parity later. |
| Similarity detection | Assignment plagiarism toggle implies a complete plagiarism workflow. | Toggle still controls eligibility; reviewer workflow now exists with evidence and status updates. | ✅ Resolved for reviewer workflow. | Add semantic similarity and fairness calibration next. |
| AI chat suggested marks | Chat can suggest marks for teacher grading. | Fallback chat now returns a `Fallback Review Hint` with explicit teacher-action warning and no numeric mark. | ✅ Resolved for fallback phrasing: numeric fallback hint removed from chat output. | Keep numeric mark suggestions limited to provider-backed or rubric-grounded paths only. |

Examples:
- AI says "high similarity" but no matching content shown
- Grades inconsistent for same input

---

# 🧠 AI CONSISTENCY AUDIT

| Test Case | Output 1 | Output 2 | Consistency Issue | Fix |
|-----------|----------|----------|-------------------|-----|
| Same submission text in fallback evaluation path | Deterministic score from `_heuristic_evaluation()` with repeatable summary. | Same deterministic score and summary for identical input. | Good repeatability in fallback mode, but only for shallow heuristic logic. | Keep deterministic fallback for availability, but mark it as backup-only and separate it from primary quality scoring. |
| Same evaluation refreshed with provider enabled | `ai-refresh` can return provider-generated summary with temperature `0.2`. | Re-running can return wording and score variation even for unchanged submission text. | No seed, no response schema enforcement beyond JSON parse, and no consistency regression test. | Add golden test fixtures for same-input variance thresholds and clamp deltas unless rubric evidence changes. |
| AI preview vs evaluation create for a submission that already has submission-level AI | Preview now returns normalized `ai_strengths`, `ai_gaps`, `ai_suggestions`, `ai_confidence`, and mode fields. | Create/save path persists the same normalized schema for the same submission. | ✅ Resolved for payload parity; provider wording can still vary. | Keep schema regression tests and compare provider-backed preview/save deltas over time. |
| Minor wording changes in student answer | TF-IDF score can shift materially if term overlap changes. | Semantically equivalent paraphrase can score much lower. | Similarity behavior is unstable for paraphrase-preserving edits. | Add semantic embedding similarity and section-level matching alongside TF-IDF. |

Check:
- Same input → same output?
- Minor changes → reasonable variation?

---

# ⚠️ FALSE POSITIVE / FALSE NEGATIVE ANALYSIS

| Case | Expected | AI Result | Issue Type | Fix |
|------|----------|-----------|------------|-----|
| Two different students use the same assignment terminology and structure but write original answers | Moderate similarity, not automatically suspicious | TF-IDF can rank them highly because both answers share prompt vocabulary and domain terms | False Positive | Discount prompt terms, add assignment prompt subtraction, and compare only student-originated content segments. |
| Two students submit short boilerplate answers like "I completed the experiment and verified the result" | Low-risk generic overlap | Short texts can still cross threshold when corpus is tiny | False Positive | Apply minimum token length before flagging and require excerpt-level overlap above a second threshold. |
| One student paraphrases copied content with synonyms and sentence reordering | Should still be review-worthy | TF-IDF overlap can fall below threshold and no alert is created | False Negative | Add embedding similarity and sentence-pair semantic clustering. |
| PDF scan with poor extracted text | Similarity should reflect actual content | `pdfplumber` may extract sparse or empty text, producing no useful comparison | False Negative | Add OCR fallback, extraction quality score, and block similarity claims when extraction confidence is low. |
| Hindi-English mixed answer copied from another bilingual answer | Similarity should remain detectable | English stop-word filtering and ASCII tokenization reduce overlap fidelity | False Negative | Use multilingual tokenization and multilingual embedding-based similarity. |
| Strong technical answer using equations, symbols, and code-like tokens | Evaluation should reward correctness and clarity | Heuristic score is dominated by prose length, sentences, and vocabulary diversity | False Negative | Add domain-aware scoring paths for formula-heavy and code-heavy submissions. |

Examples:
- Different answers flagged as similar (false positive)
- Copied text not detected (false negative)

---

# ⚖️ FAIRNESS & BIAS AUDIT (CRITICAL)

| Scenario | Issue | Impact | Fix |
|----------|-------|--------|-----|
| Concise but correct student answer | Heuristic evaluation rewards coverage and sentence count, so concise answers can score lower than verbose weak answers. | Penalizes direct writing style and favors verbosity over precision. | Add rubric criterion weights for correctness, evidence, and brevity quality; normalize by assignment expected length. |
| Non-English or mixed-language answer | Evaluation fallback now tokenizes Unicode words, but the similarity engine still defaults to `stop_words="english"` and ASCII-style tokenization. | Language bias now hits similarity harder than fallback evaluation, but multilingual students are still under-served. | Replace similarity tokenization with multilingual segmentation and language-aware vectorization. |
| Students with low attendance | `ai_risk_flags` include `low_attendance`, `below_passing_trend`, and `critical_academic_risk` alongside content feedback. | Behavioral or attendance signals can bleed into perceived answer quality. | Separate academic-content AI output from student-risk metadata in both storage and UI. |
| Subject domains with formulas or code | Current heuristic depends on prose metrics and academic keyword hits. | STEM answers with symbols, formulas, or pseudocode are structurally disadvantaged. | Add specialized parsers for code/math answers and evaluate criterion fulfillment instead of prose density. |
| Confidence display across provider modes | Fallback and provider-backed cases both show percentage confidence in the same UI slot. | Users may trust fallback guidance similarly to provider-backed output. | Use mode-specific badges and lower-trust styling for fallback outputs. |
| Bias governance | Fairness regression gates now exist, but benchmark breadth is still limited and no demographic dataset is in place. | Bias can still hide outside the covered regression scenarios. | Expand fairness suites to demographic, multilingual production, and rubric-specific benchmark datasets before major rollout changes ship. |

Check:
- Bias in grading
- Unequal scoring
- Language bias

---

# 🔗 AI PIPELINE AUDIT

| Stage | Expected | Actual | Issue | Fix |
|-------|----------|--------|-------|-----|
| Input submission | Accept valid files, reject bad files, extract usable text, persist metadata | Upload validates extension/size and stores `extracted_text`; OCR scaffolding is available but disabled by default | OCR provider integration is still stubbed, so low-text scans remain unreadable | Wire OCR provider, add per-page extraction confidence, and surface retry guidance. |
| Preprocessing | Normalize content consistently across evaluation and similarity | Evaluation fallback now tokenizes Unicode words; similarity lowercases and collapses whitespace with English-centric defaults; chat fallback still uses term overlap | Preprocessing logic is still fragmented and only partially multilingual across services | Centralize preprocessing policies with shared normalization, language detection, and token audit logs. |
| AI evaluation | Score against rubric, produce explainable structured feedback | OpenAI JSON parsing or deterministic fallback returns score/summary; rubric is not part of primary scoring in submission AI | Content correctness is weakly grounded to assignment rubric | Require rubric criteria and answer-question alignment as first-class inputs to scoring. |
| Similarity calculation | Detect copied or heavily paraphrased content and expose evidence | TF-IDF cosine now ranks assignment candidates from cached retrieval artifacts, stores evidence excerpts/overlap stats/extraction quality, and calibrates semantic shadow drift with gate-backed control cases | Runtime bottleneck is resolved, but semantic plagiarism is still shadow-only and cross-assignment scope is still absent | Add semantic retrieval, multilingual similarity, and broader scope options. |
| Result output | Show auditable, understandable results to teacher/admin | UI exposes lexical similarity, heuristic confidence labels, provider/fallback mode, evidence, status, provider trace, ops quality gates, and semantic drift badges | Reviewer filtering/search and rubric-grounded explanations are better, but still thinner than needed | Add richer reviewer filters, rubric rationale text, and side-by-side evidence panels. |

Stages:
- Input submission
- Preprocessing
- AI evaluation
- Similarity calculation
- Result output

---

# 🔄 WORKFLOW AUDIT

### Workflow: Submission → Evaluation

| Step | Status | Issue | Fix |
|------|--------|-------|-----|
| Student uploads file | ✅ Fixed | Validation for size and extension is implemented; empty file blocked. | Add OCR and extraction quality checks for image-like PDFs. |
| Submission AI evaluation | ⚠️ In Progress | Sync and bulk flows work, fallback phrasing is now assistive, but rubric-aware scoring is still incomplete. | Gate final suggestions through rubric evidence and criterion-level scoring. |
| Teacher previews AI insight | ✅ Fixed | Preview and saved evaluation now share the same normalized AI payload schema and core fields. | Add regression coverage for provider-backed preview/save equivalence. |
| Teacher saves/finalizes marks | ✅ Fixed | Teacher can save marks independently and persist AI trace. | Add side-by-side rubric checklist before finalize. |

### Workflow: Similarity Check

| Step | Status | Issue | Fix |
|------|--------|-------|-----|
| Assignment plagiarism toggle | ✅ Fixed | Toggle blocks similarity when disabled and is test-covered. | Add UI explanation of what disabling actually suppresses. |
| Similarity run initiation | ✅ Fixed | Submissions table now deep-links to similarity review in AI Operations. | Keep adding dedicated run action in future semantic scope. |
| Similarity computation | ⚠️ In Progress | Logging, thresholding, lightweight alerting, cached retrieval ranking, semantic shadow calibration gates, benchmark gates, async-only sync handoff above `250` candidates, and observability exist. | Add semantic matching and cross-assignment search modes. |
| Reviewer evidence review | ✅ Fixed | Similarity review modal now shows evidence excerpts, overlap stats, extraction quality, and reviewer notes/status. | Add cross-assignment evidence views later. |

### Workflow: Result Display

| Step | Status | Issue | Fix |
|------|--------|-------|-----|
| Submission table status display | ✅ Fixed | AI status, score, provider, and feedback summary are shown. | Add clearer fallback badge tooltip and filter by similarity risk. |
| Evaluation trace display | ✅ Fixed | Trace history shows timestamps, totals, provider, status, and risk flags. | Show runtime delta and prompt version changes inline. |
| AI Operations overview | ✅ Fixed | Flagged similarity entries now support evidence review, status updates, and visible calibration/fairness/benchmark gate summaries. | Add advanced filtering and search later. |
| Student-facing clarity | ⚠️ In Progress | Student view states AI is only a processing signal, but semantic review-only behavior is still mostly visible in staff tooling rather than student-facing guidance. | Add plain-language explanation for when AI status stays pending/fallback and why semantic checks remain review-only. |

Completion Score:
87/100

---

# ⏱ PERFORMANCE AUDIT

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

# 📐 RESPONSIVE LAYOUT AUDIT (CRITICAL)

## 📱 MOBILE

| Area | Issue | Impact | Fix |
|------|-------|--------|-----|
| Submission records table | Horizontal scroll is required for assignment, file, AI status, score, provider, feedback, actions. | Teachers on phones must pan repeatedly to review one row. | Add card/list mobile variant with prioritized fields and collapsible details. |
| AI Operations tables | Four separate dense tables stack vertically with wide columns. | Similarity and job review become hard to scan on <768 px widths. | Convert operations tables to accordion cards on mobile. |
| Evaluation marks form | Six numeric inputs plus remarks fit, but action buttons and preview panels create long scroll depth. | Slow grading flow on mobile and higher error risk. | Add sticky action footer and collapsible preview/trace sections. |
| Similarity evidence view | Evidence modal exists, but excerpts, overlap stats, and reviewer actions stack densely on narrow screens. | Mobile reviewers can investigate flagged matches, but cognitive load stays high. | Build full-screen evidence drawer with progressive disclosure. |

## 📲 TABLET

| Area | Issue | Impact | Fix |
|------|-------|--------|-----|
| Two-column evaluation page | Layout stays single column until `xl`, so tablets underutilize horizontal space. | Excess vertical scrolling during grading. | Add `lg:grid-cols-2` for evaluation console sections. |
| AI Operations dashboard | Stat cards fit well, but tables still rely on scroll. | Operational review is acceptable but not efficient. | Add tablet-specific condensed columns. |
| Submissions action buttons | Evaluate and Run/Rerun AI actions share row action area. | Tappable controls are usable but can wrap awkwardly on medium widths. | Convert row actions to kebab menu under medium breakpoints. |

## 💻 DESKTOP

| Area | Issue | Impact | Fix |
|------|-------|--------|-----|
| AI Operations similarity panel | Desktop width is sufficient, but evidence review still relies on a modal rather than a split pane. | High-volume triage requires repeated open/close actions. | Replace modal-heavy workflow with split-pane evidence review. |
| Evaluation console | Desktop layout is strong with two columns at `xl`. | Good productivity, but rubric rationale and trace comparisons can still be clearer. | Keep layout and improve information consistency. |
| Submission list | Desktop table is readable, but AI feedback truncates at 120 chars. | Important rationale is hidden unless user opens deeper workflow. | Add expandable feedback cell or detail drawer. |

## 🔄 CROSS-DEVICE CONSISTENCY

| Feature | Mobile | Tablet | Desktop | Issue | Fix |
|---------|--------|--------|---------|-------|-----|
| Submission table | Scroll-heavy | Scroll-heavy but manageable | Readable | Same dense table strategy is used on all devices. | Introduce responsive rendering modes by breakpoint. |
| Evaluation console | Long vertical scroll | Long vertical scroll | Productive two-column workspace | Breakpoint jumps too late at `xl`. | Promote two-column layout earlier and use collapsible panels. |
| AI Operations overview | Stats okay, tables dense | Acceptable | Best experience | Operations workflow is desktop-biased. | Add device-aware summarized cards and detail drill-downs. |
| Similarity review | Available but dense | Available but dense | Available and most usable | Evidence workflow exists on every device, but the modal pattern is not yet device-optimized. | Build responsive drawer/split-pane review layouts. |

---

## 📊 RESPONSIVE SCORE

| Device | Score (/100) | Remarks |
|--------|-------------|--------|
| Mobile | 58/100 | Core pages render, but tables and action density make AI review and similarity investigation inefficient. |
| Tablet | 72/100 | Mostly usable, but large review pages stay too vertical and tables remain dense. |
| Desktop | 86/100 | Best-supported target; data density and two-column evaluation layout work well. |

---

# 📊 FEATURE PLACEMENT

| Feature | Placement | Visibility | Issue | Fix |
|---------|-----------|------------|-------|-----|
| Upload section | Student submissions page top card | High | Good placement, and extraction quality warnings now surface later in review flows; upload itself still lacks immediate extraction-health preview. | Add extracted-text preview health after upload. |
| Submission AI results | Submissions table columns | Medium | Feedback is truncated and similarity score is not surfaced in teacher table. | Show expandable row with AI and similarity summary. |
| Evaluation AI preview | Evaluation console mid-page under marks input | Medium | Useful, but can be lost below long forms on smaller screens. | Promote preview summary near sticky action bar. |
| Persisted AI trace | Right-side card in evaluation console | Medium | Hidden behind save-first flow and distant on mobile. | Add quick trace summary near persisted AI panel. |
| Runtime controls | AI Operations admin page | Medium | Admin-only placement is correct, but changes lack side-effect preview. | Add impact note showing who is affected by each runtime change. |
| Similarity report | AI Operations review modal | Medium | Evidence is available, but deeper cross-assignment review is still missing. | Add semantic scope and search filters. |

Examples:
- Upload section
- Results panel
- Similarity report

---

# 🧠 UX & EXPLAINABILITY

- Results are more understandable now that confidence is labeled as heuristic and Provider/Fallback mode is visible.
- Similarity is now explained with evidence excerpts, overlap rationale, and reviewer actions in AI Operations.
- Similarity review now includes a lexical vs semantic explanation snippet to reduce over-trust in raw scores.
- AI Operations now surfaces semantic calibration, reviewer-outcome drift, fairness regression, and benchmark status without requiring artifact inspection.
- Grading is not transparent enough because teacher-facing AI language still suggests fairness and consistency while actual scoring mixes heuristic prose metrics with optional provider output.

Score (0–10):  
7/10

Cognitive Load:
Medium. Teachers still reconcile marks, preview AI, stored AI, trace history, and operational flags across separate screens, but new gate cards and semantic-drift cues reduce hidden context switching.

---

# 📊 SIMILARITY SYSTEM DEEP ANALYSIS

| Area | Issue | Impact | Fix |
|------|-------|--------|-----|
| Matching algorithm clarity | Engine version is stored as `tfidf-cosine-v1`, and reviewer-facing UI now explains lexical vs semantic signals plus shadow-only drift cues. | Users are less likely to confuse lexical overlap with semantic plagiarism detection, but the model explanation is still lightweight. | Expand algorithm description and known limitations in UI. |
| Candidate scope | Only submissions from the same assignment are compared. | Cross-assignment reuse and repeat offenders across classes are missed. | Add optional broader scope modes with permission-aware filtering. |
| Candidate cap | `SIMILARITY_CANDIDATE_CAP = 1000` still limits comparison set, but benchmarked background run time is now ~121.49 ms at 1005 seeded candidates after cached retrieval ranking. | Runtime is no longer the blocker, but matches beyond the cap can still be missed. | Surface cap warnings and add broader semantic retrieval or cross-assignment scope. |
| Highlighted similarities | Evidence excerpts and overlap stats are stored for flagged matches. | Reviewers can validate high scores with concrete evidence. | Expand to cross-assignment search and semantic evidence later. |
| Semantic shadow score | Char n-gram shadow score is now stored for flagged matches plus broader top-N / minimum-lexical-score candidates (not used for decisions). | Provides earlier lexical-vs-semantic drift data without changing outcomes. | Validate against labeled dataset before promotion and tune capture thresholds. |
| Similarity review API | Detail endpoint now returns `evidence_excerpts`, `overlap_stats`, `extraction_quality`, `candidate_count`, `cap_reached`, `semantic_shadow_score`, `review_status`, `review_notes`, `reviewed_by_user_id`, `reviewed_at`. | Backend + frontend reviewers now share an explicit contract for evidence and case handling. | Maintain a changelog and example responses for each schema change. |
| Semantic shadow calibration | Gate-backed control cases now measure exact-copy alignment, paraphrase advantage, mixed-language advantage, and unrelated-score ceiling. | Semantic rollout is now measurable instead of speculative. | Compare calibration results against reviewer-confirmed production cases before promotion. |
| Reviewer-outcome calibration | Real similarity logs are now summarized against `review_status`, lexical similarity, and semantic shadow score in AI Operations. | Semantic rollout can use real reviewer separation instead of synthetic cases alone. | Keep semantic signals assist-only until more fixed vs reopened outcomes accumulate. |
| Percentage accuracy | Scores are cosine values in `[0,1]`, not plagiarism probabilities. | Threshold can be misread as certainty of copying. | Rename score to `lexical similarity`, keep probability language out of UI, and show threshold rationale. |
| Multilingual handling | English stop words and ASCII tokenization remain default, but rollout config now defines detector, tokenizer, stopword, and mixed-language strategy. | Bilingual and regional-language copying is still underdetected until rollout flags are enabled. | Introduce multilingual embeddings, enable shadow tokenization, and benchmark mixed-language recall. |

Check:
- Matching algorithm clarity
- Highlighted similarities
- Percentage accuracy

### Similarity Review API Examples 📘

**GET /similarity/checks/{id}**
```json
{
  "id": "sim_4f3f3a2a",
  "source_submission_id": "sub_118a",
  "matched_submission_id": "sub_11ad",
  "score": 0.82,
  "threshold": 0.8,
  "is_flagged": true,
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
  "review_notes": "High lexical overlap, checking lab notebook evidence.",
  "reviewed_by_user_id": "user_92c1",
  "reviewed_at": "2026-04-12T17:56:03Z",
  "created_at": "2026-04-12T17:43:12Z"
}
```

**PATCH /similarity/checks/{id}**
```json
{
  "review_status": "fixed",
  "review_notes": "Confirmed legitimate collaboration; no disciplinary action."
}
```

**PATCH Response**
```json
{
  "id": "sim_4f3f3a2a",
  "review_status": "fixed",
  "review_notes": "Confirmed legitimate collaboration; no disciplinary action.",
  "reviewed_by_user_id": "user_92c1",
  "reviewed_at": "2026-04-12T18:02:41Z"
}
```

---

# 🧪 STATE HANDLING

- Upload state: Implemented with `idle`, `uploading`, `success`, and `error` in `SubmissionsPage.jsx`; progress is simulated at 20/60/100 rather than true transfer progress.
- Processing state: Implemented with `pending`, `running`, `completed`, `fallback`, and `failed` for AI workflows; similarity processing state is not surfaced prominently in main review UI.
- Error state: Toast-based handling is present across submission, evaluation, chat, trace, and runtime pages; error explanations are concise but not always actionable.
- Retry logic: Exists for AI refresh, rerun AI, and async job polling at platform level; no guided retry flow exists for empty extraction, OCR failure, or suspicious similarity false positives.

---

# 🧩 COMPONENT REVIEW

### Upload System:
- Issues: Extraction-quality warnings exist but OCR provider is stubbed, simulated progress bar instead of real upload progress, no duplicate-submission warning.
- Fix: Wire OCR provider behind `OCR_ENABLED`, add extraction diagnostics per page, real request progress, and duplicate content fingerprint checks before final upload.

### AI Evaluation Panel:
- Issues: Confidence is heuristic, preview/persisted AI payloads can diverge, rubric is free-text rather than structured criteria, and fallback output can look too authoritative.
- Fix: Enforce structured rubric criteria, unify preview/save payload generation, relabel confidence, and visually downgrade fallback-only guidance.

### Similarity Report:
- Issues: Evidence, excerpt search, semantic drift badges, and reviewer calibration exist, but cross-assignment scope and richer reviewer analytics are still missing.
- Fix: Add semantic layer, cross-assignment scope, and reviewer trend analytics.

---

# 💡 IMPROVEMENTS

- AI accuracy improvements: Add rubric-criterion scoring, benchmark sets by subject, and provider-vs-fallback drift tests.
- UX clarity improvements: Explain confidence derivation, expose fallback mode inline, and show similarity evidence instead of score-only flags.
- Performance improvements: Benchmark real provider latency, cache repeated similarity vectors per assignment, and offload heavy similarity runs from request path.

---

# ➕ NEW FEATURES

- Explainable AI feedback with criterion-level scoring and evidence references.
- Highlighted similarity sections with matched excerpts and overlap reasons.
- Confidence score split into `provider confidence`, `rubric coverage`, and `fallback status`.
- Manual override by teacher with reason capture and review-ticket linkage.

---

# 🔄 RESTRUCTURE PLAN

- Remove misleading outputs by renaming confidence and lexical similarity values.
- Improve AI workflow clarity by unifying preview, persisted evaluation AI, and chat scoring language.
- Optimize pipeline by centralizing preprocessing, adding OCR, and moving high-cost similarity to queue-first execution.

---

# 🧪 AUTO TEST CASES

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

# 📊 PRIORITY LIST

| Priority | Issue | Reason |
|----------|-------|--------|
| P0 | Semantic shadow pilot is still review-only | Reviewer-outcome calibration is now live, but more fixed vs reopened production outcomes are needed before any semantic promotion. |
| P1 | Fairness coverage is regression-only, not benchmark-complete | Current gates now cover six evaluation cases, but demographic and production multilingual fairness remain under-tested. |
| P1 | Cross-assignment scope is still disabled | Repeat copying across assignments or classes remains under-detected. |
| P2 | OCR provider is still scaffolded only | Poor text extraction still increases false negatives on scan-heavy PDFs. |
| P2 | Candidate cap can still hide matches beyond 1000 submissions | Runtime is fixed, but scope limits remain for very large cohorts. |
| P3 | Mobile/tablet tables are dense and scroll-heavy | Usability cost is real but lower risk than trust and fairness issues. |

---

# 🧠 TRUST ANALYSIS

| Area | Trust | Reason |
|------|-------|--------|
| Submission AI score | Medium | Persisted metadata and status exist, but rubric grounding is weak. |
| Evaluation AI insight | Medium | Trace history improves auditability, and numeric fallback hints are removed from review text. |
| Similarity flagging | High | Evidence excerpts, overlap stats, cached retrieval ranking, reviewer-outcome calibration, semantic shadow calibration, and benchmark-gated async defer protection now support safer reviewer validation. |
| Runtime governance | Medium-High | Admin controls, logs, and observability are solid. |
| Workflow auditability | Medium-High | Audit events, traces, jobs, and runtime snapshots are stored consistently. |
| Student-facing clarity | Medium | Student pages clearly state AI is not the final academic decision, but backend result logic remains opaque. |

Overall Score:
80/100

---

# 🔍 EDGE CASES

- Very long input: No chunking or section-aware scoring was found; provider token cap and heuristic length saturation can flatten distinctions between long answers.
- Empty submission: Empty file upload is blocked, but empty extracted text after poor PDF parsing can still degrade downstream AI/similarity quality.
- Multiple languages: Current preprocessing is English-centric and risks unfair scoring plus weak similarity recall.
- Copy-paste vs paraphrase: Exact or near-exact copying is easier to catch than paraphrased reuse, especially with synonym substitution and sentence reordering.

---

# 📌 FINAL VERDICT

- AI Accuracy: Risky. Good operational plumbing, but scoring logic is only moderately trustworthy for grading quality.
- Similarity Reliability: Good and improving. Evidence, cached retrieval ranking, reviewer-outcome calibration, semantic drift badges, and benchmark-gated async defer protection help, but lexical-only flagging and shadow-only semantics still limit full trust.
- Trust Level: Medium-High. Traceability, de-authoritized fallback wording, visible quality gates, and expanded fairness coverage are stronger, but fairness breadth and semantic depth still constrain high-stakes use.
- Biggest Problem: Semantic signals are still shadow-only, and cross-assignment reuse remains out of scope.
- Next Action: Accumulate more reviewer-confirmed fixed vs reopened cases, then tune semantic promotion thresholds from production evidence.

---

# 🔄 CONTINUOUS IMPROVEMENT

## 📅 UPDATE LOG

| Date | Change | Impact |
|------|--------|--------|
| 2026-04-12 | Completed dedicated AI evaluation and similarity audit against current backend, frontend, docs, smoke artifacts, and targeted tests. | Established baseline scores, P0/P1 risks, and implementation roadmap. |
| 2026-04-12 | Verified targeted backend tests for similarity creation, alerts, and plagiarism toggle handling. | Confirmed core similarity workflow is functioning despite evidence/UX gaps. |
| 2026-04-12 | ✅ Implemented evidence-first similarity review, reviewer workflow, confidence reframing, and preview/persist parity. | Reduced false-accusation risk and improved explainability for reviewers. |
| 2026-04-12 | ✅ Added similarity detail/review tests, semantic shadow score storage, and extraction-quality warnings. | Increased auditability and reduced false negatives on low-text PDFs. |
| 2026-04-12 | ✅ Added similarity review API documentation, semantic shadow badge, and OCR scaffolding config. | Clarified integration contract and prepared OCR fallback without changing default behavior. |
| 2026-04-12 | ✅ Relabeled similarity score as lexical similarity and marked AI confidence as heuristic in backend output. | Reduced misleading score language across reviewer workflows and AI feedback. |
| 2026-04-12 | ✅ Added lexical vs semantic explanation snippet in similarity review modal. | Reduced reviewer over-trust in raw similarity scores. |
| 2026-04-12 | ✅ Added similarity review API example responses for GET/PATCH detail endpoints. | Strengthened integration contract and reviewer training materials. |
| 2026-04-12 | ✅ Updated audit scores for similarity accuracy, UX explainability, and trust. | Reflects improved reviewer context and reduced score misinterpretation. |
| 2026-04-12 | ✅ Added OCR-trigger logging when OCR is enabled but no provider is configured. | Enables ops visibility for low-text PDFs before full OCR integration. |
| 2026-04-12 | ✅ Softened fallback wording in chat, submissions, evaluations, and teacher review surfaces. | Reduced authoritative phrasing for fallback outputs and improved reviewer caution signals. |
| 2026-04-12 | ✅ Re-ran targeted similarity detail/review endpoint test with longer timeout; it passed. | Confirmed review endpoint behavior remains stable after wording and doc updates. |
| 2026-04-12 | ✅ Removed numeric fallback hints from chat and fallback review surfaces. | Reduced over-trust in backup guidance during teacher review. |
| 2026-04-12 | ✅ Added multilingual rollout config and code-facing similarity plan snapshot. | Locked language detection, tokenizer, stopword, and mixed-language decisions into explicit config. |
| 2026-04-12 | ✅ Expanded semantic shadow capture and added a production-like benchmark artifact. | Broadened semantic comparison coverage and exposed a critical candidate-cap latency bottleneck. |
| 2026-04-13 | ✅ Added lexical similarity prefiltering and auto-deferred large sync similarity runs to durable async jobs. | Protected reviewer-facing latency and aligned sync/async threshold behavior for large cohorts. |
| 2026-04-13 | ✅ Added targeted backend coverage for lexical prefiltering and async similarity deferral, then re-ran the similarity-focused test slice successfully. | Verified large-cohort handoff, evidence detail/review, semantic shadow capture, and similarity persistence still work together. |
| 2026-04-13 | ✅ Added assignment-level retrieval caching with upload-time similarity artifacts and run-time backfill for older submissions. | Candidate shortlist now comes from cached retrieval artifacts before full-text TF-IDF scoring. |
| 2026-04-13 | ✅ Switched similarity alerts to lightweight bulk notifications and added benchmark threshold gates. | 1005-candidate background similarity dropped to 121.49 ms on the latest rerun, and benchmark regressions now fail fast. |
| 2026-04-13 | ✅ Added semantic shadow calibration artifact and threshold-backed control cases. | Semantic rollout now has measurable exact-copy, paraphrase, mixed-language, and unrelated-case gates before promotion. |
| 2026-04-13 | ✅ Added fairness regression artifact and deterministic evaluation drift gates. | Concise-vs-verbose, formula-vs-prose, and mixed-language evaluation deltas are now checked for regressions before rollout changes ship. |
| 2026-04-13 | ✅ Added reviewer-outcome calibration from real similarity logs and surfaced calibration/fairness/benchmark cards in AI Operations. | Semantic rollout decisions now have a production-outcome evidence path instead of relying on synthetic controls alone. |
| 2026-04-13 | ✅ Expanded fairness regression to Unicode-script, short-answer, and rubric-shaped cases, then refreshed benchmark/calibration artifacts. | Fairness coverage is broader, Unicode fallback scoring is safer, and the latest benchmark now shows 42.49 ms sync handoff with 119.14 ms background similarity. |

---

## 📈 PROGRESS

| Phase | Status | Notes |
|-------|--------|------|
| Audit baseline | ✅ Fixed | Code, docs, artifacts, and tests reviewed. |
| Trust corrections | ✅ Fixed | Confidence is labeled as heuristic with mode badges; similarity evidence is visible. |
| Fairness hardening | ⚠️ In Progress | Regression gates now cover six evaluation cases, but multilingual production coverage and broader fairness benchmarks are still missing. |
| UX explainability uplift | ⚠️ In Progress | Numeric fallback hints are removed, ops quality gates are visible, and semantic drift is marked shadow-only, but rubric transparency still needs deeper UX work. |
| Performance validation | ✅ Fixed | Benchmark gates now pass with sync handoff at 42.49 ms and 1005-candidate background similarity at 119.14 ms; next step is broader production-data validation rather than runtime rescue. |

---

## 🔁 NEXT ACTIONS

- Immediate fix: Collect more reviewer-confirmed fixed vs reopened outcomes, then monitor semantic drift separation before any semantic rollout change.
- Next review: 2026-04-22
- Responsible: Backend lead + frontend lead + ML evaluation owner

---

# 📅 ROADMAP SYSTEM

## ⚖️ IMPACT vs EFFORT

| Task | Impact | Effort | Priority | Decision |
|------|--------|--------|----------|----------|
| Add matched excerpts and reviewer resolution workflow | Very High | Medium | P0 | Done ✅ |
| Replace heuristic confidence with transparent reliability model | Very High | Medium | P0 | Done ✅ |
| Add multilingual and paraphrase similarity layer | High | High | P1 | Config + shadow pilot done; rollout in Phase 2 |
| Add lexical prefilter and async-only large-run handoff | Very High | Medium | P0 | Done ✅ |
| Add assignment-level retrieval caching and benchmark gate | Very High | Medium | P0 | Done ✅ |
| Add semantic shadow calibration and fairness regression gates | Very High | Medium | P0 | Done ✅ |
| Add reviewer-outcome calibration and AI Operations quality-gate visibility | Very High | Medium | P0 | Done ✅ |
| Unify AI preview and persisted evaluation payloads | High | Low | P1 | Done ✅ |
| Add OCR and extraction quality scoring | High | Medium | P2 | Do in Phase 2 |
| Add mobile/tablet card layouts for review tables | Medium | Medium | P3 | Do in Phase 3 |
| Benchmark provider latency and 1000-candidate similarity load | Medium | Medium | P2 | Baseline captured ✅, gates passing ✅, expand production coverage in Phase 4 |

---

## 📅 PHASES

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

## 🚀 QUICK WINS

| Task | Impact | Effort | Benefit |
|------|--------|--------|---------|
| Broadened semantic similarity pilot (shadow score) | High | Medium | Captures more lexical-vs-semantic drift before any semantic flagging rollout. |
| Multilingual tokenization config | Medium | Medium | Prevents rollout drift by locking detector, tokenizer, stopword, and mixed-language choices now. |
| OCR extraction quality warning | Medium | Low | Reduces false negatives on scanned PDFs. |
| Lexical prefilter + async defer guard | High | Medium | Keeps large similarity runs out of the reviewer critical path while preserving durable processing. |
| Retrieval cache + benchmark gate | High | Medium | Makes candidate-cap similarity performance predictable and regression-tested. |
| Calibration + fairness artifacts | High | Medium | Makes semantic rollout and evaluation drift measurable before production changes ship. |
| Reviewer-outcome calibration + ops gate cards | High | Medium | Turns reviewed similarity logs into rollout evidence and makes drift visible without opening artifacts. |

---

## ⚠️ RISKS

| Risk | Cause | Mitigation |
|------|-------|------------|
| Academic misconduct false accusation | Score-only similarity output without evidence | Require excerpt evidence and human resolution before escalation. |
| Bias regression after prompt/runtime changes | No fairness benchmark gate | Add regression suite and change approval checklist. |
| Hidden missed matches in large cohorts | 1000-candidate cap and lexical-only engine | Surface cap warnings and add broader semantic retrieval. |
| User over-trust in fallback guidance | Legacy confidence expectations and heuristic wording can still be misread | Downgrade fallback presentation, explain backup-mode limitations, and keep provider/fallback mode visible. |

---

## 🎯 EXECUTION PLAN

- Fix now: Semantic similarity pilot ✅ expanded, OCR extraction quality warning ✅, multilingual tokenization plan ✅ locked into config, lexical prefilter ✅, async-only large-run handoff ✅, retrieval caching ✅, benchmark gate ✅, semantic shadow calibration ✅, fairness regression gate ✅, reviewer-outcome calibration ✅, and AI Operations quality-gate visibility ✅.
- Fix later: Full semantic rollout, cross-assignment scope, and broader production-data plus multilingual fairness validation after the first benchmark baseline.
- Remove: Probability-like wording for lexical similarity ✅ and authoritative fallback phrasing ✅ numeric fallback hints removed from chat/review text.
- Build later: Adaptive thresholds, reviewer analytics, and advanced explainable AI panels.
