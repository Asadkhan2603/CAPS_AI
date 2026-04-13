# SELF-IMPROVING GRIEVANCE MODULE AUDIT

## 🗓 Date & Time:
2026-04-12 13:52:11 +05:30

## 📦 Project:
CAPS_AI

---

# 📊 CURRENT SYSTEM SCORES

| Category | Score | Previous | Trend | Remarks |
|----------|------|----------|-------|--------|
| Submission System | 84/100 | N/A | ↑ | `POST /grievances` is real, attachments are stored, student context is resolved server-side, and the student banner `CREATE` shortcut now opens a real compose modal; the biggest remaining submission gap is missing pagination/history depth. |
| Tracking & Status | 72/100 | N/A | → | Students can see stage, status, due date, timeline, and attachment links, but status meaning is still too generic and coordinator inbox logic does not isolate only coordinator-stage work. |
| Resolution Workflow | 66/100 | N/A | → | Staff can comment, add internal notes, forward, escalate, resolve, and students can reopen, but final resolution rationale is optional and the fallback reassignment path is not explicit in the UI. |
| Transparency | 61/100 | N/A | → | Timeline visibility is a strong base, but decision explanations are weak because resolution notes are optional, reopen reasons are optional, and there is no explicit SLA timeline or owner accountability panel. |
| Admin Handling | 69/100 | N/A | → | Routing, escalation, fallback queue, and assigned-resolver support exist in backend services, but staff workflow remains dense and manual on the single-page UI. |
| UX & Clarity | 66/100 | N/A | ↑ | The student create flow is now honest and modal-based, but browser `window.prompt` for resolution, manual refresh dependence for filters, and dense tables still hurt clarity. |
| Responsiveness | 64/100 | N/A | → | Layout stacks reasonably with Tailwind breakpoints, but the main list remains a horizontal table, action density is high, and small-screen tracking is not optimized for quick scanning. |
| Integration | 84/100 | N/A | → | Frontend services map correctly to backend endpoints, router access is wired, scheduler escalation exists, and backend/frontend contract alignment is mostly strong. |
| Trust | 64/100 | N/A | ↑ | Real grievance data exists and the misleading student `CREATE` entry point has been fixed, but non-mandatory explanation fields and limited decision accountability still reduce trust. |

---

# 🚨 FEATURE STATUS CLASSIFICATION

| Feature | Status | Notes |
|---------|--------|-------|
| Student grievance submission | ✅ Active | `createGrievance()` posts multipart data to `POST /grievances/`, backend persists the record plus optional attachment, and the student banner `CREATE` shortcut now opens a real compose modal. |
| Attachment upload | ✅ Active | Backend enforces file-type allowlist and 10 MB cap; frontend exposes drag/drop plus choose-file flow. |
| Student grievance history | ⚠️ Partial | `GET /grievances/mine` works, but frontend exposes no pagination or load-more path beyond the first 20 records. |
| Student grievance detail timeline | ✅ Active | `GET /grievances/{id}` returns timeline, due state, attachment link, and actor labels. |
| Public comments | ✅ Active | Students and authorized staff can add public thread replies through `/comments`. |
| Internal notes | ✅ Active | Staff-only internal notes are implemented and hidden from students in serializer logic. |
| Coordinator inbox | ⚠️ Partial | Route exists, but query logic returns section grievances broadly instead of only active coordinator-stage items. |
| HOD inbox | ✅ Active | Admin route plus department-scoped query are implemented. |
| Dean inbox | ✅ Active | Admin route plus department-scoped query are implemented. |
| Assigned resolver inbox | ✅ Active | `/grievances/assigned` view resolves grievances explicitly assigned to the current user. |
| Fallback grievance queue | ✅ Active | `routing_failed` grievances are visible to `academic_admin` and `super_admin`. |
| Auto escalation | ✅ Active | Scheduler loop dispatches overdue grievance escalations through `escalate_due_grievances()`. |
| Resolution notes | ⚠️ Partial | Backend accepts `resolution_note`, but it is optional and frontend uses `window.prompt` instead of a structured required form. |
| Reopen after resolution | ✅ Active | Students can reopen resolved grievances through `/reopen`. |
| Anonymous complaints | 🚫 Missing | No anonymous mode, privacy mask, or identity-shielded submission flow exists. |
| Priority tagging | 🚫 Missing | No grievance priority field or SLA-by-priority behavior exists. |
| Escalation dashboard/timeline | ⚠️ Partial | Escalation events are written into timeline entries, but there is no dedicated visible stage-timeline summary panel in UI. |
| Feedback after resolution | 🚫 Missing | No satisfaction capture or closure feedback form exists. |

