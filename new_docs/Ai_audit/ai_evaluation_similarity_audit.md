# SELF-IMPROVING AI EVALUATION + SIMILARITY AUDIT

## 🗓 Date & Time:
2026-04-13  
12:46:23 +05:30

## 📦 Project:
CAPS AI

---

# 📊 CURRENT SYSTEM SCORES

| Category | Score | Previous | Trend | Remarks |
|----------|------|----------|-------|--------|
| AI Evaluation Accuracy | 78/100 | 70/100 | ↑ | Preview/save flows now accept normalized `rubric_criteria`, compute criterion-level scores/rationales, and persist the same rubric-grounded payload shape through evaluation records and traces. |
| Similarity Detection Accuracy | 82/100 | 76/100 | ↑ | Similarity logs now store `match_scope`, `language_profile`, extraction diagnostics, and cross-assignment shadow candidates while queue forecasting and reviewer evidence reduce blind spots in staff review. |
| False Positives | 57/100 | 56/100 | ↑ | Evidence-first review is stronger because AI Operations now surfaces reviewer-outcome drift thresholds, semantic-drift badges, and structured reopened reasons before any semantic rollout. |
| False Negatives | 58/100 | 57/100 | ↑ | Semantic shadow capture plus reviewer-outcome calibration improves visibility into paraphrase misses, and saved queues make low-text and high-drift triage easier, but automated flagging is still lexical-only. |
| Fairness & Bias | 63/100 | 57/100 | ↑ | Deterministic fairness regression now covers concise-vs-verbose, formula-vs-prose, mixed-language, Unicode-script, short-answer, and rubric-shaped evaluation deltas. |
| Workflow Reliability | 96/100 | 95/100 | ↑ | Similarity runs queue safely, cached retrieval artifacts remain stable, quality gates now surface in AI Operations, and reviewer triage now has default queues plus server-backed shared preset libraries with queue telemetry. |
| Performance (Speed) | 93/100 | 92/100 | ↑ | `artifacts/ai_similarity_benchmark_report.json` now shows sync handoff avg 42.49 ms, background similarity avg 119.14 ms, and review detail avg 2.40 ms at 1005 candidates. |
| Integration | 98/100 | 97/100 | ↑ | Runtime controls, quality-gate artifacts, reviewer calibration analytics, shared triage presets, queue metrics, reopened-reason trends, and structured reopened reasons now share one coherent trust-monitoring path across backend and AI Operations UI. |
| UX & Explainability | 88/100 | 84/100 | ↑ | AI Operations now shows queue-workload forecast risk, cross-assignment shadow evidence, language profiles, OCR-aware extraction diagnostics, and rubric criterion rationales in teacher review surfaces. |
| Responsiveness | 74/100 | 67/100 | ↑ | The review modal and evaluation console now expose more breakpoint-friendly summary blocks and checklist cards, though table-to-card mobile conversion is still pending. |
| Trust | 90/100 | 86/100 | ↑ | Cross-assignment shadow stays reviewer-only, fallback grading remains assistive, OCR/extraction confidence is visible, and rubric-grounded criterion scoring makes AI rationale materially easier to audit. |

---

# 🚨 FEATURE STATUS CLASSIFICATION

