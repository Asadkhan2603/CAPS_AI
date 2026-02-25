import { Link } from 'react-router-dom';
import Card from '../../components/ui/Card';
import AdminDomainNav from '../../components/admin/AdminDomainNav';

const links = [
  { to: '/faculties', label: 'Faculties' },
  { to: '/departments', label: 'Departments' },
  { to: '/programs', label: 'Programs' },
  { to: '/specializations', label: 'Specializations' },
  { to: '/batches', label: 'Batches' },
  { to: '/semesters', label: 'Semesters' },
  { to: '/sections', label: 'Sections' }
];

export default function AdminAcademicStructurePage() {
  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Academic Structure</h1>
        <p className="text-sm text-slate-500">Build and manage faculty-department-program-specialization-batch-semester-section hierarchy.</p>
      </Card>
      <AdminDomainNav />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {links.map((item) => (
          <Card key={item.to} className="space-y-2">
            <p className="font-medium">{item.label}</p>
            <Link className="btn-secondary" to={item.to}>Open {item.label}</Link>
          </Card>
        ))}
      </div>
    </div>
  );
}
