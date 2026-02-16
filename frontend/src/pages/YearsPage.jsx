import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';

const initialForm = { course_id: '', year_number: 1, label: '' };

export default function YearsPage() {
  const [rows, setRows] = useState([]);
  const [courseId, setCourseId] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState(initialForm);

  async function loadData() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/years/', { params: { course_id: courseId || undefined, skip, limit } });
      setRows(response.data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load years');
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
      await apiClient.post('/years/', { ...form, year_number: Number(form.year_number) });
      setForm(initialForm);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to create year');
    }
  }

  return (
    <div className="stack">
      <div className="panel">
        <h1>Years</h1>
        <div className="inline-form">
          <input value={courseId} onChange={(e) => setCourseId(e.target.value)} placeholder="Filter by course ID" />
          <button onClick={() => { setSkip(0); loadData(); }}>Apply</button>
        </div>
      </div>

      <div className="panel">
        <h3>Create Year</h3>
        <form onSubmit={onCreate} className="grid-form">
          <input name="course_id" value={form.course_id} onChange={onChange} placeholder="Course ID" required />
          <input name="year_number" type="number" min="1" max="10" value={form.year_number} onChange={onChange} required />
          <input name="label" value={form.label} onChange={onChange} placeholder="Label (e.g. First Year)" required />
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
            <tr><th>Course ID</th><th>Year Number</th><th>Label</th></tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.id}><td>{item.course_id}</td><td>{item.year_number}</td><td>{item.label}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