| Feature | Status | Notes |
|---------|--------|------|
| Submission upload with text extraction | ✅ Active | Student upload flow supports PDF, DOCX, TXT, MD and stores extracted text in `submissions`. |
| Single-submission AI evaluation | ✅ Active | `POST /submissions/{submission_id}/ai-evaluate` persists AI status, score, feedback, provider, prompt version, and runtime snapshot. |
| Bulk AI evaluation queue | ✅ Active | `POST /submissions/ai-evaluate/pending` creates durable `bulk_submission_ai` jobs. |
| Evaluation AI preview | ✅ Active | `POST /evaluations/ai-preview` now returns rubric criteria, criterion scores, criterion rationales, provider/fallback confidence mode, and the same normalized insight shape used by persisted evaluations. |
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
| Similarity reviewer workflow | ✅ Active | AI Operations review modal supports evidence inspection, status updates, reviewer notes, and structured reopened reasons. |
| Similarity review API docs | ✅ Active | 📘 `GET /similarity/checks/{id}` returns evidence + review fields; `PATCH` updates `review_status`, `review_reason_code`, and `review_notes`, and AI Ops now exposes `GET/POST/DELETE /ai/ops/similarity/views` for shared preset libraries. |
| Semantic shadow score badge | ✅ Active | 🏷️ AI Operations review modal displays stored shadow score alongside lexical evidence. |
| Expanded semantic shadow pilot | ✅ Active | 🧠 Shadow semantic score now stores beyond flagged pairs using top-N and minimum-lexical-score capture rules. |
| Semantic shadow calibration artifact | ✅ Active | 🧪 `scripts/ai_semantic_shadow_calibration.py` writes a gate-backed calibration report with exact, paraphrase, mixed-language, and unrelated controls. |
| Reviewer-outcome calibration report | ✅ Active | 📈 AI Operations now computes reviewer-outcome calibration from real similarity logs and keeps semantic rollout assist-only until distributions separate; current live DB snapshot has `0` final reviewed outcomes, so threshold tuning stays blocked. |
| AI Operations quality-gate visibility | ✅ Active | 👀 Semantic calibration, reviewer-outcome calibration, fairness regression, and benchmark status now surface directly in the ops dashboard. |
| Reviewer analytics in AI Operations | ✅ Active | 📊 AI Operations now shows review-status counts, semantic drift buckets, top reopened reasons, reopened-reason trends, and assist-only threshold trend over time. |
| Reviewer filtering/search in similarity table | ✅ Active | 🔎 AI Operations similarity table now filters by `review_status`, semantic drift, cap reached, low extraction quality, lexical range, and search across submission IDs plus reviewer notes. |
| Reviewer default queues in AI Operations | ✅ Active | 📚 Quick tabs now expose `Needs review`, `Reopened`, `Low text risk`, `High semantic drift`, and `Cap reached` queues without rebuilding filters. |
| Saved similarity filter presets | ✅ Active | 💾 Reviewers can save and reuse shared similarity views through the server-backed AI Operations preset library. |
| Similarity queue metrics in AI Operations | ✅ Active | 📈 Quick queues and shared presets now show count, average age, reopened rate, and low-extraction rate before reviewers open a queue. |
| Reopened-reason trend cards | ✅ Active | 📉 AI Operations now shows whether reopened reasons like `Extraction quality` or `Low evidence` are rising, falling, or flat across recent review windows. |
| Structured reopened reason capture | ✅ Active | 🧾 Reopened similarity cases now capture a structured reason code so reviewer analytics stay usable over time. |
| Cross-assignment shadow similarity | ✅ Active | 🕶️ Similarity runs now store `cross_assignment_shadow` candidates separately from flagged lexical matches and surface them as reviewer-only evidence in similarity detail. |
| Multilingual rollout config | ⚠️ Partial | 🌐 Language detection, tokenizer, stopword, and mixed-language plan are now persisted into similarity `language_profile` metadata for shadow review, but lexical flagging thresholds remain unchanged. |
| OCR fallback scaffolding | ⚠️ Partial | 🧩 OCR now uses a provider-adapter contract with persisted diagnostics (`ocr_attempted`, `ocr_provider`, `ocr_chars_added`, `page_count`, `extraction_confidence`, `low_text_reason`), but production OCR is still disabled by default until a real provider is selected. |
| Queue workload forecasting | ✅ Active | 📈 `GET /ai/ops/overview` now returns `similarity_queue_forecast` with backlog risk, attention badge, oldest age, and forecast reason for default queues and shared views. |
| Production-like similarity benchmark | ✅ Active | ⏱️ `scripts/ai_similarity_benchmark.py` still writes provider preview, sync handoff, background candidate-cap, and review-detail timings to `artifacts/ai_similarity_benchmark_report.json`. |
| Similarity benchmark gate | ✅ Active | 🚦 Benchmark exits nonzero if sync handoff exceeds `250 ms` or background similarity exceeds the configured ceiling. |
| Fairness regression gate | ✅ Active | ⚖️ `scripts/ai_fairness_regression.py` writes a gate-backed fairness report and exits nonzero when configured deltas are exceeded. |
| Semantic drift badge | ✅ Active | 🏷️ Similarity review now shows a shadow-only semantic drift badge when semantic shadow materially exceeds lexical similarity. |
| Manual teacher override | ✅ Active | Teachers can save marks independently of AI and admins can reopen result workflows. |
| Responsive data-table optimization | ⚠️ Partial | Review and evaluation screens now expose more responsive summary cards and checklist blocks, but full table-to-card conversion and split-pane evidence review are still pending. |
| Rubric-grounded evaluation payloads | ✅ Active | 🧠 Evaluation preview, save, update, refresh, and trace flows now persist `rubric_criteria`, criterion scores, criterion rationales, and academic rationale separately from risk flags. |

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
| Similarity computation | ⚠️ In Progress | Logging, thresholding, lightweight alerting, cached retrieval ranking, semantic shadow calibration gates, benchmark gates, async-only sync handoff above `250` candidates, multilingual language-profile metadata, and cross-assignment shadow storage now exist. | Keep semantic and cross-assignment logic assist-only until reviewer-confirmed outcomes grow. |
| Reviewer evidence review | ✅ Fixed | Similarity review modal now shows evidence excerpts, overlap stats, extraction quality, OCR-aware extraction diagnostics, language profile, reviewer notes/status, structured reopened reasons, and cross-assignment shadow candidates. | Add split-pane review and richer mobile evidence layouts later. |

