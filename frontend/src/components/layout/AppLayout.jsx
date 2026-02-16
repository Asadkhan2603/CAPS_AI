import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/students", label: "Students" },
  { to: "/subjects", label: "Subjects" },
  { to: "/assignments", label: "Assignments" },
];

export default function AppLayout({ children }) {
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <h2>CAPS AI</h2>
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
      <section className="content-area">{children}</section>
    </main>
  );
}
