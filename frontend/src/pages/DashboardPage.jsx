import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export default function DashboardPage() {
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
    <main className="page">
      <section className="card">
        <h1>CAPS AI Dashboard</h1>
        <p>Project baseline is ready for module-by-module development.</p>
        <p>
          API status: <strong>{apiStatus}</strong>
        </p>
      </section>
    </main>
  );
}