Statuses:
- ✅ Active
- ⚠️ Partial
- ❌ Broken
- 🚫 Missing
- 🟡 Planned

---

# 🚨 FEATURE REALITY CHECK

| Feature | UI Claim | Actual | Issue | Fix |
|---------|----------|--------|-------|-----|
| Student `CREATE` banner button | Looks like a shortcut to start a grievance flow | Opens a real `Submit New Grievance` modal and reuses the live grievance submission API | No longer misleading, but the compose flow still lacks draft persistence and richer confirmation UX. | Keep the modal flow; next add durable confirmation and optional draft recovery. |
| Coordinator grievance inbox | Implies coordinator work queue | `grievance_inbox_query()` returns all grievances for coordinator-owned sections, not only `current_stage = coordinator` | Coordinators see historical/escalated items mixed into their queue, weakening triage accuracy. | Filter coordinator view to unresolved coordinator-stage items by default and move historical items to a separate "All Section Grievances" view. |
| Resolution flow | Implies meaningful case closure | Staff can click `Resolve` and leave no real explanation because note is optional | Users may see "resolved" without knowing why the decision was made. | Require structured resolution note, action taken, and responsible actor before closure. |
| Tracking clarity | Shows stage and timeline | Student sees due date and event list, but not a clear SLA countdown or next expected action | Transparency is only partial; users must infer what happens next. | Add "Current owner", "Next escalation time", and "What happens next" summary card above timeline. |
| Staff action controls | Looks like guided admin workflow | Forward, resolve, note, and comment controls are all presented together with no guardrails or completion checklist | Easy to perform incomplete actions or miss required communication steps. | Convert action area into staged workflow with required fields and action-specific panels. |

---

# 🚫 DEAD / MISLEADING FEATURES

| Feature | Expected | Actual | Issue | Fix |
|---------|----------|--------|-------|-----|
| Resolution note entry | Accessible and auditable closure form | Browser `window.prompt` popup | Weak UX, poor accessibility, easy blank submission | Replace with modal/form that enforces explanation fields |
| Coordinator queue label | Only current coordinator tasks | Includes section-wide historical and escalated grievances | Queue label overstates accuracy of filtered worklist | Rename or tighten backend query |
| Mobile complaint list | Easy mobile triage | Wide data table with horizontal scroll | Tracking on phones is slower than necessary | Add card/list layout for `<768px` |

---

# 🔗 GRIEVANCE API AUDIT

| Feature | FE Expectation | BE Reality | Issue | Fix |
|---------|----------------|------------|-------|-----|
| Submit grievance | Multipart submit with category, title, description, attachment | `POST /grievances/` supports all expected fields and stores file metadata | No anonymous option and no explicit duplicate prevention | Add optional duplicate heuristics and anonymous/privacy mode |
| Fetch student grievances | Load current user history | `GET /grievances/mine` returns own grievances sorted newest-first | Frontend does not expose `skip/limit`, so history is capped at first page | Add pagination or infinite scroll |
| Fetch staff inbox | Load role-specific work queue | `GET /grievances/inbox` supports `view`, `status`, `only_overdue`, `q` | Coordinator query is too broad for a queue view | Add stage-specific filter for coordinator view |
| Fetch grievance detail | Load timeline, fields, attachment link | `GET /grievances/{id}` matches frontend expectations | No summary contract for next step, current owner, or closure reason quality | Extend response with explicit accountability fields |
| Forward grievance | Assign helper resolver | `POST /grievances/{id}/forward` updates assigned resolver and logs timeline | No dedicated reassignment UX for fallback recovery | Add explicit "Reassign to stage owner" workflow |
| Update status | Mark in progress or resolved | `PATCH /grievances/{id}/status` supports both and logs timeline | Closure explanation is optional and `in_progress` note is generic | Require reason fields and richer status metadata |
| Reopen grievance | Student reopens resolved case | `POST /grievances/{id}/reopen` works and reactivates SLA | Reopen reason is optional, weakening traceability | Make reopen reason mandatory |
| Attachment access | Open original file from detail view | `GET /grievances/{id}/attachment` serves stored file if authorized | No preview metadata or virus-scan signal in UI | Add file safety/preview metadata |

