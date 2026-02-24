import { Link } from 'react-router-dom';
import Card from '../../components/ui/Card';
import AdminDomainNav from '../../components/admin/AdminDomainNav';

export default function AdminDeveloperPage() {
  return (
    <div className="space-y-4 page-fade">
      <Card>
        <h1 className="text-2xl font-semibold">Developer Domain</h1>
        <p className="text-sm text-slate-500">Technical admin controls and platform diagnostics.</p>
      </Card>
      <AdminDomainNav />
      <Card className="space-y-2">
        <p className="text-sm text-slate-600 dark:text-slate-300">Use developer panel for debugging and controlled system operations.</p>
        <Link className="btn-primary" to="/developer-panel">Open Developer Panel</Link>
      </Card>
    </div>
  );
}
