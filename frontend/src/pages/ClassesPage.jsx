import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';

const initialForm = {
  course_id: '',
  year_id: '',
  name: '',
  section: '',
  class_coordinator_user_id: '',
};

export default function ClassesPage() {
  const [rows, setRows] = useState([]);
  const [courseId, setCourseId] = useState('');
  const [yearId, setYearId] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState(initialForm);

  async function loadData() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/classes/', {
        params: { course_id: courseId || undefined, year_id: yearId || undefined, skip, limit },
      });
      setRows(response.data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load classes');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [skip, limit]);

  function onChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function onCreate(event) {
    event.preventDefault();
    setError('');
    try {
      await apiClient.post('/classes/', {
        ...form,
        section: form.section || null,
        class_coordinator_user_id: form.class_coordinator_user_id || null,
      });
      setForm(initialForm);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to create class');
    }
  }

  return (
    <div className="stack">
      <div className="panel">
        <h1>Classes</h1>
        <div className="inline-form">
          <input value={courseId} onChange={(e) => setCourseId(e.target.value)} placeholder="Filter by course ID" />
          <input value={yearId} onChange={(e) => setYearId(e.target.value)} placeholder="Filter by year ID" />
          <button onClick={() => { setSkip(0); loadData(); }}>Apply</button>
        </div>
      </div>

      <div className="panel">
        <h3>Create Class</h3>
        <form onSubmit={onCreate} className="grid-form">
          <input name="course_id" value={form.course_id} onChange={onChange} placeholder="Course ID" required />
          <input name="year_id" value={form.year_id} onChange={onChange} placeholder="Year ID" required />
          <input name="name" value={form.name} onChange={onChange} placeholder="Class name" required />
          <input name="section" value={form.section} onChange={onChange} placeholder="Section (optional)" />
          <input name="class_coordinator_user_id" value={form.class_coordinator_user_id} onChange={onChange} placeholder="Class coordinator user ID (optional)" />
          <button type="submit">Create</button>
        </form>
      </div>

      <div className="panel">
        <div className="toolbar">
          <h3>List</h3>
          <div className="inline-form">
            <button disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - limit))}>Prev</button>
            <span>skip: {skip}</span>
            <button onClick={() => setSkip(skip + limit)}>Next</button>
            <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
            </select>
          </div>
        </div>
        {loading ? <p>Loading...</p> : null}
        {error ? <p className="error">{error}</p> : null}
        <table className="data-table">
          <thead>
            <tr><th>Name</th><th>Course ID</th><th>Year ID</th><th>Section</th><th>Coordinator</th></tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.id}>
                <td>{item.name}</td>
                <td>{item.course_id}</td>
                <td>{item.year_id}</td>
                <td>{item.section || '-'}</td>
                <td>{item.class_coordinator_user_id || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