---

# 🔄 USER WORKFLOW AUDIT

### Workflow: Submit Grievance

| Step | Status | Issue | Fix |
|------|--------|-------|-----|
| Open grievance page | ✅ Fixed | Route and access control are live for students | N/A |
| Discover how to submit | ✅ Fixed | Banner `CREATE` action now opens the real grievance compose modal | N/A |
| Fill category, title, description | ✅ Fixed | Required fields are present | N/A |
| Attach evidence | ✅ Fixed | File chooser works, but no file-size hint is shown before upload | Show allowed types and 10 MB limit inline |
| Submit and confirm receipt | ⚠️ In Progress | Modal-based create flow works, but success is still shown only as a toast and row refresh | Show confirmation panel with grievance ID, current stage, and expected next step |

### Workflow: Track Grievance

| Step | Status | Issue | Fix |
|------|--------|-------|-----|
| Open personal grievance list | ✅ Fixed | Student history loads from API | N/A |
| Locate older complaint | ❌ Open | No pagination or history segmentation after first 20 records | Add paging, filters, and date range controls |
| Understand current status | ⚠️ In Progress | Status badges are visible but not explained in plain language | Add human-readable status descriptions and expected next action |
| Review timeline and replies | ✅ Fixed | Public timeline is visible and internal notes are hidden from students | N/A |
| Reopen resolved complaint | ⚠️ In Progress | Function exists, but reopen reason is optional and no warning explains consequences | Require reason and explain reopen behavior before submit |

### Workflow: Admin Resolution

| Step | Status | Issue | Fix |
|------|--------|-------|-----|
| Load role-specific queue | ⚠️ In Progress | HOD/Dean queues are scoped correctly, but coordinator queue mixes active and historical work | Restrict coordinator queue to active coordinator-stage items |
| Inspect case detail | ✅ Fixed | Detail timeline, student context, due date, and attachment link are present | N/A |
| Add note/comment/forward | ✅ Fixed | Actions are live and persisted | N/A |
| Resolve with explanation | ❌ Open | `Resolve` relies on `window.prompt` and allows empty rationale | Replace with structured resolution form and required explanation |
| Recover routing-failed cases | ⚠️ In Progress | Backend fallback exists, but UI does not clearly guide reassignment or ownership recovery | Add dedicated fallback admin workflow with assign-back options |

Completion Score:
71/100

---

# ⏱ TIME-TO-RESOLUTION

| Stage | Expected | Actual | Issue |
|-------|----------|--------|-------|
| Submission acknowledgment | Immediate after submit | Immediate toast + item refresh on success | No durable acknowledgment card or clearly highlighted public grievance ID |
| First response time | Within 24 hours at coordinator stage | Not enforced as first-response metric; only stage escalation after 24 hours is enforced | System escalates ownership but does not measure or display first human response SLA |
| Final resolution time | Clear end-to-end SLA | No final-resolution SLA; only 24h per-stage escalation windows exist | Users cannot predict closure timeline and admins cannot see breach severity by case |
| Reopen handling time | Clear restart and owner notification | Reopen resets to unresolved and re-notifies stage/fallback owners | No visible reopen SLA explanation to the student |

---

# 📐 RESPONSIVE LAYOUT AUDIT

## 📱 MOBILE (<768px)

