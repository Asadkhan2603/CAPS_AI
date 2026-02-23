import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { Card } from '../components/ui';
import { apiClient } from '../services/apiClient';

interface Submission {
  id: string;
  assignment_id: string;
  student_user_id: string;
  extracted_text?: string;
  notes?: string;
}

export const EvaluateSubmissionPage: React.FC = () => {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [evaluationId, setEvaluationId] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [marks, setMarks] = useState({
    attendance_percent: 85,
    skill: 2,
    behavior: 2,
    report: 8,
    viva: 15,
    final_exam: 40,
    remarks: ''
  });

  useEffect(() => {
    async function load() {
      if (!submissionId) return;
      setLoading(true);
      setError('');
      try {
        const [subRes, evalRes] = await Promise.all([
          apiClient.get(`/submissions/${submissionId}`),
          apiClient.get('/evaluations/', { params: { submission_id: submissionId, skip: 0, limit: 1 } })
        ]);
        setSubmission(subRes.data);
        const existing = (evalRes.data || [])[0];
        if (existing) {
          setEvaluationId(existing.id);
          setMarks({
            attendance_percent: existing.attendance_percent ?? 85,
            skill: existing.skill ?? 2,
            behavior: existing.behavior ?? 2,
            report: existing.report ?? 8,
            viva: existing.viva ?? 15,
            final_exam: existing.final_exam ?? 40,
            remarks: existing.remarks || ''
          });
        }
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load submission');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [submissionId]);

  async function saveEvaluation() {
    if (!submission) return;
    setSaving(true);
    setError('');
    try {
      if (evaluationId) {
        await apiClient.put(`/evaluations/${evaluationId}`, marks);
      } else {
        const created = await apiClient.post('/evaluations/', {
          submission_id: submission.id,
          ...marks,
          is_finalized: false
        });
        setEvaluationId(created.data?.id || '');
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save evaluation');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button className="p-2 hover:bg-slate-100 rounded-lg transition-colors" onClick={() => navigate('/dashboard')}>
            <ChevronLeft size={20} />
          </button>
          <div>
            <h1 className="text-xl font-bold text-slate-900">Evaluate Submission</h1>
            <p className="text-sm text-slate-500">Marks + remarks workflow</p>
          </div>
        </div>
        <button className="btn-primary" onClick={saveEvaluation} disabled={saving || loading}>{saving ? 'Saving...' : 'Save Evaluation'}</button>
      </header>

      {error ? <div className="p-3 bg-red-50 border border-red-100 text-red-600 text-sm rounded-lg">{error}</div> : null}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Submission">
          {loading ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : (
            <pre className="bg-slate-900 text-slate-200 rounded-xl p-4 overflow-auto text-xs whitespace-pre-wrap">
{submission?.extracted_text || submission?.notes || 'No content available'}
            </pre>
          )}
        </Card>

        <Card title="Marks">
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm">Attendance %<input type="number" className="input mt-1" value={marks.attendance_percent} onChange={(e) => setMarks((p) => ({ ...p, attendance_percent: Number(e.target.value) }))} /></label>
            <label className="text-sm">Skill<input type="number" step="0.1" className="input mt-1" value={marks.skill} onChange={(e) => setMarks((p) => ({ ...p, skill: Number(e.target.value) }))} /></label>
            <label className="text-sm">Behavior<input type="number" step="0.1" className="input mt-1" value={marks.behavior} onChange={(e) => setMarks((p) => ({ ...p, behavior: Number(e.target.value) }))} /></label>
            <label className="text-sm">Report<input type="number" step="0.1" className="input mt-1" value={marks.report} onChange={(e) => setMarks((p) => ({ ...p, report: Number(e.target.value) }))} /></label>
            <label className="text-sm">Viva<input type="number" step="0.1" className="input mt-1" value={marks.viva} onChange={(e) => setMarks((p) => ({ ...p, viva: Number(e.target.value) }))} /></label>
            <label className="text-sm">Final Exam<input type="number" step="0.1" className="input mt-1" value={marks.final_exam} onChange={(e) => setMarks((p) => ({ ...p, final_exam: Number(e.target.value) }))} /></label>
          </div>
          <label className="text-sm block mt-3">Remarks<textarea className="input mt-1 min-h-[90px]" value={marks.remarks} onChange={(e) => setMarks((p) => ({ ...p, remarks: e.target.value }))} /></label>
        </Card>
      </div>
    </div>
  );
};
