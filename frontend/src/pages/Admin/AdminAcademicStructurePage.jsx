import { Link } from 'react-router-dom';
import Card from '../../components/ui/Card';
import AdminDomainNav from '../../components/admin/AdminDomainNav';

const canonicalLinks = [
  { to: '/faculties', label: 'Faculties' },
  { to: '/departments', label: 'Departments' },
  { to: '/programs', label: 'Programs' },
  { to: '/specializations', label: 'Specializations' },
  { to: '/batches', label: 'Batches' },
  { to: '/semesters', label: 'Semesters' },
  { to: '/sections', label: 'Sections' }
];

const legacyLinks = [
  { to: '/courses', label: 'Courses' },
  { to: '/years', label: 'Years' },
  { to: '/branches', label: 'Branches' }
];

export default function AdminAcademicStructurePage() {
  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Academic Structure</h1>
        <p className="text-sm text-slate-500">
          Canonical model: faculty-department-program-specialization-batch-semester-section.
        </p>
      </Card>
      <AdminDomainNav />
      <Card className="space-y-2 border-emerald-200 bg-emerald-50/70">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Canonical Academic Setup</p>
        <p className="text-sm text-slate-600">
          Use these modules for current academic hierarchy management and new data creation.
        </p>
      </Card>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {canonicalLinks.map((item) => (
          <Card key={item.to} className="space-y-2">
            <p className="font-medium">{item.label}</p>
            <Link className="btn-secondary" to={item.to}>Open {item.label}</Link>
          </Card>
        ))}
      </div>
      <Card className="space-y-2 border-amber-200 bg-amber-50/70">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Legacy Compatibility</p>
        <p className="text-sm text-slate-600">
          These modules remain available for backward compatibility and migration support. They are not part of the canonical academic tree.
        </p>
      </Card>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {legacyLinks.map((item) => (
          <Card key={item.to} className="space-y-2 border-amber-200/80">
            <p className="font-medium">{item.label}</p>
            <p className="text-xs uppercase tracking-[0.14em] text-amber-700">Legacy</p>
            <Link className="btn-secondary" to={item.to}>Open {item.label}</Link>
          </Card>
        ))}
      </div>
    </div>
  );
}
