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
  getAiOperationsOverview,
  getAiRuntimeConfig,
  getSimilarityCheck,
  listAiJobs,
  listSimilarityChecks,
  updateSimilarityCheck,
  updateAiRuntimeConfig
} from '../services/aiService';
import { formatApiError } from '../utils/apiError';

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

function gateVariant(status) {
  if (status === 'passed') return 'success';
  if (status === 'failed') return 'danger';
  if (status === 'assist_only') return 'info';
  if (status === 'missing') return 'warning';
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
  const [reviewStatus, setReviewStatus] = useState('open');
  const [reviewNotes, setReviewNotes] = useState('');
  const [reviewSaving, setReviewSaving] = useState(false);
  const [excerptQuery, setExcerptQuery] = useState('');
  const [excerptMinOverlap, setExcerptMinOverlap] = useState('0.15');
  const isAdmin = user?.role === 'admin';

  async function loadPageData() {
    setLoading(true);
    try {
      const requests = [getAiOperationsOverview({ limit: 8 }), listAiJobs({ limit: 8 })];
      if (isAdmin) {
        requests.push(getAiRuntimeConfig());
      }
      const [overviewResponse, jobsResponse, runtimeResponse] = await Promise.all(requests);
      setOverview(overviewResponse || null);
      setJobs(jobsResponse?.items || []);
      if (isAdmin && runtimeResponse?.effective) {
        setRuntimeConfig({
          provider_enabled: Boolean(runtimeResponse.effective.provider_enabled),
          openai_model: runtimeResponse.effective.openai_model || '',
          openai_timeout_seconds: String(runtimeResponse.effective.openai_timeout_seconds ?? 20),
          openai_max_output_tokens: String(runtimeResponse.effective.openai_max_output_tokens ?? 400),
          similarity_threshold: String(runtimeResponse.effective.similarity_threshold ?? 0.8)
        });
      }
    } catch (err) {
      setOverview(null);
      setJobs([]);
      pushToast({
        title: 'AI module load failed',
        description: formatApiError(err, 'Unable to load AI operations overview'),
        variant: 'error'
      });
    } finally {
      setLoading(false);
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
  const fairnessGate = qualityGates.fairness_regression || {};
  const benchmarkGate = qualityGates.benchmark || {};
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
      { key: 'threshold', label: 'Threshold', render: (row) => (row.threshold != null ? Number(row.threshold).toFixed(2) : '-') },
      { key: 'engine_version', label: 'Engine', render: (row) => row.engine_version || '-' },
      { key: 'created_at', label: 'Flagged At', render: (row) => formatTimestamp(row.created_at) }
    ],
    []
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
                  Most recent flagged similarity records in the current scope.
                </p>
              </div>
              <Table columns={similarityColumns} data={overview.recent_similarity_flags || []} rowActions={similarityActions} />
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

            <div className="space-y-2">
              <p className="text-xs uppercase tracking-wide text-slate-500">Reviewer Actions</p>
              <div className="grid gap-3 lg:grid-cols-2">
                <label className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Status</span>
                  <select
                    className="input"
                    value={reviewStatus}
                    onChange={(e) => setReviewStatus(e.target.value)}
                  >
                    <option value="open">Open</option>
                    <option value="in_progress">In Progress</option>
                    <option value="fixed">Fixed</option>
                    <option value="reopened">Reopened</option>
                  </select>
                </label>
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
                  setReviewSaving(true);
                  try {
                    const updated = await updateSimilarityCheck(similarityDetail.id, {
                      review_status: reviewStatus,
                      review_notes: reviewNotes
                    });
                    setSimilarityDetail(updated);
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
