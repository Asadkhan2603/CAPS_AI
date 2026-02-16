import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

const initialForm = {
  full_name: "",
  roll_number: "",
  email: "",
  section_id: "",
};

export default function StudentsPage() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
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
      const response = await apiClient.get("/students/", {
        params: { q: q || undefined, section_id: sectionId || undefined, skip, limit },
      });
      setRows(response.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load students");
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
      await apiClient.post("/students/", {
        ...form,
        email: form.email || null,
        section_id: form.section_id || null,
      });
      setForm(initialForm);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create student");
    }
  }

  return (
    <div className="stack">
      <div className="panel">
        <h1>Students</h1>
        <div className="inline-form">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name/roll/email" />
          <input value={sectionId} onChange={(e) => setSectionId(e.target.value)} placeholder="Section ID" />
          <button onClick={() => { setSkip(0); loadData(); }}>Apply</button>
        </div>
      </div>

      <div className="panel">
        <h3>Add Student</h3>
        <form onSubmit={onCreate} className="grid-form">
          <input name="full_name" value={form.full_name} onChange={onChange} placeholder="Full name" required />
          <input name="roll_number" value={form.roll_number} onChange={onChange} placeholder="Roll number" required />
          <input name="email" value={form.email} onChange={onChange} placeholder="Email (optional)" />
          <input name="section_id" value={form.section_id} onChange={onChange} placeholder="Section ID (optional)" />
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
              <th>Name</th>
              <th>Roll</th>
              <th>Email</th>
              <th>Section</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.id}>
                <td>{item.full_name}</td>
                <td>{item.roll_number}</td>
                <td>{item.email || "-"}</td>
                <td>{item.section_id || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
