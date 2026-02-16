import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

const initialForm = {
  section_id: "",
  subject_id: "",
  teacher_user_id: "",
};

export default function SectionSubjectsPage() {
  const [rows, setRows] = useState([]);
  const [sectionId, setSectionId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState(initialForm);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const response = await apiClient.get("/section-subjects/", {
        params: {
          section_id: sectionId || undefined,
          subject_id: subjectId || undefined,
          skip,
          limit,
        },
      });
      setRows(response.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load section-subject mappings");
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
      await apiClient.post("/section-subjects/", {
        ...form,
        teacher_user_id: form.teacher_user_id || null,
      });
      setForm(initialForm);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create mapping");
    }
  }

  return (
    <div className="stack">
      <div className="panel">
        <h1>Section Subjects</h1>
        <div className="inline-form">
          <input value={sectionId} onChange={(e) => setSectionId(e.target.value)} placeholder="Section ID" />
          <input value={subjectId} onChange={(e) => setSubjectId(e.target.value)} placeholder="Subject ID" />
          <button onClick={() => { setSkip(0); loadData(); }}>Apply</button>
        </div>
      </div>

      <div className="panel">
        <h3>Create Mapping</h3>
        <form onSubmit={onCreate} className="grid-form">
          <input name="section_id" value={form.section_id} onChange={onChange} placeholder="Section ID" required />
          <input name="subject_id" value={form.subject_id} onChange={onChange} placeholder="Subject ID" required />
          <input name="teacher_user_id" value={form.teacher_user_id} onChange={onChange} placeholder="Teacher User ID (optional)" />
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
              <th>Section ID</th>
              <th>Subject ID</th>
              <th>Teacher User ID</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.id}>
                <td>{item.section_id}</td>
                <td>{item.subject_id}</td>
                <td>{item.teacher_user_id || "-"}</td>
                <td>{String(item.is_active)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
