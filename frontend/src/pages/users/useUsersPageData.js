import { useEffect, useState } from 'react';
import { apiClient } from '../../services/apiClient';
import { getSectionPage } from '../../services/sectionsApi';

export function useUsersPageData({ pushToast }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [draftRoles, setDraftRoles] = useState({});
  const [draftScopes, setDraftScopes] = useState({});
  const [savingIds, setSavingIds] = useState([]);
  const [faculties, setFaculties] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [specializations, setSpecializations] = useState([]);
  const [batches, setBatches] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [sections, setSections] = useState([]);
  const [clubs, setClubs] = useState([]);

  async function loadUsers() {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/users/');
      setRows(response.data || []);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to load users';
      setError(String(detail));
      pushToast({ title: 'Load failed', description: String(detail), variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  async function loadLookups() {
    const [facultiesRes, departmentsRes, programsRes, specializationsRes, batchesRes, semestersRes, sectionsRes, clubsRes] =
      await Promise.allSettled([
        apiClient.get('/faculties/', { params: { skip: 0, limit: 100 } }),
        apiClient.get('/departments/', { params: { skip: 0, limit: 100 } }),
        apiClient.get('/programs/', { params: { skip: 0, limit: 100 } }),
        apiClient.get('/specializations/', { params: { skip: 0, limit: 100 } }),
        apiClient.get('/batches/', { params: { skip: 0, limit: 100 } }),
        apiClient.get('/semesters/', { params: { skip: 0, limit: 100 } }),
        getSectionPage({}, 100),
        apiClient.get('/clubs/', { params: { skip: 0, limit: 100 } })
      ]);
    setFaculties(facultiesRes.status === 'fulfilled' ? facultiesRes.value.data || [] : []);
    setDepartments(departmentsRes.status === 'fulfilled' ? departmentsRes.value.data || [] : []);
    setPrograms(programsRes.status === 'fulfilled' ? programsRes.value.data || [] : []);
    setSpecializations(specializationsRes.status === 'fulfilled' ? specializationsRes.value.data || [] : []);
    setBatches(batchesRes.status === 'fulfilled' ? batchesRes.value.data || [] : []);
    setSemesters(semestersRes.status === 'fulfilled' ? semestersRes.value.data || [] : []);
    setSections(sectionsRes.status === 'fulfilled' ? sectionsRes.value || [] : []);
    setClubs(clubsRes.status === 'fulfilled' ? clubsRes.value.data || [] : []);
  }

  useEffect(() => {
    loadUsers();
    loadLookups();
  }, []);

  function getEffectiveExtensions(row) {
    return draftRoles[row.id] ?? row.extended_roles ?? [];
  }

  function getEffectiveScope(row) {
    return draftScopes[row.id] ?? row.role_scope ?? {};
  }

  function setScopeForUser(row, nextScope) {
    setDraftScopes((prev) => ({ ...prev, [row.id]: nextScope }));
  }

  function updateClassCoordinatorScope(row, patch) {
    const current = getEffectiveScope(row);
    const existing = current.class_coordinator || {};
    setScopeForUser(row, {
      ...current,
      class_coordinator: { ...existing, ...patch }
    });
  }

  function updateClubPresidentScope(row, patch) {
    const current = getEffectiveScope(row);
    const existing = current.club_president || {};
    setScopeForUser(row, {
      ...current,
      club_president: { ...existing, ...patch }
    });
  }

  function toggleExtension(row, extension) {
    const current = getEffectiveExtensions(row);
    const next = current.includes(extension) ? current.filter((item) => item !== extension) : [...current, extension];
    setDraftRoles((prev) => ({ ...prev, [row.id]: next }));
  }

  async function savePermissions(row) {
    const nextRoles = getEffectiveExtensions(row);
    const nextScope = getEffectiveScope(row);
    setSavingIds((prev) => (prev.includes(row.id) ? prev : [...prev, row.id]));
    try {
      await apiClient.patch(`/users/${row.id}/extensions`, { extended_roles: nextRoles, role_scope: nextScope });
      setRows((prev) =>
        prev.map((item) =>
          item.id === row.id ? { ...item, extended_roles: nextRoles, role_scope: nextScope } : item
        )
      );
      setDraftRoles((prev) => {
        const copy = { ...prev };
        delete copy[row.id];
        return copy;
      });
      setDraftScopes((prev) => {
        const copy = { ...prev };
        delete copy[row.id];
        return copy;
      });
      pushToast({ title: 'Updated', description: 'Permissions updated successfully.', variant: 'success' });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update permissions';
      pushToast({ title: 'Update failed', description: String(detail), variant: 'error' });
    } finally {
      setSavingIds((prev) => prev.filter((id) => id !== row.id));
    }
  }

  return {
    batches,
    clubs,
    departments,
    error,
    faculties,
    getEffectiveExtensions,
    getEffectiveScope,
    loading,
    loadUsers,
    programs,
    rows,
    savePermissions,
    savingIds,
    sections,
    semesters,
    specializations,
    toggleExtension,
    updateClassCoordinatorScope,
    updateClubPresidentScope
  };
}
