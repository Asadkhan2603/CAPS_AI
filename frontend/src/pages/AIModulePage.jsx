import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  Bot,
  CheckSquare,
  ClipboardCheck,
  MessageSquareText,
  RefreshCcw,
  Settings2
} from 'lucide-react';
import Card from '../components/ui/Card';
import StatCard from '../components/ui/StatCard';
import Table from '../components/ui/Table';
import Badge from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import {
  activateAiOpsSemanticThresholds,
  approveAiSemanticRolloutRecommendations,
  createSharedSimilarityView,
  deleteSharedSimilarityView,
  getAiOperationsOverview,
  getAiOpsSemanticThresholdHistory,
  getAiRuntimeConfig,
  getAiSemanticRolloutConfig,
  getSimilarityCheck,
  listAiJobs,
  listSimilarityChecks,
  rollbackAiOpsSemanticThresholds,
  listSharedSimilarityViews,
  updateAiSemanticRolloutConfig,
  updateSimilarityCheck,
  updateAiRuntimeConfig
} from '../services/aiService';
import { formatApiError } from '../utils/apiError';

const REVIEW_REASON_OPTIONS = [
  { value: '', label: 'Select reopened reason' },
  { value: 'low_evidence', label: 'Low evidence' },
  { value: 'extraction_quality', label: 'Extraction quality' },
  { value: 'common_prompt_language', label: 'Common prompt language' },
  { value: 'allowed_collaboration', label: 'Allowed collaboration' },
  { value: 'multilingual_mismatch', label: 'Multilingual mismatch' },
  { value: 'assignment_context_mismatch', label: 'Assignment context mismatch' },
  { value: 'other', label: 'Other' }
];
const DEFAULT_SIMILARITY_FILTERS = {
  search: '',
  review_status: '',
  decision_mode: '',
  awaiting_final_decision: false,
  stale_review: false,
  counts_toward_calibration: false,
  calibration_eligible: false,
  semantic_review_candidate: false,
  semantic_drift_present: false,
  match_scope: '',
  language_bucket: '',
  cap_reached: false,
  low_extraction_quality: false,
  min_score: '',
  max_score: ''
};
const DEFAULT_QUEUE_PRESETS = [
  { id: 'needs-review', label: 'Needs review', filters: { ...DEFAULT_SIMILARITY_FILTERS, review_status: 'open' } },
  { id: 'awaiting-final', label: 'Awaiting final decision', filters: { ...DEFAULT_SIMILARITY_FILTERS, awaiting_final_decision: true } },
  { id: 'stale-open', label: 'Stale open', filters: { ...DEFAULT_SIMILARITY_FILTERS, review_status: 'open', stale_review: true } },
  { id: 'stale-in-progress', label: 'Stale in progress', filters: { ...DEFAULT_SIMILARITY_FILTERS, review_status: 'in_progress', stale_review: true } },
  { id: 'reopened', label: 'Reopened', filters: { ...DEFAULT_SIMILARITY_FILTERS, review_status: 'reopened' } },
  { id: 'ready-calibration', label: 'Ready for calibration', filters: { ...DEFAULT_SIMILARITY_FILTERS, counts_toward_calibration: true } },
  { id: 'calibration-eligible', label: 'Calibration eligible', filters: { ...DEFAULT_SIMILARITY_FILTERS, calibration_eligible: true } },
  {
    id: 'same-assignment-semantic-candidates',
    label: 'Same-assignment semantic candidates',
    filters: { ...DEFAULT_SIMILARITY_FILTERS, semantic_review_candidate: true, match_scope: 'same_assignment_shadow' }
  },
  {
    id: 'cross-assignment-shadow-candidates',
    label: 'Cross-assignment shadow candidates',
    filters: { ...DEFAULT_SIMILARITY_FILTERS, match_scope: 'cross_assignment_shadow' }
  },
  {
    id: 'mixed-transliterated-review-candidates',
    label: 'Mixed/transliterated review candidates',
    filters: { ...DEFAULT_SIMILARITY_FILTERS, language_bucket: 'mixed_transliterated' }
  },
  { id: 'suppressed-high-risk', label: 'Suppressed high lexical risk', filters: { ...DEFAULT_SIMILARITY_FILTERS, decision_mode: 'suppressed' } },
  { id: 'semantic-review', label: 'Semantic review candidates', filters: { ...DEFAULT_SIMILARITY_FILTERS, semantic_review_candidate: true } },
  { id: 'low-extraction-hold', label: 'Low extraction hold', filters: { ...DEFAULT_SIMILARITY_FILTERS, decision_mode: 'suppressed', low_extraction_quality: true } },
  { id: 'low-text-risk', label: 'Low text risk', filters: { ...DEFAULT_SIMILARITY_FILTERS, low_extraction_quality: true } },
  { id: 'high-drift', label: 'High semantic drift', filters: { ...DEFAULT_SIMILARITY_FILTERS, semantic_drift_present: true, review_status: 'open' } },
  { id: 'cap-reached', label: 'Cap reached', filters: { ...DEFAULT_SIMILARITY_FILTERS, cap_reached: true } }
];

