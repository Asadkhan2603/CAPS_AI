import { Link } from 'react-router-dom';
import Card from '../../components/ui/Card';
import AdminDomainNav from '../../components/admin/AdminDomainNav';

export default function AdminGovernancePage() {
  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Governance</h1>
        <p className="text-sm text-slate-500">Identity, roles, extension scopes, and governance controls.</p>
      </Card>
      <AdminDomainNav />
      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">User Governance</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">Manage users and extension roles with scoped validation.</p>
        <Link className="btn-primary" to="/users">Open Users Management</Link>
      </Card>
    </div>
  );
}
