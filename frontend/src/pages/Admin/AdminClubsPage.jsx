import { Link } from 'react-router-dom';
import Card from '../../components/ui/Card';
import AdminDomainNav from '../../components/admin/AdminDomainNav';

export default function AdminClubsPage() {
  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Clubs Governance</h1>
        <p className="text-sm text-slate-500">Manage club lifecycle, membership, events, and participation governance.</p>
      </Card>
      <AdminDomainNav />
      <Card className="space-y-2">
        <p className="text-sm text-slate-600 dark:text-slate-300">Open Clubs Hub to manage coordinator assignment, status transitions, membership applications, and analytics.</p>
        <Link className="btn-primary" to="/clubs">Open Clubs Hub</Link>
      </Card>
    </div>
  );
}
