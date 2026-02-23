import { useEffect, useMemo, useRef, useState } from 'react';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import { apiClient } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { formatApiError } from '../utils/apiError';

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
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const backendBaseUrl = useMemo(() => {
    const base = apiClient.defaults.baseURL || '';
    return base.replace(/\/api\/v1\/?$/, '');
  }, []);

  const avatarSrc = user?.avatar_url ? `${backendBaseUrl}${user.avatar_url}${user.avatar_updated_at ? `?v=${encodeURIComponent(user.avatar_updated_at)}` : ''}` : '';

  useEffect(() => {
    setForm(initialProfileForm(user));
  }, [user]);

  function onChange(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function onSave(event) {
    event.preventDefault();
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
      </form>
    </div>
  );
}
