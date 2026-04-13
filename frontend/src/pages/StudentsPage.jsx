import { useEffect, useMemo, useState } from 'react';
import Card from '../components/ui/Card';
import EntityManager from '../components/ui/EntityManager';
import { apiClient } from '../services/apiClient';
import { getSections } from '../services/sectionsApi';

export default function StudentsPage() {
  const [sections, setSections] = useState([]);
  const [groups, setGroups] = useState([]);
  const [duplicateAudit, setDuplicateAudit] = useState(null);

  useEffect(() => {
    async function loadSections() {
      try {
        const [sectionsRes, groupsRes, duplicateAuditRes] = await Promise.allSettled([
          getSections({ skip: 0, limit: 100 }),
          apiClient.get('/groups/', { params: { skip: 0, limit: 100, is_active: true } }),
          apiClient.get('/students/duplicate-audit')
        ]);
        setSections(sectionsRes.status === 'fulfilled' ? sectionsRes.value.data || [] : []);
        setGroups(groupsRes.status === 'fulfilled' ? groupsRes.value.data || [] : []);
        setDuplicateAudit(duplicateAuditRes.status === 'fulfilled' ? duplicateAuditRes.value.data || null : null);
      } catch {
        setSections([]);
        setGroups([]);
        setDuplicateAudit(null);
      }
    }
    loadSections();
  }, []);

  const sectionOptions = useMemo(
    () =>
      sections.map((item) => ({
        value: item.id,
        label: item.name
      })),
    [sections]
  );

  const sectionNameById = useMemo(
    () => Object.fromEntries(sectionOptions.map((item) => [item.value, item.label])),
    [sectionOptions]
  );
  const groupOptions = useMemo(
    () =>
      groups.map((item) => ({
        value: item.id,
        label: item.name,
        section_id: item.section_id
      })),
    [groups]
  );
  const groupNameById = useMemo(
    () => Object.fromEntries(groups.map((item) => [item.id, item.name])),
    [groups]
  );

  const filters = useMemo(
    () => [
      { name: 'q', label: 'Search', placeholder: 'Name / roll / email' },
      { name: 'class_id', label: 'Section', type: 'select', options: sectionOptions, placeholder: 'All Sections' },
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: null }
    ],
    [sectionOptions]
  );

  const createFields = useMemo(
    () => [
      { name: 'full_name', label: 'Full Name', required: true },
      { name: 'roll_number', label: 'Roll Number', required: true },
      { name: 'email', label: 'Email', nullable: true },
      { name: 'class_id', label: 'Section', type: 'select', options: sectionOptions, nullable: true, placeholder: 'No Section' },
      {
        name: 'group_id',
        label: 'Group',
        type: 'select',
        options: groupOptions,
        nullable: true,
        placeholder: 'No Group',
        dependsOn: 'class_id',
        optionMatchKey: 'section_id',
        requireParentSelection: true
      }
    ],
    [groupOptions, sectionOptions]
  );

  const editFields = useMemo(
    () => [
      ...createFields,
      { name: 'is_active', label: 'Active', type: 'switch', defaultValue: true }
    ],
    [createFields]
  );

  const columns = useMemo(
    () => [
      { key: 'full_name', label: 'Name' },
      { key: 'roll_number', label: 'Roll Number' },
      { key: 'email', label: 'Email' },
      {
        key: 'class_id',
        label: 'Section',
        render: (row) => {
          const canonical = row.canonical_class_id || row.class_id;
          const label = sectionNameById[canonical] || canonical || '-';
          return row.placement_source === 'enrollment' && row.class_id && row.class_id !== row.canonical_class_id ? `${label} (Enrollment)` : label;
        }
      },
      { key: 'group_id', label: 'Group', render: (row) => groupNameById[row.group_id] || row.group_id || '-' },
      { key: 'is_active', label: 'Active', render: (row) => (row.is_active ? 'Yes' : 'No') }
    ],
    [groupNameById, sectionNameById]
  );

  return (
    <div className="space-y-3">
      {duplicateAudit ? (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            {[
              ['Total Students', duplicateAudit.summary?.total_students || 0],
              ['Duplicate Groups', duplicateAudit.summary?.duplicate_groups || 0],
              ['Roll Duplicates', duplicateAudit.summary?.roll_number_groups || 0],
              ['Email Duplicates', duplicateAudit.summary?.email_groups || 0],
              ['User Link Duplicates', duplicateAudit.summary?.user_id_groups || 0],
            ].map(([label, value]) => (
              <Card key={label} className="!p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-1 text-2xl font-semibold">{value}</p>
              </Card>
            ))}
          </div>
          <Card className="space-y-3">
            <div>
              <h2 className="text-lg font-semibold">Duplicate Audit</h2>
              <p className="text-sm text-slate-500">
                These groups share the same roll number, email, or linked student user. Review them before they fragment attendance, results, or timetable trust.
              </p>
            </div>
            {duplicateAudit.groups?.length ? (
              <div className="grid gap-3 xl:grid-cols-2">
                {duplicateAudit.groups.slice(0, 8).map((group) => (
                  <div key={`${group.match_type}-${group.match_value}`} className="rounded-2xl border border-slate-200 px-4 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-medium text-slate-900">{group.match_type.replace('_', ' ')}</h3>
                        <p className="text-sm text-slate-500">{group.match_value}</p>
                      </div>
                      <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
                        {group.count} records
                      </span>
                    </div>
                    <div className="mt-3 space-y-2">
                      {(group.students || []).map((student) => (
                        <div key={student.id} className="rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2 text-sm">
                          <p className="font-medium text-slate-900">{student.full_name}</p>
                          <p className="text-xs text-slate-500">
                            Roll {student.roll_number || '-'} • Email {student.email || '-'}
                          </p>
                          <p className="text-xs text-slate-500">
                            User {student.user_id || '-'} • Section {sectionNameById[student.class_id] || student.class_id || 'None'}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
                No duplicate student groups are currently detected in the audit window.
              </div>
            )}
          </Card>
        </div>
      ) : null}
      <EntityManager
        title="Students"
        endpoint="/students/"
        filters={filters}
        createFields={createFields}
        editFields={editFields}
        columns={columns}
        enableEdit
        enableDelete
        createTransform={(payload) => ({
          ...payload,
          email: payload.email || null,
          class_id: payload.class_id || null,
          group_id: payload.group_id || null
        })}
        updateTransform={(payload) => ({
          ...payload,
          email: payload.email || null,
          class_id: payload.class_id || null,
          group_id: payload.group_id || null
        })}
      />
    </div>
  );
}
