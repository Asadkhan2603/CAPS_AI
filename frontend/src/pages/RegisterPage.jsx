import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register, login } = useAuth();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    role: "teacher",
    extended_roles: [],
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function onChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function onExtendedRoleChange(event) {
    const { value, checked } = event.target;
    setForm((prev) => {
      const nextRoles = checked
        ? [...prev.extended_roles, value]
        : prev.extended_roles.filter((item) => item !== value);
      return { ...prev, extended_roles: nextRoles };
    });
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const payload = {
        ...form,
        extended_roles: form.role === "teacher" ? form.extended_roles : [],
      };
      await register(payload);
      await login(form.email, form.password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err?.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-wrap">
      <section className="auth-card">
        <h1>Register</h1>
        <form onSubmit={onSubmit} className="stack">
          <input
            name="full_name"
            placeholder="Full name"
            value={form.full_name}
            onChange={onChange}
            required
          />
          <input
            name="email"
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={onChange}
            required
          />
          <input
            name="password"
            type="password"
            placeholder="Password"
            minLength={8}
            value={form.password}
            onChange={onChange}
            required
          />
          <select name="role" value={form.role} onChange={onChange}>
            <option value="admin">Admin</option>
            <option value="teacher">Teacher</option>
            <option value="student">Student</option>
          </select>
          {form.role === "teacher" ? (
            <div className="stack">
              <label>
                <input
                  type="checkbox"
                  value="year_head"
                  checked={form.extended_roles.includes("year_head")}
                  onChange={onExtendedRoleChange}
                />{" "}
                Year Head
              </label>
              <label>
                <input
                  type="checkbox"
                  value="class_coordinator"
                  checked={form.extended_roles.includes("class_coordinator")}
                  onChange={onExtendedRoleChange}
                />{" "}
                Class Coordinator
              </label>
              <label>
                <input
                  type="checkbox"
                  value="club_coordinator"
                  checked={form.extended_roles.includes("club_coordinator")}
                  onChange={onExtendedRoleChange}
                />{" "}
                Club Coordinator
              </label>
            </div>
          ) : null}
          <button type="submit" disabled={loading}>
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>
        {error ? <p className="error">{error}</p> : null}
        <p>
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </section>
    </main>
  );
}
