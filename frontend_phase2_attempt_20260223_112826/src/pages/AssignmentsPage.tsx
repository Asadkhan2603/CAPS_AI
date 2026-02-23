import React, { useEffect, useMemo, useState } from 'react';
import { FileText, Clock, CheckCircle2, Search } from 'lucide-react';
import { Card, Table, Badge } from '../components/ui';
import { apiClient } from '../services/apiClient';

interface Assignment {
  id: string;
  title: string;
  subject_id?: string;
  due_date?: string;
  status?: string;
}

interface SubjectMap {
  [key: string]: string;
}

export const AssignmentsPage: React.FC = () => {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [subjects, setSubjects] = useState<SubjectMap>({});
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [assignmentsRes, subjectsRes] = await Promise.all([
          apiClient.get('/assignments/', { params: { skip: 0, limit: 200 } }),
          apiClient.get('/subjects/', { params: { skip: 0, limit: 200 } })
        ]);
        setAssignments(assignmentsRes.data || []);
        const map: SubjectMap = {};
        (subjectsRes.data || []).forEach((s: any) => {
          map[s.id] = s.name;
        });
        setSubjects(map);
      } catch {
        setAssignments([]);
        setSubjects({});
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered = useMemo(() => assignments.filter((a) => a.title?.toLowerCase().includes(query.toLowerCase())), [assignments, query]);

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Assignments</h1>
        <p className="text-slate-500">Read-only assignment listing from backend.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-brand-50 flex items-center justify-center text-brand-600"><FileText size={24} /></div>
          <div><p className="text-sm text-slate-500">Total</p><h3 className="text-2xl font-bold text-slate-900">{assignments.length}</h3></div>
        </Card>
        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 flex items-center justify-center text-emerald-600"><CheckCircle2 size={24} /></div>
          <div><p className="text-sm text-slate-500">Open</p><h3 className="text-2xl font-bold text-slate-900">{assignments.filter((a) => (a.status || 'open') === 'open').length}</h3></div>
        </Card>
        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-amber-50 flex items-center justify-center text-amber-600"><Clock size={24} /></div>
          <div><p className="text-sm text-slate-500">Closed</p><h3 className="text-2xl font-bold text-slate-900">{assignments.filter((a) => a.status === 'closed').length}</h3></div>
        </Card>
      </div>

      <Card>
        <div className="mb-6 relative max-w-sm w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search assignments..." className="input pl-10 text-sm" />
        </div>

        {loading ? (
          <div className="py-16 text-center text-slate-500">Loading...</div>
        ) : (
          <Table headers={['Assignment', 'Subject', 'Due Date', 'Status']}>
            {filtered.map((assignment) => (
              <tr key={assignment.id} className="hover:bg-slate-50">
                <td className="px-4 py-4">
                  <p className="font-semibold text-slate-900">{assignment.title}</p>
                  <p className="text-xs text-slate-500 mt-0.5">ID: {assignment.id}</p>
                </td>
                <td className="px-4 py-4 text-slate-600">{subjects[assignment.subject_id || ''] || '-'}</td>
                <td className="px-4 py-4 text-slate-600">{assignment.due_date ? new Date(assignment.due_date).toLocaleDateString() : '-'}</td>
                <td className="px-4 py-4">
                  <Badge variant={(assignment.status || 'open') === 'closed' ? 'error' : 'success'}>{assignment.status || 'open'}</Badge>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
};
