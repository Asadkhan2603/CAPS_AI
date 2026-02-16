import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";

const navItems = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/students", label: "Students" },
  { to: "/subjects", label: "Subjects" },
  { to: "/assignments", label: "Assignments" },
];

export default function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <h2>CAPS AI</h2>
        <p className="sidebar-user">
          {user?.full_name || "User"} ({user?.role || "guest"})
        </p>
        <button className="secondary-button" onClick={logout}>
          Logout
        </button>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                isActive ? "nav-link nav-link-active" : "nav-link"
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <section className="content-area">
        <Outlet />
      </section>
    </main>
  );
}
