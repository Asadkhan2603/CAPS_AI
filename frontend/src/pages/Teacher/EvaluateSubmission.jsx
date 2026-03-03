import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Card from '../../components/ui/Card';
import FormInput from '../../components/ui/FormInput';
import AIChatPanel from '../../components/Teacher/AIChatPanel';
import { apiClient } from '../../services/apiClient';
import { getEvaluationChatHistory, sendEvaluationChatMessage } from '../../services/aiService';
import { useToast } from '../../hooks/useToast';
import { useAuth } from '../../hooks/useAuth';
import { formatApiError } from '../../utils/apiError';

function questionCandidatesFromAssignment(assignment) {
  const lines = String(assignment?.description || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  const normalized = lines.filter((line) => /^(q[\d]+|question[\d\s:.])/i.test(line));
  if (normalized.length > 0) {
    return normalized.map((line, index) => ({ id: `q${index + 1}`, text: line }));
  }
  return [
    {
      id: 'q1',
      text: assignment?.title ? `Evaluate submission for "${assignment.title}"` : 'Evaluate this submission'
    }
  ];
}

export default function EvaluateSubmissionPage() {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { pushToast } = useToast();

  const [submission, setSubmission] = useState(null);
  const [assignment, setAssignment] = useState(null);
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatSending, setChatSending] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [selectedQuestionId, setSelectedQuestionId] = useState('q1');
  const [rubric, setRubric] = useState('Concept clarity, correctness, depth, and structure');
  const [evaluationId, setEvaluationId] = useState('');
  const [aiPreview, setAiPreview] = useState(null);
  const [aiPreviewLoading, setAiPreviewLoading] = useState(false);
  const [marks, setMarks] = useState({
    attendance_percent: 85,
    skill: 2,
    behavior: 2,
    report: 8,
    viva: 15,
    final_exam: 40,
    remarks: ''
  });

  const questions = useMemo(() => questionCandidatesFromAssignment(assignment), [assignment]);
  const selectedQuestion = useMemo(
    () => questions.find((question) => question.id === selectedQuestionId) || questions[0],
    [questions, selectedQuestionId]
  );

  async function loadCore() {
    if (!submissionId) return;
    setLoading(true);
    try {
      const submissionRes = await apiClient.get(`/submissions/${submissionId}`);
      const submissionData = submissionRes.data;
      setSubmission(submissionData);

      const [assignmentRes, usersRes, evalRes] = await Promise.all([
        apiClient.get(`/assignments/${submissionData.assignment_id}`),
        apiClient.get('/users/'),
        apiClient.get('/evaluations/', { params: { submission_id: submissionId, skip: 0, limit: 1 } })
      ]);
      setAssignment(assignmentRes.data || null);
      const matchedStudent = (usersRes.data || []).find((item) => item.id === submissionData.student_user_id);
      setStudent(matchedStudent || null);
      const existingEvaluation = (evalRes.data || [])[0];
      if (existingEvaluation) {
        setEvaluationId(existingEvaluation.id);
        setMarks({
          attendance_percent: existingEvaluation.attendance_percent ?? 85,
          skill: existingEvaluation.skill ?? 2,
          behavior: existingEvaluation.behavior ?? 2,
          report: existingEvaluation.report ?? 8,
          viva: existingEvaluation.viva ?? 15,
          final_exam: existingEvaluation.final_exam ?? 40,
          remarks: existingEvaluation.remarks || ''
        });
      }
    } catch (err) {
      pushToast({
        title: 'Load failed',
        description: formatApiError(err, 'Failed to load submission evaluation view'),
        variant: 'error'
      });
    } finally {
      setLoading(false);
    }
  }

  async function loadHistory(currentSubmission = submission) {
    if (!currentSubmission?.student_user_id || !currentSubmission?.assignment_id) return;
    setChatLoading(true);
    try {
      const history = await getEvaluationChatHistory(
        currentSubmission.student_user_id,
        currentSubmission.assignment_id
      );
      setChatMessages(history.messages || []);
    } catch (err) {
      if (err?.response?.status === 404) {
        setChatMessages([]);
      } else {
        pushToast({
          title: 'Chat history failed',
          description: formatApiError(err, 'Unable to load AI chat history'),
          variant: 'error'
        });
      }
    } finally {
      setChatLoading(false);
    }
  }

  useEffect(() => {
    loadCore();
  }, [submissionId]);

  useEffect(() => {
    loadHistory(submission);
  }, [submission?.id]);

  async function onSaveMarks() {
    if (!submission) return;
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
      pushToast({ title: 'Saved', description: 'Marks saved successfully.', variant: 'success' });
    } catch (err) {
      pushToast({ title: 'Save failed', description: formatApiError(err, 'Failed to save marks'), variant: 'error' });
    }
  }

  async function onPreviewAI() {
    if (!submission) return;
    setAiPreviewLoading(true);
    try {
      const response = await apiClient.post('/evaluations/ai-preview', {
        submission_id: submission.id,
        ...marks
      });
      setAiPreview(response.data || null);
      pushToast({ title: 'AI preview ready', description: 'Review AI insight before saving marks.', variant: 'success' });
    } catch (err) {
      pushToast({ title: 'AI preview failed', description: formatApiError(err, 'Failed to generate AI preview'), variant: 'error' });
    } finally {
      setAiPreviewLoading(false);
    }
  }

  async function onSendChat() {
    if (!submission || !chatInput.trim() || !selectedQuestion) return;
    setChatSending(true);
    try {
      const payload = {
        teacher_id: user?.id,
        student_id: submission.student_user_id,
        exam_id: submission.assignment_id,
        question_id: selectedQuestion.id,
        teacher_message: chatInput.trim(),
        question_text: selectedQuestion.text,
        student_answer: submission.extracted_text || submission.notes || '',
        rubric,
        submission_id: submission.id
      };
      const response = await sendEvaluationChatMessage(payload);
      setChatMessages(response?.thread?.messages || []);
      setChatInput('');
    } catch (err) {
      pushToast({ title: 'AI failed', description: formatApiError(err, 'AI chat request failed'), variant: 'error' });
    } finally {
      setChatSending(false);
    }
  }

  if (!['teacher', 'admin'].includes(user?.role || '')) {
    return (
      <Card>
        <p className="text-sm text-rose-600">Only teachers/admin can access AI Assisted Evaluation Console.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4 page-fade">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">AI Assisted Evaluation Console</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Evaluate submission with marks + AI support in one workspace.
          </p>
        </div>
        <button className="btn-secondary" onClick={() => navigate('/submissions')}>
          Back to Submissions
        </button>
      </div>

      {loading ? <Card><p className="text-sm text-slate-500">Loading submission...</p></Card> : null}

      {!loading && submission ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="space-y-4">
            <Card className="space-y-3">
              <h2 className="text-lg font-semibold">Submission Details</h2>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Student: {student?.full_name || submission.student_user_id}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Exam/Assignment: {assignment?.title || submission.assignment_id}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                File: {submission.original_filename} ({submission.file_size_bytes} bytes)
              </p>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/50">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Student Answer Text</p>
                <p className="max-h-56 overflow-y-auto whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-200">
                  {submission.extracted_text || submission.notes || 'No extracted answer text available.'}
                </p>
              </div>
            </Card>

            <Card className="space-y-3">
              <h2 className="text-lg font-semibold">Question List</h2>
              <div className="flex flex-wrap gap-2">
                {questions.map((question) => (
                  <button
                    key={question.id}
                    className={`rounded-lg border px-3 py-1 text-sm ${
                      selectedQuestion?.id === question.id
                        ? 'border-brand-500 bg-brand-100 text-brand-700 dark:border-brand-400 dark:bg-brand-900/30 dark:text-brand-300'
                        : 'border-slate-300 text-slate-700 dark:border-slate-700 dark:text-slate-300'
                    }`}
                    onClick={() => setSelectedQuestionId(question.id)}
                  >
                    {question.id.toUpperCase()}
                  </button>
                ))}
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-300">{selectedQuestion?.text}</p>
              <FormInput
                as="textarea"
                label="Rubric"
                value={rubric}
                onChange={(event) => setRubric(event.target.value)}
              />
            </Card>

            <Card className="space-y-3">
              <h2 className="text-lg font-semibold">Marks Input</h2>
              <div className="grid gap-3 sm:grid-cols-2">
                <FormInput label="Attendance %" type="number" value={marks.attendance_percent} onChange={(e) => setMarks((p) => ({ ...p, attendance_percent: Number(e.target.value) }))} />
                <FormInput label="Skill (0-2.5)" type="number" step="0.1" value={marks.skill} onChange={(e) => setMarks((p) => ({ ...p, skill: Number(e.target.value) }))} />
                <FormInput label="Behavior (0-2.5)" type="number" step="0.1" value={marks.behavior} onChange={(e) => setMarks((p) => ({ ...p, behavior: Number(e.target.value) }))} />
                <FormInput label="Report (0-10)" type="number" step="0.1" value={marks.report} onChange={(e) => setMarks((p) => ({ ...p, report: Number(e.target.value) }))} />
                <FormInput label="Viva (0-20)" type="number" step="0.1" value={marks.viva} onChange={(e) => setMarks((p) => ({ ...p, viva: Number(e.target.value) }))} />
                <FormInput label="Final Exam (0-60)" type="number" step="0.1" value={marks.final_exam} onChange={(e) => setMarks((p) => ({ ...p, final_exam: Number(e.target.value) }))} />
              </div>
              <FormInput as="textarea" label="Remarks" value={marks.remarks} onChange={(e) => setMarks((p) => ({ ...p, remarks: e.target.value }))} />
              <div className="flex flex-wrap gap-2">
                <button className="btn-secondary" onClick={onPreviewAI} disabled={aiPreviewLoading}>
                  {aiPreviewLoading ? 'Generating...' : 'Preview AI Insight'}
                </button>
                <button className="btn-primary" onClick={onSaveMarks}>Save Marks</button>
              </div>
              {aiPreview ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/50">
                  <p className="text-sm font-semibold">AI Insight Preview</p>
                  <p className="mt-1 text-xs text-slate-500">Grade: {aiPreview.grade} | Total: {aiPreview.grand_total} | AI Score: {aiPreview.ai_score ?? '-'}</p>
                  <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">{aiPreview.ai_feedback || aiPreview.ai_insight?.summary}</p>
                  {(aiPreview.ai_insight?.strengths || []).length ? (
                    <p className="mt-2 text-xs text-emerald-700 dark:text-emerald-300">Strengths: {(aiPreview.ai_insight?.strengths || []).join(' | ')}</p>
                  ) : null}
                  {(aiPreview.ai_insight?.gaps || []).length ? (
                    <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">Gaps: {(aiPreview.ai_insight?.gaps || []).join(' | ')}</p>
                  ) : null}
                  {(aiPreview.ai_insight?.suggestions || []).length ? (
                    <p className="mt-1 text-xs text-sky-700 dark:text-sky-300">Suggestions: {(aiPreview.ai_insight?.suggestions || []).join(' | ')}</p>
                  ) : null}
                </div>
              ) : null}
            </Card>
          </div>

          <div>
            {chatLoading ? <Card><p className="text-sm text-slate-500">Loading chat history...</p></Card> : null}
            <AIChatPanel
              messages={chatMessages}
              inputValue={chatInput}
              onInputChange={setChatInput}
              onSend={onSendChat}
              onClear={() => setChatMessages([])}
              sending={chatSending}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
