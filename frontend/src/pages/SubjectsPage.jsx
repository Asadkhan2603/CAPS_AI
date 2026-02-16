import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

const initialForm = {
  name: "",
  code: "",
  description: "",
};

export default function SubjectsPage() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState(initialForm);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const response = await apiClient.get("/subjects/", {
        params: { q: q || undefined, skip, limit },
      });
      setRows(response.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load subjects");
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
      await apiClient.post("/subjects/", { ...form, description: form.description || null });
      setForm(initialForm);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create subject");
    }
  }

  return (
    <div className="stack">
      <div className="panel">
        <h1>Subjects</h1>
        <div className="inline-form">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name/code" />
          <button onClick={() => { setSkip(0); loadData(); }}>Apply</button>
        </div>
      </div>

      <div className="panel">
        <h3>Add Subject</h3>
        <form onSubmit={onCreate} className="grid-form">
          <input name="name" value={form.name} onChange={onChange} placeholder="Name" required />
          <input name="code" value={form.code} onChange={onChange} placeholder="Code" required />
          <input name="description" value={form.description} onChange={onChange} placeholder="Description (optional)" />
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
              <th>Code</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.id}>
                <td>{item.name}</td>
                <td>{item.code}</td>
                <td>{item.description || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
