import Badge from './Badge';
import Card from './Card';

function statusTone(status) {
  if (status === 'risk') return 'danger';
  if (status === 'attention') return 'warning';
  return 'success';
}

export default function TeacherClassTiles({ items = [] }) {
  if (!items.length) {
    return (
      <Card>
        <h2 className="text-lg font-semibold">My Sections</h2>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">No section analytics found for this teacher.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">My Sections</h2>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {items.map((tile) => (
          <Card key={tile.class_id} className="border-l-4 border-l-brand-500 transition hover:-translate-y-0.5">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-base font-semibold">{tile.class_name}</p>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Semester: {tile.semester_id || '-'}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">Subjects: {(tile.subjects || []).join(', ') || '-'}</p>
              </div>
              <Badge variant={statusTone(tile.health_status)}>
                {tile.health_status}
              </Badge>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
              <p>Students: <span className="font-semibold">{tile.total_students}</span></p>
              <p>Active Asg: <span className="font-semibold">{tile.active_assignments}</span></p>
              <p>Late: <span className="font-semibold">{tile.late_submissions_count}</span></p>
              <p>Similarity: <span className="font-semibold">{tile.similarity_alert_count}</span></p>
              <p className="col-span-2">Risk Students: <span className="font-semibold">{tile.risk_student_count}</span></p>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
