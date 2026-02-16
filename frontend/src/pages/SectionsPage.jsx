import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

const initialForm = {
  name: "",
  program: "",
  academic_year: "",
  semester: 1,
};

export default function SectionsPage() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [academicYear, setAcademicYear] = useState("");
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState(initialForm);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const response = await apiClient.get("/sections/", {
        params: {
          q: q || undefined,
          academic_year: academicYear || undefined,
          skip,
          limit,
        },
      });
      setRows(response.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load sections");
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
      await apiClient.post("/sections/", {
        ...form,
        semester: Number(form.semester),
      });
      setForm(initialForm);
      await loadData();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create section");
    }
  }

  return (
    <div className="stack">
      <div className="panel">
        <h1>Sections</h1>
        <div className="inline-form">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name/program" />
          <input value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} placeholder="Academic year" />
          <button onClick={() => { setSkip(0); loadData(); }}>Apply</button>
        </div>
      </div>

      <div className="panel">
        <h3>Create Section</h3>
        <form onSubmit={onCreate} className="grid-form">
          <input name="name" value={form.name} onChange={onChange} placeholder="Section name" required />
          <input name="program" value={form.program} onChange={onChange} placeholder="Program" required />
          <input name="academic_year" value={form.academic_year} onChange={onChange} placeholder="Academic year (e.g. 2026-27)" required />
          <input name="semester" type="number" min="1" max="12" value={form.semester} onChange={onChange} required />
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
              <th>Program</th>
              <th>Academic Year</th>
              <th>Semester</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.id}>
                <td>{item.name}</td>
                <td>{item.program}</td>
                <td>{item.academic_year}</td>
                <td>{item.semester}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