### Workflow: Result Display

| Step | Status | Issue | Fix |
|------|--------|-------|-----|
| Submission table status display | ✅ Fixed | AI status, score, provider, and feedback summary are shown. | Add clearer fallback badge tooltip and filter by similarity risk. |
| Evaluation trace display | ✅ Fixed | Trace history shows timestamps, totals, provider, status, and risk flags. | Show runtime delta and prompt version changes inline. |
| AI Operations overview | ✅ Fixed | Flagged similarity entries now support evidence review, status updates, visible calibration/fairness/benchmark gate summaries, default queues, shared reviewer views, queue metrics, queue workload forecasting, and reopened-reason trend cards. | Add preset usage analytics and admin-pinned queues later. |
| Student-facing clarity | ⚠️ In Progress | Student view states AI is only a processing signal, but semantic review-only behavior is still mostly visible in staff tooling rather than student-facing guidance. | Add plain-language explanation for when AI status stays pending/fallback and why semantic checks remain review-only. |

Completion Score:
95/100

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
| Similarity report | AI Operations review modal + similarity queue strip | High | Evidence, quick queues, shared views, queue metrics, and reopened-reason trends are visible now, but deeper cross-assignment review is still missing. | Add semantic scope and search filters. |

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
- AI Operations now also surfaces reviewer-status counts, drift buckets, reopened-reason clustering, reopened-reason trends, threshold trend, quick queue tabs, shared reviewer views, and queue metrics so calibration is visible over time instead of as a single snapshot.
- Reopened similarity cases now require a structured reason selector, which makes reviewer analytics more consistent than free-text notes alone.
- Grading is not transparent enough because teacher-facing AI language still suggests fairness and consistency while actual scoring mixes heuristic prose metrics with optional provider output.

Score (0–10):  
9.0/10

Cognitive Load:
Medium. Teachers still reconcile marks, preview AI, stored AI, trace history, and operational flags across separate screens, but new gate cards, shared queue presets, queue metrics, reopened-reason trends, and structured reopened reasons reduce hidden context switching.

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
  "review_reason_code": null,
  "review_notes": "High lexical overlap, checking lab notebook evidence.",
  "reviewed_by_user_id": "user_92c1",
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
- Issues: Evidence, excerpt search, semantic drift badges, reviewer calibration, reviewer analytics, reviewer filtering/search, default queues, shared reviewer views, queue metrics, and reopened-reason trend cards now exist, but cross-assignment scope and workload forecasting are still missing.
- Fix: Add semantic layer, cross-assignment scope, workload forecasting, and preset-usage analytics.

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
- Reviewer preset sharing and team queue analytics for repeated similarity triage patterns.

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
86/100

