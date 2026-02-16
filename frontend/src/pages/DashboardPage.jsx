import { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import { Link } from "react-router-dom";

export default function DashboardPage() {
  const [apiStatus, setApiStatus] = useState("Checking API...");
  const [token, setToken] = useState(localStorage.getItem("caps_ai_token") || "");
  const [tokenSaved, setTokenSaved] = useState("");

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

  function saveToken(event) {
    event.preventDefault();
    const value = token.trim();
    if (value) {
      localStorage.setItem("caps_ai_token", value);
      setTokenSaved("Token saved");
    } else {
      localStorage.removeItem("caps_ai_token");
      setTokenSaved("Token cleared");
    }
  }

  return (
    <div className="stack">
      <section className="panel">
        <h1>CAPS AI Dashboard</h1>
        <p>Frontend CRUD pages are connected to protected backend endpoints.</p>
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
        <h3>Auth Token</h3>
        <p>Paste JWT from `/api/v1/auth/login` response.</p>
        <form onSubmit={saveToken} className="grid-form">
          <input
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder="Bearer token value"
          />
          <button type="submit">Save Token</button>
        </form>
        {tokenSaved ? <p>{tokenSaved}</p> : null}
      </section>
    </div>
  );
}