| Area | Issue | Impact | Fix |
|------|-------|--------|-----|
| Grievance list table | Six-column table requires horizontal scrolling | Slow scanning and poor triage on phones | Replace table with stacked grievance cards on mobile |
| Action panel | Comment, note, forward, and resolve controls stack into a long dense block | High interaction cost and missed actions | Collapse actions into accordions or tabs |
| `CREATE` banner | Real shortcut now opens the grievance compose modal | Useful, but still occupies premium mobile space without summarizing draft/help text | Keep it, but refine sizing and add lightweight helper copy |
| Timeline cards | Works visually, but repeated bordered cards create long scroll depth | Important events are harder to summarize quickly | Add compact milestone timeline summary at top |

## 📲 TABLET (768px–1024px)

| Area | Issue | Impact | Fix |
|------|-------|--------|-----|
| Filters row | Filter controls wrap unevenly with checkbox and refresh button | Medium scanning friction during triage | Group filters into a single compact toolbar |
| Table density | Table remains desktop-shaped with limited optimization | Acceptable but still not ideal for touch triage | Hide low-priority columns and expose row drawer |
| Detail metadata | Long labels wrap into multiple rows | Mild readability loss | Use two-column metadata grid on tablet |
| Resolution prompt | Browser prompt still interrupts flow | Awkward on touch devices | Use in-app modal instead |

## 💻 DESKTOP (>1024px)

| Area | Issue | Impact | Fix |
|------|-------|--------|-----|
| Queue accuracy | Coordinator queue label is inaccurate for mixed-stage rows | Staff may act on wrong worklist assumptions | Tighten data query and view naming |
| Action clustering | All staff actions appear at once without priority order | Increases cognitive load in complex cases | Reorder into "Reply", "Escalate/Assign", "Resolve" sequence |
| Closure transparency | Closure UX is still a prompt, not a proper form | Weak auditability even on large screens | Add structured closure form with mandatory fields |
| Historical navigation | No paging or saved filters for larger datasets | Desktop operators cannot efficiently work long queues | Add pagination, sorting, and saved views |

## 🔄 CROSS-DEVICE CONSISTENCY

| Feature | Mobile | Tablet | Desktop | Issue | Fix |
|---------|--------|--------|---------|-------|-----|
| Submission form | Modal compose flow | Modal compose flow | Modal compose flow | Consistent, but confirmation remains toast-only everywhere | Add persistent post-submit confirmation block |
| Grievance list | Horizontal table scroll | Dense table | Dense table | Same component is reused without device-specific optimization | Introduce responsive list/card variant |
| Resolution action | Browser prompt | Browser prompt | Browser prompt | Same weak interaction across all devices | Replace with modal form shared across breakpoints |
| Timeline visibility | Long scroll | Better | Best | No condensed status summary on any device | Add summary header with owner, SLA, and next step |

---

# 📊 FEATURE PLACEMENT

| Feature | Placement | Visibility | Issue | Fix |
|---------|-----------|------------|-------|-----|
| Submit button | Bottom-right of form card | Good | Clear after form completion, but not surfaced as top CTA | Add sticky mobile submit footer or summary CTA |
| Status tracker | Inside detail card and badges | Medium | Exists only after selecting a grievance | Add queue-row quick status summary and timeline preview |
| Complaint history | Table below filters | Medium | Works for small lists but becomes hard to scan on mobile and large data sets | Add grouped history cards, pagination, and date filters |
| Public reply box | Right-side action column in detail area | Medium | Hidden until detail is selected; no guidance for who can see message | Add helper text "Visible to student and staff" |
| Internal note box | Staff-only action column | Medium | Hidden correctly but not visually distinguished enough as internal-only workflow | Use stronger warning styling and note retention guidance |
| Resolve button | Staff action card | High | Highly visible, but under-specified due to prompt-based follow-up | Pair with structured explanation form |

---

# 🧠 HUMAN EASE & CLARITY