function formatTimestamp(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

function formatProviderMode(mode) {
  if (mode === 'openai+fallback') return 'OpenAI + fallback';
  if (mode === 'fallback-only') return 'Fallback only';
  return mode || '-';
}

function formatNumeric(value, digits = 2) {
  if (value == null) return '-';
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return '-';
  return numeric.toFixed(digits);
}

function formatPercent(value) {
  if (value == null) return '-';
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return '-';
  return `${Math.round(numeric * 100)}%`;
}

function formatAgeHours(value) {
  if (value == null) return '-';
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return '-';
  if (numeric >= 48) return `${Math.round(numeric / 24)}d`;
  if (numeric >= 24) return `${(numeric / 24).toFixed(1)}d`;
  return `${Math.round(numeric)}h`;
}

function hoursSinceTimestamp(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return Math.max(0, (Date.now() - date.getTime()) / (1000 * 60 * 60));
}

function isStaleReviewCase(item) {
  if (!item) return false;
  const status = item.review_status || 'open';
  if (!['open', 'in_progress'].includes(status)) return false;
  const ageHours = hoursSinceTimestamp(item.review_updated_at || item.reviewed_at || item.created_at);
  if (ageHours == null) return false;
  return status === 'open' ? ageHours >= 48 : ageHours >= 72;
}

function formatMatchScope(scope) {
  if (scope === 'cross_assignment_shadow') return 'Cross-assignment shadow';
  if (scope === 'same_assignment_shadow') return 'Same-assignment shadow';
  if (scope === 'same_assignment_lexical') return 'Same-assignment lexical';
  return scope || '-';
}

function formatLanguageBucket(bucket) {
  if (bucket === 'latin_only') return 'Latin only';
  if (bucket === 'mixed_transliterated') return 'Mixed/transliterated';
  if (bucket === 'non_latin') return 'Non-Latin';
  return bucket || '-';
}

function formatOcrResultState(state) {
  if (state === 'success') return 'OCR success';
  if (state === 'timeout') return 'OCR timeout';
  if (state === 'failed') return 'OCR failed';
  if (state === 'empty') return 'OCR empty';
  if (state === 'provider_not_configured') return 'OCR not configured';
  if (state === 'not_needed') return 'OCR not needed';
  if (state === 'disabled') return 'OCR disabled';
  if (state === 'unsupported') return 'OCR unsupported';
  return state || '-';
}

function trendVariant(value) {
  if (value === 'up') return 'warning';
  if (value === 'down') return 'success';
  return 'default';
}

function gateVariant(status) {
  if (status === 'passed') return 'success';
  if (status === 'failed') return 'danger';
  if (status === 'assist_only') return 'info';
  if (status === 'missing') return 'warning';
  return 'default';
}

function reviewStatusVariant(status) {
  if (status === 'fixed') return 'success';
  if (status === 'reopened') return 'danger';
  if (status === 'in_progress') return 'warning';
  return 'default';
}

function decisionModeVariant(mode) {
  if (mode === 'flagged') return 'danger';
  if (mode === 'assist_only') return 'warning';
  if (mode === 'suppressed') return 'default';
  return 'default';
}

function statusVariant(status) {
  if (status === 'completed') return 'success';
  if (status === 'failed') return 'danger';
  if (status === 'running') return 'info';
  if (status === 'pending' || status === 'queued') return 'warning';
  if (status === 'fallback') return 'warning';
  return 'default';
}

function promotionStateVariant(state) {
  if (state === 'active_assist_only') return 'success';
  if (state === 'approved_manual') return 'info';
  if (state === 'candidate') return 'warning';
  return 'default';
}

function formatPromotionState(state) {
  if (state === 'active_assist_only') return 'Active assist-only';
  if (state === 'approved_manual') return 'Approved manual';
  if (state === 'candidate') return 'Candidate';
  if (state === 'blocked') return 'Blocked';
  return state || '-';
}

function formatJobType(value) {
  if (value === 'bulk_submission_ai') return 'Bulk Submission AI';
  if (value === 'similarity_check') return 'Similarity Check';
  return value || '-';
}

function formatScopeLabel(value) {
  if (value === 'same_assignment') return 'Same-assignment';
  if (value === 'cross_assignment') return 'Cross-assignment';
  if (value === 'both') return 'Both scopes';
  return value || '-';
}

function formatReviewReasonLabel(reason) {
  if (!reason) return 'Auto-flag evidence passed';
  return reason
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function formatDecisionModeLabel(mode, isFlagged) {
  if (mode === 'flagged') return 'Auto-flagged';
  if (mode === 'assist_only') return 'Review only';
  if (mode === 'suppressed') return 'Suppressed';
  if (isFlagged) return 'Flagged';
  return 'Unflagged';
}

function formatReviewStatusLabel(status) {
  if (!status) return 'Open';
  return status
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function buildSimilarityDecisionSummary(detail) {
  if (!detail) return 'Review the matched excerpts before deciding whether this is true copying, prompt overlap, or weak evidence.';
  const score = Number(detail.score || 0);
  const threshold = Number(detail.threshold || 0);
  const excerptCount = detail.risk_signals?.effective_excerpt_count ?? 0;
  const effectiveOverlap = detail.overlap_stats?.effective_overlap_ratio;
  if (detail.decision_mode === 'flagged') {
    return `This case was auto-flagged because wording overlap is ${score.toFixed(2)} against a threshold of ${threshold.toFixed(2)}, with ${excerptCount || 'multiple'} strong matching excerpt${excerptCount === 1 ? '' : 's'} and effective overlap ${formatNumeric(effectiveOverlap, 2)} after prompt discount.`;
  }
  if (detail.decision_mode === 'assist_only') {
    return `This case was kept review-only because the system saw similarity worth checking, but not enough safe evidence to auto-flag. Compare the highlighted excerpts before deciding.`;
  }
  return `This case was suppressed from auto-flagging because evidence was weak, risky, or incomplete. Use the excerpts and file-quality notes before taking action.`;
}

function buildSimilarityReviewerChecklist(detail) {
  if (!detail) return [];
  const items = [];
  items.push('Confirm whether the shared text is actual student content or just common assignment wording.');
  if ((detail.risk_signals?.effective_excerpt_count ?? 0) > 0) {
    items.push(`Check the ${detail.risk_signals?.effective_excerpt_count} highlighted excerpt${detail.risk_signals?.effective_excerpt_count === 1 ? '' : 's'} for copied phrasing, order, and examples.`);
  }
  if (detail.risk_signals?.low_extraction_block || detail.extraction_diagnostics?.source?.low_text_reason || detail.extraction_diagnostics?.matched?.low_text_reason) {
    items.push('Treat this as weak evidence until extraction quality improves or OCR recovery succeeds.');
  }
  if (detail.semantic_review_candidate) {
    items.push('Semantic drift is high enough to suggest paraphrase risk, so compare meaning as well as exact wording.');
  }
  if (detail.risk_signals?.prompt_overlap_ratio >= 0.2) {
    items.push('A meaningful part of the overlap comes from prompt/common wording, so avoid accusing based on score alone.');
  }
  return items.slice(0, 4);
}

export default function AIModulePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [overview, setOverview] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [runtimeConfig, setRuntimeConfig] = useState(null);
  const [semanticRolloutConfig, setSemanticRolloutConfig] = useState(null);
  const [semanticRolloutStatus, setSemanticRolloutStatus] = useState(null);
  const [semanticRolloutHistory, setSemanticRolloutHistory] = useState([]);
  const [savingSemanticConfig, setSavingSemanticConfig] = useState(false);
  const [applyingSemanticRecommendations, setApplyingSemanticRecommendations] = useState(false);
  const [activatingSemanticRecommendations, setActivatingSemanticRecommendations] = useState(false);
  const [rollingBackSemanticSnapshot, setRollingBackSemanticSnapshot] = useState(false);
  const [semanticApplyForm, setSemanticApplyForm] = useState({
    scope: 'both',
    force: false,
    include_sample_sizes: true
  });
  const [semanticGovernanceJustification, setSemanticGovernanceJustification] = useState('');
  const [similarityDetail, setSimilarityDetail] = useState(null);
  const [similarityDetailOpen, setSimilarityDetailOpen] = useState(false);
  const [similarityDetailLoading, setSimilarityDetailLoading] = useState(false);
  const [similarityRows, setSimilarityRows] = useState([]);
  const [similarityRowsLoading, setSimilarityRowsLoading] = useState(false);
  const [similarityFilters, setSimilarityFilters] = useState(DEFAULT_SIMILARITY_FILTERS);
  const [savedSimilarityPresets, setSavedSimilarityPresets] = useState([]);
  const [similarityPresetName, setSimilarityPresetName] = useState('');
  const [activeQueueId, setActiveQueueId] = useState('all');
  const [reviewStatus, setReviewStatus] = useState('open');
  const [reviewReasonCode, setReviewReasonCode] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');
  const [reviewSaving, setReviewSaving] = useState(false);
  const [excerptQuery, setExcerptQuery] = useState('');
  const [excerptMinOverlap, setExcerptMinOverlap] = useState('0.15');
  const isAdmin = user?.role === 'admin';

  async function loadPageData() {
    setLoading(true);
    try {
      const requests = [getAiOperationsOverview({ limit: 8 }), listAiJobs({ limit: 8 }), listSharedSimilarityViews()];
      if (isAdmin) {
        requests.push(getAiRuntimeConfig());
        requests.push(getAiSemanticRolloutConfig());
        requests.push(getAiOpsSemanticThresholdHistory({ limit: 10 }));
      }
      const [
        overviewResponse,
        jobsResponse,
        similarityViewsResponse,
        runtimeResponse,
        semanticRolloutResponse,
        semanticRolloutHistoryResponse
      ] = await Promise.all(requests);
      setOverview(overviewResponse || null);
      setJobs(jobsResponse?.items || []);
      setSavedSimilarityPresets(similarityViewsResponse || []);
      if (isAdmin && runtimeResponse?.effective) {
        setRuntimeConfig({
          provider_enabled: Boolean(runtimeResponse.effective.provider_enabled),
          openai_model: runtimeResponse.effective.openai_model || '',
          openai_timeout_seconds: String(runtimeResponse.effective.openai_timeout_seconds ?? 20),
          openai_max_output_tokens: String(runtimeResponse.effective.openai_max_output_tokens ?? 400),
          similarity_threshold: String(runtimeResponse.effective.similarity_threshold ?? 0.8)
        });
      }
      if (isAdmin && semanticRolloutResponse?.effective) {
        setSemanticRolloutStatus(semanticRolloutResponse || null);
        setSemanticRolloutConfig({
          semantic_same_assignment_drift_threshold: String(semanticRolloutResponse.effective.semantic_same_assignment_drift_threshold ?? 0.15),
          semantic_cross_assignment_drift_threshold: String(semanticRolloutResponse.effective.semantic_cross_assignment_drift_threshold ?? 0.22),
          semantic_same_assignment_min_score: String(semanticRolloutResponse.effective.semantic_same_assignment_min_score ?? 0.7),
          semantic_cross_assignment_min_score: String(semanticRolloutResponse.effective.semantic_cross_assignment_min_score ?? 0.8),
          semantic_same_assignment_min_sample_size: String(semanticRolloutResponse.effective.semantic_same_assignment_min_sample_size ?? 5),
          semantic_cross_assignment_min_sample_size: String(semanticRolloutResponse.effective.semantic_cross_assignment_min_sample_size ?? 8),
          semantic_multilingual_min_sample_size: String(semanticRolloutResponse.effective.semantic_multilingual_min_sample_size ?? 4),
          manual_promotion_guidance_only: Boolean(semanticRolloutResponse.effective.manual_promotion_guidance_only)
        });
      }
      setSemanticRolloutHistory(semanticRolloutHistoryResponse?.items || []);
      await loadSimilarityRows();
    } catch (err) {
      setOverview(null);
      setJobs([]);
      setSimilarityRows([]);
      setSavedSimilarityPresets([]);
      setSemanticRolloutStatus(null);
      setSemanticRolloutHistory([]);
      pushToast({
        title: 'AI module load failed',
        description: formatApiError(err, 'Unable to load AI operations overview'),
        variant: 'error'
      });
    } finally {
      setLoading(false);
    }
  }

  async function loadSimilarityRows(activeFilters = similarityFilters) {
    setSimilarityRowsLoading(true);
    try {
      const params = {
        limit: 50
      };
      if (activeFilters.review_status) params.review_status = activeFilters.review_status;
      if (activeFilters.decision_mode) params.decision_mode = activeFilters.decision_mode;
      if (activeFilters.awaiting_final_decision) params.awaiting_final_decision = true;
      if (activeFilters.stale_review) params.stale_review = true;
      if (activeFilters.counts_toward_calibration) params.counts_toward_calibration = true;
      if (activeFilters.calibration_eligible) params.calibration_eligible = true;
      if (activeFilters.semantic_review_candidate) params.semantic_review_candidate = true;
      if (activeFilters.semantic_drift_present) params.semantic_drift_present = true;
      if (activeFilters.match_scope) params.match_scope = activeFilters.match_scope;
      if (activeFilters.language_bucket) params.language_bucket = activeFilters.language_bucket;
      if (activeFilters.cap_reached) params.cap_reached = true;
      if (activeFilters.low_extraction_quality) params.low_extraction_quality = true;
      if (activeFilters.min_score !== '') params.min_score = Number(activeFilters.min_score);
      if (activeFilters.max_score !== '') params.max_score = Number(activeFilters.max_score);
      if (activeFilters.search.trim()) params.search = activeFilters.search.trim();
      const rows = await listSimilarityChecks(params);
      setSimilarityRows(rows || []);
    } catch (err) {
      setSimilarityRows([]);
      pushToast({
        title: 'Similarity filters failed',
        description: formatApiError(err, 'Unable to load filtered similarity checks'),
        variant: 'error'
      });
    } finally {
      setSimilarityRowsLoading(false);
    }
  }

  async function applySimilarityFilters(nextFilters, queueId = 'custom') {
    setSimilarityFilters(nextFilters);
    setActiveQueueId(queueId);
    await loadSimilarityRows(nextFilters);
  }

  async function saveCurrentSimilarityPreset() {
    const label = similarityPresetName.trim();
    if (!label) {
      pushToast({
        title: 'Preset name required',
        description: 'Enter a short preset name before saving the current similarity view.',
        variant: 'error'
      });
      return;
    }
    try {
      const created = await createSharedSimilarityView({
        name: label,
        filters: { ...similarityFilters }
      });
      setSavedSimilarityPresets((current) => {
        const next = [created, ...current.filter((item) => item.id !== created.id && item.name !== created.name)];
        return next.slice(0, 20);
      });
      setSimilarityPresetName('');
      pushToast({
        title: 'Shared preset saved',
        description: `Saved shared similarity view "${label}".`,
        variant: 'success'
      });
    } catch (err) {
      pushToast({
        title: 'Save failed',
        description: formatApiError(err, 'Unable to save shared similarity view'),
        variant: 'error'
      });
    }
  }

  async function deleteSimilarityPreset(presetId) {
    try {
      await deleteSharedSimilarityView(presetId);
      setSavedSimilarityPresets((current) => current.filter((item) => item.id !== presetId));
    } catch (err) {
      pushToast({
        title: 'Delete failed',
        description: formatApiError(err, 'Unable to delete shared similarity view'),
        variant: 'error'
      });
    }
  }

  async function openSimilarityDetail(logId) {
    if (!logId) return;
    setSimilarityDetailLoading(true);
    setSimilarityDetailOpen(true);
    try {
      const detail = await getSimilarityCheck(logId);
      setSimilarityDetail(detail);
      setReviewStatus(detail?.review_status || 'open');
      setReviewReasonCode(detail?.review_reason_code || '');
      setReviewNotes(detail?.review_notes || '');
    } catch (err) {
      pushToast({
        title: 'Similarity detail failed',
        description: formatApiError(err, 'Unable to load similarity detail'),
        variant: 'error'
      });
      setSimilarityDetail(null);
      setSimilarityDetailOpen(false);
    } finally {
      setSimilarityDetailLoading(false);
    }
  }

  async function loadSimilarityFromQuery() {
    const params = new URLSearchParams(location.search);
    const similarityLogId = params.get('similarity_log_id');
    if (similarityLogId) {
      await openSimilarityDetail(similarityLogId);
      return;
    }
    const sourceSubmissionId = params.get('source_submission_id');
    if (!sourceSubmissionId) return;
    try {
      const results = await listSimilarityChecks({ source_submission_id: sourceSubmissionId, limit: 1 });
      const first = (results || [])[0];
      if (first?.id) {
        await openSimilarityDetail(first.id);
      }
    } catch (err) {
      pushToast({
        title: 'Similarity lookup failed',
        description: formatApiError(err, 'Unable to load similarity detail from link'),
        variant: 'error'
      });
    }
  }

  async function saveSimilarityReview(nextStatus = reviewStatus) {
    if (!similarityDetail?.id) return;
    if (nextStatus === 'reopened' && !reviewReasonCode) {
      pushToast({
        title: 'Reopened reason required',
        description: 'Pick a structured reopened reason so reviewer analytics stay useful.',
        variant: 'error'
      });
      return;
    }
    setReviewSaving(true);
    try {
      const updated = await updateSimilarityCheck(similarityDetail.id, {
        review_status: nextStatus,
        review_reason_code: nextStatus === 'reopened' ? reviewReasonCode : '',
        review_notes: reviewNotes
      });
      setSimilarityDetail(updated);
      setReviewStatus(updated?.review_status || 'open');
      setReviewReasonCode(updated?.review_reason_code || '');
      setReviewNotes(updated?.review_notes || '');
      pushToast({
        title: nextStatus === 'fixed' || nextStatus === 'reopened' ? 'Similarity finalized' : 'Similarity updated',
        description:
          nextStatus === 'fixed' || nextStatus === 'reopened'
            ? 'Final reviewer outcome saved for calibration tracking.'
            : 'Review progress saved.',
        variant: 'success'
      });
      await loadPageData();
    } catch (err) {
      pushToast({
        title: 'Update failed',
        description: formatApiError(err, 'Unable to update similarity review'),
        variant: 'error'
      });
    } finally {
      setReviewSaving(false);
    }
  }

  useEffect(() => {
    loadPageData();
  }, [isAdmin]);

  useEffect(() => {
    loadSimilarityFromQuery();
  }, [location.search]);

  async function onSaveRuntimeConfig(event) {
    event.preventDefault();
    if (!runtimeConfig) return;
    setSavingConfig(true);
    try {
      await updateAiRuntimeConfig({
        provider_enabled: runtimeConfig.provider_enabled,
        openai_model: runtimeConfig.openai_model,
        openai_timeout_seconds: Number(runtimeConfig.openai_timeout_seconds),
        openai_max_output_tokens: Number(runtimeConfig.openai_max_output_tokens),
        similarity_threshold: Number(runtimeConfig.similarity_threshold)
      });
      pushToast({
        title: 'AI runtime updated',
        description: 'Runtime settings saved successfully.',
        variant: 'success'
      });
      await loadPageData();
    } catch (err) {
      pushToast({
        title: 'AI runtime update failed',
        description: formatApiError(err, 'Unable to save AI runtime settings'),
        variant: 'error'
      });
    } finally {
      setSavingConfig(false);
    }
  }

  async function onSaveSemanticRolloutConfig(event) {
    event.preventDefault();
    if (!semanticRolloutConfig) return;
    setSavingSemanticConfig(true);
    try {
      await updateAiSemanticRolloutConfig({
        semantic_same_assignment_drift_threshold: Number(semanticRolloutConfig.semantic_same_assignment_drift_threshold),
        semantic_cross_assignment_drift_threshold: Number(semanticRolloutConfig.semantic_cross_assignment_drift_threshold),
        semantic_same_assignment_min_score: Number(semanticRolloutConfig.semantic_same_assignment_min_score),
        semantic_cross_assignment_min_score: Number(semanticRolloutConfig.semantic_cross_assignment_min_score),
        semantic_same_assignment_min_sample_size: Number(semanticRolloutConfig.semantic_same_assignment_min_sample_size),
        semantic_cross_assignment_min_sample_size: Number(semanticRolloutConfig.semantic_cross_assignment_min_sample_size),
        semantic_multilingual_min_sample_size: Number(semanticRolloutConfig.semantic_multilingual_min_sample_size),
        justification: semanticGovernanceJustification.trim() || 'Manual semantic rollout threshold update.'
      });
      pushToast({
        title: 'Semantic rollout config updated',
        description: 'Semantic thresholds and sample-size settings were saved successfully.',
        variant: 'success'
      });
      await loadPageData();
    } catch (err) {
      pushToast({
        title: 'Semantic rollout update failed',
        description: formatApiError(err, 'Unable to save semantic rollout settings'),
        variant: 'error'
      });
    } finally {
      setSavingSemanticConfig(false);
    }
  }

  async function onApproveSemanticRecommendations() {
    setApplyingSemanticRecommendations(true);
    try {
      const response = await approveAiSemanticRolloutRecommendations({
        scope: semanticApplyForm.scope,
        force: semanticApplyForm.force,
        include_sample_sizes: semanticApplyForm.include_sample_sizes,
        justification: semanticGovernanceJustification.trim()
      });
      pushToast({
        title: 'Semantic recommendations approved',
        description: `Approved recommendation snapshot v${response?.approved_snapshot_version ?? '-'} for ${formatScopeLabel(response?.approved_scope)}.`,
        variant: 'success'
      });
      await loadPageData();
    } catch (err) {
      pushToast({
        title: 'Recommendation approval failed',
        description: formatApiError(err, 'Unable to approve semantic rollout recommendations'),
        variant: 'error'
      });
    } finally {
      setApplyingSemanticRecommendations(false);
    }
  }

  async function onActivateSemanticRecommendations() {
    const selectedScope = semanticApplyForm.scope;
    const sameApprovedVersion = semanticRolloutStatus?.approved_versions?.same_assignment ?? null;
    const crossApprovedVersion = semanticRolloutStatus?.approved_versions?.cross_assignment ?? null;
    let targetVersion = null;
    if (selectedScope === 'same_assignment') targetVersion = sameApprovedVersion;
    if (selectedScope === 'cross_assignment') targetVersion = crossApprovedVersion;
    if (selectedScope === 'both' && sameApprovedVersion && sameApprovedVersion === crossApprovedVersion) {
      targetVersion = sameApprovedVersion;
    }
    if (!targetVersion) {
      pushToast({
        title: 'Activation target missing',
        description: 'Choose a scope with an approved snapshot version before activating assist-only guidance.',
        variant: 'error'
      });
      return;
    }
    setActivatingSemanticRecommendations(true);
    try {
      const response = await activateAiOpsSemanticThresholds({
        scope: selectedScope,
        force: semanticApplyForm.force,
        target_version: targetVersion,
        justification: semanticGovernanceJustification.trim()
      });
      pushToast({
        title: 'Assist-only activation updated',
        description: `Activated snapshot v${response?.target_version ?? targetVersion} for ${formatScopeLabel(response?.activated_scope)} without changing automatic flagging.`,
        variant: 'success'
      });
      await loadPageData();
    } catch (err) {
      pushToast({
        title: 'Activation failed',
        description: formatApiError(err, 'Unable to activate the approved semantic snapshot'),
        variant: 'error'
      });
    } finally {
      setActivatingSemanticRecommendations(false);
    }
  }

  async function onRollbackSemanticSnapshot(targetVersion, targetScope) {
    if (!targetVersion) return;
    setRollingBackSemanticSnapshot(true);
    try {
      const response = await rollbackAiOpsSemanticThresholds({
        scope: targetScope || 'both',
        target_version: targetVersion,
        justification: semanticGovernanceJustification.trim()
      });
      pushToast({
        title: 'Semantic rollback completed',
        description: `Rolled back ${formatScopeLabel(response?.rolled_back_scope)} to snapshot v${response?.restored_from_version ?? targetVersion}.`,
        variant: 'success'
      });
      await loadPageData();
    } catch (err) {
      pushToast({
        title: 'Rollback failed',
        description: formatApiError(err, 'Unable to roll back the semantic snapshot'),
        variant: 'error'
      });
    } finally {
      setRollingBackSemanticSnapshot(false);
    }
  }

  const summary = overview?.summary || {};
  const provider = overview?.provider || {};
  const scope = overview?.scope || {};
  const qualityGates = overview?.quality_gates || {};
  const semanticCalibration = qualityGates.semantic_calibration || {};
  const reviewerCalibration = qualityGates.reviewer_outcome_calibration || {};
  const reviewerAnalytics = reviewerCalibration.analytics || {};
  const fairnessGate = qualityGates.fairness_regression || {};
  const falsePositiveNegativeGate = qualityGates.false_positive_negative_regression || {};
  const benchmarkGate = qualityGates.benchmark || {};
  const similarityQueueMetrics = overview?.similarity_queue_metrics || {};
  const similarityQueueForecast = overview?.similarity_queue_forecast || {};
  const reviewerOutcomePipeline = overview?.reviewer_outcome_pipeline || {};
  const semanticRolloutReadiness = overview?.semantic_rollout_readiness || {};
  const sameAssignmentReadiness = semanticRolloutReadiness.same_assignment || {};
  const crossAssignmentReadiness = semanticRolloutReadiness.cross_assignment || {};
  const languageCoverageReadiness = semanticRolloutReadiness.language_coverage || {};
  const semanticRolloutBlockers = semanticRolloutReadiness.blocker_reasons || [];
  const semanticScopeStates = semanticRolloutStatus?.scope_states || {};
  const semanticApprovedVersions = semanticRolloutStatus?.approved_versions || {};
  const semanticActiveVersions = semanticRolloutStatus?.active_versions || {};
  const semanticCurrentVersion = semanticRolloutStatus?.current_version ?? 0;
  const semanticRolloutBlockerAging = semanticRolloutReadiness.blocker_aging || [];
  const readinessTrend = reviewerAnalytics.readiness_trend || semanticRolloutReadiness.readiness_trend || [];
  const legacyValidation = reviewerAnalytics.legacy_validation || {};
  const crossAssignmentReviewOutcomes = reviewerAnalytics.cross_assignment_review_outcomes || {};
  const crossAssignmentReversalRanking = reviewerAnalytics.cross_assignment_reversal_ranking || [];
  const crossAssignmentReasonTrends = reviewerAnalytics.cross_assignment_reopened_reason_trends || [];
  const semanticHistoryRows = semanticRolloutHistory || [];
  const sameAssignmentBlockers = sameAssignmentReadiness.blocker_reasons || [];
  const crossAssignmentBlockers = crossAssignmentReadiness.blocker_reasons || [];
  const selectedSemanticScopeBlockers = useMemo(() => {
    if (semanticApplyForm.scope === 'same_assignment') return sameAssignmentBlockers;
    if (semanticApplyForm.scope === 'cross_assignment') return crossAssignmentBlockers;
    return Array.from(new Set([...(sameAssignmentBlockers || []), ...(crossAssignmentBlockers || [])]));
  }, [semanticApplyForm.scope, sameAssignmentBlockers, crossAssignmentBlockers]);
  const selectedScopeHasMultilingualBlocker = selectedSemanticScopeBlockers.some((item) =>
    String(item || '').toLowerCase().includes('multilingual coverage')
  );
  const selectedApprovedVersion = useMemo(() => {
    if (semanticApplyForm.scope === 'same_assignment') return semanticApprovedVersions.same_assignment ?? null;
    if (semanticApplyForm.scope === 'cross_assignment') return semanticApprovedVersions.cross_assignment ?? null;
    if (
      semanticApprovedVersions.same_assignment &&
      semanticApprovedVersions.same_assignment === semanticApprovedVersions.cross_assignment
    ) {
      return semanticApprovedVersions.same_assignment;
    }
    return null;
  }, [semanticApplyForm.scope, semanticApprovedVersions.cross_assignment, semanticApprovedVersions.same_assignment]);
  const approveActionBlocked = !semanticApplyForm.force && selectedSemanticScopeBlockers.length > 0;
  const activateActionBlocked =
    !selectedApprovedVersion ||
    selectedScopeHasMultilingualBlocker ||
    (!semanticApplyForm.force && selectedSemanticScopeBlockers.length > 0);
  const defaultQueueMetrics = similarityQueueMetrics.default_queues || [];
  const defaultQueueMetricsById = useMemo(
    () => new Map(defaultQueueMetrics.map((item) => [item.id, item])),
    [defaultQueueMetrics]
  );
  const defaultQueueForecastById = useMemo(
    () => new Map((similarityQueueForecast.default_queues || []).map((item) => [item.id, item])),
    [similarityQueueForecast.default_queues]
  );
  const sharedQueueMetricsById = useMemo(
    () => new Map((similarityQueueMetrics.shared_views || []).map((item) => [item.id, item])),
    [similarityQueueMetrics.shared_views]
  );
  const sharedQueueForecastById = useMemo(
    () => new Map((similarityQueueForecast.shared_views || []).map((item) => [item.id, item])),
    [similarityQueueForecast.shared_views]
  );
  const semanticDriftThreshold = Number(
    reviewerCalibration?.recommendations?.assist_only_semantic_advantage_threshold ??
      semanticCalibration?.recommended_semantic_advantage_trigger ??
      0.15
  );
  const semanticDriftValue =
    similarityDetail?.semantic_shadow_score != null && similarityDetail?.score != null
      ? Number(similarityDetail.semantic_shadow_score) - Number(similarityDetail.score)
      : null;
  const semanticDriftDetected =
    semanticDriftValue != null &&
    !Number.isNaN(semanticDriftValue) &&
    semanticDriftValue >= semanticDriftThreshold;
  const similarityDetailStale = isStaleReviewCase(similarityDetail);
  const similarityDetailCountsTowardCalibration = Boolean(similarityDetail?.counts_toward_calibration);

  const runColumns = useMemo(
    () => [
      {
        key: 'ai_status',
        label: 'Status',
        render: (row) => <Badge variant={statusVariant(row.ai_status)}>{row.ai_status || '-'}</Badge>
      },
      { key: 'ai_provider', label: 'Provider', render: (row) => row.ai_provider || '-' },
      { key: 'ai_score', label: 'AI Score', render: (row) => row.ai_score ?? '-' },
      { key: 'grade', label: 'Grade', render: (row) => row.grade || '-' },
      { key: 'grand_total', label: 'Total', render: (row) => row.grand_total ?? '-' },
      { key: 'created_at', label: 'Created', render: (row) => formatTimestamp(row.created_at) }
    ],
    []
  );

  const similarityColumns = useMemo(
    () => [
      {
        key: 'source_submission_public_id',
        label: 'Source Submission',
        render: (row) => row.source_submission_public_id || row.source_submission_id || '-'
      },
      {
        key: 'matched_submission_public_id',
        label: 'Matched Submission',
        render: (row) => row.matched_submission_public_id || row.matched_submission_id || '-'
      },
      { key: 'score', label: 'Lexical Similarity', render: (row) => (row.score != null ? Number(row.score).toFixed(2) : '-') },
      { key: 'decision_mode', label: 'Decision', render: (row) => <Badge variant={decisionModeVariant(row.decision_mode)}>{row.decision_mode || 'unknown'}</Badge> },
      { key: 'match_scope', label: 'Scope', render: (row) => formatMatchScope(row.match_scope) },
      { key: 'language_bucket', label: 'Language', render: (row) => formatLanguageBucket(row.language_bucket) },
      { key: 'review_status', label: 'Review Status', render: (row) => <Badge variant={reviewStatusVariant(row.review_status)}>{row.review_status || 'open'}</Badge> },
      { key: 'suppression_reason', label: 'Reason', render: (row) => row.suppression_reason || '-' },
      { key: 'semantic_shadow_score', label: 'Semantic Drift', render: (row) => {
        if (row.semantic_shadow_score == null || row.score == null) return '-';
        const drift = Number(row.semantic_shadow_score) - Number(row.score);
        return drift >= semanticDriftThreshold ? `+${formatNumeric(drift, 2)}` : formatNumeric(drift, 2);
      }},
      { key: 'cap_reached', label: 'Cap', render: (row) => <Badge variant={row.cap_reached ? 'warning' : 'default'}>{row.cap_reached ? 'Reached' : 'OK'}</Badge> },
      { key: 'extraction_quality', label: 'Extraction', render: (row) => {
        const source = row.extraction_quality?.source;
        const matched = row.extraction_quality?.matched;
        const low = [source, matched].some((value) => typeof value === 'number' && value < 0.5);
        if (source == null && matched == null) return '-';
        return <Badge variant={low ? 'warning' : 'default'}>{low ? 'Low' : 'OK'}</Badge>;
      }},
      { key: 'threshold', label: 'Threshold', render: (row) => (row.threshold != null ? Number(row.threshold).toFixed(2) : '-') },
      { key: 'engine_version', label: 'Engine', render: (row) => row.engine_version || '-' },
      { key: 'created_at', label: 'Flagged At', render: (row) => formatTimestamp(row.created_at) }
    ],
    [semanticDriftThreshold]
  );

  const similarityActions = useMemo(
    () => [
      {
        key: 'review',
        label: 'Review',
        onClick: (row) => openSimilarityDetail(row.id)
      }
    ],
    []
  );

  const chatColumns = useMemo(
    () => [
      { key: 'student_label', label: 'Student', render: (row) => row.student_label || row.student_id || '-' },
      { key: 'assignment_label', label: 'Assignment', render: (row) => row.assignment_label || row.exam_id || '-' },
      { key: 'question_id', label: 'Question', render: (row) => row.question_id || '-' },
      { key: 'message_count', label: 'Messages', render: (row) => row.message_count ?? 0 },
      {
        key: 'last_role',
        label: 'Last Actor',
        render: (row) => <Badge variant={row.last_role === 'ai' ? 'info' : 'default'}>{row.last_role || '-'}</Badge>
      },
      { key: 'updated_at', label: 'Updated', render: (row) => formatTimestamp(row.updated_at) }
    ],
    []
  );

  const jobColumns = useMemo(
    () => [
      { key: 'job_type', label: 'Job Type', render: (row) => formatJobType(row.job_type) },
      {
        key: 'status',
        label: 'Status',
        render: (row) => <Badge variant={statusVariant(row.status)}>{row.status || '-'}</Badge>
      },
      {
        key: 'progress',
        label: 'Progress',
        render: (row) => {
          const progress = row.progress || {};
          const total = progress.total ?? 0;
          const completed = progress.completed ?? 0;
          const failed = progress.failed ?? 0;
          const skipped = progress.skipped ?? 0;
          const fallback = progress.fallback ?? 0;
          return `${completed}/${total} done | ${fallback} fallback | ${failed} failed | ${skipped} skipped`;
        }
      },
      {
        key: 'summary',
        label: 'Summary',
        render: (row) => {
          if (row.error) return row.error;
          if (row.job_type === 'similarity_check') {
            return `Flags ${row.summary?.flagged_count ?? 0} | Max ${row.summary?.max_score ?? '-'}`;
          }
          return `Completed ${row.summary?.completed ?? 0} | Fallback ${row.summary?.fallback ?? 0}`;
        }
      },
      { key: 'requested_at', label: 'Requested', render: (row) => formatTimestamp(row.requested_at) }
    ],
    []
  );

  const runActions = useMemo(
    () => [
      {
        key: 'open-console',
        label: 'Open Console',
        onClick: (row) => navigate(`/submissions/${row.submission_id}/evaluate`)
      }
    ],
    [navigate]
  );

  const statCards = useMemo(
    () => [
      {
        title: 'AI Reviewed Submissions',
        value: summary.submissions_completed ?? 0,
        hint: `Fallback ${summary.submissions_fallback ?? 0} | Pending ${summary.submissions_pending ?? 0}`,
        icon: ClipboardCheck,
        to: '/submissions'
      },
      {
        title: 'Evaluations With AI',
        value: summary.evaluations_with_ai ?? 0,
        hint: `Total evaluations ${summary.evaluations_total ?? 0}`,
        icon: CheckSquare,
        to: '/evaluations'
      },
      {
        title: 'AI Jobs',
        value: summary.jobs_total ?? 0,
        hint: `Queued ${summary.jobs_queued ?? 0} | Running ${summary.jobs_running ?? 0}`,
        icon: RefreshCcw
      },
      {
        title: 'Similarity Flags',
        value: summary.similarity_flags_total ?? 0,
        hint: `Assist-only ${summary.similarity_assist_only_total ?? 0} | Suppressed ${summary.similarity_suppressed_total ?? 0}`,
        icon: AlertTriangle
      },
      {
        title: 'AI Chat Threads',
        value: summary.chat_threads_total ?? 0,
        hint: 'Teacher/admin AI conversations',
        icon: MessageSquareText
      }
    ],
    [summary]
  );

  return (
    <div className="space-y-5 page-fade">
      <Card className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold">AI Operations</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Runtime visibility, durable job status, evaluation traces, chat activity, and similarity flags.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="btn-secondary" onClick={loadPageData} disabled={loading}>
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
            <Link className="btn-secondary" to="/submissions">Review Submissions</Link>
            <Link className="btn-secondary" to="/evaluations">Open Evaluations</Link>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <Badge variant={user?.role === 'admin' ? 'info' : 'default'}>{user?.role || '-'}</Badge>
          <span>{scope.label || 'Scoped AI visibility'}</span>
          <span>Assignments: {scope.assignments_count ?? 0}</span>
          <span>Submissions: {scope.submissions_count ?? 0}</span>
        </div>
      </Card>

      {loading ? (
        <Card>
          <p className="text-sm text-slate-500 dark:text-slate-400">Loading AI operations overview...</p>
        </Card>
      ) : null}

      {overview ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <Card className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Provider Mode</p>
                  <p className="mt-2 text-2xl font-semibold">{formatProviderMode(provider.mode)}</p>
                </div>
                <div className="rounded-2xl bg-brand-50 p-3 text-brand-600 dark:bg-brand-900/30 dark:text-brand-300">
                  <Bot size={20} />
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant={provider.openai_configured ? 'success' : 'warning'}>
                  {provider.openai_configured ? 'Provider configured' : 'Fallback mode active'}
                </Badge>
                <Badge variant={provider.provider_enabled ? 'info' : 'default'}>
                  {provider.provider_enabled ? 'Provider enabled' : 'Provider disabled'}
                </Badge>
                <Badge variant="default">Threshold {provider.similarity_threshold ?? '-'}</Badge>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Model: {provider.model || '-'} | Timeout: {provider.timeout_seconds ?? '-'}s | Max tokens:{' '}
                {provider.max_output_tokens ?? '-'}
              </p>
            </Card>

            {statCards.map((item) => (
              <StatCard
                key={item.title}
                icon={item.icon}
                title={item.title}
                value={item.value}
                hint={item.hint}
                to={item.to}
              />
            ))}
          </div>

          {isAdmin && runtimeConfig ? (
            <Card className="space-y-4">
              <div className="flex items-center gap-2">
                <Settings2 size={18} className="text-slate-500" />
                <div>
                  <h2 className="text-lg font-semibold">AI Runtime Controls</h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Runtime overrides are persisted and applied to evaluation AI, chat, similarity, and queued jobs.
                  </p>
                </div>
              </div>
              <form className="grid gap-4 lg:grid-cols-2" onSubmit={onSaveRuntimeConfig}>
                <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-3 text-sm dark:border-slate-700">
                  <input
                    type="checkbox"
                    checked={runtimeConfig.provider_enabled}
                    onChange={(e) => setRuntimeConfig((prev) => ({ ...prev, provider_enabled: e.target.checked }))}
                  />
                  <span>Enable OpenAI provider when configured</span>
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Model</span>
                  <input
                    className="input"
                    value={runtimeConfig.openai_model}
                    onChange={(e) => setRuntimeConfig((prev) => ({ ...prev, openai_model: e.target.value }))}
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Timeout (seconds)</span>
                  <input
                    className="input"
                    type="number"
                    min="5"
                    max="120"
                    value={runtimeConfig.openai_timeout_seconds}
                    onChange={(e) => setRuntimeConfig((prev) => ({ ...prev, openai_timeout_seconds: e.target.value }))}
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Max Output Tokens</span>
                  <input
                    className="input"
                    type="number"
                    min="50"
                    max="4000"
                    value={runtimeConfig.openai_max_output_tokens}
                    onChange={(e) => setRuntimeConfig((prev) => ({ ...prev, openai_max_output_tokens: e.target.value }))}
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Similarity Threshold</span>
                  <input
                    className="input"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={runtimeConfig.similarity_threshold}
                    onChange={(e) => setRuntimeConfig((prev) => ({ ...prev, similarity_threshold: e.target.value }))}
                  />
                </label>
                <div className="flex items-end gap-2">
                  <button className="btn-primary" type="submit" disabled={savingConfig}>
                    {savingConfig ? 'Saving...' : 'Save Runtime Settings'}
                  </button>
                  <button className="btn-secondary" type="button" onClick={loadPageData} disabled={loading}>
                    Reset
                  </button>
                </div>
              </form>
            </Card>
          ) : null}

          {isAdmin && semanticRolloutConfig ? (
            <Card className="space-y-5">
              <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                <div className="space-y-1">
                  <h2 className="text-lg font-semibold">Semantic Rollout Governance</h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Manual promotion guidance only. Approve a recommendation snapshot first, then activate assist-only guidance separately. Cross-assignment remains shadow-only and no action here changes automatic flagging.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant={promotionStateVariant(semanticScopeStates.same_assignment)}>
                    Same-assignment {formatPromotionState(semanticScopeStates.same_assignment)}
                  </Badge>
                  <Badge variant={promotionStateVariant(semanticScopeStates.cross_assignment)}>
                    Cross-assignment {formatPromotionState(semanticScopeStates.cross_assignment)}
                  </Badge>
                  <Badge variant={languageCoverageReadiness.coverage_ready ? 'success' : 'warning'}>
                    Language coverage {languageCoverageReadiness.coverage_ready ? 'ready' : 'insufficient'}
                  </Badge>
                  <Badge variant="default">Config v{semanticCurrentVersion}</Badge>
                </div>
              </div>

              <form className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]" onSubmit={onSaveSemanticRolloutConfig}>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-1">
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Same-assignment drift</span>
                    <input
                      className="input"
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={semanticRolloutConfig.semantic_same_assignment_drift_threshold}
                      onChange={(e) => setSemanticRolloutConfig((prev) => ({ ...prev, semantic_same_assignment_drift_threshold: e.target.value }))}
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Cross-assignment drift</span>
                    <input
                      className="input"
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={semanticRolloutConfig.semantic_cross_assignment_drift_threshold}
                      onChange={(e) => setSemanticRolloutConfig((prev) => ({ ...prev, semantic_cross_assignment_drift_threshold: e.target.value }))}
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Same-assignment min semantic</span>
                    <input
                      className="input"
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={semanticRolloutConfig.semantic_same_assignment_min_score}
                      onChange={(e) => setSemanticRolloutConfig((prev) => ({ ...prev, semantic_same_assignment_min_score: e.target.value }))}
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Cross-assignment min semantic</span>
                    <input
                      className="input"
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={semanticRolloutConfig.semantic_cross_assignment_min_score}
                      onChange={(e) => setSemanticRolloutConfig((prev) => ({ ...prev, semantic_cross_assignment_min_score: e.target.value }))}
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Same-assignment min samples</span>
                    <input
                      className="input"
                      type="number"
                      min="1"
                      max="5000"
                      value={semanticRolloutConfig.semantic_same_assignment_min_sample_size}
                      onChange={(e) => setSemanticRolloutConfig((prev) => ({ ...prev, semantic_same_assignment_min_sample_size: e.target.value }))}
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Cross-assignment min samples</span>
                    <input
                      className="input"
                      type="number"
                      min="1"
                      max="5000"
                      value={semanticRolloutConfig.semantic_cross_assignment_min_sample_size}
                      onChange={(e) => setSemanticRolloutConfig((prev) => ({ ...prev, semantic_cross_assignment_min_sample_size: e.target.value }))}
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Multilingual min samples</span>
                    <input
                      className="input"
                      type="number"
                      min="1"
                      max="5000"
                      value={semanticRolloutConfig.semantic_multilingual_min_sample_size}
                      onChange={(e) => setSemanticRolloutConfig((prev) => ({ ...prev, semantic_multilingual_min_sample_size: e.target.value }))}
                    />
                  </label>
                  <div className="flex items-end gap-2 md:col-span-2">
                    <button className="btn-primary" type="submit" disabled={savingSemanticConfig}>
                      {savingSemanticConfig ? 'Saving...' : 'Save Semantic Settings'}
                    </button>
                    <button className="btn-secondary" type="button" onClick={loadPageData} disabled={loading}>
                      Reset
                    </button>
                  </div>
                </div>

                <div className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/40">
                  <div className="space-y-1">
                    <h3 className="text-sm font-semibold">Approve + Activate Flow</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Approve a recommendation snapshot with justification, then activate assist-only guidance when the approved version is ready. Assist-only activation does not change automatic flagging.
                    </p>
                  </div>
                  <div className="grid gap-3">
                    <label className="space-y-1">
                      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Apply scope</span>
                      <select
                        className="input"
                        value={semanticApplyForm.scope}
                        onChange={(e) => setSemanticApplyForm((prev) => ({ ...prev, scope: e.target.value }))}
                      >
                        <option value="both">Both scopes</option>
                        <option value="same_assignment">Same-assignment</option>
                        <option value="cross_assignment">Cross-assignment</option>
                      </select>
                    </label>
                    <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-3 text-sm dark:border-slate-700">
                      <input
                        type="checkbox"
                        checked={semanticApplyForm.include_sample_sizes}
                        onChange={(e) => setSemanticApplyForm((prev) => ({ ...prev, include_sample_sizes: e.target.checked }))}
                      />
                      <span>Also apply recommended sample-size targets</span>
                    </label>
                    <label className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
                      <input
                        type="checkbox"
                        checked={semanticApplyForm.force}
                        onChange={(e) => setSemanticApplyForm((prev) => ({ ...prev, force: e.target.checked }))}
                      />
                      <span>Force apply even if readiness is blocked</span>
                    </label>
                    <label className="space-y-1">
                      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Justification</span>
                      <textarea
                        className="input min-h-[96px]"
                        value={semanticGovernanceJustification}
                        onChange={(e) => setSemanticGovernanceJustification(e.target.value)}
                        placeholder="Explain why this recommendation should be approved, activated, or rolled back."
                      />
                    </label>
                    <div className="grid gap-2 md:grid-cols-2">
                      <button
                        className="btn-primary"
                        type="button"
                        onClick={onApproveSemanticRecommendations}
                        disabled={applyingSemanticRecommendations || approveActionBlocked}
                      >
                        {applyingSemanticRecommendations ? 'Approving...' : 'Approve Recommendations'}
                      </button>
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={onActivateSemanticRecommendations}
                        disabled={activatingSemanticRecommendations || activateActionBlocked}
                      >
                        {activatingSemanticRecommendations ? 'Activating...' : 'Activate Assist-Only'}
                      </button>
                    </div>
                    {approveActionBlocked ? (
                      <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
                        Approval blocked: {selectedSemanticScopeBlockers[0]}
                      </p>
                    ) : null}
                    {activateActionBlocked ? (
                      <p className="rounded-xl border border-slate-200 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-300">
                        Activation check: {selectedApprovedVersion ? (selectedSemanticScopeBlockers[0] || 'Selected scope is ready for assist-only activation.') : 'No approved snapshot version is available for the selected scope.'}
                      </p>
                    ) : null}
                  </div>
                  <div className="space-y-2 text-xs text-slate-500 dark:text-slate-400">
                    <p>
                      Same-assignment rec: drift {formatNumeric(sameAssignmentReadiness.recommended_thresholds?.drift_threshold, 2)} | min semantic {formatNumeric(sameAssignmentReadiness.recommended_thresholds?.min_semantic_score, 2)}
                    </p>
                    <p>
                      Cross-assignment rec: drift {formatNumeric(crossAssignmentReadiness.recommended_thresholds?.drift_threshold, 2)} | min semantic {formatNumeric(crossAssignmentReadiness.recommended_thresholds?.min_semantic_score, 2)}
                    </p>
                    <p>
                      Current language sample target {languageCoverageReadiness.minimum_sample_size ?? 0} | Eligible rows {reviewerCalibration.summary?.reviewed_final_count ?? 0}
                    </p>
                    <p>
                      Queue shortcuts: calibration-eligible {defaultQueueMetricsById.get('calibration-eligible')?.count ?? 0} | mixed/transliterated {defaultQueueMetricsById.get('mixed-transliterated-review-candidates')?.count ?? 0}
                    </p>
                    <p>
                      Approved versions: same {semanticApprovedVersions.same_assignment ?? '-'} | cross {semanticApprovedVersions.cross_assignment ?? '-'} | Active versions: same {semanticActiveVersions.same_assignment ?? '-'} | cross {semanticActiveVersions.cross_assignment ?? '-'}
                    </p>
                  </div>
                </div>
              </form>

              <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
                <div className="space-y-3 rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-semibold">Current Scope States</h3>
                    <Badge variant={semanticRolloutBlockers.length ? 'warning' : 'success'}>
                      {semanticRolloutBlockers.length ? `${semanticRolloutBlockers.length} active` : 'clear'}
                    </Badge>
                  </div>
                  <div className="space-y-3">
                    {[
                      {
                        key: 'same_assignment',
                        label: 'Same-assignment',
                        state: semanticScopeStates.same_assignment,
                        blockers: sameAssignmentBlockers,
                        approvedVersion: semanticApprovedVersions.same_assignment,
                        activeVersion: semanticActiveVersions.same_assignment
                      },
                      {
                        key: 'cross_assignment',
                        label: 'Cross-assignment',
                        state: semanticScopeStates.cross_assignment,
                        blockers: crossAssignmentBlockers,
                        approvedVersion: semanticApprovedVersions.cross_assignment,
                        activeVersion: semanticActiveVersions.cross_assignment
                      }
                    ].map((item) => (
                      <div key={item.key} className="rounded-xl border border-slate-200 px-3 py-3 text-sm dark:border-slate-700">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="font-medium text-slate-900 dark:text-slate-100">{item.label}</p>
                          <Badge variant={promotionStateVariant(item.state)}>{formatPromotionState(item.state)}</Badge>
                        </div>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          Approved v{item.approvedVersion ?? '-'} | Active v{item.activeVersion ?? '-'}
                        </p>
                        <p className="mt-2 text-xs text-slate-600 dark:text-slate-300">
                          {item.blockers.length ? item.blockers[0] : 'No active blocker. Manual promotion guidance only remains in effect.'}
                        </p>
                      </div>
                    ))}
                    {semanticRolloutBlockers.length ? (
                      <div className="space-y-2">
                        {semanticRolloutBlockers.map((item, index) => (
                          <div key={`${item}-${index}`} className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
                            {item}
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>

                <div className="space-y-3 rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-semibold">Recent Config History</h3>
                    <Badge variant="default">{semanticHistoryRows.length} entries</Badge>
                  </div>
                  {semanticHistoryRows.length ? (
                    <div className="space-y-2">
                      {semanticHistoryRows.map((item) => (
                        <div key={item.id} className="rounded-xl border border-slate-200 px-3 py-3 text-sm dark:border-slate-700">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="font-medium text-slate-900 dark:text-slate-100">
                              v{item.version ?? '-'} Â· {item.action || 'semantic config update'}
                            </p>
                            <span className="text-xs text-slate-500">{formatTimestamp(item.created_at)}</span>
                          </div>
                          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                            Scope {formatScopeLabel(item.scope)} | Severity {item.severity || '-'} | Actor {item.actor_user_id || '-'}
                          </p>
                          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{item.detail || 'No audit detail recorded.'}</p>
                          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                            Justification: {item.justification || 'N/A'}
                          </p>
                          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                            Resulting state: same {formatPromotionState(item.resulting_scope_states?.same_assignment)} | cross {formatPromotionState(item.resulting_scope_states?.cross_assignment)}
                          </p>
                          {item.restored_from_version ? (
                            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Restored from version {item.restored_from_version}</p>
                          ) : null}
                          <div className="mt-3 flex flex-wrap gap-2">
                            <button
                              className="btn-secondary"
                              type="button"
                              onClick={() => onRollbackSemanticSnapshot(item.version, item.scope || 'both')}
                              disabled={rollingBackSemanticSnapshot}
                            >
                              {rollingBackSemanticSnapshot ? 'Rolling back...' : 'Rollback to This Version'}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">No semantic rollout config mutations have been recorded yet.</p>
                  )}
                </div>
              </div>
            </Card>
          ) : null}

          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Pipeline Snapshot</h2>
            <div className="flex flex-wrap gap-2">
              <Badge variant="default">Total submissions {summary.submissions_total ?? 0}</Badge>
              <Badge variant="warning">Pending {summary.submissions_pending ?? 0}</Badge>
              <Badge variant="info">Running {summary.submissions_running ?? 0}</Badge>
              <Badge variant="success">Completed {summary.submissions_completed ?? 0}</Badge>
              <Badge variant="warning">Fallback {summary.submissions_fallback ?? 0}</Badge>
              <Badge variant="danger">Failed {summary.submissions_failed ?? 0}</Badge>
            </div>
          </Card>

          <Card className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">Quality Gates</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Latest semantic calibration, reviewer-outcome drift, fairness, and benchmark signals.
              </p>
            </div>
            <div className="grid gap-4 xl:grid-cols-2">
              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">Semantic Calibration</h3>
                  <Badge variant={gateVariant(semanticCalibration.status)}>{semanticCalibration.status || 'unknown'}</Badge>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  Cases {semanticCalibration.case_count ?? 0} | Failures {semanticCalibration.failed_count ?? 0}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Drift trigger {formatNumeric(semanticCalibration.recommended_semantic_advantage_trigger, 2)} | Updated{' '}
                  {formatTimestamp(semanticCalibration.generated_at)}
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">Reviewer Outcome Calibration</h3>
                  <Badge variant={gateVariant(reviewerCalibration.status)}>{reviewerCalibration.status || 'assist_only'}</Badge>
                  <Badge variant="default">Shadow-only</Badge>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  Reviewed {reviewerCalibration.summary?.reviewed_final_count ?? 0} | Fixed {reviewerCalibration.summary?.fixed_count ?? 0} | Reopened{' '}
                  {reviewerCalibration.summary?.reopened_count ?? 0}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Assist-only drift {formatNumeric(reviewerCalibration.recommendations?.assist_only_semantic_advantage_threshold, 2)} | Promotion{' '}
                  {reviewerCalibration.recommendations?.promotion_thresholds?.semantic_advantage_min != null
                    ? `candidate ${formatNumeric(reviewerCalibration.recommendations?.promotion_thresholds?.semantic_advantage_min, 2)}`
                    : 'not ready'}
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">Same-Assignment Semantic Readiness</h3>
                  <Badge variant={sameAssignmentReadiness.promotion_ready ? 'success' : 'warning'}>
                    {sameAssignmentReadiness.promotion_ready ? 'ready' : 'blocked'}
                  </Badge>
                  <Badge variant="default">Manual guidance only</Badge>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  Eligible {sameAssignmentReadiness.eligible_sample_count ?? 0} | Fixed {sameAssignmentReadiness.finalized_outcomes?.fixed ?? 0} | Reopened {sameAssignmentReadiness.finalized_outcomes?.reopened ?? 0}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Drift rec {formatNumeric(sameAssignmentReadiness.recommended_thresholds?.drift_threshold, 2)} | Drift gap {formatNumeric(sameAssignmentReadiness.drift_separation?.drift_gap, 2)}
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">Cross-Assignment Semantic Readiness</h3>
                  <Badge variant={crossAssignmentReadiness.promotion_ready ? 'success' : 'warning'}>
                    {crossAssignmentReadiness.promotion_ready ? 'ready' : 'blocked'}
                  </Badge>
                  <Badge variant="default">Shadow-only</Badge>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  Eligible {crossAssignmentReadiness.eligible_sample_count ?? 0} | Fixed {crossAssignmentReadiness.finalized_outcomes?.fixed ?? 0} | Reopened {crossAssignmentReadiness.finalized_outcomes?.reopened ?? 0}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Drift rec {formatNumeric(crossAssignmentReadiness.recommended_thresholds?.drift_threshold, 2)} | Drift gap {formatNumeric(crossAssignmentReadiness.drift_separation?.drift_gap, 2)}
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">Language Coverage Readiness</h3>
                  <Badge variant={languageCoverageReadiness.coverage_ready ? 'success' : 'warning'}>
                    {languageCoverageReadiness.coverage_ready ? 'ready' : 'insufficient'}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  Min samples {languageCoverageReadiness.minimum_sample_size ?? 0} | Mixed/transliterated {(languageCoverageReadiness.coverage?.mixed_transliterated?.count) ?? 0} | Non-Latin {(languageCoverageReadiness.coverage?.non_latin?.count) ?? 0}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Latin only {(languageCoverageReadiness.coverage?.latin_only?.count) ?? 0} | Promotion remains manual until coverage is stable.
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">Reviewer Finalization Pipeline</h3>
                  <Badge variant={reviewerOutcomePipeline.minimum_sample_gap > 0 ? 'warning' : 'success'}>
                    {reviewerOutcomePipeline.minimum_sample_gap > 0 ? 'Needs outcomes' : 'Healthy'}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  Finalized {reviewerOutcomePipeline.finalized_count ?? 0} | Gap {reviewerOutcomePipeline.minimum_sample_gap ?? 0} | Rate 7d{' '}
                  {formatPercent(reviewerOutcomePipeline.finalization_rate_7d)}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Stale open {reviewerOutcomePipeline.stale_open_count ?? 0} | Stale in progress {reviewerOutcomePipeline.stale_in_progress_count ?? 0} | Median finalize{' '}
                  {reviewerOutcomePipeline.median_hours_to_finalize != null
                    ? `${formatNumeric(reviewerOutcomePipeline.median_hours_to_finalize, 1)}h`
                    : '-'}
                </p>
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  {reviewerOutcomePipeline.calibration_blocker_reason || 'Reviewer finalization flow is not available yet.'}
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">Readiness Trend</h3>
                  <Badge variant={readinessTrend.length ? 'info' : 'default'}>
                    {readinessTrend.length ? `${readinessTrend.length} points` : 'No trend yet'}
                  </Badge>
                </div>
                <div className="mt-3 space-y-2">
                  {readinessTrend.length ? (
                    readinessTrend
                      .slice(-5)
                      .reverse()
                      .map((point) => (
                        <div key={point.date} className="rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/40">
                          <div className="flex items-center justify-between gap-2">
                            <span>{point.date}</span>
                            <Badge variant={point.blocker_count > 0 ? 'warning' : 'success'}>
                              {point.blocker_count > 0 ? `${point.blocker_count} blockers` : 'clear'}
                            </Badge>
                          </div>
                          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                            Samples {point.eligible_sample_count ?? 0} | Fixed {point.fixed_count ?? 0} | Reopened {point.reopened_count ?? 0}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            Same gap {point.same_assignment?.sample_gap ?? 0} / drift {formatNumeric(point.same_assignment?.drift_gap, 2)} | Cross gap {point.cross_assignment?.sample_gap ?? 0} / drift {formatNumeric(point.cross_assignment?.drift_gap, 2)}
                          </p>
                        </div>
                      ))
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Readiness trend will appear after finalized semantic-review outcomes accumulate.
                    </p>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">Blocker Aging</h3>
                  <Badge variant={semanticRolloutBlockerAging.length ? 'warning' : 'success'}>
                    {semanticRolloutBlockerAging.length ? `${semanticRolloutBlockerAging.length} active` : 'clear'}
                  </Badge>
                </div>
                <div className="mt-3 space-y-2">
                  {semanticRolloutBlockerAging.length ? (
                    semanticRolloutBlockerAging.map((item) => (
                      <div key={`${item.reason}-${item.first_seen_date || 'now'}`} className="rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/40">
                        <div className="flex items-center justify-between gap-2">
                          <span>{item.reason}</span>
                          <Badge variant="warning">
                            {item.days_active != null ? `${item.days_active}d` : 'new'}
                          </Badge>
                        </div>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          First seen {item.first_seen_date || '-'} | Latest seen {item.latest_seen_date || '-'}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      No active blockers are aging right now.
                    </p>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">Legacy Finalization Validation</h3>
                  <Badge variant={(legacyValidation.invalid_finalized_rows ?? 0) > 0 ? 'warning' : 'success'}>
                    {(legacyValidation.invalid_finalized_rows ?? 0) > 0 ? 'Needs cleanup' : 'Clean'}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  Finalized {legacyValidation.finalized_rows ?? 0} | Eligible {legacyValidation.eligible_finalized_rows ?? 0} | Invalid {(legacyValidation.invalid_finalized_rows ?? 0)}
                </p>
                <div className="mt-3 space-y-2">
                  {(legacyValidation.reason_counts || []).length ? (
                    legacyValidation.reason_counts.map((item) => (
                      <div key={item.reason} className="rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/40">
                        <div className="flex items-center justify-between gap-2">
                          <span>{item.label || item.reason}</span>
                          <Badge variant="warning">{item.count ?? 0}</Badge>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      No invalid finalized legacy rows were detected in the current accessible dataset.
                    </p>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">Fairness Regression</h3>
                  <Badge variant={gateVariant(fairnessGate.status)}>{fairnessGate.status || 'unknown'}</Badge>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  Checks {fairnessGate.check_count ?? 0} | Failures {fairnessGate.failed_count ?? 0}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Max observed delta {formatNumeric(fairnessGate.max_observed_delta, 2)} | Updated {formatTimestamp(fairnessGate.generated_at)}
                </p>
                {fairnessGate.coverage ? (
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Coverage default {fairnessGate.coverage.default_check_count ?? 0} / external {fairnessGate.coverage.external_check_count ?? 0} / minimum {fairnessGate.coverage.minimum_required_check_count ?? 0}
                  </p>
                ) : null}
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">FP / FN Regression</h3>
                  <Badge variant={gateVariant(falsePositiveNegativeGate.status)}>{falsePositiveNegativeGate.status || 'unknown'}</Badge>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  Cases {falsePositiveNegativeGate.case_count ?? 0} | Failures {falsePositiveNegativeGate.failed_count ?? 0}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Flagged {falsePositiveNegativeGate.flagged_count ?? 0} | Assist-only {falsePositiveNegativeGate.assist_only_count ?? 0} | Suppressed {falsePositiveNegativeGate.suppressed_count ?? 0}
                </p>
                {falsePositiveNegativeGate.coverage ? (
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Coverage default {falsePositiveNegativeGate.coverage.default_case_count ?? 0} / external {falsePositiveNegativeGate.coverage.external_case_count ?? 0} / minimum {falsePositiveNegativeGate.coverage.minimum_required_case_count ?? 0}
                  </p>
                ) : null}
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">Benchmark Guard</h3>
                  <Badge variant={gateVariant(benchmarkGate.status)}>{benchmarkGate.status || 'missing'}</Badge>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  Sync {formatNumeric(benchmarkGate.metrics?.sync_handoff_ms, 2)} ms | Background {formatNumeric(benchmarkGate.metrics?.background_processing_ms, 2)} ms
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Detail fetch {formatNumeric(benchmarkGate.metrics?.review_modal_detail_ms, 2)} ms | Updated {formatTimestamp(benchmarkGate.generated_at)}
                </p>
              </div>
            </div>
          </Card>

          <Card className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">Reviewer Analytics</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Review status counts, finalization readiness, semantic drift buckets, reopened reasons, cross-assignment reversals, and assist-only threshold trend over time.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Badge variant="default">Open {reviewerAnalytics.review_status_counts?.open ?? 0}</Badge>
              <Badge variant="warning">In Progress {reviewerAnalytics.review_status_counts?.in_progress ?? 0}</Badge>
              <Badge variant="success">Fixed {reviewerAnalytics.review_status_counts?.fixed ?? 0}</Badge>
              <Badge variant="danger">Reopened {reviewerAnalytics.review_status_counts?.reopened ?? 0}</Badge>
              <Badge variant="info">Awaiting final {reviewerOutcomePipeline.open_count + reviewerOutcomePipeline.in_progress_count || 0}</Badge>
              <Badge variant={reviewerOutcomePipeline.minimum_sample_gap > 0 ? 'warning' : 'success'}>
                Calibration gap {reviewerOutcomePipeline.minimum_sample_gap ?? 0}
              </Badge>
            </div>

            <div className="grid gap-4 xl:grid-cols-3">
              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <h3 className="text-sm font-semibold">Drift Buckets</h3>
                <div className="mt-3 space-y-2">
                  {(reviewerAnalytics.drift_buckets || []).length ? (
                    reviewerAnalytics.drift_buckets.map((bucket) => (
                      <div key={bucket.label} className="rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/40">
                        <div className="flex items-center justify-between gap-2">
                          <span>{bucket.label}</span>
                          <span className="font-medium">{bucket.count ?? 0}</span>
                        </div>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          Fixed {bucket.fixed_count ?? 0} | Reopened {bucket.reopened_count ?? 0}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">No final reviewed semantic drift buckets yet.</p>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <h3 className="text-sm font-semibold">Top Reopened Reasons</h3>
                <div className="mt-3 space-y-2">
                  {(reviewerAnalytics.top_reopened_reasons || []).length ? (
                    reviewerAnalytics.top_reopened_reasons.map((reason) => (
                      <div key={reason.reason} className="rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/40">
                        <div className="flex items-center justify-between gap-2">
                          <span>{reason.reason}</span>
                          <span className="font-medium">{reason.count ?? 0}</span>
                        </div>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          {reason.example_note || 'No reviewer note sample available.'}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">No reopened reviewer notes yet.</p>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <h3 className="text-sm font-semibold">Reopened Reason Trends</h3>
                <div className="mt-3 space-y-2">
                  {(reviewerAnalytics.reopened_reason_trends || []).length ? (
                    reviewerAnalytics.reopened_reason_trends.map((reason) => (
                      <div key={reason.reason} className="rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/40">
                        <div className="flex items-center justify-between gap-2">
                          <span>{reason.reason}</span>
                          <Badge variant={trendVariant(reason.trend)}>
                            {reason.trend_symbol} {reason.delta > 0 ? `+${reason.delta}` : reason.delta}
                          </Badge>
                        </div>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          Recent {reason.recent_count ?? 0} | Previous {reason.previous_count ?? 0} | Window {reason.window_days ?? 7}d
                        </p>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          {reason.example_note || 'No reviewer note sample available.'}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">No reopened reason trends yet because final reviewed outcomes are still limited.</p>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <h3 className="text-sm font-semibold">Cross-Assignment Reversal Ranking</h3>
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  Finalized {crossAssignmentReviewOutcomes.reviewed_final_count ?? 0} | Fixed {crossAssignmentReviewOutcomes.fixed_count ?? 0} | Reopened {crossAssignmentReviewOutcomes.reopened_count ?? 0} | Reopened rate {formatPercent(crossAssignmentReviewOutcomes.reopened_rate)}
                </p>
                <div className="mt-3 space-y-2">
                  {crossAssignmentReversalRanking.length ? (
                    crossAssignmentReversalRanking.map((reason) => (
                      <div key={reason.reason} className="rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/40">
                        <div className="flex items-center justify-between gap-2">
                          <span>{reason.reason}</span>
                          <span className="font-medium">{reason.count ?? 0}</span>
                        </div>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          Share {formatPercent(reason.share)} | {reason.example_note || 'No reviewer note sample available.'}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">No cross-assignment reopened decisions have been finalized yet.</p>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <h3 className="text-sm font-semibold">Cross-Assignment Reason Trends</h3>
                <div className="mt-3 space-y-2">
                  {crossAssignmentReasonTrends.length ? (
                    crossAssignmentReasonTrends.map((reason) => (
                      <div key={reason.reason} className="rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/40">
                        <div className="flex items-center justify-between gap-2">
                          <span>{reason.reason}</span>
                          <Badge variant={trendVariant(reason.trend)}>
                            {reason.trend_symbol} {reason.delta > 0 ? `+${reason.delta}` : reason.delta}
                          </Badge>
                        </div>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          Recent {reason.recent_count ?? 0} | Previous {reason.previous_count ?? 0} | Window {reason.window_days ?? 7}d
                        </p>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          {reason.example_note || 'No reviewer note sample available.'}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">No cross-assignment reason trend is available yet because reviewer reversals are still sparse.</p>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <h3 className="text-sm font-semibold">Threshold Trend</h3>
                <div className="mt-3 space-y-2">
                  {(reviewerAnalytics.threshold_trend || []).length ? (
                    reviewerAnalytics.threshold_trend
                      .slice(-5)
                      .reverse()
                      .map((point) => (
                        <div key={point.date} className="rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/40">
                          <div className="flex items-center justify-between gap-2">
                            <span>{point.date}</span>
                            <span className="font-medium">{formatNumeric(point.assist_only_semantic_advantage_threshold, 2)}</span>
                          </div>
                          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                            Reviewed {point.reviewed_final_count ?? 0} | Fixed {point.fixed_count ?? 0} | Reopened {point.reopened_count ?? 0}
                          </p>
                        </div>
                      ))
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">No threshold trend yet because final reviewed outcomes are still missing.</p>
                  )}
                </div>
              </div>
            </div>
          </Card>

          <Card className="space-y-3">
            <div>
              <h2 className="text-lg font-semibold">AI Job Queue</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Durable background jobs for bulk submission AI and similarity processing.
              </p>
            </div>
            <Table columns={jobColumns} data={jobs} />
          </Card>

          <Card className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-lg font-semibold">Recent Evaluation AI Runs</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Latest persisted evaluation runs across the current AI scope.
                </p>
              </div>
              <button className="btn-secondary" onClick={() => navigate('/evaluations')}>View Evaluations</button>
            </div>
            <Table columns={runColumns} data={overview.recent_evaluation_runs || []} rowActions={runActions} />
          </Card>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold">Similarity Review Queue</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Filter flagged, assist-only, and suppressed similarity records by decision mode, review state, drift, candidate cap, extraction quality, and lexical range.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  className={activeQueueId === 'all' ? 'btn-primary' : 'btn-secondary'}
                  type="button"
                  onClick={() => applySimilarityFilters(DEFAULT_SIMILARITY_FILTERS, 'all')}
                >
                  All reviewable
                </button>
                {DEFAULT_QUEUE_PRESETS.map((preset) => (
                  <button
                    key={preset.id}
                    className={activeQueueId === preset.id ? 'btn-primary' : 'btn-secondary'}
                    type="button"
                    onClick={() => applySimilarityFilters(preset.filters, preset.id)}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
              {(defaultQueueMetrics || []).length ? (
                <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                  {defaultQueueMetrics.map((metric) => (
                    <button
                      key={metric.id}
                      type="button"
                      className={`rounded-xl border p-3 text-left transition ${
                        activeQueueId === metric.id
                          ? 'border-brand-500 bg-brand-50 dark:border-brand-400 dark:bg-brand-900/20'
                          : 'border-slate-200 bg-white hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900/40 dark:hover:border-slate-600'
                      }`}
                      onClick={() => applySimilarityFilters(metric.filters || DEFAULT_SIMILARITY_FILTERS, metric.id)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{metric.label}</p>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant={metric.count > 0 ? 'info' : 'default'}>{metric.count ?? 0}</Badge>
                          {defaultQueueForecastById.get(metric.id)?.attention_badge ? (
                            <Badge variant={defaultQueueForecastById.get(metric.id).backlog_risk === 'high' ? 'danger' : 'warning'}>
                              {defaultQueueForecastById.get(metric.id).backlog_risk}
                            </Badge>
                          ) : null}
                        </div>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                        <span>Avg age {formatAgeHours(metric.average_age_hours)}</span>
                        <span>Reopened {formatPercent(metric.reopened_rate)}</span>
                        <span>Low text {formatPercent(metric.low_extraction_rate)}</span>
                      </div>
                      {defaultQueueForecastById.get(metric.id) ? (
                        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                          Forecast: {defaultQueueForecastById.get(metric.id).backlog_risk} risk | Oldest {formatAgeHours(defaultQueueForecastById.get(metric.id).oldest_age_hours)} | {defaultQueueForecastById.get(metric.id).reason}
                        </p>
                      ) : null}
                    </button>
                  ))}
                </div>
              ) : null}
              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    className="input min-w-[220px] flex-1"
                    placeholder="Preset name"
                    value={similarityPresetName}
                    onChange={(e) => setSimilarityPresetName(e.target.value)}
                  />
                  <button className="btn-secondary" type="button" onClick={saveCurrentSimilarityPreset}>
                    Save Shared View
                  </button>
                  <button
                    className="btn-secondary"
                    type="button"
                    onClick={() => applySimilarityFilters(DEFAULT_SIMILARITY_FILTERS, 'all')}
                    disabled={similarityRowsLoading}
                  >
                    Show All
                  </button>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(savedSimilarityPresets || []).length ? (
                    savedSimilarityPresets.map((preset) => (
                      <div key={preset.id} className="flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1 dark:border-slate-700">
                        <button
                          className="text-sm font-medium text-slate-700 dark:text-slate-200"
                          type="button"
                          onClick={() => applySimilarityFilters(preset.filters, preset.id)}
                        >
                          {preset.name || preset.label}
                        </button>
                        {preset.created_by_label ? (
                          <span className="text-xs text-slate-500 dark:text-slate-400">by {preset.created_by_label}</span>
                        ) : null}
                        {sharedQueueMetricsById.get(preset.id) ? (
                          <span className="text-xs text-slate-500 dark:text-slate-400">
                            {sharedQueueMetricsById.get(preset.id).count ?? 0} cases â€¢ Avg age {formatAgeHours(sharedQueueMetricsById.get(preset.id).average_age_hours)} â€¢ Reopened {formatPercent(sharedQueueMetricsById.get(preset.id).reopened_rate)} â€¢ Low text {formatPercent(sharedQueueMetricsById.get(preset.id).low_extraction_rate)}
                          </span>
                        ) : null}
                        <button
                          className="text-xs text-slate-500 hover:text-rose-600 dark:text-slate-400 dark:hover:text-rose-300"
                          type="button"
                          onClick={() => deleteSimilarityPreset(preset.id)}
                        >
                          Remove
                        </button>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">No shared reviewer presets yet.</p>
                  )}
                </div>
              </div>
              <div className="grid gap-3 lg:grid-cols-3">
                <label className="space-y-1 lg:col-span-2">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Search</span>
                  <input
                    className="input"
                    placeholder="Submission ID or reviewer note"
                    value={similarityFilters.search}
                    onChange={(e) => setSimilarityFilters((prev) => ({ ...prev, search: e.target.value }))}
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Review status</span>
                  <select
                    className="input"
                    value={similarityFilters.review_status}
                    onChange={(e) => setSimilarityFilters((prev) => ({ ...prev, review_status: e.target.value }))}
                  >
                    <option value="">All</option>
                    <option value="open">Open</option>
                    <option value="in_progress">In Progress</option>
                    <option value="fixed">Fixed</option>
                    <option value="reopened">Reopened</option>
                  </select>
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Decision mode</span>
                  <select
                    className="input"
                    value={similarityFilters.decision_mode}
                    onChange={(e) => setSimilarityFilters((prev) => ({ ...prev, decision_mode: e.target.value }))}
                  >
                    <option value="">All</option>
                    <option value="flagged">Flagged</option>
                    <option value="assist_only">Assist-only</option>
                    <option value="suppressed">Suppressed</option>
                  </select>
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Match scope</span>
                  <select
                    className="input"
                    value={similarityFilters.match_scope}
                    onChange={(e) => setSimilarityFilters((prev) => ({ ...prev, match_scope: e.target.value }))}
                  >
                    <option value="">All</option>
                    <option value="same_assignment_lexical">Same-assignment lexical</option>
                    <option value="same_assignment_shadow">Same-assignment shadow</option>
                    <option value="cross_assignment_shadow">Cross-assignment shadow</option>
                  </select>
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Language bucket</span>
                  <select
                    className="input"
                    value={similarityFilters.language_bucket}
                    onChange={(e) => setSimilarityFilters((prev) => ({ ...prev, language_bucket: e.target.value }))}
                  >
                    <option value="">All</option>
                    <option value="latin_only">Latin only</option>
                    <option value="mixed_transliterated">Mixed/transliterated</option>
                    <option value="non_latin">Non-Latin</option>
                  </select>
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Min lexical</span>
                  <input
                    className="input"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={similarityFilters.min_score}
                    onChange={(e) => setSimilarityFilters((prev) => ({ ...prev, min_score: e.target.value }))}
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Max lexical</span>
                  <input
                    className="input"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={similarityFilters.max_score}
                    onChange={(e) => setSimilarityFilters((prev) => ({ ...prev, max_score: e.target.value }))}
                  />
                </label>
                <div className="flex flex-wrap items-end gap-2 lg:col-span-3">
                  <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={similarityFilters.semantic_review_candidate}
                      onChange={(e) => setSimilarityFilters((prev) => ({ ...prev, semantic_review_candidate: e.target.checked }))}
                    />
                    <span>Semantic review candidate</span>
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={similarityFilters.calibration_eligible}
                      onChange={(e) => setSimilarityFilters((prev) => ({ ...prev, calibration_eligible: e.target.checked }))}
                    />
                    <span>Calibration eligible</span>
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={similarityFilters.semantic_drift_present}
                      onChange={(e) => setSimilarityFilters((prev) => ({ ...prev, semantic_drift_present: e.target.checked }))}
                    />
                    <span>Semantic drift present</span>
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={similarityFilters.cap_reached}
                      onChange={(e) => setSimilarityFilters((prev) => ({ ...prev, cap_reached: e.target.checked }))}
                    />
                    <span>Cap reached</span>
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={similarityFilters.low_extraction_quality}
                      onChange={(e) => setSimilarityFilters((prev) => ({ ...prev, low_extraction_quality: e.target.checked }))}
                    />
                    <span>Low extraction quality</span>
                  </label>
                  <button
                    className="btn-primary"
                    type="button"
                    onClick={() => applySimilarityFilters(similarityFilters)}
                    disabled={similarityRowsLoading}
                  >
                    {similarityRowsLoading ? 'Filtering...' : 'Apply Filters'}
                  </button>
                  <button
                    className="btn-secondary"
                    type="button"
                    onClick={() => {
                      const resetFilters = {
                        ...DEFAULT_SIMILARITY_FILTERS
                      };
                      applySimilarityFilters(resetFilters, 'all');
                    }}
                    disabled={similarityRowsLoading}
                  >
                    Reset
                  </button>
                </div>
              </div>
              {similarityRowsLoading ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">Loading filtered similarity checks...</p>
              ) : null}
              <Table columns={similarityColumns} data={similarityRows} rowActions={similarityActions} />
            </Card>

            <Card className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold">Recent AI Chat Threads</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Latest teacher/admin evaluation chat activity tied to accessible assignments.
                </p>
              </div>
              <Table columns={chatColumns} data={overview.recent_chat_threads || []} />
            </Card>
          </div>
        </>
      ) : null}
      <Modal
        open={similarityDetailOpen}
        title="Similarity Review"
        onClose={() => {
          setSimilarityDetailOpen(false);
          setSimilarityDetail(null);
        }}
        size="large"
      >
        {similarityDetailLoading ? (
          <p className="text-sm text-slate-500">Loading similarity detail...</p>
        ) : similarityDetail ? (
          <div className="space-y-5">
            <div className="space-y-3">
              <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/40">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">At a glance</p>
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                      {similarityDetail.source_submission_summary?.student_label || 'Student A'} vs{' '}
                      {similarityDetail.matched_submission_summary?.student_label || 'Student B'}
                    </h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      {similarityDetail.source_submission_summary?.assignment_label ||
                        similarityDetail.source_assignment_label ||
                        'Assignment not available'}
                    </p>
                  </div>
                  <div className="rounded-xl bg-slate-50 px-3 py-2 text-right dark:bg-slate-800/50">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Current review</p>
                    <p className="mt-1 text-sm font-medium text-slate-900 dark:text-slate-100">
                      {formatReviewStatusLabel(similarityDetail.review_status)}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Last updated {formatTimestamp(similarityDetail.review_updated_at || similarityDetail.reviewed_at)}
                    </p>
                  </div>
                </div>
                <p className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-200">
                  {buildSimilarityDecisionSummary(similarityDetail)}
                </p>
              </div>
              <div className="grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
                <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/40">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Case summary</p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Decision</p>
                      <p className="mt-1 text-sm font-medium text-slate-900 dark:text-slate-100">
                        {formatDecisionModeLabel(similarityDetail.decision_mode, similarityDetail.is_flagged)}
                      </p>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {formatReviewReasonLabel(similarityDetail.suppression_reason)}
                      </p>
                    </div>
                    <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Match strength</p>
                      <p className="mt-1 text-sm font-medium text-slate-900 dark:text-slate-100">
                        Lexical similarity {formatNumeric(similarityDetail.score, 2)}
                      </p>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        Threshold {formatNumeric(similarityDetail.threshold, 2)} | Effective overlap{' '}
                        {formatNumeric(similarityDetail.overlap_stats?.effective_overlap_ratio, 2)}
                      </p>
                    </div>
                    <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Students compared</p>
                      <p className="mt-1 text-sm font-medium text-slate-900 dark:text-slate-100">
                        {similarityDetail.source_submission_summary?.submission_public_id || similarityDetail.source_submission_public_id || '-'}
                        {' '}and{' '}
                        {similarityDetail.matched_submission_summary?.submission_public_id || similarityDetail.matched_submission_public_id || '-'}
                      </p>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {similarityDetail.source_submission_summary?.student_label || '-'} |{' '}
                        {similarityDetail.matched_submission_summary?.student_label || '-'}
                      </p>
                    </div>
                    <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Evidence quality</p>
                      <p className="mt-1 text-sm font-medium text-slate-900 dark:text-slate-100">
                        {similarityDetail.risk_signals?.effective_excerpt_count ?? 0} strong excerpt
                        {(similarityDetail.risk_signals?.effective_excerpt_count ?? 0) === 1 ? '' : 's'}
                      </p>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        Source quality {formatNumeric(similarityDetail.extraction_quality?.source, 3)} | Matched quality{' '}
                        {formatNumeric(similarityDetail.extraction_quality?.matched, 3)}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/40">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">What to review first</p>
                  <div className="mt-3 space-y-2">
                    {buildSimilarityReviewerChecklist(similarityDetail).map((item) => (
                      <p key={item} className="rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-700 dark:bg-slate-800/50 dark:text-slate-200">
                        {item}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 text-xs text-slate-500">
              <Badge variant={decisionModeVariant(similarityDetail.decision_mode)}>
                {formatDecisionModeLabel(similarityDetail.decision_mode, similarityDetail.is_flagged)}
              </Badge>
              <Badge variant="default">{formatMatchScope(similarityDetail.match_scope)}</Badge>
              <Badge variant="default">{formatLanguageBucket(similarityDetail.language_bucket)}</Badge>
              <Badge variant="default">Lexical similarity {Number(similarityDetail.score || 0).toFixed(2)}</Badge>
              <Badge variant="default">Threshold {Number(similarityDetail.threshold || 0).toFixed(2)}</Badge>
              <Badge variant="default">Engine {similarityDetail.engine_version || '-'}</Badge>
              <Badge variant="info">Review {formatReviewStatusLabel(similarityDetail.review_status)}</Badge>
              {similarityDetail.semantic_review_candidate ? (
                <Badge variant="warning">Semantic review candidate</Badge>
              ) : null}
              {similarityDetailCountsTowardCalibration ? (
                <Badge variant="success">Counts toward calibration</Badge>
              ) : null}
              <Badge variant={similarityDetail.cap_reached ? 'warning' : 'default'}>
                {similarityDetail.cap_reached ? 'Candidate cap reached' : 'Candidate cap OK'}
              </Badge>
              {similarityDetail.semantic_shadow_score != null ? (
                <Badge variant="default">
                  Semantic shadow {Number(similarityDetail.semantic_shadow_score).toFixed(2)}
                </Badge>
              ) : null}
              {similarityDetail.semantic_shadow_score != null ? (
                <Badge variant="info">Shadow-only assist</Badge>
              ) : null}
              {semanticDriftDetected ? (
                <Badge variant="warning">Semantic drift +{formatNumeric(semanticDriftValue, 2)}</Badge>
              ) : null}
            </div>
            {similarityDetailStale ? (
              <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-200">
                This case has stayed {similarityDetail.review_status === 'in_progress' ? 'in progress' : 'open'} long enough to risk calibration lag. Finalize it as fixed or reopened when your evidence review is complete.
              </p>
            ) : null}
            {semanticDriftDetected ? (
              <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-200">
                Semantic shadow exceeds lexical similarity by {formatNumeric(semanticDriftValue, 2)}. Treat this as a reviewer hint only; it does not change flagging without manual approval.
              </p>
            ) : null}
            {(similarityDetail.risk_signals?.low_extraction_block ||
              similarityDetail.extraction_diagnostics?.source?.low_text_reason ||
              similarityDetail.extraction_diagnostics?.matched?.low_text_reason) ? (
              <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-200">
                Low-text extraction is limiting evidence quality for this comparison. Treat this case as insufficient evidence until OCR succeeds or a clearer text-searchable file is available.
                {' '}
                {similarityDetail.extraction_diagnostics?.source?.ocr_retry_guidance ||
                  similarityDetail.extraction_diagnostics?.matched?.ocr_retry_guidance ||
                  'Do not treat weak extraction alone as copying evidence.'}
              </p>
            ) : null}

            <div className="grid gap-3 lg:grid-cols-2">
              {[
                {
                  title: 'Source submission',
                  summary: similarityDetail.source_submission_summary,
                },
                {
                  title: 'Matched submission',
                  summary: similarityDetail.matched_submission_summary,
                },
              ].map((item) => (
                <div key={item.title} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/40">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{item.title}</p>
                      <p className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
                        {item.summary?.student_label || 'Student not available'}
                      </p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {item.summary?.submission_public_id || item.summary?.submission_label || '-'} |{' '}
                        {item.summary?.assignment_label || '-'}
                      </p>
                    </div>
                    <Badge variant="default">{item.summary?.file_name || 'No file name'}</Badge>
                  </div>
                  <div className="mt-3 space-y-2 text-sm text-slate-700 dark:text-slate-200">
                    <p><span className="font-medium">Uploaded:</span> {formatTimestamp(item.summary?.uploaded_at)}</p>
                    <p><span className="font-medium">Extracted text length:</span> {item.summary?.text_length ?? '-'}</p>
                  </div>
                  <div className="mt-3 rounded-xl bg-slate-50 p-3 text-sm text-slate-700 dark:bg-slate-800/50 dark:text-slate-200">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Answer preview</p>
                    <p className="mt-2 whitespace-pre-wrap">{item.summary?.text_preview || 'No extracted preview available.'}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="grid gap-3 lg:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/40">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Why this case needs review</p>
                  <div className="mt-3 space-y-2 text-sm text-slate-700 dark:text-slate-200">
                    <p><span className="font-medium">Decision:</span> {formatDecisionModeLabel(similarityDetail.decision_mode, similarityDetail.is_flagged)}</p>
                    <p><span className="font-medium">System reason:</span> {formatReviewReasonLabel(similarityDetail.suppression_reason)}</p>
                    <p><span className="font-medium">Effective overlap:</span> {formatNumeric(similarityDetail.overlap_stats?.effective_overlap_ratio, 2)}</p>
                    <p><span className="font-medium">Matching excerpts:</span> {similarityDetail.risk_signals?.effective_excerpt_count ?? '-'}</p>
                    <p><span className="font-medium">Non-prompt shared tokens:</span> {similarityDetail.risk_signals?.non_prompt_shared_tokens ?? '-'}</p>
                  </div>
              </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/40">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Evidence quality</p>
                  <div className="mt-3 space-y-2 text-sm text-slate-700 dark:text-slate-200">
                    <p><span className="font-medium">Lexical score:</span> {formatNumeric(similarityDetail.score, 2)} against threshold {formatNumeric(similarityDetail.threshold, 2)}</p>
                    <p><span className="font-medium">Prompt discount:</span> {formatNumeric(similarityDetail.overlap_stats?.prompt_term_discount, 2)}</p>
                    <p><span className="font-medium">Extraction quality:</span> Source {formatNumeric(similarityDetail.extraction_quality?.source, 3)} | Matched {formatNumeric(similarityDetail.extraction_quality?.matched, 3)}</p>
                    <p><span className="font-medium">Candidate count:</span> {similarityDetail.candidate_count ?? '-'}</p>
                  <p><span className="font-medium">Cap status:</span> {similarityDetail.cap_reached ? 'Reached' : 'OK'}</p>
                </div>
              </div>
            </div>

            <div className="grid gap-3 lg:grid-cols-3">
              <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/40">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Risk checks</p>
                <div className="mt-3 space-y-2 text-sm text-slate-700 dark:text-slate-200">
                  <p><span className="font-medium">Prompt overlap:</span> {formatNumeric(similarityDetail.risk_signals?.prompt_overlap_ratio, 2)}</p>
                  <p><span className="font-medium">Generic overlap:</span> {formatNumeric(similarityDetail.risk_signals?.generic_overlap_ratio, 2)}</p>
                  <p><span className="font-medium">Boilerplate risk:</span> {similarityDetail.risk_signals?.boilerplate_risk ? 'Yes' : 'No'}</p>
                  <p><span className="font-medium">Language mismatch:</span> {similarityDetail.risk_signals?.language_mismatch ? 'Yes' : 'No'}</p>
                  <p><span className="font-medium">Tokenization:</span> {similarityDetail.tokenization_mode_applied || '-'}</p>
                </div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/40">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Language and semantic hints</p>
                <div className="mt-3 space-y-2 text-sm text-slate-700 dark:text-slate-200">
                  <p><span className="font-medium">Language bucket:</span> {formatLanguageBucket(similarityDetail.language_bucket)}</p>
                  <p><span className="font-medium">Scripts:</span> Source {similarityDetail.language_profile?.source?.primary_script || '-'} | Matched {similarityDetail.language_profile?.matched?.primary_script || '-'}</p>
                  <p><span className="font-medium">Mixed/non-Latin:</span> {similarityDetail.language_profile?.mixed_or_non_latin ? 'Yes' : 'No'}</p>
                  <p><span className="font-medium">Semantic shadow:</span> {formatNumeric(similarityDetail.semantic_shadow_score, 2)}</p>
                  <p><span className="font-medium">Semantic candidate:</span> {similarityDetail.semantic_review_candidate ? 'Yes' : 'No'}</p>
                </div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/40">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Review state</p>
                <div className="mt-3 space-y-2 text-sm text-slate-700 dark:text-slate-200">
                  <p><span className="font-medium">Status:</span> {similarityDetail.review_status || 'open'}</p>
                  <p><span className="font-medium">Counts toward calibration:</span> {similarityDetailCountsTowardCalibration ? 'Yes' : 'No'}</p>
                  <p><span className="font-medium">Scope:</span> {formatMatchScope(similarityDetail.match_scope)}</p>
                  <p><span className="font-medium">Last update:</span> {formatTimestamp(similarityDetail.review_updated_at || similarityDetail.reviewed_at)}</p>
                  <p><span className="font-medium">Finalized:</span> {formatTimestamp(similarityDetail.review_finalized_at)}</p>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/40">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">File quality and OCR diagnostics</p>
              <div className="mt-3 grid gap-3 lg:grid-cols-2 text-sm text-slate-700 dark:text-slate-200">
                <div className="space-y-2">
                  <p><span className="font-medium">Source OCR:</span> {similarityDetail.extraction_diagnostics?.source?.ocr_attempted ? 'Yes' : 'No'} ({similarityDetail.extraction_diagnostics?.source?.ocr_provider || '-'})</p>
                  <p><span className="font-medium">Matched OCR:</span> {similarityDetail.extraction_diagnostics?.matched?.ocr_attempted ? 'Yes' : 'No'} ({similarityDetail.extraction_diagnostics?.matched?.ocr_provider || '-'})</p>
                  <p><span className="font-medium">Confidence:</span> {formatNumeric(similarityDetail.extraction_diagnostics?.source?.extraction_confidence, 2)} → {formatNumeric(similarityDetail.extraction_diagnostics?.matched?.extraction_confidence, 2)}</p>
                </div>
                <div className="space-y-2">
                  <p><span className="font-medium">Low-text reason:</span> {similarityDetail.extraction_diagnostics?.source?.low_text_reason || similarityDetail.extraction_diagnostics?.matched?.low_text_reason || '-'}</p>
                  <p><span className="font-medium">OCR state:</span> {formatOcrResultState(similarityDetail.extraction_diagnostics?.source?.ocr_result_state)} → {formatOcrResultState(similarityDetail.extraction_diagnostics?.matched?.ocr_result_state)}</p>
                  <p><span className="font-medium">Guidance:</span> {similarityDetail.extraction_diagnostics?.source?.ocr_retry_guidance || similarityDetail.extraction_diagnostics?.matched?.ocr_retry_guidance || 'No OCR retry guidance needed.'}</p>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Similar content found</p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Compare the exact wording below from {similarityDetail.source_submission_summary?.student_label || 'the source submission'} and{' '}
                  {similarityDetail.matched_submission_summary?.student_label || 'the matched submission'}. Higher-overlap excerpts are the strongest evidence.
                </p>
              </div>
              <div className="grid gap-3 lg:grid-cols-2">
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Search excerpts</span>
                  <input
                    className="input"
                    placeholder="Filter by text..."
                    value={excerptQuery}
                    onChange={(e) => setExcerptQuery(e.target.value)}
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Min overlap</span>
                  <input
                    className="input"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={excerptMinOverlap}
                    onChange={(e) => setExcerptMinOverlap(e.target.value)}
                  />
                </label>
              </div>
              {(similarityDetail.evidence_excerpts || []).length ? (
                <div className="space-y-3">
                  {similarityDetail.evidence_excerpts
                    .filter((item) => {
                      const query = excerptQuery.trim().toLowerCase();
                      const overlap = Number(item.effective_overlap_ratio ?? item.overlap_ratio ?? 0);
                      const minOverlap = Number(excerptMinOverlap || 0);
                      const combined = `${item.source_sentence} ${item.matched_sentence}`.toLowerCase();
                      const matchesQuery = !query || combined.includes(query);
                      return matchesQuery && overlap >= minOverlap;
                    })
                    .map((item, index) => (
                    <div key={`${item.source_sentence}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/40">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Match {index + 1} • Overlap {formatPercent(item.effective_overlap_ratio ?? item.overlap_ratio ?? 0)}
                      </p>
                      <div className="mt-3 grid gap-3 lg:grid-cols-2">
                        <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            {similarityDetail.source_submission_summary?.student_label || 'Source student'}
                          </p>
                          <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">{item.source_sentence}</p>
                        </div>
                        <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            {similarityDetail.matched_submission_summary?.student_label || 'Matched student'}
                          </p>
                          <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">{item.matched_sentence}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No excerpts match the current filter, or no evidence excerpts were stored for this case.</p>
              )}
            </div>

            {(similarityDetail.related_shadow_candidates || []).length ? (
              <div className="space-y-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Cross-assignment shadow candidates</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    These are review-only semantic hints from other assignments. They never change automatic flagging.
                  </p>
                </div>
                <div className="grid gap-3 lg:grid-cols-2">
                  {(similarityDetail.related_shadow_candidates || []).map((candidate) => (
                    <div key={candidate.id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                          {candidate.matched_submission_summary?.student_label || candidate.matched_submission_public_id || candidate.matched_submission_id || '-'}
                        </p>
                        <Badge variant="info">{formatMatchScope(candidate.match_scope)}</Badge>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {candidate.matched_submission_summary?.submission_public_id || candidate.matched_submission_public_id || '-'} |{' '}
                        {candidate.matched_assignment_label || candidate.matched_assignment_id || '-'}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        Semantic {formatNumeric(candidate.semantic_shadow_score, 2)} | Lexical {formatNumeric(candidate.score, 2)}
                      </p>
                      <p className="text-xs text-slate-500">
                        Script {candidate.language_profile?.matched?.primary_script || '-'} | Review {formatReviewStatusLabel(candidate.review_status)}
                      </p>
                      <div className="mt-2 rounded-lg bg-slate-50 p-2 text-xs text-slate-600 dark:bg-slate-800/50 dark:text-slate-300">
                        {candidate.matched_submission_summary?.text_preview || 'No extracted preview available.'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="space-y-2">
              <p className="text-xs uppercase tracking-wide text-slate-500">Reviewer Actions</p>
              <div className="flex flex-wrap gap-2">
                <button
                  className="btn-primary"
                  type="button"
                  onClick={() => {
                    setReviewStatus('fixed');
                    saveSimilarityReview('fixed');
                  }}
                  disabled={reviewSaving}
                >
                  {reviewSaving && reviewStatus === 'fixed' ? 'Saving...' : 'Mark Fixed'}
                </button>
                <button
                  className="btn-primary"
                  type="button"
                  onClick={() => {
                    setReviewStatus('reopened');
                    saveSimilarityReview('reopened');
                  }}
                  disabled={reviewSaving}
                >
                  {reviewSaving && reviewStatus === 'reopened' ? 'Saving...' : 'Reopen'}
                </button>
                <button
                  className="btn-secondary"
                  type="button"
                  onClick={() => {
                    setReviewStatus('in_progress');
                    saveSimilarityReview('in_progress');
                  }}
                  disabled={reviewSaving}
                >
                  Set In Progress
                </button>
                <button
                  className="btn-secondary"
                  type="button"
                  onClick={() => {
                    setReviewStatus('open');
                    saveSimilarityReview('open');
                  }}
                  disabled={reviewSaving}
                >
                  Reset To Open
                </button>
              </div>
              <div className="grid gap-3 lg:grid-cols-2">
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Status</span>
                  <select
                    className="input"
                    value={reviewStatus}
                    onChange={(e) => {
                      const nextStatus = e.target.value;
                      setReviewStatus(nextStatus);
                      if (nextStatus !== 'reopened') {
                        setReviewReasonCode('');
                      }
                    }}
                  >
                    <option value="open">Open</option>
                    <option value="in_progress">In Progress</option>
                    <option value="fixed">Fixed</option>
                    <option value="reopened">Reopened</option>
                  </select>
                </label>
                {reviewStatus === 'reopened' ? (
                  <label className="space-y-1">
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Reopened reason</span>
                    <select
                      className="input"
                      value={reviewReasonCode}
                      onChange={(e) => setReviewReasonCode(e.target.value)}
                    >
                      {REVIEW_REASON_OPTIONS.map((option) => (
                        <option key={option.value || 'blank'} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}
                <label className="space-y-1 lg:col-span-2">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Notes</span>
                  <textarea
                    className="input min-h-[96px]"
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                  />
                </label>
              </div>
              <button
                className="btn-primary"
                onClick={() => saveSimilarityReview(reviewStatus)}
                disabled={reviewSaving}
              >
                {reviewSaving ? 'Saving...' : 'Save Notes / Status'}
              </button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">No similarity detail available.</p>
        )}
      </Modal>
    </div>
  );
}

