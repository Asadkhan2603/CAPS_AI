import { useEffect, useMemo, useRef, useState } from 'react';
import { CalendarDays, GraduationCap, Mail, MapPin, Phone, ShieldCheck, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { formatApiError } from '../utils/apiError';
import { useAuthorizedImage } from '../hooks/useAuthorizedImage';

const personalFields = [
  { name: 'full_name', label: 'Full Name' },
  { name: 'phone', label: 'Phone' },
  { name: 'date_of_birth', label: 'Date of Birth' },
  { name: 'gender', label: 'Gender' },
  { name: 'address_line', label: 'Address' },
  { name: 'city', label: 'City' },
  { name: 'state', label: 'State' },
  { name: 'country', label: 'Country' },
  { name: 'postal_code', label: 'Postal Code' }
];

const professionalFields = [
  { name: 'designation', label: 'Designation' },
  { name: 'department', label: 'Department' },
  { name: 'organization', label: 'Organization' },
  { name: 'skills', label: 'Skills' },
  { name: 'linkedin_url', label: 'LinkedIn URL' },
  { name: 'website_url', label: 'Website URL' },
  { name: 'bio', label: 'Bio' }
];

function initialProfileForm(user) {
  const profile = user?.profile || {};
  return {
    full_name: user?.full_name || '',
    phone: profile.phone || '',
    date_of_birth: profile.date_of_birth || '',
    gender: profile.gender || '',
    address_line: profile.address_line || '',
    city: profile.city || '',
    state: profile.state || '',
    country: profile.country || '',
    postal_code: profile.postal_code || '',
    designation: profile.designation || '',
    department: profile.department || '',
    organization: profile.organization || '',
    skills: profile.skills || '',
    linkedin_url: profile.linkedin_url || '',
    website_url: profile.website_url || '',
    bio: profile.bio || ''
  };
}

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const { pushToast } = useToast();
  const [form, setForm] = useState(() => initialProfileForm(user));
  const [saving, setSaving] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [studentSnapshot, setStudentSnapshot] = useState({
    totalSubmissions: 0,
    totalEvaluations: 0,
    pendingReviews: 0,
    urgentNotices: 0
  });
  const fileInputRef = useRef(null);

  const avatarSrc = useAuthorizedImage(user?.avatar_url, user?.avatar_updated_at);

  useEffect(() => {
    setForm(initialProfileForm(user));
  }, [user]);

  useEffect(() => {
    async function loadStudentSnapshot() {
      if (user?.role !== 'student') {
        return;
      }
      try {
        const [summaryRes, noticesRes] = await Promise.all([
          apiClient.get('/analytics/summary'),
          apiClient.get('/notices/', { params: { priority: 'urgent', limit: 20 } })
        ]);
        const summary = summaryRes.data?.summary || {};
        setStudentSnapshot({
          totalSubmissions: summary.total_submissions ?? 0,
          totalEvaluations: summary.total_evaluations ?? 0,
          pendingReviews: summary.pending_reviews ?? 0,
          urgentNotices: Array.isArray(noticesRes.data) ? noticesRes.data.length : 0
        });
      } catch {
        setStudentSnapshot({
          totalSubmissions: 0,
          totalEvaluations: 0,
          pendingReviews: 0,
          urgentNotices: 0
        });
      }
    }

    loadStudentSnapshot();
  }, [user?.role]);

  function onChange(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function onSave(event) {
    if (event?.preventDefault) {
      event.preventDefault();
    }
    setSaving(true);
    try {
      await apiClient.patch('/auth/profile', form);
      await refreshUser();
      pushToast({ title: 'Profile saved', description: 'Your profile details were updated.', variant: 'success' });
    } catch (err) {
      pushToast({ title: 'Save failed', description: formatApiError(err, 'Failed to save profile'), variant: 'error' });
    } finally {
      setSaving(false);
    }
  }

  async function onChangePassword(event) {
    if (event?.preventDefault) {
      event.preventDefault();
    }
    if (!passwordForm.current_password || !passwordForm.new_password || !passwordForm.confirm_password) {
      pushToast({ title: 'Missing fields', description: 'Please fill all password fields.', variant: 'error' });
      return;
    }
    if (passwordForm.new_password.length < 8) {
      pushToast({ title: 'Invalid password', description: 'New password must be at least 8 characters.', variant: 'error' });
      return;
    }
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      pushToast({ title: 'Mismatch', description: 'New password and confirm password do not match.', variant: 'error' });
      return;
    }

    setPasswordSaving(true);
    try {
      await apiClient.post('/auth/change-password', {
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password
      });
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
      pushToast({ title: 'Password updated', description: 'Your password has been changed successfully.', variant: 'success' });
      await refreshUser();
    } catch (err) {
      pushToast({ title: 'Update failed', description: formatApiError(err, 'Failed to change password'), variant: 'error' });
    } finally {
      setPasswordSaving(false);
    }
  }

  async function onUploadAvatar(file) {
    if (!file) {
      return;
    }
    setUploading(true);
    try {
      const multipart = new FormData();
      multipart.append('file', file);
      await apiClient.post('/auth/profile/avatar', multipart, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      await refreshUser();
      pushToast({ title: 'Photo updated', description: 'Profile photo uploaded successfully.', variant: 'success' });
    } catch (err) {
      pushToast({ title: 'Upload failed', description: formatApiError(err, 'Failed to upload profile photo'), variant: 'error' });
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  }

  const enrollmentNumber = useMemo(() => {
    const explicit = user?.profile?.enrollment_number;
    if (explicit) {
      return explicit;
    }
    const email = user?.email || '';
    const username = email.includes('@') ? email.split('@')[0] : '';
    return username || user?.id || '-';
  }, [user]);

  const memberSince = useMemo(() => {
    if (!user?.created_at) return '-';
    const date = new Date(user.created_at);
    if (Number.isNaN(date.getTime())) return '-';
    return date.toLocaleDateString();
  }, [user?.created_at]);

  const studentAcademicItems = [
    { label: 'Enrollment', value: enrollmentNumber },
    { label: 'Department', value: form.department || '-' },
    { label: 'Program / Course', value: form.organization || '-' },
    { label: 'Current Year', value: form.designation || '-' }
  ];

  const isStudent = user?.role === 'student';

  if (isStudent) {
    return (
      <div className="space-y-5 page-fade">
        <Card className="overflow-hidden !p-0">
          <div className="bg-gradient-to-r from-sky-50 via-blue-50 to-indigo-50 p-5 dark:from-slate-900 dark:via-slate-900 dark:to-slate-950">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-center gap-4">
                {avatarSrc ? (
                  <img src={avatarSrc} alt="Profile" className="h-20 w-20 rounded-2xl border border-slate-200 object-cover dark:border-slate-700" />
                ) : (
                  <div className="flex h-20 w-20 items-center justify-center rounded-2xl border border-dashed border-slate-300 text-xs text-slate-500 dark:border-slate-700">
                    No Photo
                  </div>
                )}
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-brand-600">Student Profile</p>
                  <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{user?.full_name || 'Student'}</h1>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                    <span className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-white px-2 py-1 dark:border-slate-700 dark:bg-slate-900">
                      <GraduationCap size={12} /> {enrollmentNumber}
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-white px-2 py-1 dark:border-slate-700 dark:bg-slate-900">
                      <ShieldCheck size={12} /> Active Student
                    </span>
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp"
                  className="hidden"
                  onChange={(e) => onUploadAvatar(e.target.files?.[0])}
                />
                <button className="btn-secondary w-full" type="button" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
                  {uploading ? 'Uploading...' : 'Change Photo'}
                </button>
                <Link className="btn-secondary w-full" to="/submissions">Go To Submissions</Link>
              </div>
            </div>
          </div>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Card className="!rounded-2xl !p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Submissions</p>
            <p className="mt-1 text-3xl font-bold">{studentSnapshot.totalSubmissions}</p>
          </Card>
          <Card className="!rounded-2xl !p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Evaluations</p>
            <p className="mt-1 text-3xl font-bold">{studentSnapshot.totalEvaluations}</p>
          </Card>
          <Card className="!rounded-2xl !p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Pending Reviews</p>
            <p className="mt-1 text-3xl font-bold">{studentSnapshot.pendingReviews}</p>
          </Card>
          <Card className="!rounded-2xl !p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Urgent Notices</p>
            <p className="mt-1 text-3xl font-bold">{studentSnapshot.urgentNotices}</p>
          </Card>
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          <Card className="space-y-3 xl:col-span-2">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Personal Information</h2>
              <span className="inline-flex items-center gap-1 text-xs text-slate-500"><Sparkles size={12} /> Keep details up to date</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <FormInput label="Full Name" value={form.full_name || ''} onChange={(e) => onChange('full_name', e.target.value)} />
              <FormInput label="Phone" value={form.phone || ''} onChange={(e) => onChange('phone', e.target.value)} />
              <FormInput label="Date of Birth" value={form.date_of_birth || ''} onChange={(e) => onChange('date_of_birth', e.target.value)} />
              <FormInput label="Gender" value={form.gender || ''} onChange={(e) => onChange('gender', e.target.value)} />
              <FormInput label="City" value={form.city || ''} onChange={(e) => onChange('city', e.target.value)} />
              <FormInput label="State" value={form.state || ''} onChange={(e) => onChange('state', e.target.value)} />
              <div className="sm:col-span-2">
                <FormInput label="Address" value={form.address_line || ''} onChange={(e) => onChange('address_line', e.target.value)} />
              </div>
              <FormInput label="Country" value={form.country || ''} onChange={(e) => onChange('country', e.target.value)} />
              <FormInput label="Postal Code" value={form.postal_code || ''} onChange={(e) => onChange('postal_code', e.target.value)} />
            </div>
          </Card>

          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Academic Identity</h2>
            <div className="space-y-2">
              {studentAcademicItems.map((item) => (
                <div key={item.label} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">{item.label}</p>
                  <p className="mt-1 text-sm font-semibold">{item.value}</p>
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700">
              <p className="inline-flex items-center gap-1 text-slate-600 dark:text-slate-300"><Mail size={13} /> {user?.email || '-'}</p>
              <p className="mt-1 inline-flex items-center gap-1 text-slate-600 dark:text-slate-300"><CalendarDays size={13} /> Member since {memberSince}</p>
            </div>
          </Card>
        </div>

        <Card className="space-y-3">
          <h2 className="text-lg font-semibold">About and Links</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormInput label="Bio" value={form.bio || ''} onChange={(e) => onChange('bio', e.target.value)} />
            <FormInput label="Skills" value={form.skills || ''} onChange={(e) => onChange('skills', e.target.value)} />
            <FormInput label="LinkedIn URL" value={form.linkedin_url || ''} onChange={(e) => onChange('linkedin_url', e.target.value)} />
            <FormInput label="Website URL" value={form.website_url || ''} onChange={(e) => onChange('website_url', e.target.value)} />
          </div>
          <div className="flex justify-end">
            <button className="btn-primary" type="button" onClick={onSave} disabled={saving}>
              {saving ? 'Saving...' : 'Save Profile'}
            </button>
          </div>
        </Card>

        <Card className="space-y-3">
          <h2 className="text-lg font-semibold">Security</h2>
          <form className="grid gap-3 sm:grid-cols-3" onSubmit={onChangePassword}>
            <FormInput
              type="password"
              label="Current Password"
              value={passwordForm.current_password}
              onChange={(e) => setPasswordForm((prev) => ({ ...prev, current_password: e.target.value }))}
            />
            <FormInput
              type="password"
              label="New Password"
              value={passwordForm.new_password}
              onChange={(e) => setPasswordForm((prev) => ({ ...prev, new_password: e.target.value }))}
            />
            <FormInput
              type="password"
              label="Confirm Password"
              value={passwordForm.confirm_password}
              onChange={(e) => setPasswordForm((prev) => ({ ...prev, confirm_password: e.target.value }))}
            />
            <div className="sm:col-span-3 flex justify-end">
              <button className="btn-secondary" type="submit" disabled={passwordSaving}>
                {passwordSaving ? 'Updating...' : 'Change Password'}
              </button>
            </div>
          </form>
        </Card>

        <Card className="grid gap-3 sm:grid-cols-3">
          <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700">
            <Phone size={14} className="text-slate-500" /> {form.phone || 'Add phone number'}
          </div>
          <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700">
            <Mail size={14} className="text-slate-500" /> {user?.email || '-'}
          </div>
          <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700">
            <MapPin size={14} className="text-slate-500" /> {form.city || form.state || form.country ? `${form.city || ''} ${form.state || ''} ${form.country || ''}`.trim() : 'Add location'}
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4 page-fade">
      <Card className="space-y-4">
        <h1 className="text-2xl font-semibold">Manage Profile</h1>
        <div className="flex flex-wrap items-center gap-4">
          {avatarSrc ? (
            <img src={avatarSrc} alt="Profile" className="h-20 w-20 rounded-full border border-slate-200 object-cover dark:border-slate-700" />
          ) : (
            <div className="flex h-20 w-20 items-center justify-center rounded-full border border-dashed border-slate-300 text-xs text-slate-500 dark:border-slate-700">
              No Photo
            </div>
          )}
          <div className="space-y-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".png,.jpg,.jpeg,.webp"
              className="hidden"
              onChange={(e) => onUploadAvatar(e.target.files?.[0])}
            />
            <button className="btn-secondary" type="button" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
              {uploading ? 'Uploading...' : 'Upload Profile Photo'}
            </button>
            <p className="text-xs text-slate-500">Allowed: png, jpg, jpeg, webp (max 3MB)</p>
          </div>
        </div>
      </Card>

      <form onSubmit={onSave} className="space-y-4">
        <Card className="space-y-3">
          <h2 className="text-lg font-semibold">Personal Details</h2>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {personalFields.map((field) => (
              <FormInput
                key={field.name}
                label={field.label}
                value={form[field.name] || ''}
                onChange={(e) => onChange(field.name, e.target.value)}
              />
            ))}
          </div>
        </Card>

        <Card className="space-y-3">
          <h2 className="text-lg font-semibold">Professional Details</h2>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {professionalFields.map((field) => (
              <FormInput
                key={field.name}
                label={field.label}
                value={form[field.name] || ''}
                onChange={(e) => onChange(field.name, e.target.value)}
              />
            ))}
          </div>
          <div className="flex justify-end">
            <button className="btn-primary" type="submit" disabled={saving}>
              {saving ? 'Saving...' : 'Save Profile'}
            </button>
          </div>
        </Card>

        <Card className="space-y-3">
          <h2 className="text-lg font-semibold">Security</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <FormInput
              type="password"
              label="Current Password"
              value={passwordForm.current_password}
              onChange={(e) => setPasswordForm((prev) => ({ ...prev, current_password: e.target.value }))}
            />
            <FormInput
              type="password"
              label="New Password"
              value={passwordForm.new_password}
              onChange={(e) => setPasswordForm((prev) => ({ ...prev, new_password: e.target.value }))}
            />
            <FormInput
              type="password"
              label="Confirm Password"
              value={passwordForm.confirm_password}
              onChange={(e) => setPasswordForm((prev) => ({ ...prev, confirm_password: e.target.value }))}
            />
          </div>
          <div className="flex justify-end">
            <button className="btn-secondary" type="button" onClick={onChangePassword} disabled={passwordSaving}>
              {passwordSaving ? 'Updating...' : 'Change Password'}
            </button>
          </div>
        </Card>
      </form>
    </div>
  );
}