---

# 🔍 EDGE CASES

- Very long input: No chunking or section-aware scoring was found; provider token cap and heuristic length saturation can flatten distinctions between long answers.
- Empty submission: Empty file upload is blocked, but empty extracted text after poor PDF parsing can still degrade downstream AI/similarity quality.
- Multiple languages: Current preprocessing is English-centric and risks unfair scoring plus weak similarity recall.
- Copy-paste vs paraphrase: Exact or near-exact copying is easier to catch than paraphrased reuse, especially with synonym substitution and sentence reordering.

---

# 📌 FINAL VERDICT

- AI Accuracy: Risky. Good operational plumbing, but scoring logic is only moderately trustworthy for grading quality.
- Similarity Reliability: Good and improving. Evidence, cached retrieval ranking, reviewer-outcome calibration, semantic drift badges, shared reviewer presets, queue metrics, reopened-reason trends, and benchmark-gated async defer protection help, but lexical-only flagging and shadow-only semantics still limit full trust.
- Trust Level: Medium-High. Traceability, de-authoritized fallback wording, visible quality gates, reviewer analytics, shared preset libraries, queue metrics, reopened-reason trends, and expanded fairness coverage are stronger, but fairness breadth and semantic depth still constrain high-stakes use.
- Biggest Problem: Semantic evidence is now visible across assignments, but promotion still lacks enough real reviewer-finalized outcomes and OCR remains adapter-only until a production provider is selected.
- Next Action: Keep collecting reviewer-confirmed fixed vs reopened outcomes, then calibrate semantic promotion thresholds and choose a production OCR provider.

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
| 2026-04-13 | ✅ Ran live reviewer-outcome calibration against the current database and fixed the empty-dataset crash path. | Current DB snapshot has `0` final reviewed similarity outcomes, so the assist-only semantic drift threshold stays at `0.15` pending real reviewer evidence. |
| 2026-04-13 | ✅ Added reviewer analytics in AI Operations for status counts, drift buckets, reopened reasons, and threshold trend. | Calibration is now visible as an evolving workflow signal instead of a point-in-time summary only. |
| 2026-04-13 | ✅ Added reviewer filtering/search in the AI Operations similarity table and backend list endpoint. | Reviewers can now narrow flagged similarity cases by review state, drift, candidate cap, extraction quality, lexical range, and search terms. |
| 2026-04-13 | ✅ Added reviewer default queues, saved similarity filter presets, and structured reopened reasons in AI Operations. | Reviewers can return to high-value triage views quickly, and reopened-case analytics now capture reason codes more consistently. |
| 2026-04-13 | ✅ Moved similarity presets into a shared server-backed AI Operations library with list/create/delete endpoints. | Reviewers can now reuse the same triage views across the team instead of losing them in browser-local storage. |
| 2026-04-13 | ✅ Added queue metrics for quick queues and shared similarity presets in AI Operations. | Reviewers can now see count, average age, reopened rate, and low-extraction rate before opening a queue. |
| 2026-04-13 | ✅ Added reopened-reason trend cards to reviewer analytics in AI Operations. | Reviewers can now see whether reasons like `Extraction quality` or `Low evidence` are rising, falling, or flat across recent review windows. |
| 2026-04-13 | ✅ Added queue workload forecasting, cross-assignment shadow evidence, OCR extraction diagnostics, and rubric-grounded criterion outputs across backend and frontend. | Similarity review is now more evidence-first, evaluation preview/save parity is rubric-aware, and low-text OCR risk is visible instead of hidden. |
| 2026-04-13 | ✅ Re-ran targeted backend trust-control tests and completed a passing frontend production build. | Verified queue forecast, OCR diagnostics persistence, cross-assignment shadow isolation, rubric preview/save parity, and the updated AI Operations/evaluation UI build. |