- The complaint process is technically simple because the core form only asks for category, title, description, and optional attachment.
- Status is partially understandable because badges use readable labels, but there is no plain-language explanation of what each stage means for the student.
- Users are less likely to be confused now that the `CREATE` shortcut opens the real compose modal, but the lack of durable submission confirmation and weak visible resolution rationale still create uncertainty.

Score:
59/100

Cognitive Load:
Moderate to High for staff, Moderate for students

---

# ⚖️ FAIRNESS & TRANSPARENCY AUDIT (CRITICAL)

| Area | Issue | Impact | Fix |
|------|-------|--------|-----|
| Resolution explanation | Resolution note is optional | Students can receive a final decision without a meaningful explanation | Make explanation mandatory and template it by grievance category |
| Reopen traceability | Reopen reason is optional | Reopened cases may lack a documented justification for reactivation | Require reopen reason and display it in timeline |
| Current owner visibility | Stage is visible, but named responsible owner is not explicit unless forwarded | Students cannot clearly tell who currently owns the case | Show "Current owner/queue" and "Assigned helper" separately |
| Decision transparency | Timeline shows events, not decision criteria | Users can see that something happened but not why it happened | Add decision summary fields, evidence reviewed, and action taken |
| Queue fairness | Coordinator inbox shows section-wide cases, not only active queue items | Staff workload view may look fuller or more actionable than it really is | Restrict default queue view to active coordinator-stage grievances |
| SLA transparency | Due date is visible, but next escalation logic is not explained | Students cannot judge whether delay handling is fair | Show countdown and next escalation policy inline |

---

# 🧪 STATE HANDLING

- Submission loading: Present. Submit button changes to `Submitting...` and disables during request.
- Success confirmation: Partial. Success relies on transient toast and row refresh, not a persistent acknowledgment view.
- Error handling: Partial. Errors surface as toasts, but there is no inline field-level guidance or retry affordance for failed submit.
- Retry logic: Weak. Users manually retry by re-submitting or clicking `Refresh`; no automatic retry, draft recovery, or offline persistence exists.

---

# 🧩 COMPONENT REVIEW

- Grievance form: Strong basic shape with category, title, description, and attachment, but no duplicate detection, no pre-submit guidance on SLA, and no privacy/anonymous options.
- Status tracker: Timeline and badges are real, but not yet a true tracker because next action, owner accountability, and decision rationale are not summarized.
- Admin panel: Functional action set exists in one page, but it is workflow-heavy, prompt-driven for closure, and weak for fallback recovery.

Issues:
The module is functional and the student create shortcut is now real, but it still exposes incomplete decision documentation and queue-quality gaps. The worst issues are optional closure/reopen rationale and coordinator queue over-breadth.

Fix:
Prioritize accountability next: require structured rationale fields, tighten queue filters, and add visible owner/SLA summary cards before adding new capability.

---

# 💡 IMPROVEMENTS

- UX improvements: Replace mobile table with stacked cards, add persistent submission confirmation, and polish the new modal-based create flow.
- Transparency improvements: Make resolution and reopen reasons mandatory, show current owner and next escalation time, and expose clearer status explanations.
- Workflow improvements: Split staff actions into structured panels, add fallback reassignment flow, and introduce queue pagination plus saved filters.

---

# ➕ NEW FEATURES

- Status timeline: Add a compact milestone timeline with submitted, assigned, escalated, resolved, and reopened checkpoints.
- Escalation system: Surface live countdown and breach state in UI, not only backend scheduler behavior.
- Priority tagging: Add P0-P3 priority with queue sort, SLA variants, and workload dashboards.
- Anonymous complaints: Add privacy-safe submission mode with restricted identity exposure rules.
- Feedback after resolution: Capture student closure satisfaction and reopen reasons for quality review.

---

# 🔄 RESTRUCTURE PLAN

- Remove fake flows: The banner `CREATE` shortcut is now fixed; next replace browser prompts with real forms and remove other weak placeholder interactions.
- Simplify submission: Keep the student form short but add visible rules, evidence guidance, and confirmation details.
- Improve admin workflow: Separate queue filtering, investigation, collaboration, reassignment, and closure into clearer action stages.

---

