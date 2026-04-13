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
  createSharedSimilarityView,
  deleteSharedSimilarityView,
  getAiOperationsOverview,
  getAiRuntimeConfig,
  getSimilarityCheck,
  listAiJobs,
  listSimilarityChecks,
  listSharedSimilarityViews,
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
  semantic_drift_present: false,
  cap_reached: false,
  low_extraction_quality: false,
  min_score: '',
  max_score: ''
};
const DEFAULT_QUEUE_PRESETS = [
  { id: 'needs-review', label: 'Needs review', filters: { ...DEFAULT_SIMILARITY_FILTERS, review_status: 'open' } },
  { id: 'reopened', label: 'Reopened', filters: { ...DEFAULT_SIMILARITY_FILTERS, review_status: 'reopened' } },
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

function formatMatchScope(scope) {
  if (scope === 'cross_assignment_shadow') return 'Cross-assignment shadow';
  if (scope === 'same_assignment_shadow') return 'Same-assignment shadow';
  if (scope === 'same_assignment_lexical') return 'Same-assignment lexical';
  return scope || '-';
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

function statusVariant(status) {
  if (status === 'completed') return 'success';
  if (status === 'failed') return 'danger';
  if (status === 'running') return 'info';
  if (status === 'pending' || status === 'queued') return 'warning';
  if (status === 'fallback') return 'warning';
  return 'default';
}

function formatJobType(value) {
  if (value === 'bulk_submission_ai') return 'Bulk Submission AI';
  if (value === 'similarity_check') return 'Similarity Check';
  return value || '-';
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
      }
      const [overviewResponse, jobsResponse, similarityViewsResponse, runtimeResponse] = await Promise.all(requests);
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
      await loadSimilarityRows();
    } catch (err) {
      setOverview(null);
      setJobs([]);
      setSimilarityRows([]);
      setSavedSimilarityPresets([]);
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
        is_flagged: true,
        limit: 50
      };
      if (activeFilters.review_status) params.review_status = activeFilters.review_status;
      if (activeFilters.semantic_drift_present) params.semantic_drift_present = true;
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

  const summary = overview?.summary || {};
  const provider = overview?.provider || {};
  const scope = overview?.scope || {};
  const qualityGates = overview?.quality_gates || {};
  const semanticCalibration = qualityGates.semantic_calibration || {};
  const reviewerCalibration = qualityGates.reviewer_outcome_calibration || {};
  const reviewerAnalytics = reviewerCalibration.analytics || {};
  const fairnessGate = qualityGates.fairness_regression || {};
  const benchmarkGate = qualityGates.benchmark || {};
  const similarityQueueMetrics = overview?.similarity_queue_metrics || {};
  const similarityQueueForecast = overview?.similarity_queue_forecast || {};
  const defaultQueueMetrics = similarityQueueMetrics.default_queues || [];
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
      { key: 'source_submission_id', label: 'Source Submission' },
      { key: 'matched_submission_id', label: 'Matched Submission' },
      { key: 'score', label: 'Lexical Similarity', render: (row) => (row.score != null ? Number(row.score).toFixed(2) : '-') },
      { key: 'review_status', label: 'Review Status', render: (row) => <Badge variant={reviewStatusVariant(row.review_status)}>{row.review_status || 'open'}</Badge> },
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
      { key: 'student_id', label: 'Student' },
      { key: 'exam_id', label: 'Assignment' },
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
        hint: 'Flagged similarity alerts',
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
                  <h3 className="text-sm font-semibold">Fairness Regression</h3>
                  <Badge variant={gateVariant(fairnessGate.status)}>{fairnessGate.status || 'unknown'}</Badge>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  Checks {fairnessGate.check_count ?? 0} | Failures {fairnessGate.failed_count ?? 0}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Max observed delta {formatNumeric(fairnessGate.max_observed_delta, 2)} | Updated {formatTimestamp(fairnessGate.generated_at)}
                </p>
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
                Review status counts, semantic drift buckets, reopened reasons, and assist-only threshold trend over time.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Badge variant="default">Open {reviewerAnalytics.review_status_counts?.open ?? 0}</Badge>
              <Badge variant="warning">In Progress {reviewerAnalytics.review_status_counts?.in_progress ?? 0}</Badge>
              <Badge variant="success">Fixed {reviewerAnalytics.review_status_counts?.fixed ?? 0}</Badge>
              <Badge variant="danger">Reopened {reviewerAnalytics.review_status_counts?.reopened ?? 0}</Badge>
            </div>

            <div className="grid gap-4 xl:grid-cols-4">
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
                <h2 className="text-lg font-semibold">Flagged Similarity Checks</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Filter flagged similarity records by review state, drift, candidate cap, extraction quality, and lexical range.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  className={activeQueueId === 'all' ? 'btn-primary' : 'btn-secondary'}
                  type="button"
                  onClick={() => applySimilarityFilters(DEFAULT_SIMILARITY_FILTERS, 'all')}
                >
                  All flagged
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
                            {sharedQueueMetricsById.get(preset.id).count ?? 0} cases • Avg age {formatAgeHours(sharedQueueMetricsById.get(preset.id).average_age_hours)} • Reopened {formatPercent(sharedQueueMetricsById.get(preset.id).reopened_rate)} • Low text {formatPercent(sharedQueueMetricsById.get(preset.id).low_extraction_rate)}
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
          <div className="space-y-4">
            <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-300">
              Lexical similarity measures shared wording, while semantic signals (if present) suggest paraphrase risk. Review excerpts before deciding.
            </p>
            <div className="flex flex-wrap gap-2 text-xs text-slate-500">
              <Badge variant={similarityDetail.is_flagged ? 'danger' : 'default'}>
                {similarityDetail.is_flagged ? 'Flagged' : 'Unflagged'}
              </Badge>
              <Badge variant="default">{formatMatchScope(similarityDetail.match_scope)}</Badge>
              <Badge variant="default">Lexical similarity {Number(similarityDetail.score || 0).toFixed(2)}</Badge>
              <Badge variant="default">Threshold {Number(similarityDetail.threshold || 0).toFixed(2)}</Badge>
              <Badge variant="default">Engine {similarityDetail.engine_version || '-'}</Badge>
              <Badge variant="info">Review {similarityDetail.review_status || 'open'}</Badge>
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
            {semanticDriftDetected ? (
              <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-200">
                Semantic shadow exceeds lexical similarity by {formatNumeric(semanticDriftValue, 2)}. Treat this as a reviewer hint only; it does not change flagging without manual approval.
              </p>
            ) : null}

            <div className="grid gap-3 lg:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/40">
                <p className="text-xs uppercase tracking-wide text-slate-500">Overlap Stats</p>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  Lexical overlap: {similarityDetail.overlap_stats?.overlap_ratio ?? '-'} |
                  Effective overlap: {similarityDetail.overlap_stats?.effective_overlap_ratio ?? '-'}
                </p>
                <p className="text-xs text-slate-500">
                  Prompt discount: {similarityDetail.overlap_stats?.prompt_term_discount ?? '-'} |
                  Tokens: {similarityDetail.overlap_stats?.source_token_count ?? '-'} → {similarityDetail.overlap_stats?.matched_token_count ?? '-'}
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/40">
                <p className="text-xs uppercase tracking-wide text-slate-500">Extraction Quality</p>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  Source: {similarityDetail.extraction_quality?.source ?? '-'} | Matched: {similarityDetail.extraction_quality?.matched ?? '-'}
                </p>
                <p className="text-xs text-slate-500">
                  Candidates evaluated: {similarityDetail.candidate_count ?? '-'}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Source OCR {similarityDetail.extraction_diagnostics?.source?.ocr_attempted ? 'yes' : 'no'} ({similarityDetail.extraction_diagnostics?.source?.ocr_provider || '-'}) |
                  Matched OCR {similarityDetail.extraction_diagnostics?.matched?.ocr_attempted ? 'yes' : 'no'} ({similarityDetail.extraction_diagnostics?.matched?.ocr_provider || '-'})
                </p>
                <p className="text-xs text-slate-500">
                  Extraction confidence {formatNumeric(similarityDetail.extraction_diagnostics?.source?.extraction_confidence, 2)} → {formatNumeric(similarityDetail.extraction_diagnostics?.matched?.extraction_confidence, 2)} |
                  Low-text reason {similarityDetail.extraction_diagnostics?.source?.low_text_reason || similarityDetail.extraction_diagnostics?.matched?.low_text_reason || '-'}
                </p>
              </div>
            </div>

            <div className="grid gap-3 lg:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/40">
                <p className="text-xs uppercase tracking-wide text-slate-500">Language Profile</p>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  Source {similarityDetail.language_profile?.source?.primary_script || '-'} | Matched {similarityDetail.language_profile?.matched?.primary_script || '-'}
                </p>
                <p className="text-xs text-slate-500">
                  Mixed/non-Latin: {similarityDetail.language_profile?.mixed_or_non_latin ? 'yes' : 'no'}
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/40">
                <p className="text-xs uppercase tracking-wide text-slate-500">Shadow Scope</p>
                <p className="text-sm text-slate-700 dark:text-slate-200">
                  {formatMatchScope(similarityDetail.match_scope)}
                </p>
                <p className="text-xs text-slate-500">
                  Cross-assignment shadow evidence is reviewer-only and never changes automatic flagging.
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Matched Excerpts</p>
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
                    <div key={`${item.source_sentence}-${index}`} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                      <p className="text-xs text-slate-500">Overlap: {item.effective_overlap_ratio ?? item.overlap_ratio ?? '-'}</p>
                      <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">Source: {item.source_sentence}</p>
                      <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">Matched: {item.matched_sentence}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No excerpts stored for this match.</p>
              )}
            </div>

            {(similarityDetail.related_shadow_candidates || []).length ? (
              <div className="space-y-3">
                <p className="text-xs uppercase tracking-wide text-slate-500">Cross-Assignment Shadow Candidates</p>
                <div className="grid gap-3 lg:grid-cols-2">
                  {(similarityDetail.related_shadow_candidates || []).map((candidate) => (
                    <div key={candidate.id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                          {candidate.matched_submission_id}
                        </p>
                        <Badge variant="info">{formatMatchScope(candidate.match_scope)}</Badge>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        Semantic {formatNumeric(candidate.semantic_shadow_score, 2)} | Lexical {formatNumeric(candidate.score, 2)}
                      </p>
                      <p className="text-xs text-slate-500">
                        Assignment {candidate.matched_assignment_id || '-'} | Script {candidate.language_profile?.matched?.primary_script || '-'}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="space-y-2">
              <p className="text-xs uppercase tracking-wide text-slate-500">Reviewer Actions</p>
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
                onClick={async () => {
                  if (reviewStatus === 'reopened' && !reviewReasonCode) {
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
                      review_status: reviewStatus,
                      review_reason_code: reviewStatus === 'reopened' ? reviewReasonCode : '',
                      review_notes: reviewNotes
                    });
                    setSimilarityDetail(updated);
                    setReviewReasonCode(updated?.review_reason_code || '');
                    pushToast({ title: 'Similarity updated', description: 'Review status saved.', variant: 'success' });
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
                }}
                disabled={reviewSaving}
              >
                {reviewSaving ? 'Saving...' : 'Save Review'}
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