---

## 📈 PROGRESS

| Phase | Status | Notes |
|-------|--------|------|
| Audit baseline | ✅ Fixed | Code, docs, artifacts, and tests reviewed. |
| Trust corrections | ✅ Fixed | Confidence is labeled as heuristic with mode badges; similarity evidence is visible. |
| Fairness hardening | ⚠️ In Progress | Regression gates now cover six evaluation cases and similarity shadow now stores multilingual language-profile hints, but representative multilingual production datasets are still missing. |
| UX explainability uplift | ✅ Fixed | Numeric fallback hints are removed, ops quality gates plus reviewer analytics are visible, queue workload forecasting is live, cross-assignment shadow evidence is visible, and rubric criterion rationale now appears in evaluation flows. |
| Performance validation | ✅ Fixed | Benchmark gates still pass with sync handoff at 42.49 ms and 1005-candidate background similarity at 119.14 ms; next step is broader production-data validation rather than runtime rescue. |

---

## 🔁 NEXT ACTIONS

- Immediate fix: Collect more reviewer-confirmed fixed vs reopened outcomes and select a production OCR provider so the new shadow and extraction-diagnostic surfaces can graduate beyond adapter-only scaffolding.
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
| Add reviewer default queues, saved presets, and structured reopened reasons | High | Medium | P1 | Done ✅ |
| Add shared server-backed reviewer preset libraries | High | Medium | P1 | Done ✅ |
| Add similarity queue metrics for quick queues and shared presets | High | Medium | P1 | Done ✅ |
| Add reopened-reason trend cards in AI Operations | High | Medium | P1 | Done ✅ |
| Unify AI preview and persisted evaluation payloads | High | Low | P1 | Done ✅ |
| Add queue workload forecasting for reviewer queues | High | Medium | P1 | Done ✅ |
| Add cross-assignment shadow evidence and language-profile metadata | High | Medium | P1 | Done ✅ shadow-only |
| Add rubric-grounded criterion outputs to preview/save flows | Very High | Medium | P1 | Done ✅ |
| Add OCR adapter diagnostics and extraction confidence | High | Medium | P1 | Done partially ✅ provider selection pending |
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

## ⚠️ RISKS

| Risk | Cause | Mitigation |
|------|-------|------------|
| Academic misconduct false accusation | Score-only similarity output without evidence | Require excerpt evidence and human resolution before escalation. |
| Bias regression after prompt/runtime changes | No fairness benchmark gate | Add regression suite and change approval checklist. |
| Hidden missed matches in large cohorts | 1000-candidate cap and lexical-only engine | Surface cap warnings and add broader semantic retrieval. |
| User over-trust in fallback guidance | Legacy confidence expectations and heuristic wording can still be misread | Downgrade fallback presentation, explain backup-mode limitations, and keep provider/fallback mode visible. |

---

## 🎯 EXECUTION PLAN

- Fix now: Semantic similarity pilot ✅ expanded, OCR extraction quality warning + diagnostics ✅, OCR adapter contract ✅, multilingual tokenization metadata ✅ shadowed, lexical prefilter ✅, async-only large-run handoff ✅, retrieval caching ✅, benchmark gate ✅, semantic shadow calibration ✅, fairness regression gate ✅, reviewer-outcome calibration ✅, AI Operations quality-gate visibility ✅, queue workload forecasting ✅, cross-assignment shadow evidence ✅, and rubric-grounded preview/save payloads ✅.
- Fix later: Full semantic rollout, production OCR provider selection, and broader production-data plus multilingual fairness validation after more reviewed outcomes land.
- Remove: Probability-like wording for lexical similarity ✅ and authoritative fallback phrasing ✅ numeric fallback hints removed from chat/review text.
- Build later: Adaptive thresholds, preset-usage insights, admin-pinned queues, and advanced explainable AI panels.
