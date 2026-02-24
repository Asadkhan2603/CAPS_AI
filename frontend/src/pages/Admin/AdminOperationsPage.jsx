import { Link } from 'react-router-dom';
import Card from '../../components/ui/Card';
import AdminDomainNav from '../../components/admin/AdminDomainNav';

const links = [
  { to: '/students', label: 'Students' },
  { to: '/subjects', label: 'Subjects' },
  { to: '/assignments', label: 'Assignments' },
  { to: '/submissions', label: 'Submissions' },
  { to: '/evaluations', label: 'Evaluations' },
  { to: '/review-tickets', label: 'Review Tickets' },
  { to: '/enrollments', label: 'Enrollments' }
];

export default function AdminOperationsPage() {
  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Operations</h1>
        <p className="text-sm text-slate-500">Academic operations and execution workflows.</p>
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
