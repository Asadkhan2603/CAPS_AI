import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Badge from '../../components/ui/Badge';
import Card from '../../components/ui/Card';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';

function toneForStep(step) {
  if (step.is_complete) return 'success';
  if (step.is_blocked) return 'warning';
  return 'info';
}

export default function AdminOnboardingPage() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError('');
      try {
        const response = await apiClient.get('/admin/analytics/onboarding-overview');
        setOverview(response.data || null);
      } catch (err) {
        setError(formatApiError(err, 'Failed to load onboarding wizard'));
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  const progress = overview?.progress || {};
  const nextStep = overview?.next_step || null;
  const steps = overview?.steps || [];

  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Admin Onboarding Wizard</h1>
        <p className="text-sm text-slate-500">
          Follow the minimum academic setup path from university root to active course delivery.
        </p>
      </Card>

      {loading ? (
        <Card>
          <p className="text-sm text-slate-500">Loading onboarding progress...</p>
        </Card>
      ) : null}

      {error ? (
        <Card>
          <p className="text-sm text-rose-600">{error}</p>
        </Card>
      ) : null}

      {!loading && !error ? (
        <>
          <div className="grid gap-3 md:grid-cols-4">
            <Metric label="Required Steps Complete" value={`${progress.completed_steps ?? 0}/${progress.total_steps ?? 0}`} />
            <Metric label="Progress" value={`${progress.percent ?? 0}%`} />
            <Metric label="Total Tracked Steps" value={steps.length} />
            <Metric label="Next Recommended Step" value={nextStep?.label || 'Complete'} />
          </div>

          {nextStep ? (
            <Card className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Next Best Step</p>
                  <h2 className="text-lg font-semibold">{nextStep.label}</h2>
                  <p className="text-sm text-slate-500">{nextStep.description}</p>
                </div>
                <Link to={nextStep.action_path} className="btn-primary">
                  {nextStep.cta_label}
                </Link>
              </div>
            </Card>
          ) : (
            <Card>
              <p className="text-sm text-emerald-700 dark:text-emerald-300">
                The minimum onboarding path is complete. You can move on to student onboarding, course delivery, and communication setup.
              </p>
            </Card>
          )}

          <div className="grid gap-3 xl:grid-cols-2">
            {steps.map((step) => (
              <Card key={step.key} className="space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold">{step.label}</h3>
                      <Badge variant={toneForStep(step)}>
                        {step.is_complete ? 'complete' : step.is_blocked ? 'blocked' : step.required ? 'required' : 'optional'}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-slate-500">{step.description}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Current Count</p>
                    <p className="text-2xl font-semibold">{step.count ?? 0}</p>
                  </div>
                </div>

                {step.blocked_by?.length ? (
                  <div className="flex flex-wrap gap-2">
                    {step.blocked_by.map((dependency) => (
                      <span
                        key={`${step.key}-${dependency}`}
                        className="rounded-full bg-amber-100 px-2.5 py-1 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
                      >
                        Waiting on {dependency.replaceAll('_', ' ')}
                      </span>
                    ))}
                  </div>
                ) : null}

                <div className="flex flex-wrap gap-2">
                  <Link to={step.action_path} className="btn-secondary">
                    {step.cta_label}
                  </Link>
                  {step.key === 'students' ? (
                    <Link to="/students" className="btn-secondary">
                      Open Student Directory
                    </Link>
                  ) : null}
                  {step.key === 'course_offerings' ? (
                    <Link to="/class-slots" className="btn-secondary">
                      Open Class Slots
                    </Link>
                  ) : null}
                </div>
              </Card>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-2xl font-semibold">{value ?? 0}</p>
    </Card>
  );
}