# 🧪 AUTO TEST CASES

### Test Case:
- Scenario: Student submits a grievance from profile page
- Steps: Open `/grievances`; fill category, title, description; upload valid PDF; submit
- Expected: `201` response, grievance row appears immediately, acknowledgment shows public ID/current stage/next step
- Failure: Toast-only confirmation hides durable receipt even though the modal-based `CREATE` shortcut now works

### Test Case:
- Scenario: Coordinator queue should show only active coordinator-stage items
- Steps: Seed one coordinator-stage grievance, one HOD-stage grievance, and one resolved grievance for same section; open `/grievances/coordinator`
- Expected: Only unresolved `current_stage = coordinator` items appear in default queue
- Failure: Current query returns section-wide grievances and mixes historical items

### Test Case:
- Scenario: Resolution must include explanation
- Steps: Open staff grievance detail; click `Resolve`; attempt submit without reason
- Expected: Inline validation blocks closure until required explanation fields are completed
- Failure: Current UI uses `window.prompt` and backend accepts empty note

### Test Case:
- Scenario: Student should not lose access to older grievance history
- Steps: Seed 25 grievances for one student; open `/grievances`; scroll/search
- Expected: User can paginate or load all historical grievances
- Failure: Frontend only loads first 20 and exposes no pagination controls

---

# 📊 PRIORITY LIST

| Priority | Issue | Reason |
|----------|-------|--------|
| P0 | Optional closure rationale | High transparency and fairness risk in final decisions |
| P1 | Coordinator queue over-broad query | Causes incorrect triage context and queue confusion |
| P1 | No pagination for grievance history/inbox | Large-volume cases become inaccessible or inefficient |
| P1 | Prompt-based resolution UX | Accessibility, auditability, and quality problem across all devices |
| P2 | Missing owner/SLA summary card | Makes tracking harder for users and staff |
| P2 | No feedback-after-resolution flow | Prevents trust measurement and quality monitoring |
| P3 | No anonymous complaint mode | Valuable capability but less urgent than current honesty and fairness gaps |

---

# 🧠 TRUST ANALYSIS

| Area | Trust | Reason |
|------|-------|--------|
| Submission honesty | 84/100 | The grievance create flow is now honest: the banner `CREATE` action opens a real compose modal backed by the live API. |
| Status credibility | 62/100 | Real statuses and timelines exist, yet meanings and ownership are not explained clearly enough. |
| Resolution fairness | 48/100 | Decisions can be closed without mandatory rationale, which weakens perceived fairness. |
| Staff accountability | 55/100 | Actor labels exist in timeline, but there is no strong decision summary or owner panel. |
| UI truthfulness | 63/100 | The placeholder student CTA is fixed, but prompt-based closure still keeps the UI below production trust standards. |

Overall Score:
64/100

---

# 🔍 EDGE CASES

- Duplicate complaints: No explicit deduplication, merge suggestion, or "possible duplicate" warning exists.
- No response: Backend escalates by due date, but frontend does not clearly explain escalation milestones to the student.
- Invalid submission: Required fields and attachment restrictions exist, but inline validation feedback is limited and server-side errors surface only as toasts.
- Large complaint volume: API supports `skip/limit`, but frontend has no pagination, no bulk triage tools, and no saved filters.

---

# 📌 FINAL VERDICT

- System Quality: Risky but real. The grievance module is implemented end to end and not fake overall, but several user-trust and workflow gaps keep it out of a production-ready fairness standard.
- Transparency Level: Moderate. Students can see timeline and stage, yet closure rationale and next-step clarity are still too weak.
- Trust Level: Risky. Core data is real and the student create shortcut is now fixed, but optional explanations still undermine confidence.
- Biggest Problem: The module still resolves cases without requiring a clear explanation.
- Next Action: Enforce structured resolution/reopen rationale and tighten coordinator queue filtering.

---

# 🔄 CONTINUOUS IMPROVEMENT

## 📅 UPDATE LOG

