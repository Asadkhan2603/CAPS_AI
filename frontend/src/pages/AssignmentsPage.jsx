import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

const initialForm = {
  title: "",
  description: "",
  subject_id: "",
  section_id: "",
  total_marks: 100,
};

export default function AssignmentsPage() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState(initialForm);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const response = await apiClient.get("/assignments/", {
        params: {
          q: q || undefined,
          subject_id: subjectId || undefined,
          section_id: sectionId || undefined,
          skip,
          limit,
        },
      });
      setRows(response.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load assignments");
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
    setError("");
    try {
      await apiClient.post("/assignments/", {
        ...form,
        description: form.description || null,
        subject_id: form.subject_id || null,
        section_id: form.section_id || null,
        total_marks: Number(form.total_marks),
      });
      setForm(initialForm);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create assignment");
    }
  }

  return (
    <div className="stack">
      <div className="panel">
        <h1>Assignments</h1>
        <div className="inline-form">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by title" />
          <input value={subjectId} onChange={(e) => setSubjectId(e.target.value)} placeholder="Subject ID" />
          <input value={sectionId} onChange={(e) => setSectionId(e.target.value)} placeholder="Section ID" />
          <button onClick={() => { setSkip(0); loadData(); }}>Apply</button>
        </div>
      </div>

      <div className="panel">
        <h3>Add Assignment</h3>
        <form onSubmit={onCreate} className="grid-form">
          <input name="title" value={form.title} onChange={onChange} placeholder="Title" required />
          <input name="description" value={form.description} onChange={onChange} placeholder="Description (optional)" />
          <input name="subject_id" value={form.subject_id} onChange={onChange} placeholder="Subject ID (optional)" />
          <input name="section_id" value={form.section_id} onChange={onChange} placeholder="Section ID (optional)" />
          <input name="total_marks" type="number" min="1" max="1000" value={form.total_marks} onChange={onChange} />
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
            <tr>
              <th>Title</th>
              <th>Subject</th>
              <th>Section</th>
              <th>Marks</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.id}>
                <td>{item.title}</td>
                <td>{item.subject_id || "-"}</td>
                <td>{item.section_id || "-"}</td>
                <td>{item.total_marks}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
