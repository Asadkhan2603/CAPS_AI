import { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function DashboardPage() {
  const { user } = useAuth();
  const [apiStatus, setApiStatus] = useState("Checking API...");

  useEffect(() => {
    let mounted = true;

    async function checkApi() {
      try {
        const response = await apiClient.get("/analytics/summary");
        if (mounted) {
          setApiStatus(`Connected (${response.status})`);
        }
      } catch {
        if (mounted) {
          setApiStatus("Backend not reachable");
        }
      }
    }

    checkApi();

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="stack">
      <section className="panel">
        <h1>CAPS AI Dashboard</h1>
        <p>Welcome, {user?.full_name || "User"}.</p>
        <p>
          API status: <strong>{apiStatus}</strong>
        </p>
        <div className="inline-form">
          <Link to="/students">Open Students</Link>
          <Link to="/subjects">Open Subjects</Link>
          <Link to="/assignments">Open Assignments</Link>
        </div>
      </section>

      <section className="panel">
        <h3>Account</h3>
        <p>Email: {user?.email || "-"}</p>
        <p>Role: {user?.role || "-"}</p>
      </section>
    </div>
  );
}
