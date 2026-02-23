import React, { useEffect, useMemo, useState } from 'react';
import { Camera, Mail, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Card } from '../components/ui';
import { apiClient } from '../services/apiClient';

interface ProfileForm {
  full_name: string;
  phone?: string;
  bio?: string;
}

export const ProfilePage: React.FC = () => {
  const { user, login } = useAuth();
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [form, setForm] = useState<ProfileForm>({ full_name: '' });

  useEffect(() => {
    setForm({
      full_name: user?.full_name || '',
      phone: '',
      bio: ''
    });
  }, [user?.id]);

  const avatarSrc = useMemo(() => {
    if (!user?.avatar_url) return '';
    const base = (apiClient.defaults.baseURL || '').replace(/\/api\/v1\/?$/, '');
    const suffix = user.avatar_updated_at ? `?v=${encodeURIComponent(user.avatar_updated_at)}` : '';
    return `${base}${user.avatar_url}${suffix}`;
  }, [user?.avatar_url, user?.avatar_updated_at]);

  async function refreshMe() {
    const me = await apiClient.get('/auth/me');
    const token = localStorage.getItem('caps_ai_token') || '';
    if (token && me.data) {
      login(token, me.data);
    }
  }

  async function onSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await apiClient.patch('/auth/profile', {
        full_name: form.full_name,
        phone: form.phone,
        bio: form.bio
      });
      await refreshMe();
      setSuccess('Profile updated successfully.');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  }

  async function onUploadAvatar(file?: File | null) {
    if (!file) return;
    setUploading(true);
    setError('');
    setSuccess('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      await apiClient.post('/auth/profile/avatar', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      await refreshMe();
      setSuccess('Avatar updated successfully.');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to upload avatar');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Account Settings</h1>
        <p className="text-slate-500">Manage your profile information.</p>
      </header>

      <Card title="Profile">
        <div className="flex items-center gap-6 mb-6">
          <div className="relative">
            <div className="w-20 h-20 rounded-2xl bg-brand-100 flex items-center justify-center text-brand-700 text-2xl font-bold border-4 border-white shadow-soft overflow-hidden">
              {avatarSrc ? <img src={avatarSrc} alt={user?.full_name} className="w-full h-full object-cover" /> : (user?.full_name?.charAt(0) || 'U')}
            </div>
            <label className="absolute -bottom-2 -right-2 p-2 bg-white rounded-lg shadow border border-slate-100 text-slate-600 hover:text-brand-600 cursor-pointer">
              <Camera size={14} />
              <input type="file" accept=".png,.jpg,.jpeg,.webp" className="hidden" onChange={(e) => onUploadAvatar(e.target.files?.[0])} disabled={uploading} />
            </label>
          </div>
          <div>
            <p className="font-semibold text-slate-900">{user?.full_name}</p>
            <p className="text-sm text-slate-500 capitalize">{user?.role}</p>
            <p className="text-sm text-slate-500">{user?.email}</p>
          </div>
        </div>

        {error ? <div className="mb-4 p-3 bg-red-50 border border-red-100 text-red-600 text-sm rounded-lg">{error}</div> : null}
        {success ? <div className="mb-4 p-3 bg-emerald-50 border border-emerald-100 text-emerald-700 text-sm rounded-lg">{success}</div> : null}

        <form onSubmit={onSaveProfile} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Full Name</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input
                type="text"
                className="input pl-10"
                value={form.full_name}
                onChange={(e) => setForm((p) => ({ ...p, full_name: e.target.value }))}
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input type="email" className="input pl-10" value={user?.email || ''} disabled />
            </div>
          </div>

          <div className="flex justify-end">
            <button type="submit" className="btn-primary" disabled={saving || uploading}>
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </Card>
    </div>
  );
};
