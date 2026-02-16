import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";

const baseNavItems = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/students", label: "Students" },
  { to: "/subjects", label: "Subjects" },
  { to: "/assignments", label: "Assignments" },
];

const adminNavItems = [
  { to: "/courses", label: "Courses" },
  { to: "/years", label: "Years" },
  { to: "/classes", label: "Classes" },
  { to: "/sections", label: "Sections" },
  { to: "/section-subjects", label: "Section Subjects" },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navItems = user?.role === "admin" ? [...baseNavItems, ...adminNavItems] : baseNavItems;

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