| Date | Change | Impact |
|------|--------|--------|
| 2026-04-12 | Updated audit after replacing the fake student `CREATE` shortcut with a real grievance compose modal | Improved submission honesty, UX clarity, and trust baseline |
| 2026-04-12 | Initial grievance module audit completed against live frontend, backend, router, scheduler, and tests | Established first baseline and identified P0 trust/transparency fixes |

---

## 📈 PROGRESS

| Phase | Status | Notes |
|-------|--------|-------|
| Baseline audit | ✅ Fixed | Real system behavior mapped against code and tests |
| Trust repair | ⚠️ In Progress | Fake CTA is fixed, but weak closure explanation is still unresolved |
| Queue accuracy | ❌ Open | Coordinator view needs scope tightening |
| Workflow hardening | ⚠️ In Progress | Backend core exists, but UI/admin guidance is incomplete |
| Feature expansion | 🟡 Planned | Anonymous mode, priority tagging, and feedback loops are still future work |

---

## 🔁 NEXT ACTIONS

- Immediate fix: Replace `window.prompt` closure with a required in-app form.
- Next review: After queue filter fix, closure-rationale enforcement, and pagination are shipped.
- Responsible: Frontend owner for CTA/resolution UX and responsive list; backend owner for mandatory rationale fields and coordinator query contract.

---

# 📅 ROADMAP SYSTEM

## ⚖️ IMPACT vs EFFORT

| Task | Impact | Effort | Priority | Decision |
|------|--------|--------|----------|----------|
| Require resolution note and reopen reason | High | Medium | P0 | Do now |
| Fix coordinator inbox query | High | Medium | P1 | Do now |
| Add pagination/load-more for lists | High | Medium | P1 | Do next |
| Replace `window.prompt` with modal form | High | Medium | P1 | Do next |
| Add owner/SLA summary card | Medium | Medium | P2 | Plan |
| Add mobile card layout for grievance list | Medium | Medium | P2 | Plan |
| Add priority tagging | Medium | High | P3 | Build later |
| Add anonymous complaints | Medium | High | P3 | Build later |
| Add feedback-after-resolution survey | Medium | Medium | P2 | Plan |

---

## 📅 PHASES

Phase 1: Critical Fixes  
Require closure/reopen rationale and fix coordinator queue accuracy.

Phase 2: Stability  
Add pagination, better error states, and explicit fallback reassignment workflow.

Phase 3: UX Improvements  
Replace prompt UX, add owner/SLA summary, and improve mobile/tablet grievance browsing.

Phase 4: Performance  
Add better queue filtering, pagination efficiency, and search/index review for high-volume grievance datasets.

Phase 5: Feature Enhancements  
Add priority, anonymous submissions, satisfaction feedback, and richer reporting.

---

## 🚀 QUICK WINS

| Task | Impact | Effort | Benefit |
|------|--------|--------|---------|
| Make resolution note required | High | Low | Stronger fairness and auditability |
| Make reopen reason required | Medium | Low | Better traceability |
| Add inline file limit/type help text | Medium | Low | Fewer failed submissions |
| Show grievance public ID in success state | Medium | Low | Better user confidence after submission |

---

## ⚠️ RISKS

| Risk | Cause | Mitigation |
|------|-------|------------|
| User distrust after closure | Cases can close without explanation | Enforce required rationale and show it prominently |
| Queue misuse by coordinators | Coordinator inbox shows mixed-stage records | Filter default queue to active stage only |
| Mobile abandonment | Dense table-first UI on small screens | Add responsive card list and shorter action flows |
| Operational slowdown at scale | No pagination or bulk queue tools | Implement paging, filters, and saved views |
| Fallback cases stall | No explicit reassignment workflow in UI | Add dedicated fallback admin actions and ownership visibility |

---

## 🎯 EXECUTION PLAN

- Fix now: Mandatory closure/reopen rationale and coordinator queue filter.
- Fix later: Pagination, mobile card layout, owner/SLA summary, fallback reassignment UX.
- Remove: Placeholder shortcut behavior and browser prompt-based closure flow.
- Build later: Priority tagging, anonymous complaints, resolution feedback, analytics/reporting layer.
