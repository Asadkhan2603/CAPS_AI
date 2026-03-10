import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
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
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import {
  getAiOperationsOverview,
  getAiRuntimeConfig,
  listAiJobs,
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
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [overview, setOverview] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [runtimeConfig, setRuntimeConfig] = useState(null);
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

  useEffect(() => {
    loadPageData();
  }, [isAdmin]);

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
      { key: 'score', label: 'Score', render: (row) => (row.score != null ? Number(row.score).toFixed(2) : '-') },
      { key: 'threshold', label: 'Threshold', render: (row) => (row.threshold != null ? Number(row.threshold).toFixed(2) : '-') },
      { key: 'engine_version', label: 'Engine', render: (row) => row.engine_version || '-' },
      { key: 'created_at', label: 'Flagged At', render: (row) => formatTimestamp(row.created_at) }
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
              <Table columns={similarityColumns} data={overview.recent_similarity_flags || []} />
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
    </div>
  );
}
