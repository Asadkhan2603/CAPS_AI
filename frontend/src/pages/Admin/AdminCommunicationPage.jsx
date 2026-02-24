import { useState } from 'react';
import { Link } from 'react-router-dom';
import Card from '../../components/ui/Card';
import FormInput from '../../components/ui/FormInput';
import AdminDomainNav from '../../components/admin/AdminDomainNav';
import { apiClient } from '../../services/apiClient';
import { formatApiError } from '../../utils/apiError';

export default function AdminCommunicationPage() {
  const [scope, setScope] = useState('college');
  const [scopeRefId, setScopeRefId] = useState('');
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function runPreview() {
    setLoading(true);
    setError('');
    try {
      const payload = { scope, scope_ref_id: scope === 'college' ? null : scopeRefId || null };
      const response = await apiClient.post('/admin/communication/preview-target', payload);
      setPreview(response.data || null);
    } catch (err) {
      setPreview(null);
      setError(formatApiError(err, 'Failed to preview target audience'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Communication</h1>
        <p className="text-sm text-slate-500">Announcements, notices, and communication stream governance.</p>
      </Card>
      <AdminDomainNav />
      <div className="grid gap-3 md:grid-cols-2">
        <Card className="space-y-2">
          <p className="font-medium">Announcements</p>
          <Link className="btn-secondary" to="/communication/announcements">Open Announcements</Link>
        </Card>
        <Card className="space-y-2">
          <p className="font-medium">Feed</p>
          <Link className="btn-secondary" to="/communication/feed">Open Feed</Link>
        </Card>
      </div>
      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">Audience Preview</h2>
        <div className="grid gap-3 md:grid-cols-3">
          <FormInput as="select" label="Scope" value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="college">College</option>
            <option value="year">Year</option>
            <option value="class">Class</option>
            <option value="subject">Subject</option>
          </FormInput>
          <FormInput
            label="Scope Ref ID"
            value={scopeRefId}
            onChange={(e) => setScopeRefId(e.target.value)}
            placeholder="ObjectId for year/class/subject"
            disabled={scope === 'college'}
          />
          <div className="flex items-end">
            <button className="btn-primary" onClick={runPreview} disabled={loading}>
              {loading ? 'Previewing...' : 'Preview Audience'}
            </button>
          </div>
        </div>
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        {preview ? (
          <div className="rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700">
            <p>Scope: <strong>{preview.scope}</strong></p>
            <p>Matched users: <strong>{preview.matched_users}</strong></p>
            <p>Estimated reach: <strong>{preview.estimated_reach}</strong></p>
          </div>
        ) : null}
      </Card>
    </div>
  );
}
