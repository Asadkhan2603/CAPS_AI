import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, CirclePlus, Funnel, Settings } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, Tooltip, XAxis, YAxis } from 'recharts';
import CommunicationTabs from '../components/communication/CommunicationTabs';
import CommunicationDeliveryModal from '../components/communication/CommunicationDeliveryModal';
import { useSearchParams } from 'react-router-dom';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import SafeResponsiveContainer from '../components/charts/SafeResponsiveContainer';
import FormInput from '../components/ui/FormInput';
import { apiClient } from '../services/apiClient';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../hooks/useAuth';
import { formatApiError } from '../utils/apiError';

const PRIORITY_OPTIONS = [
  { value: 'normal', label: 'Normal' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'info', label: 'Info' }
];

const SCOPE_OPTIONS = [
  { value: 'global', label: 'Global' },
  { value: 'notice', label: 'Notice' },
  { value: 'similarity', label: 'Similarity' },
  { value: 'ai', label: 'AI' },
  { value: 'system', label: 'System' }
];

const NOTIFICATION_SCOPE_FIELDS = [
  { key: 'global_scope', label: 'Global', description: 'Default rule for notifications without a more specific override.' },
  { key: 'notice', label: 'Notice', description: 'Announcement-linked alerts and notice fanout updates.' },
  { key: 'similarity', label: 'Similarity', description: 'Similarity detections and review pipeline events.' },
  { key: 'ai', label: 'AI', description: 'AI evaluation, queue, and assistive workflow events.' },
  { key: 'system', label: 'System', description: 'Operational, policy, and account-level alerts.' }
];

const NOTIFICATION_EMAIL_MODE_OPTIONS = [
  { value: 'off', label: 'Off' },
  { value: 'instant', label: 'Instant' },
  { value: 'daily_digest', label: 'Daily Digest' },
  { value: 'weekly_digest', label: 'Weekly Digest' }
];

const SCOPE_EMAIL_MODE_OPTIONS = [
  { value: 'inherit', label: 'Inherit Base Rule' },
  ...NOTIFICATION_EMAIL_MODE_OPTIONS
];

const SCOPE_IN_APP_OPTIONS = [
  { value: 'inherit', label: 'Inherit Base Rule' },
  { value: 'enabled', label: 'Force Enabled' },
  { value: 'disabled', label: 'Force Disabled' }
];

const DIGEST_DAY_OPTIONS = [
  { value: 0, label: 'Monday' },
  { value: 1, label: 'Tuesday' },
  { value: 2, label: 'Wednesday' },
  { value: 3, label: 'Thursday' },
  { value: 4, label: 'Friday' },
  { value: 5, label: 'Saturday' },
  { value: 6, label: 'Sunday' }
];

const DIGEST_HOUR_OPTIONS = Array.from({ length: 24 }, (_, hour) => ({
  value: hour,
  label: `${String(hour).padStart(2, '0')}:00 UTC`
}));

const DEFAULT_NOTIFICATION_SCOPE_PREFERENCES = {
  global_scope: { in_app: null, email_mode: 'inherit' },
  notice: { in_app: null, email_mode: 'inherit' },
  similarity: { in_app: null, email_mode: 'inherit' },
  ai: { in_app: null, email_mode: 'inherit' },
  system: { in_app: null, email_mode: 'inherit' }
};

const DEFAULT_DIGEST_PREFERENCES = {
  daily_digest_hour_utc: 8,
  weekly_digest_day_of_week: 0
};

const DEFAULT_COMMUNICATION_PREFERENCES = {
  announcement_email: true,
  club_announcement_email: true,
  notification_email: true,
  notification_in_app: true,
  notification_email_mode: 'instant',
  notification_scope_preferences: DEFAULT_NOTIFICATION_SCOPE_PREFERENCES,
  digest_preferences: DEFAULT_DIGEST_PREFERENCES
};

const BASIC_EMAIL_PREFERENCE_FIELDS = [
  {
    key: 'announcement_email',
    label: 'Announcement Emails',
    description: 'Receive central college, batch, class, and subject announcement emails.'
  },
  {
    key: 'club_announcement_email',
    label: 'Club Update Emails',
    description: 'Receive club announcement emails when you are part of the club audience.'
  },
  {
    key: 'notification_in_app',
    label: 'In-App Notifications',
    description: 'Show notification-center items inside CAPS AI by default.'
  }
];

const REPORT_STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'sent', label: 'Sent' },
  { value: 'read', label: 'Read' },
  { value: 'failed', label: 'Failed' },
  { value: 'skipped', label: 'Skipped' }
];

const REPORT_EXPORT_VIEW_OPTIONS = [
  { value: 'rows', label: 'Detailed Rows' },
  { value: 'creator_summary', label: 'Creator Summary' },
  { value: 'scope_summary', label: 'Scope Summary' },
  { value: 'email_health', label: 'Email Health' }
];

const NOTIFICATION_PRESET_OPTIONS = [
  {
    key: 'student',
    label: 'Student',
    description: 'Keep email quiet by batching most alerts while leaving urgent system notices instant.',
  },
  {
    key: 'faculty',
    label: 'Faculty',
    description: 'Stay responsive to teaching and review activity with more instant delivery.',
  },
  {
    key: 'admin',
    label: 'Admin Ops',
    description: 'Favor immediate delivery across operational scopes for tighter oversight.',
  }
];

const REPORT_VIEW_STORAGE_PREFIX = 'caps_ai_notification_report_views_v1';

const REPORT_VIEW_STARTERS = [
  {
    key: 'starter:all',
    label: 'All Activity',
    description: 'Default operational view across all notification delivery activity.',
    days: 7,
    filters: { scope: '', status: '', created_by: '' },
    readonly: true
  },
  {
    key: 'starter:failed',
    label: 'Failed Deliveries',
    description: 'Focus on failed notification deliveries that may need follow-up.',
    days: 14,
    filters: { scope: '', status: 'failed', created_by: '' },
    readonly: true
  },
  {
    key: 'starter:system',
    label: 'System Alerts',
    description: 'Review operational notifications coming from system scope.',
    days: 7,
    filters: { scope: 'system', status: '', created_by: '' },
    readonly: true
  }
];

const SECTION_HASH_BY_ACTION = {
  settings: '#notification-preferences',
  filter: '#notification-filters',
  create: '#notification-create'
};

const COMMUNICATION_OPERATOR_TEACHER_EXTENSIONS = ['year_head', 'class_coordinator', 'club_coordinator'];

function formatTimestamp(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

function priorityVariant(priority) {
  if (priority === 'urgent') return 'danger';
  if (priority === 'info') return 'info';
  return 'default';
}

function deliveryBreakdown(item) {
  const summary = item?.delivery_summary || {};
  const totalRecipients = Number(summary.total_recipients || 0);
  const readCount = Number(summary.read_count || 0);
  const email = summary.email || {};
  const sentCount = Number(email.sent_count || 0);
  const failedCount = Number(email.failed_count || 0);
  const skippedCount = Number(email.skipped_count || 0);
  return {
    totalRecipients,
    readCount,
    unreadCount: Math.max(totalRecipients - readCount, 0),
    sentCount,
    failedCount,
    skippedCount
  };
}

function notifyNotificationBadgeRefresh() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('caps-ai:notifications-changed'));
  }
}

function normalizeScopePreference(scopePreference) {
  return {
    in_app: scopePreference?.in_app ?? null,
    email_mode: scopePreference?.email_mode || 'inherit'
  };
}

function normalizeCommunicationPreferences(preferences) {
  const raw = preferences || {};
  return {
    ...DEFAULT_COMMUNICATION_PREFERENCES,
    ...raw,
    notification_scope_preferences: {
      ...DEFAULT_NOTIFICATION_SCOPE_PREFERENCES,
      ...(raw.notification_scope_preferences || {}),
      global_scope: normalizeScopePreference(raw.notification_scope_preferences?.global_scope),
      notice: normalizeScopePreference(raw.notification_scope_preferences?.notice),
      similarity: normalizeScopePreference(raw.notification_scope_preferences?.similarity),
      ai: normalizeScopePreference(raw.notification_scope_preferences?.ai),
      system: normalizeScopePreference(raw.notification_scope_preferences?.system)
    },
    digest_preferences: {
      ...DEFAULT_DIGEST_PREFERENCES,
      ...(raw.digest_preferences || {})
    }
  };
}

function formatScopeInAppValue(value) {
  if (value === true) return 'enabled';
  if (value === false) return 'disabled';
  return 'inherit';
}

function parseScopeInAppValue(value) {
  if (value === 'enabled') return true;
  if (value === 'disabled') return false;
  return null;
}

function parseContentDispositionFilename(headerValue, fallback) {
  if (!headerValue) return fallback;
  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(headerValue);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }
  const quotedMatch = /filename="([^"]+)"/i.exec(headerValue);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }
  return fallback;
}

function reportViewStorageKey(userId) {
  return `${REPORT_VIEW_STORAGE_PREFIX}:${userId || 'anonymous'}`;
}

function normalizeReportFilters(filters) {
  return {
    scope: String(filters?.scope || ''),
    status: String(filters?.status || ''),
    created_by: String(filters?.created_by || '')
  };
}

function buildReportViewSignature(days, filters) {
  return JSON.stringify({
    days: Number(days || 7),
    filters: normalizeReportFilters(filters)
  });
}

function readSavedReportViews(userId) {
  try {
    const raw = globalThis.localStorage?.getItem(reportViewStorageKey(userId));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((item) => item && typeof item === 'object' && item.key && item.label)
      .map((item) => ({
        key: String(item.key),
        label: String(item.label),
        description: String(item.description || 'Saved report view'),
        days: Number(item.days || 7),
        filters: normalizeReportFilters(item.filters),
        readonly: false
      }));
  } catch {
    return [];
  }
}

function writeSavedReportViews(userId, views) {
  try {
    globalThis.localStorage?.setItem(reportViewStorageKey(userId), JSON.stringify(views));
  } catch {
    // Ignore local storage failures for saved report views.
  }
}

function slugifyReportViewLabel(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48);
}

function buildNotificationPreset(presetKey) {
  const base = normalizeCommunicationPreferences(DEFAULT_COMMUNICATION_PREFERENCES);
  if (presetKey === 'student') {
    return normalizeCommunicationPreferences({
      ...base,
      announcement_email: true,
      club_announcement_email: true,
      notification_in_app: true,
      notification_email: true,
      notification_email_mode: 'daily_digest',
      digest_preferences: {
        daily_digest_hour_utc: 18,
        weekly_digest_day_of_week: 5
      },
      notification_scope_preferences: {
        ...base.notification_scope_preferences,
        notice: { in_app: true, email_mode: 'daily_digest' },
        similarity: { in_app: true, email_mode: 'off' },
        ai: { in_app: true, email_mode: 'daily_digest' },
        system: { in_app: true, email_mode: 'instant' }
      }
    });
  }
  if (presetKey === 'faculty') {
    return normalizeCommunicationPreferences({
      ...base,
      announcement_email: true,
      club_announcement_email: true,
      notification_in_app: true,
      notification_email: true,
      notification_email_mode: 'instant',
      digest_preferences: {
        daily_digest_hour_utc: 16,
        weekly_digest_day_of_week: 4
      },
      notification_scope_preferences: {
        ...base.notification_scope_preferences,
        notice: { in_app: true, email_mode: 'instant' },
        similarity: { in_app: true, email_mode: 'instant' },
        ai: { in_app: true, email_mode: 'instant' },
        system: { in_app: true, email_mode: 'instant' }
      }
    });
  }
  if (presetKey === 'admin') {
    return normalizeCommunicationPreferences({
      ...base,
      announcement_email: true,
      club_announcement_email: true,
      notification_in_app: true,
      notification_email: true,
      notification_email_mode: 'instant',
      digest_preferences: {
        daily_digest_hour_utc: 9,
        weekly_digest_day_of_week: 0
      },
      notification_scope_preferences: {
        ...base.notification_scope_preferences,
        global_scope: { in_app: true, email_mode: 'instant' },
        notice: { in_app: true, email_mode: 'instant' },
        similarity: { in_app: true, email_mode: 'instant' },
        ai: { in_app: true, email_mode: 'instant' },
        system: { in_app: true, email_mode: 'instant' }
      }
    });
  }
  return base;
}

function nextDigestRun(kind, digestPreferences) {
  const now = new Date();
  const dailyHour = Number(digestPreferences?.daily_digest_hour_utc ?? 8);
  const weeklyDay = Number(digestPreferences?.weekly_digest_day_of_week ?? 0);
  if (kind === 'weekly') {
    const next = new Date(now);
    next.setUTCHours(dailyHour, 0, 0, 0);
    const currentWeekday = (next.getUTCDay() + 6) % 7;
    const daysAhead = (weeklyDay - currentWeekday + 7) % 7;
    next.setUTCDate(next.getUTCDate() + daysAhead);
    if (next <= now) {
      next.setUTCDate(next.getUTCDate() + 7);
    }
    return next;
  }
  const next = new Date(now);
  next.setUTCHours(dailyHour, 0, 0, 0);
  if (next <= now) {
    next.setUTCDate(next.getUTCDate() + 1);
  }
  return next;
}

function formatDigestPreview(timestamp) {
  if (!(timestamp instanceof Date) || Number.isNaN(timestamp.getTime())) return '-';
  return timestamp.toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  });
}

function formatPercent(value) {
  const numeric = Number(value || 0);
  return `${numeric.toFixed(numeric % 1 === 0 ? 0 : 1)}%`;
}

function formatDelta(value, { suffix = '', decimals = 1 } = {}) {
  const numeric = Number(value || 0);
  const rounded = numeric.toFixed(Number.isInteger(numeric) ? 0 : decimals);
  return `${numeric > 0 ? '+' : ''}${rounded}${suffix}`;
}

function resolveReconciliationPreset({ alertCode = '', metricKey = '', metricLabel = '' } = {}) {
  const haystack = `${alertCode} ${metricKey} ${metricLabel}`.toLowerCase();
  if (haystack.includes('failed')) {
    return { label: 'failed delivery rows', filters: { status: 'failed' }, exportView: 'rows' };
  }
  if (haystack.includes('pending')) {
    return { label: 'pending delivery rows', filters: { status: 'pending' }, exportView: 'rows' };
  }
  if (haystack.includes('read')) {
    return { label: 'read delivery rows', filters: { status: 'read' }, exportView: 'rows' };
  }
  if (haystack.includes('sent') || haystack.includes('delivered')) {
    return { label: 'sent delivery rows', filters: { status: 'sent' }, exportView: 'rows' };
  }
  if (haystack.includes('skipped')) {
    return { label: 'skipped delivery rows', filters: { status: 'skipped' }, exportView: 'rows' };
  }
  return null;
}

function ResponsiveOpsSection({ title, summary, badge = null, open, onToggle, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-900/30">
      <button
        type="button"
        className="flex w-full items-start justify-between gap-3 rounded-2xl px-4 py-3 text-left lg:hidden"
        onClick={onToggle}
        aria-expanded={open}
      >
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</p>
            {badge}
          </div>
          {summary ? <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{summary}</p> : null}
        </div>
        <ChevronDown
          size={18}
          className={`mt-0.5 shrink-0 text-slate-500 transition-transform dark:text-slate-400 ${open ? 'rotate-180' : ''}`}
        />
      </button>
      <div className={`${open ? 'block' : 'hidden'} lg:block`}>
        <div className="p-4 lg:p-0">{children}</div>
      </div>
    </section>
  );
}

export default function NotificationsPage() {
  const { user, refreshUser } = useAuth();
  const { pushToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const canCreate = ['admin', 'teacher'].includes(user?.role || '');
  const canManageCommunicationOps =
    user?.role === 'admin' ||
    (user?.role === 'teacher' &&
      COMMUNICATION_OPERATOR_TEACHER_EXTENSIONS.some((extension) => (user?.extended_roles || []).includes(extension)));
  const canSelectTargetUser = user?.role === 'admin';
  const highlightedNotificationId = searchParams.get('highlight') || '';

  const [rows, setRows] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [deliveryOpen, setDeliveryOpen] = useState(false);
  const [deliveryLoading, setDeliveryLoading] = useState(false);
  const [deliveryError, setDeliveryError] = useState('');
  const [deliveryNotificationId, setDeliveryNotificationId] = useState('');
  const [deliveryDetails, setDeliveryDetails] = useState(null);
  const [retryingDeliveryTarget, setRetryingDeliveryTarget] = useState('');
  const [preferences, setPreferences] = useState(() => normalizeCommunicationPreferences(user?.communication_preferences));
  const [savingPreferences, setSavingPreferences] = useState(false);
  const [deliveryReport, setDeliveryReport] = useState(null);
  const [reportDays, setReportDays] = useState(7);
  const [reportFilters, setReportFilters] = useState({
    scope: '',
    status: '',
    created_by: ''
  });
  const [savedReportViews, setSavedReportViews] = useState([]);
  const [reportViewName, setReportViewName] = useState('');
  const [loadingReport, setLoadingReport] = useState(false);
  const [deliveryTrends, setDeliveryTrends] = useState([]);
  const [loadingTrends, setLoadingTrends] = useState(false);
  const [deliveryAnomalies, setDeliveryAnomalies] = useState([]);
  const [loadingAnomalies, setLoadingAnomalies] = useState(false);
  const [deliveryBenchmarks, setDeliveryBenchmarks] = useState(null);
  const [loadingBenchmarks, setLoadingBenchmarks] = useState(false);
  const [deliveryIncidents, setDeliveryIncidents] = useState([]);
  const [loadingIncidents, setLoadingIncidents] = useState(false);
  const [processingDigests, setProcessingDigests] = useState(false);
  const [exportingDelivery, setExportingDelivery] = useState(false);
  const [exportingReport, setExportingReport] = useState(false);
  const [reportExportView, setReportExportView] = useState('rows');
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(20);
  const [filters, setFilters] = useState({
    is_read: '',
    scope: ''
  });
  const [form, setForm] = useState({
    title: '',
    message: '',
    priority: 'normal',
    scope: 'global',
    target_user_id: ''
  });
  const [reportingPanels, setReportingPanels] = useState({
    controls: true,
    views: false,
    anomalies: false,
    benchmarks: false,
    incidents: false,
    comparisons: false,
    emailOps: false,
    trends: false,
    breakdowns: false
  });
  const preferencesSectionRef = useRef(null);
  const filtersSectionRef = useRef(null);
  const createSectionRef = useRef(null);
  const reportControlsSectionRef = useRef(null);

  useEffect(() => {
    setPreferences(normalizeCommunicationPreferences(user?.communication_preferences));
  }, [user?.communication_preferences]);

  useEffect(() => {
    setSavedReportViews(readSavedReportViews(user?.id));
  }, [user?.id]);

  useEffect(() => {
    writeSavedReportViews(user?.id, savedReportViews);
  }, [savedReportViews, user?.id]);

  useEffect(() => {
    if (!canManageCommunicationOps) return;
    loadDeliveryReport(reportDays, reportFilters);
    loadDeliveryTrends(reportDays, reportFilters);
    loadDeliveryAnomalies(reportDays, reportFilters);
    loadDeliveryBenchmarks(reportDays, reportFilters);
    loadDeliveryIncidents();
  }, [canManageCommunicationOps, reportDays, reportFilters]);

  async function loadNotifications(nextSkip = skip, nextLimit = limit, nextFilters = filters) {
    setLoading(true);
    setError('');
    try {
      const params = {
        skip: nextSkip,
        limit: nextLimit
      };
      if (nextFilters.is_read !== '') {
        params.is_read = nextFilters.is_read === 'true';
      }
      if (nextFilters.scope) {
        params.scope = nextFilters.scope;
      }

      const response = await apiClient.get('/notifications/', { params });
      setRows(response.data || []);
    } catch (err) {
      const message = formatApiError(err, 'Failed to load notifications');
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
    } finally {
      setLoading(false);
    }
  }

  async function loadUsers() {
    if (!canSelectTargetUser) return;
    try {
      const response = await apiClient.get('/users/');
      setUsers(response.data || []);
    } catch {
      setUsers([]);
    }
  }

  useEffect(() => {
    loadNotifications(skip, limit, filters);
  }, [skip, limit]);

  useEffect(() => {
    loadUsers();
  }, [canSelectTargetUser]);

  useEffect(() => {
    if (!highlightedNotificationId || loading || rows.length === 0) return;
    const timer = window.setTimeout(() => {
      const target = document.getElementById(`notification-card-${highlightedNotificationId}`);
      target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 120);
    return () => window.clearTimeout(timer);
  }, [highlightedNotificationId, loading, rows.length]);

  const scopeOptions = useMemo(() => {
    const discovered = Array.from(new Set(rows.map((item) => item.scope).filter(Boolean)));
    const base = [...SCOPE_OPTIONS];
    discovered.forEach((scope) => {
      if (!base.some((item) => item.value === scope)) {
        base.push({ value: scope, label: scope });
      }
    });
    return base;
  }, [rows]);

  const userOptions = useMemo(
    () =>
      users
        .filter((item) => item.is_active !== false)
        .map((item) => ({
          value: item.id,
          label: `${item.full_name} (${item.email})`
        })),
    [users]
  );

  const userLabelById = useMemo(
    () => Object.fromEntries(userOptions.map((item) => [item.value, item.label])),
    [userOptions]
  );

  const stats = useMemo(() => {
    const unread = rows.filter((item) => !item.is_read).length;
    const urgent = rows.filter((item) => item.priority === 'urgent').length;
    return {
      total: rows.length,
      unread,
      urgent
    };
  }, [rows]);

  const preferenceDirty = useMemo(() => {
    const baseline = normalizeCommunicationPreferences(user?.communication_preferences);
    return JSON.stringify(preferences) !== JSON.stringify(baseline);
  }, [preferences, user?.communication_preferences]);

  const digestPreview = useMemo(
    () => ({
      daily: nextDigestRun('daily', preferences.digest_preferences),
      weekly: nextDigestRun('weekly', preferences.digest_preferences)
    }),
    [preferences.digest_preferences]
  );

  const creatorComparisonRows = useMemo(() => deliveryReport?.creator_rows || [], [deliveryReport?.creator_rows]);
  const scopeComparisonRows = useMemo(() => deliveryReport?.scope_rows || [], [deliveryReport?.scope_rows]);
  const benchmarkMetrics = useMemo(() => deliveryBenchmarks?.metrics || [], [deliveryBenchmarks?.metrics]);
  const benchmarkPrimaryMetrics = useMemo(() => benchmarkMetrics.slice(0, 4), [benchmarkMetrics]);
  const emailHealth = useMemo(
    () =>
      deliveryReport?.email_health || {
        total_rows: 0,
        sent_count: 0,
        failed_count: 0,
        skipped_count: 0,
        pending_count: 0,
        read_count: 0,
        delivered_rate_pct: 0,
        attention_rate_pct: 0,
        retry_candidate_count: 0,
        top_errors: []
      },
    [deliveryReport?.email_health]
  );

  const availableReportViews = useMemo(() => {
    const starterViews = REPORT_VIEW_STARTERS.map((view) =>
      view.key === 'starter:system' && user?.id
        ? {
            ...view,
            description:
              user.role === 'admin'
                ? 'Review operational notifications coming from system scope.'
                : view.description
          }
        : view
    );
    const creatorStarter = user?.id
      ? [
          {
            key: 'starter:mine',
            label: 'My Created',
            description: 'Show delivery rows for notifications created by you.',
            days: 14,
            filters: { scope: '', status: '', created_by: user.id },
            readonly: true
          }
        ]
      : [];
    return [...starterViews, ...creatorStarter, ...savedReportViews];
  }, [savedReportViews, user?.id, user?.role]);

  const activeReportViewKey = useMemo(() => {
    const currentSignature = buildReportViewSignature(reportDays, reportFilters);
    const matchedView = availableReportViews.find(
      (view) => buildReportViewSignature(view.days, view.filters) === currentSignature
    );
    return matchedView?.key || '';
  }, [availableReportViews, reportDays, reportFilters]);

  async function onApplyFilters(event) {
    event.preventDefault();
    setSkip(0);
    await loadNotifications(0, limit, filters);
  }

  async function onMarkRead(notificationId) {
    try {
      await apiClient.patch(`/notifications/${notificationId}/read`);
      setRows((prev) =>
        prev.map((item) => (item.id === notificationId ? { ...item, is_read: true } : item))
      );
      notifyNotificationBadgeRefresh();
      pushToast({ title: 'Marked as read', description: 'Notification state updated.', variant: 'success' });
    } catch (err) {
      pushToast({
        title: 'Update failed',
        description: formatApiError(err, 'Failed to mark notification as read'),
        variant: 'error'
      });
    }
  }

  async function onCreateNotification(event) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await apiClient.post('/notifications/', {
        ...form,
        target_user_id: form.target_user_id || null
      });
      setForm({
        title: '',
        message: '',
        priority: 'normal',
        scope: 'global',
        target_user_id: ''
      });
      pushToast({ title: 'Created', description: 'Notification created successfully.', variant: 'success' });
      await loadNotifications(0, limit, filters);
      if (canManageCommunicationOps) {
        await Promise.all([
          loadDeliveryReport(reportDays, reportFilters),
          loadDeliveryTrends(reportDays, reportFilters),
          loadDeliveryAnomalies(reportDays, reportFilters),
          loadDeliveryBenchmarks(reportDays, reportFilters),
          loadDeliveryIncidents()
        ]);
      }
      setSkip(0);
      notifyNotificationBadgeRefresh();
    } catch (err) {
      pushToast({
        title: 'Create failed',
        description: formatApiError(err, 'Failed to create notification'),
        variant: 'error'
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function onMarkVisibleRead() {
    const unreadRows = rows.filter((item) => !item.is_read);
    if (!unreadRows.length) {
      pushToast({ title: 'Up to date', description: 'Visible notifications are already read.', variant: 'info' });
      return;
    }
    setSubmitting(true);
    try {
      await Promise.all(unreadRows.map((item) => apiClient.patch(`/notifications/${item.id}/read`)));
      setRows((prev) => prev.map((item) => ({ ...item, is_read: true })));
      notifyNotificationBadgeRefresh();
      pushToast({ title: 'Updated', description: 'Visible notifications marked as read.', variant: 'success' });
    } catch (err) {
      pushToast({
        title: 'Bulk update failed',
        description: formatApiError(err, 'Unable to mark visible notifications as read'),
        variant: 'error'
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function loadDeliveryDetails(notificationId, { openModal = false } = {}) {
    if (!notificationId) return;
    if (openModal) {
      setDeliveryOpen(true);
      setDeliveryDetails(null);
      setDeliveryError('');
    }
    setDeliveryNotificationId(notificationId);
    setDeliveryLoading(true);
    try {
      const response = await apiClient.get(`/admin/communication/delivery/notifications/${notificationId}`);
      setDeliveryDetails(response.data || null);
      setDeliveryError('');
    } catch (err) {
      const message = formatApiError(err, 'Unable to load delivery details');
      setDeliveryDetails(null);
      setDeliveryError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
    } finally {
      setDeliveryLoading(false);
    }
  }

  async function retryDeliveryEmail(target = null) {
    if (!deliveryNotificationId) return;
    const payload = target
      ? {
          target_user_ids: target.target_user_id ? [target.target_user_id] : [],
          target_emails: !target.target_user_id && target.target_email ? [target.target_email] : [],
          include_skipped: true
        }
      : { include_skipped: true };
    const retryKey = target ? `${target.target_user_id || ''}::${target.target_email || ''}` : '*';
    setRetryingDeliveryTarget(retryKey);
    try {
      const response = await apiClient.post(
        `/admin/communication/delivery/notifications/${deliveryNotificationId}/retry-email`,
        payload
      );
      const retriedCount = Number(response.data?.retried_count || 0);
      setDeliveryDetails(response.data?.details || null);
      await Promise.all([
        loadNotifications(skip, limit, filters),
        loadDeliveryReport(reportDays, reportFilters),
        loadDeliveryTrends(reportDays, reportFilters),
        loadDeliveryAnomalies(reportDays, reportFilters),
        loadDeliveryBenchmarks(reportDays, reportFilters),
        loadDeliveryIncidents()
      ]);
      pushToast({
        title: retriedCount > 0 ? 'Email retry queued' : 'Nothing to retry',
        description:
          retriedCount > 0
            ? `${retriedCount} recipient${retriedCount === 1 ? '' : 's'} reprocessed for email delivery.`
            : 'No failed or skipped email rows matched this retry action.',
        variant: retriedCount > 0 ? 'success' : 'info'
      });
    } catch (err) {
      pushToast({
        title: 'Retry failed',
        description: formatApiError(err, 'Unable to retry email delivery'),
        variant: 'error'
      });
    } finally {
      setRetryingDeliveryTarget('');
    }
  }

  async function loadDeliveryReport(days = reportDays, nextReportFilters = reportFilters) {
    if (!canManageCommunicationOps) return;
    setLoadingReport(true);
    try {
      const response = await apiClient.get('/admin/communication/delivery/report', {
        params: {
          days,
          source_kind: 'notification',
          scope: nextReportFilters.scope || undefined,
          status: nextReportFilters.status || undefined,
          created_by: nextReportFilters.created_by || undefined
        }
      });
      setDeliveryReport(response.data || null);
    } catch (err) {
      pushToast({
        title: 'Report unavailable',
        description: formatApiError(err, 'Unable to load notification delivery report'),
        variant: 'error'
      });
    } finally {
      setLoadingReport(false);
    }
  }

  async function loadDeliveryTrends(days = reportDays, nextReportFilters = reportFilters) {
    if (!canManageCommunicationOps) return;
    setLoadingTrends(true);
    try {
      const response = await apiClient.get('/admin/communication/delivery/report/trends', {
        params: {
          days,
          source_kind: 'notification',
          scope: nextReportFilters.scope || undefined,
          status: nextReportFilters.status || undefined,
          created_by: nextReportFilters.created_by || undefined
        }
      });
      setDeliveryTrends(Array.isArray(response.data?.points) ? response.data.points : []);
    } catch (err) {
      pushToast({
        title: 'Trend load failed',
        description: formatApiError(err, 'Unable to load notification delivery trends'),
        variant: 'error'
      });
    } finally {
      setLoadingTrends(false);
    }
  }

  async function loadDeliveryAnomalies(days = reportDays, nextReportFilters = reportFilters) {
    if (!canManageCommunicationOps) return;
    setLoadingAnomalies(true);
    try {
      const response = await apiClient.get('/admin/communication/delivery/report/anomalies', {
        params: {
          days,
          source_kind: 'notification',
          scope: nextReportFilters.scope || undefined,
          status: nextReportFilters.status || undefined,
          created_by: nextReportFilters.created_by || undefined
        }
      });
      setDeliveryAnomalies(Array.isArray(response.data?.alerts) ? response.data.alerts : []);
    } catch (err) {
      pushToast({
        title: 'Alert load failed',
        description: formatApiError(err, 'Unable to evaluate delivery anomalies'),
        variant: 'error'
      });
    } finally {
      setLoadingAnomalies(false);
    }
  }

  async function loadDeliveryBenchmarks(days = reportDays, nextReportFilters = reportFilters) {
    if (!canManageCommunicationOps) return;
    setLoadingBenchmarks(true);
    try {
      const response = await apiClient.get('/admin/communication/delivery/report/benchmarks', {
        params: {
          days,
          source_kind: 'notification',
          scope: nextReportFilters.scope || undefined,
          status: nextReportFilters.status || undefined,
          created_by: nextReportFilters.created_by || undefined
        }
      });
      setDeliveryBenchmarks(response.data || null);
    } catch (err) {
      pushToast({
        title: 'Benchmark load failed',
        description: formatApiError(err, 'Unable to load delivery benchmarks'),
        variant: 'error'
      });
    } finally {
      setLoadingBenchmarks(false);
    }
  }

  async function loadDeliveryIncidents() {
    if (!canManageCommunicationOps) return;
    setLoadingIncidents(true);
    try {
      const response = await apiClient.get('/admin/communication/delivery/incidents', {
        params: { limit: 25 }
      });
      setDeliveryIncidents(Array.isArray(response.data?.incidents) ? response.data.incidents : []);
    } catch (err) {
      pushToast({
        title: 'Incident load failed',
        description: formatApiError(err, 'Unable to load communication incidents'),
        variant: 'error'
      });
    } finally {
      setLoadingIncidents(false);
    }
  }

  async function downloadCsv(url, fallbackFilename, onStateChange = null) {
    try {
      onStateChange?.(true);
      const response = await apiClient.get(url, { responseType: 'blob' });
      const filename = parseContentDispositionFilename(response.headers?.['content-disposition'], fallbackFilename);
      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
      const objectUrl = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.URL.revokeObjectURL(objectUrl);
      return true;
    } catch (err) {
      pushToast({
        title: 'Export failed',
        description: formatApiError(err, 'Unable to export CSV'),
        variant: 'error'
      });
      return false;
    } finally {
      onStateChange?.(false);
    }
  }

  async function exportCurrentDeliveryCsv() {
    if (!deliveryNotificationId) return;
    const ok = await downloadCsv(
      `/admin/communication/delivery/notifications/${deliveryNotificationId}/export`,
      `notification-delivery-${deliveryNotificationId}.csv`,
      setExportingDelivery
    );
    if (ok) {
      pushToast({ title: 'Export ready', description: 'Notification delivery CSV downloaded.', variant: 'success' });
    }
  }

  async function exportDeliveryReportCsv() {
    return exportDeliveryReportCsvFor(reportDays, reportFilters, reportExportView);
  }

  async function exportDeliveryReportCsvFor(days, nextReportFilters, view) {
    const query = new URLSearchParams({
      days: String(days),
      source_kind: 'notification',
      view
    });
    if (nextReportFilters.scope) {
      query.set('scope', nextReportFilters.scope);
    }
    if (nextReportFilters.status) {
      query.set('status', nextReportFilters.status);
    }
    if (nextReportFilters.created_by) {
      query.set('created_by', nextReportFilters.created_by);
    }
    const ok = await downloadCsv(
      `/admin/communication/delivery/report/export?${query.toString()}`,
      `notification-delivery-${view}-${days}d.csv`,
      setExportingReport
    );
    if (ok) {
      const exportLabel = REPORT_EXPORT_VIEW_OPTIONS.find((item) => item.value === view)?.label || 'Report';
      pushToast({ title: 'Export ready', description: `${exportLabel} download is ready.`, variant: 'success' });
    }
    return ok;
  }

  async function processDueDigests() {
    setProcessingDigests(true);
    try {
      const response = await apiClient.post('/admin/communication/digests/process?limit=200');
      const processedCount = Number(response.data?.processed_count || 0);
      await Promise.all([
        loadDeliveryReport(reportDays, reportFilters),
        loadDeliveryTrends(reportDays, reportFilters),
        loadDeliveryAnomalies(reportDays, reportFilters),
        loadDeliveryBenchmarks(reportDays, reportFilters),
        loadDeliveryIncidents(),
        loadNotifications(skip, limit, filters)
      ]);
      pushToast({
        title: processedCount > 0 ? 'Digests processed' : 'No due digests',
        description:
          processedCount > 0
            ? `${processedCount} queued digest entr${processedCount === 1 ? 'y was' : 'ies were'} processed.`
            : 'There were no queued digests ready to send right now.',
        variant: processedCount > 0 ? 'success' : 'info'
      });
    } catch (err) {
      pushToast({
        title: 'Digest processing failed',
        description: formatApiError(err, 'Unable to process due digests'),
        variant: 'error'
      });
    } finally {
      setProcessingDigests(false);
    }
  }

  function applyReportView(view) {
    setReportDays(Number(view.days || 7));
    setReportFilters(normalizeReportFilters(view.filters));
  }

  function clearReportViewFilters() {
    setReportFilters({ scope: '', status: '', created_by: '' });
    setReportDays(7);
  }

  function applyReconciliationPreset(preset, sourceLabel = 'Reconciliation') {
    if (!preset) return;
    const nextFilters = normalizeReportFilters({
      ...reportFilters,
      ...preset.filters
    });
    const nextDays = Number(preset.days || reportDays);
    const nextExportView = preset.exportView || reportExportView;
    setReportDays(nextDays);
    setReportFilters(nextFilters);
    setReportExportView(nextExportView);
    setReportingPanels((prev) => ({
      ...prev,
      controls: true,
      anomalies: true,
      benchmarks: true,
      incidents: true
    }));
    window.setTimeout(() => {
      const target = reportControlsSectionRef.current;
      target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      target?.focus({ preventScroll: true });
    }, 0);
    pushToast({
      title: 'Report view updated',
      description: `${sourceLabel} is now focused on ${preset.label}.`,
      variant: 'info'
    });
  }

  async function exportReconciliationPreset(preset, sourceLabel = 'Reconciliation') {
    if (!preset) return;
    const nextFilters = normalizeReportFilters({
      ...reportFilters,
      ...preset.filters
    });
    const nextDays = Number(preset.days || reportDays);
    const nextExportView = preset.exportView || reportExportView;
    setReportDays(nextDays);
    setReportFilters(nextFilters);
    setReportExportView(nextExportView);
    setReportingPanels((prev) => ({
      ...prev,
      controls: true,
      incidents: true
    }));
    const ok = await exportDeliveryReportCsvFor(nextDays, nextFilters, nextExportView);
    if (ok) {
      pushToast({
        title: 'Impacted rows exported',
        description: `${sourceLabel} exported ${preset.label}.`,
        variant: 'success'
      });
    }
  }

  function saveCurrentReportView() {
    const trimmedName = reportViewName.trim();
    if (!trimmedName) {
      pushToast({
        title: 'Name required',
        description: 'Give this report view a short name before saving it.',
        variant: 'info'
      });
      return;
    }

    const nextView = {
      key: `custom:${slugifyReportViewLabel(trimmedName) || Date.now()}`,
      label: trimmedName,
      description: 'Saved from the notification reporting panel.',
      days: reportDays,
      filters: normalizeReportFilters(reportFilters),
      readonly: false
    };

    setSavedReportViews((prev) => {
      const existingIndex = prev.findIndex((item) => item.key === nextView.key || item.label.toLowerCase() === trimmedName.toLowerCase());
      if (existingIndex === -1) {
        return [...prev, nextView];
      }
      const updated = [...prev];
      updated[existingIndex] = { ...updated[existingIndex], ...nextView, key: updated[existingIndex].key };
      return updated;
    });
    setReportViewName('');
    pushToast({
      title: 'View saved',
      description: `"${trimmedName}" is now available in saved report views.`,
      variant: 'success'
    });
  }

  function deleteSavedReportView(viewKey) {
    const target = savedReportViews.find((item) => item.key === viewKey);
    if (!target) return;
    setSavedReportViews((prev) => prev.filter((item) => item.key !== viewKey));
    pushToast({
      title: 'View removed',
      description: `"${target.label}" was removed from saved report views.`,
      variant: 'success'
    });
  }

  function onTogglePreference(key) {
    setPreferences((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function applyPreset(presetKey) {
    setPreferences(buildNotificationPreset(presetKey));
  }

  function onNotificationEmailModeChange(value) {
    setPreferences((prev) => ({
      ...prev,
      notification_email: value !== 'off',
      notification_email_mode: value
    }));
  }

  function onScopeInAppChange(scopeKey, value) {
    setPreferences((prev) => ({
      ...prev,
      notification_scope_preferences: {
        ...prev.notification_scope_preferences,
        [scopeKey]: {
          ...prev.notification_scope_preferences[scopeKey],
          in_app: parseScopeInAppValue(value)
        }
      }
    }));
  }

  function onScopeEmailModeChange(scopeKey, value) {
    setPreferences((prev) => ({
      ...prev,
      notification_scope_preferences: {
        ...prev.notification_scope_preferences,
        [scopeKey]: {
          ...prev.notification_scope_preferences[scopeKey],
          email_mode: value
        }
      }
    }));
  }

  function onDigestPreferenceChange(key, value) {
    setPreferences((prev) => ({
      ...prev,
      digest_preferences: {
        ...prev.digest_preferences,
        [key]: Number(value)
      }
    }));
  }

  async function onSavePreferences() {
    setSavingPreferences(true);
    try {
      await apiClient.patch('/auth/communication-preferences', preferences);
      await refreshUser();
      pushToast({
        title: 'Preferences saved',
        description: 'Notification delivery preferences updated successfully.',
        variant: 'success'
      });
    } catch (err) {
      pushToast({
        title: 'Save failed',
        description: formatApiError(err, 'Unable to update communication preferences'),
        variant: 'error'
      });
    } finally {
      setSavingPreferences(false);
    }
  }

  function scrollBannerActionTarget(actionKey) {
    const targetMap = {
      settings: preferencesSectionRef.current,
      filter: filtersSectionRef.current,
      create: createSectionRef.current
    };
    const target = targetMap[actionKey];
    if (!target) return;
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    target.focus({ preventScroll: true });
    if (typeof window !== 'undefined') {
      window.history.replaceState(null, '', SECTION_HASH_BY_ACTION[actionKey] || window.location.pathname);
    }
  }

  function onBannerActionClick(actionKey) {
    scrollBannerActionTarget(actionKey);
  }

  function toggleReportingPanel(key) {
    setReportingPanels((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <div className="space-y-4 page-fade">
      <CommunicationTabs />

      <Card className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold">Notifications</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Review unread alerts, filter by scope, and acknowledge notifications directly.
            </p>
          </div>
          <div className="flex shrink-0 items-start gap-1 sm:gap-2">
            <button
              type="button"
              aria-label="Notification settings"
              title="Notification settings"
              className="flex w-[84px] flex-col items-center gap-1 rounded-xl px-2 py-1 text-center text-[11px] leading-tight text-slate-700 transition-colors hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:text-slate-200 dark:hover:bg-slate-800"
              onClick={() => onBannerActionClick('settings')}
            >
              <Settings size={24} strokeWidth={1.9} />
              <span>Notification settings</span>
            </button>
            <button
              type="button"
              aria-label="FILTER"
              title="FILTER"
              className="flex w-[62px] flex-col items-center gap-1 rounded-xl px-2 py-1 text-center text-[11px] font-medium leading-tight text-slate-700 transition-colors hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:text-slate-200 dark:hover:bg-slate-800"
              onClick={() => onBannerActionClick('filter')}
            >
              <Funnel size={24} strokeWidth={1.9} />
              <span>FILTER</span>
            </button>
            {canCreate ? (
              <button
                type="button"
                aria-label="CREATE"
                title="CREATE"
                className="flex w-[62px] flex-col items-center gap-1 rounded-xl px-2 py-1 text-center text-[11px] font-medium leading-tight text-slate-700 transition-colors hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:text-slate-200 dark:hover:bg-slate-800"
                onClick={() => onBannerActionClick('create')}
              >
                <CirclePlus size={24} strokeWidth={1.9} />
                <span>CREATE</span>
              </button>
            ) : null}
          </div>
        </div>
      </Card>

      <section
        id="notification-preferences"
        ref={preferencesSectionRef}
        tabIndex={-1}
        className="scroll-mt-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      >
        <Card className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Notification Preferences</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Control channels by scope, choose digest behavior, and keep routine updates out of the way without losing important alerts.
            </p>
          </div>
          <button
            type="button"
            className="btn-primary"
            onClick={onSavePreferences}
            disabled={savingPreferences || !preferenceDirty}
          >
            {savingPreferences ? 'Saving...' : preferenceDirty ? 'Save Preferences' : 'Saved'}
          </button>
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          {BASIC_EMAIL_PREFERENCE_FIELDS.map((item) => (
            <label
              key={item.key}
              className="flex cursor-pointer items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950"
            >
              <div>
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{item.label}</p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{item.description}</p>
              </div>
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                checked={Boolean(preferences[item.key])}
                onChange={() => onTogglePreference(item.key)}
                disabled={savingPreferences}
              />
            </label>
          ))}
        </div>

        <div className="grid gap-3 xl:grid-cols-3">
          {NOTIFICATION_PRESET_OPTIONS.map((preset) => (
            <button
              key={preset.key}
              type="button"
              className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-left transition hover:border-brand-300 hover:bg-brand-50/60 dark:border-slate-800 dark:bg-slate-900/60 dark:hover:border-brand-700 dark:hover:bg-brand-900/10"
              onClick={() => applyPreset(preset.key)}
              disabled={savingPreferences}
            >
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{preset.label} Preset</p>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{preset.description}</p>
            </button>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Notification Email Mode</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Choose whether email notifications send immediately or wait for a digest run.
            </p>
            <select
              className="input mt-3"
              value={preferences.notification_email_mode}
              onChange={(event) => onNotificationEmailModeChange(event.target.value)}
              disabled={savingPreferences}
            >
              {NOTIFICATION_EMAIL_MODE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Daily Digest Hour</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Used whenever any scope routes notification email into the daily digest queue.
            </p>
            <select
              className="input mt-3"
              value={preferences.digest_preferences.daily_digest_hour_utc}
              onChange={(event) => onDigestPreferenceChange('daily_digest_hour_utc', event.target.value)}
              disabled={savingPreferences}
            >
              {DIGEST_HOUR_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Weekly Digest Day</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Used whenever a scope is set to weekly digest delivery.
            </p>
            <select
              className="input mt-3"
              value={preferences.digest_preferences.weekly_digest_day_of_week}
              onChange={(event) => onDigestPreferenceChange('weekly_digest_day_of_week', event.target.value)}
              disabled={savingPreferences}
            >
              {DIGEST_DAY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Next Daily Digest</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {formatDigestPreview(digestPreview.daily)}
            </p>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Daily digests use {String(preferences.digest_preferences.daily_digest_hour_utc).padStart(2, '0')}:00 UTC.
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Next Weekly Digest</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {formatDigestPreview(digestPreview.weekly)}
            </p>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Weekly digests use {DIGEST_DAY_OPTIONS.find((item) => item.value === preferences.digest_preferences.weekly_digest_day_of_week)?.label || 'Monday'} at {String(preferences.digest_preferences.daily_digest_hour_utc).padStart(2, '0')}:00 UTC.
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Scope Rules</h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Override the base rules only where needed. Inherit keeps the global notification defaults.
            </p>
          </div>
          <div className="grid gap-3 xl:grid-cols-2">
            {NOTIFICATION_SCOPE_FIELDS.map((scope) => (
              <div
                key={scope.key}
                className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950"
              >
                <div className="mb-3">
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{scope.label}</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{scope.description}</p>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    <span className="mb-1 block font-medium">In-App Delivery</span>
                    <select
                      className="input"
                      value={formatScopeInAppValue(preferences.notification_scope_preferences[scope.key]?.in_app)}
                      onChange={(event) => onScopeInAppChange(scope.key, event.target.value)}
                      disabled={savingPreferences}
                    >
                      {SCOPE_IN_APP_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    <span className="mb-1 block font-medium">Email Delivery</span>
                    <select
                      className="input"
                      value={preferences.notification_scope_preferences[scope.key]?.email_mode || 'inherit'}
                      onChange={(event) => onScopeEmailModeChange(scope.key, event.target.value)}
                      disabled={savingPreferences}
                    >
                      {SCOPE_EMAIL_MODE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>
            ))}
          </div>
        </div>
        </Card>
      </section>

      {canManageCommunicationOps ? (
        <Card className="space-y-4">
          <div
            ref={reportControlsSectionRef}
            id="notification-delivery-report"
            tabIndex={-1}
            className="flex flex-wrap items-start justify-between gap-3 scroll-mt-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <div>
              <h2 className="text-lg font-semibold">Delivery Reporting</h2>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                Reconcile notification delivery outcomes, digest backlog, and exportable recipient rows for ops follow-up.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="info">{reportDays}d Window</Badge>
              <Badge variant={deliveryAnomalies.length ? 'warning' : 'success'}>
                {loadingAnomalies ? 'Checking...' : deliveryAnomalies.length ? `${deliveryAnomalies.length} Alerts` : 'Stable'}
              </Badge>
            </div>
          </div>

          <ResponsiveOpsSection
            title="Report Controls"
            summary="Filters, export settings, refresh controls, and digest processing."
            badge={<Badge variant="default">{reportExportView.replace('_', ' ')}</Badge>}
            open={reportingPanels.controls}
            onToggle={() => toggleReportingPanel('controls')}
          >
            <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div className="hidden lg:flex lg:flex-wrap lg:items-center lg:gap-2">
                <select
                  className="input w-full sm:w-36"
                  value={reportDays}
                  onChange={(event) => setReportDays(Number(event.target.value))}
                >
                  {[1, 7, 14, 30, 90].map((days) => (
                    <option key={days} value={days}>
                      Last {days} day{days === 1 ? '' : 's'}
                    </option>
                  ))}
                </select>
                <select
                  className="input w-full sm:min-w-[180px]"
                  value={reportExportView}
                  onChange={(event) => setReportExportView(event.target.value)}
                >
                  {REPORT_EXPORT_VIEW_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn-secondary w-full sm:w-auto"
                  onClick={() => {
                    void Promise.all([
                      loadDeliveryReport(reportDays, reportFilters),
                      loadDeliveryTrends(reportDays, reportFilters),
                      loadDeliveryAnomalies(reportDays, reportFilters),
                      loadDeliveryBenchmarks(reportDays, reportFilters),
                      loadDeliveryIncidents()
                    ]);
                  }}
                  disabled={loadingReport || loadingTrends || loadingAnomalies || loadingBenchmarks || loadingIncidents}
                >
                  {loadingReport || loadingTrends || loadingAnomalies || loadingBenchmarks || loadingIncidents ? 'Refreshing...' : 'Refresh'}
                </button>
                <button type="button" className="btn-secondary w-full sm:w-auto" onClick={exportDeliveryReportCsv} disabled={exportingReport}>
                  {exportingReport ? 'Exporting...' : 'Export CSV'}
                </button>
                <button type="button" className="btn-primary w-full sm:w-auto" onClick={processDueDigests} disabled={processingDigests}>
                  {processingDigests ? 'Processing...' : 'Process Due Digests'}
                </button>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <label className="text-sm text-slate-600 dark:text-slate-300">
                  <span className="mb-1 block font-medium">Time Window</span>
                  <select
                    className="input"
                    value={reportDays}
                    onChange={(event) => setReportDays(Number(event.target.value))}
                  >
                    {[1, 7, 14, 30, 90].map((days) => (
                      <option key={days} value={days}>
                        Last {days} day{days === 1 ? '' : 's'}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm text-slate-600 dark:text-slate-300">
                  <span className="mb-1 block font-medium">Export View</span>
                  <select
                    className="input"
                    value={reportExportView}
                    onChange={(event) => setReportExportView(event.target.value)}
                  >
                    {REPORT_EXPORT_VIEW_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm text-slate-600 dark:text-slate-300">
                  <span className="mb-1 block font-medium">Scope Filter</span>
                  <select
                    className="input"
                    value={reportFilters.scope}
                    onChange={(event) => setReportFilters((prev) => ({ ...prev, scope: event.target.value }))}
                  >
                    <option value="">All Scopes</option>
                    {SCOPE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm text-slate-600 dark:text-slate-300">
                  <span className="mb-1 block font-medium">Status Filter</span>
                  <select
                    className="input"
                    value={reportFilters.status}
                    onChange={(event) => setReportFilters((prev) => ({ ...prev, status: event.target.value }))}
                  >
                    {REPORT_STATUS_OPTIONS.map((option) => (
                      <option key={option.value || 'all'} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm text-slate-600 dark:text-slate-300 sm:col-span-2 xl:col-span-3">
                  <span className="mb-1 block font-medium">Creator Filter</span>
                  <select
                    className="input"
                    value={reportFilters.created_by}
                    onChange={(event) => setReportFilters((prev) => ({ ...prev, created_by: event.target.value }))}
                  >
                    <option value="">All Creators</option>
                    {userOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="sm:col-span-2 xl:col-span-1">
                  <button type="button" className="btn-secondary w-full" onClick={clearReportViewFilters}>
                    Reset View
                  </button>
                </div>
              </div>

              <div className="grid gap-2 sm:grid-cols-3">
                <button
                  type="button"
                  className="btn-secondary w-full"
                  onClick={() => {
                    void Promise.all([
                      loadDeliveryReport(reportDays, reportFilters),
                      loadDeliveryTrends(reportDays, reportFilters),
                      loadDeliveryAnomalies(reportDays, reportFilters),
                      loadDeliveryBenchmarks(reportDays, reportFilters),
                      loadDeliveryIncidents()
                    ]);
                  }}
                  disabled={loadingReport || loadingTrends || loadingAnomalies || loadingBenchmarks || loadingIncidents}
                >
                  {loadingReport || loadingTrends || loadingAnomalies || loadingBenchmarks || loadingIncidents ? 'Refreshing...' : 'Refresh'}
                </button>
                <button type="button" className="btn-secondary w-full" onClick={exportDeliveryReportCsv} disabled={exportingReport}>
                  {exportingReport ? 'Exporting...' : 'Export CSV'}
                </button>
                <button type="button" className="btn-primary w-full" onClick={processDueDigests} disabled={processingDigests}>
                  {processingDigests ? 'Processing...' : 'Process Due Digests'}
                </button>
              </div>
            </div>
          </ResponsiveOpsSection>

          <ResponsiveOpsSection
            title="Saved Report Views"
            summary="Reuse common operational filters without rebuilding the same report every time."
            badge={<Badge variant="default">{availableReportViews.length}</Badge>}
            open={reportingPanels.views}
            onToggle={() => toggleReportingPanel('views')}
          >
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/40">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Saved Report Views</p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Reuse common operational filters without rebuilding the same report every time.
                </p>
              </div>
              <div className="flex min-w-0 flex-1 flex-col items-stretch gap-2 sm:min-w-[280px] sm:flex-row sm:flex-wrap sm:items-end">
                <label className="min-w-0 flex-1 text-sm text-slate-600 dark:text-slate-300 sm:min-w-[180px]">
                  <span className="mb-1 block font-medium">Save Current Filters</span>
                  <input
                    className="input"
                    placeholder="Example: Failed deliveries this week"
                    value={reportViewName}
                    onChange={(event) => setReportViewName(event.target.value)}
                  />
                </label>
                <button type="button" className="btn-primary w-full sm:w-auto" onClick={saveCurrentReportView}>
                  Save View
                </button>
              </div>
            </div>
            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              {availableReportViews.map((view) => {
                const isActive = activeReportViewKey === view.key;
                return (
                  <div
                    key={view.key}
                    className={`rounded-2xl border p-4 ${
                      isActive
                        ? 'border-brand-300 bg-brand-50/50 dark:border-brand-700 dark:bg-brand-900/10'
                        : 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950'
                    }`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{view.label}</p>
                          {view.readonly ? <Badge variant="default">Starter</Badge> : <Badge variant="info">Saved</Badge>}
                          {isActive ? <Badge variant="success">Active</Badge> : null}
                        </div>
                        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{view.description}</p>
                        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                          {view.days}d | Scope {view.filters.scope || 'all'} | Status {view.filters.status || 'all'} | Creator {view.filters.created_by || 'all'}
                        </p>
                      </div>
                      <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap">
                        <button type="button" className="btn-secondary w-full sm:w-auto" onClick={() => applyReportView(view)}>
                          Apply
                        </button>
                        {!view.readonly ? (
                          <button
                            type="button"
                            className="btn-secondary w-full sm:w-auto"
                            onClick={() => deleteSavedReportView(view.key)}
                          >
                            Delete
                          </button>
                        ) : null}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            </div>
          </ResponsiveOpsSection>

          <ResponsiveOpsSection
            title="Anomaly Watch"
            summary="Rule-based warnings for the active report view, focused on failure spikes and pending backlog buildup."
            badge={
              <Badge variant={deliveryAnomalies.length ? 'warning' : 'success'}>
                {loadingAnomalies ? 'Checking...' : deliveryAnomalies.length ? `${deliveryAnomalies.length} Active` : 'Stable'}
              </Badge>
            }
            open={reportingPanels.anomalies}
            onToggle={() => toggleReportingPanel('anomalies')}
          >
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/40">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Anomaly Watch</p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Rule-based warnings for the active saved view, focused on failure spikes and pending backlog buildup.
                </p>
              </div>
              <Badge variant={deliveryAnomalies.length ? 'warning' : 'success'}>
                {loadingAnomalies ? 'Checking...' : deliveryAnomalies.length ? `${deliveryAnomalies.length} Active` : 'Stable'}
              </Badge>
            </div>
            <div className="mt-4 space-y-3">
              {loadingAnomalies ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">Evaluating delivery anomalies...</p>
              ) : deliveryAnomalies.length ? (
                deliveryAnomalies.map((alert) => (
                  <div
                    key={alert.code}
                    className={`rounded-2xl border px-4 py-3 text-sm ${
                      alert.level === 'critical'
                        ? 'border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-900/20 dark:text-rose-200'
                        : 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-900/20 dark:text-amber-200'
                    }`}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold uppercase tracking-wide">{alert.level}</span>
                      <span className="text-xs opacity-80">{alert.code}</span>
                    </div>
                    <p className="mt-1">{alert.message}</p>
                    <p className="mt-2 text-xs opacity-80">
                      Metric {alert.metric} | Current {alert.current_value}
                      {alert.baseline_value !== null && alert.baseline_value !== undefined ? ` | Baseline ${alert.baseline_value}` : ''}
                    </p>
                    {resolveReconciliationPreset({ alertCode: alert.code, metricKey: alert.metric }) ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="btn-secondary"
                          aria-label={`Focus impacted rows for ${alert.code}`}
                          onClick={() =>
                            applyReconciliationPreset(
                              resolveReconciliationPreset({ alertCode: alert.code, metricKey: alert.metric }),
                              alert.code
                            )
                          }
                        >
                          Focus impacted rows
                        </button>
                      </div>
                    ) : null}
                  </div>
                ))
              ) : (
                <p className="text-sm text-emerald-600 dark:text-emerald-400">
                  No active delivery anomalies for the current report view.
                </p>
              )}
            </div>
            </div>
          </ResponsiveOpsSection>

          <ResponsiveOpsSection
            title="Benchmark View"
            summary="Compare the current reporting window against the immediately previous window using the same filters."
            badge={<Badge variant="info">{loadingBenchmarks ? 'Loading...' : `${reportDays}d vs previous`}</Badge>}
            open={reportingPanels.benchmarks}
            onToggle={() => toggleReportingPanel('benchmarks')}
          >
            <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Benchmark View</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Current window performance versus the prior matched window for the active report filters.
                  </p>
                </div>
                {deliveryBenchmarks ? (
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    {new Date(deliveryBenchmarks.current_start).toLocaleDateString()} to {new Date(deliveryBenchmarks.current_end).toLocaleDateString()}
                  </div>
                ) : null}
              </div>
              {loadingBenchmarks ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">Loading benchmark comparison...</p>
              ) : benchmarkPrimaryMetrics.length ? (
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  {benchmarkPrimaryMetrics.map((metric) => (
                    <div key={metric.key} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/40">
                      <p className="text-xs uppercase tracking-wide text-slate-500">{metric.label}</p>
                      <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">{metric.current_value}</p>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Previous {metric.previous_value}</p>
                      <p className={`mt-2 text-xs font-semibold ${metric.trend === 'up' ? 'text-emerald-600 dark:text-emerald-400' : metric.trend === 'down' ? 'text-rose-600 dark:text-rose-400' : 'text-slate-500 dark:text-slate-400'}`}>
                        Delta {formatDelta(metric.delta_value)}
                        {metric.delta_pct !== null ? ` (${formatDelta(metric.delta_pct, { suffix: '%', decimals: 1 })})` : ''}
                      </p>
                      {resolveReconciliationPreset({ metricKey: metric.key, metricLabel: metric.label }) ? (
                        <div className="mt-3 flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="btn-secondary"
                            aria-label={`Focus benchmark rows for ${metric.label}`}
                            onClick={() =>
                              applyReconciliationPreset(
                                resolveReconciliationPreset({ metricKey: metric.key, metricLabel: metric.label }),
                                metric.label
                              )
                            }
                          >
                            Focus rows
                          </button>
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">No benchmark data available for the current view.</p>
              )}
              {benchmarkMetrics.length ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      <tr>
                        <th className="pb-2 pr-3 font-medium">Metric</th>
                        <th className="pb-2 pr-3 font-medium">Current</th>
                        <th className="pb-2 pr-3 font-medium">Previous</th>
                        <th className="pb-2 pr-3 font-medium">Delta</th>
                        <th className="pb-2 font-medium">Direction</th>
                      </tr>
                    </thead>
                    <tbody className="text-slate-700 dark:text-slate-200">
                      {benchmarkMetrics.map((metric) => (
                        <tr key={metric.key} className="border-t border-slate-200 dark:border-slate-800">
                          <td className="py-2 pr-3 font-medium">{metric.label}</td>
                          <td className="py-2 pr-3">{metric.current_value}</td>
                          <td className="py-2 pr-3">{metric.previous_value}</td>
                          <td className="py-2 pr-3">
                            {formatDelta(metric.delta_value)}
                            {metric.delta_pct !== null ? ` (${formatDelta(metric.delta_pct, { suffix: '%', decimals: 1 })})` : ''}
                          </td>
                          <td className="py-2 capitalize">{metric.trend}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </div>
          </ResponsiveOpsSection>

          <ResponsiveOpsSection
            title="Incident History"
            summary="Review active and recently resolved communication incidents from the anomaly escalation pipeline."
            badge={<Badge variant={deliveryIncidents.some((item) => item.is_active) ? 'warning' : 'default'}>{loadingIncidents ? 'Loading...' : `${deliveryIncidents.filter((item) => item.is_active).length} Active`}</Badge>}
            open={reportingPanels.incidents}
            onToggle={() => toggleReportingPanel('incidents')}
          >
            <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              {loadingIncidents ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">Loading communication incidents...</p>
              ) : deliveryIncidents.length ? (
                deliveryIncidents.map((incident) => (
                  <div key={incident.alert_code} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/40">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{incident.alert_code}</p>
                          <Badge variant={incident.is_active ? 'warning' : 'success'}>{incident.is_active ? 'Active' : 'Resolved'}</Badge>
                          <Badge variant="default">{incident.level || 'info'}</Badge>
                        </div>
                        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{incident.message}</p>
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        Last seen {formatTimestamp(incident.last_seen_at)}
                      </div>
                    </div>
                    <div className="mt-3 grid gap-2 sm:grid-cols-4 text-sm text-slate-600 dark:text-slate-300">
                      <div>Routed {incident.routed_count || 0}</div>
                      <div>Resolved {incident.resolved_count || 0}</div>
                      <div>Cooldown hits {incident.cooldown_suppressed_count || 0}</div>
                      <div>Notifications {incident.notifications_sent_total || 0}</div>
                    </div>
                    {incident.history?.length ? (
                      <div className="mt-3 space-y-2">
                        {incident.history.slice().reverse().slice(0, 3).map((entry, index) => (
                          <div key={`${incident.alert_code}-${index}`} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <span className="font-semibold uppercase tracking-wide">{entry.action || 'event'}</span>
                              <span>{entry.timestamp ? formatTimestamp(entry.timestamp) : '-'}</span>
                            </div>
                            <p className="mt-1">{entry.message || incident.message}</p>
                          </div>
                        ))}
                      </div>
                    ) : null}
                    {resolveReconciliationPreset({ alertCode: incident.alert_code }) ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="btn-secondary"
                          aria-label={`Focus impacted rows for ${incident.alert_code}`}
                          onClick={() =>
                            applyReconciliationPreset(resolveReconciliationPreset({ alertCode: incident.alert_code }), incident.alert_code)
                          }
                        >
                          Focus impacted rows
                        </button>
                        <button
                          type="button"
                          className="btn-secondary"
                          aria-label={`Export impacted rows for ${incident.alert_code}`}
                          onClick={() =>
                            void exportReconciliationPreset(
                              resolveReconciliationPreset({ alertCode: incident.alert_code }),
                              incident.alert_code
                            )
                          }
                        >
                          Export impacted CSV
                        </button>
                      </div>
                    ) : null}
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">No communication incidents recorded yet.</p>
              )}
            </div>
          </ResponsiveOpsSection>

          <ResponsiveOpsSection
            title="Comparative Analytics"
            summary="Compare delivery quality by creator and scope for the active operational view."
            badge={<Badge variant="info">{activeReportViewKey ? 'Tracked View' : 'Current Filters'}</Badge>}
            open={reportingPanels.comparisons}
            onToggle={() => toggleReportingPanel('comparisons')}
          >
            <div className="grid gap-3 xl:grid-cols-[1.15fr_0.85fr]">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Comparative Analytics</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Compare delivery quality by creator and scope for the active operational view.
                  </p>
                </div>
                <Badge variant="info">{activeReportViewKey ? 'Tracked View' : 'Current Filters'}</Badge>
              </div>
              <div className="mt-4 grid gap-3 lg:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900/40">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">By Creator</p>
                    <span className="text-xs text-slate-500 dark:text-slate-400">Top volume first</span>
                  </div>
                  <div className="mt-3 overflow-x-auto">
                    <table className="min-w-full text-left text-sm">
                      <thead className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        <tr>
                          <th className="pb-2 pr-3 font-medium">Creator</th>
                          <th className="pb-2 pr-3 font-medium">Rows</th>
                          <th className="pb-2 pr-3 font-medium">Failed</th>
                          <th className="pb-2 pr-3 font-medium">Pending</th>
                          <th className="pb-2 font-medium">Read</th>
                        </tr>
                      </thead>
                      <tbody className="text-slate-700 dark:text-slate-200">
                        {creatorComparisonRows.length ? (
                          creatorComparisonRows.map((row) => (
                            <tr key={row.key} className="border-t border-slate-200 dark:border-slate-800">
                              <td className="py-2 pr-3">
                                <div className="font-medium">{row.label || row.key}</div>
                                <div className="text-xs text-slate-500 dark:text-slate-400">{row.key}</div>
                              </td>
                              <td className="py-2 pr-3">{row.total_count}</td>
                              <td className="py-2 pr-3">{row.failed_count} ({formatPercent(row.failed_rate_pct)})</td>
                              <td className="py-2 pr-3">{row.pending_count} ({formatPercent(row.pending_rate_pct)})</td>
                              <td className="py-2">{row.read_count} ({formatPercent(row.read_rate_pct)})</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td className="py-3 text-slate-500 dark:text-slate-400" colSpan="5">
                              No creator comparison rows for this view.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900/40">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">By Scope</p>
                    <span className="text-xs text-slate-500 dark:text-slate-400">Delivery quality slice</span>
                  </div>
                  <div className="mt-3 overflow-x-auto">
                    <table className="min-w-full text-left text-sm">
                      <thead className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        <tr>
                          <th className="pb-2 pr-3 font-medium">Scope</th>
                          <th className="pb-2 pr-3 font-medium">Rows</th>
                          <th className="pb-2 pr-3 font-medium">Failed</th>
                          <th className="pb-2 pr-3 font-medium">Pending</th>
                          <th className="pb-2 font-medium">Read</th>
                        </tr>
                      </thead>
                      <tbody className="text-slate-700 dark:text-slate-200">
                        {scopeComparisonRows.length ? (
                          scopeComparisonRows.map((row) => (
                            <tr key={row.key} className="border-t border-slate-200 dark:border-slate-800">
                              <td className="py-2 pr-3">
                                <div className="font-medium">{row.label || row.key}</div>
                                <div className="text-xs text-slate-500 dark:text-slate-400">{row.key}</div>
                              </td>
                              <td className="py-2 pr-3">{row.total_count}</td>
                              <td className="py-2 pr-3">{row.failed_count} ({formatPercent(row.failed_rate_pct)})</td>
                              <td className="py-2 pr-3">{row.pending_count} ({formatPercent(row.pending_rate_pct)})</td>
                              <td className="py-2">{row.read_count} ({formatPercent(row.read_rate_pct)})</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td className="py-3 text-slate-500 dark:text-slate-400" colSpan="5">
                              No scope comparison rows for this view.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Email Ops Monitor</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Track SMTP-facing delivery health, retry load, and the most common failure reasons.
                  </p>
                </div>
                <Badge variant={emailHealth.attention_rate_pct >= 25 ? 'warning' : 'success'}>
                  Attention {formatPercent(emailHealth.attention_rate_pct)}
                </Badge>
              </div>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 dark:border-slate-800 dark:bg-slate-900/40">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Email Rows</p>
                  <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">{emailHealth.total_rows || 0}</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Delivered {formatPercent(emailHealth.delivered_rate_pct)}
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 dark:border-slate-800 dark:bg-slate-900/40">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Retry Candidates</p>
                  <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">{emailHealth.retry_candidate_count || 0}</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Failed {emailHealth.failed_count || 0} | Skipped {emailHealth.skipped_count || 0}
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 dark:border-slate-800 dark:bg-slate-900/40">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Pending Email</p>
                  <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">{emailHealth.pending_count || 0}</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Read {emailHealth.read_count || 0} | Sent {emailHealth.sent_count || 0}
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 dark:border-slate-800 dark:bg-slate-900/40">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Digest Queue</p>
                  <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">{deliveryReport?.digest?.queued_total || 0}</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Failed {deliveryReport?.digest?.failed_total || 0} | Sent {deliveryReport?.digest?.sent_total || 0}
                  </p>
                </div>
              </div>
              <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900/40">
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Top Email Errors</p>
                <div className="mt-3 space-y-2 text-sm text-slate-700 dark:text-slate-200">
                  {emailHealth.top_errors?.length ? (
                    emailHealth.top_errors.map((item) => (
                      <div key={item.error} className="flex items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2 dark:border-slate-800 dark:bg-slate-950">
                        <span className="min-w-0 flex-1 break-words">{item.error}</span>
                        <span className="shrink-0 font-semibold">{item.count}</span>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-emerald-600 dark:text-emerald-400">
                      No email error strings recorded for the current report view.
                    </p>
                  )}
                </div>
              </div>
            </div>
            </div>
          </ResponsiveOpsSection>

          <ResponsiveOpsSection
            title="Trend Charts"
            summary="Open the delivery health and engagement trend charts for the active report view."
            badge={<Badge variant="default">{reportDays}d</Badge>}
            open={reportingPanels.trends}
            onToggle={() => toggleReportingPanel('trends')}
          >
            <div className="grid gap-3 xl:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Delivery Health Trend</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Failed, skipped, pending, and sent rows over time for the active report view.
                  </p>
                </div>
                <Badge variant="default">{reportDays}d</Badge>
              </div>
              <div className="mt-4 h-64">
                {loadingTrends ? (
                  <div className="flex h-full items-center justify-center text-sm text-slate-500 dark:text-slate-400">
                    Loading trend data...
                  </div>
                ) : deliveryTrends.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-sm text-slate-500 dark:text-slate-400">
                    No trend data for the current report view.
                  </div>
                ) : (
                  <SafeResponsiveContainer>
                    <AreaChart data={deliveryTrends}>
                      <CartesianGrid stroke="#cbd5e1" strokeDasharray="3 3" />
                      <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#64748b' }} />
                      <YAxis tick={{ fontSize: 12, fill: '#64748b' }} allowDecimals={false} />
                      <Tooltip
                        contentStyle={{ borderRadius: '1rem', borderColor: '#cbd5e1' }}
                        labelStyle={{ fontWeight: 600 }}
                      />
                      <Area type="monotone" dataKey="failed_count" stroke="#e11d48" fill="#ffe4e6" fillOpacity={0.7} strokeWidth={2} />
                      <Area type="monotone" dataKey="skipped_count" stroke="#d97706" fill="#fef3c7" fillOpacity={0.6} strokeWidth={2} />
                      <Area type="monotone" dataKey="pending_count" stroke="#2563eb" fill="#dbeafe" fillOpacity={0.45} strokeWidth={2} />
                      <Area type="monotone" dataKey="sent_count" stroke="#059669" fill="#d1fae5" fillOpacity={0.3} strokeWidth={2} />
                    </AreaChart>
                  </SafeResponsiveContainer>
                )}
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Engagement Trend</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Compare total delivery volume against read activity for the same saved view.
                  </p>
                </div>
                <Badge variant="info">{activeReportViewKey ? 'Saved View' : 'Custom View'}</Badge>
              </div>
              <div className="mt-4 h-64">
                {loadingTrends ? (
                  <div className="flex h-full items-center justify-center text-sm text-slate-500 dark:text-slate-400">
                    Loading trend data...
                  </div>
                ) : deliveryTrends.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-sm text-slate-500 dark:text-slate-400">
                    No trend data for the current report view.
                  </div>
                ) : (
                  <SafeResponsiveContainer>
                    <AreaChart data={deliveryTrends}>
                      <CartesianGrid stroke="#cbd5e1" strokeDasharray="3 3" />
                      <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#64748b' }} />
                      <YAxis tick={{ fontSize: 12, fill: '#64748b' }} allowDecimals={false} />
                      <Tooltip
                        contentStyle={{ borderRadius: '1rem', borderColor: '#cbd5e1' }}
                        labelStyle={{ fontWeight: 600 }}
                      />
                      <Area type="monotone" dataKey="total_count" stroke="#7c3aed" fill="#ede9fe" fillOpacity={0.45} strokeWidth={2} />
                      <Area type="monotone" dataKey="read_count" stroke="#0f766e" fill="#ccfbf1" fillOpacity={0.45} strokeWidth={2} />
                    </AreaChart>
                  </SafeResponsiveContainer>
                )}
              </div>
            </div>
            </div>
          </ResponsiveOpsSection>

          <ResponsiveOpsSection
            title="Delivery Snapshot"
            summary="Open the current report totals and breakdowns by status, channel, and scope."
            badge={<Badge variant="default">{deliveryReport?.total_rows || 0} rows</Badge>}
            open={reportingPanels.breakdowns}
            onToggle={() => toggleReportingPanel('breakdowns')}
          >
            <div className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
                <p className="text-xs uppercase tracking-wide text-slate-500">Rows</p>
                <p className="mt-1 text-3xl font-bold text-slate-900 dark:text-slate-100">{deliveryReport?.total_rows || 0}</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Sources {deliveryReport?.total_sources || 0}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
                <p className="text-xs uppercase tracking-wide text-slate-500">Sent</p>
                <p className="mt-1 text-3xl font-bold text-slate-900 dark:text-slate-100">{deliveryReport?.sent_count || 0}</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Failed {deliveryReport?.failed_count || 0} | Pending {deliveryReport?.pending_count || 0}
                </p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
                <p className="text-xs uppercase tracking-wide text-slate-500">Skipped</p>
                <p className="mt-1 text-3xl font-bold text-slate-900 dark:text-slate-100">{deliveryReport?.skipped_count || 0}</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Read rows {deliveryReport?.read_count || 0}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
                <p className="text-xs uppercase tracking-wide text-slate-500">Digest Queue</p>
                <p className="mt-1 text-3xl font-bold text-slate-900 dark:text-slate-100">{deliveryReport?.digest?.queued_total || 0}</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Sent {deliveryReport?.digest?.sent_total || 0} | Failed {deliveryReport?.digest?.failed_total || 0}
                </p>
              </div>
            </div>

            <div className="grid gap-3 lg:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">By Status</p>
              <div className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                {Object.entries(deliveryReport?.by_status || {}).length ? (
                  Object.entries(deliveryReport?.by_status || {}).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between">
                      <span className="capitalize">{key.replaceAll('_', ' ')}</span>
                      <span className="font-semibold">{value}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-slate-500 dark:text-slate-400">No delivery rows in this window.</p>
                )}
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">By Channel</p>
              <div className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                {Object.entries(deliveryReport?.by_channel || {}).length ? (
                  Object.entries(deliveryReport?.by_channel || {}).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between">
                      <span className="capitalize">{key.replaceAll('_', ' ')}</span>
                      <span className="font-semibold">{value}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-slate-500 dark:text-slate-400">No channel data recorded yet.</p>
                )}
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">By Scope</p>
              <div className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                {Object.entries(deliveryReport?.by_scope || {}).length ? (
                  Object.entries(deliveryReport?.by_scope || {}).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between">
                      <span className="capitalize">{key.replaceAll('_', ' ')}</span>
                      <span className="font-semibold">{value}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-slate-500 dark:text-slate-400">No scope breakdown recorded yet.</p>
                )}
              </div>
            </div>
          </div>
            </div>
          </ResponsiveOpsSection>
        </Card>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="!p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Loaded</p>
          <p className="mt-1 text-3xl font-bold">{stats.total}</p>
        </Card>
        <Card className="!p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Unread</p>
          <p className="mt-1 text-3xl font-bold">{stats.unread}</p>
        </Card>
        <Card className="!p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Urgent</p>
          <p className="mt-1 text-3xl font-bold">{stats.urgent}</p>
        </Card>
      </div>

      <section
        id="notification-filters"
        ref={filtersSectionRef}
        tabIndex={-1}
        className="scroll-mt-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      >
        <Card>
        <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" onSubmit={onApplyFilters}>
          <FormInput
            as="select"
            label="Read State"
            value={filters.is_read}
            onChange={(event) => setFilters((prev) => ({ ...prev, is_read: event.target.value }))}
          >
            <option value="">All</option>
            <option value="false">Unread</option>
            <option value="true">Read</option>
          </FormInput>
          <FormInput
            as="select"
            label="Scope"
            value={filters.scope}
            onChange={(event) => setFilters((prev) => ({ ...prev, scope: event.target.value }))}
          >
            <option value="">All Scopes</option>
            {scopeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </FormInput>
          <div className="flex items-end gap-2">
            <button type="submit" className="btn-primary w-full">
              Apply
            </button>
            <button
              type="button"
              className="btn-secondary w-full"
              onClick={() => {
                const nextFilters = { is_read: '', scope: '' };
                setFilters(nextFilters);
                setSkip(0);
                loadNotifications(0, limit, nextFilters);
              }}
            >
              Reset
            </button>
          </div>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              const nextFilters = { ...filters, is_read: 'false' };
              setFilters(nextFilters);
              setSkip(0);
              loadNotifications(0, limit, nextFilters);
            }}
          >
            Unread Only
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              const nextFilters = { ...filters, scope: 'notice' };
              setFilters(nextFilters);
              setSkip(0);
              loadNotifications(0, limit, nextFilters);
            }}
          >
            Announcement Deliveries
          </button>
          <button type="button" className="btn-secondary" onClick={() => loadNotifications(skip, limit, filters)}>
            Refresh
          </button>
          <button type="button" className="btn-secondary" onClick={onMarkVisibleRead} disabled={submitting}>
            {submitting ? 'Updating...' : `Mark Visible Read (${stats.unread})`}
          </button>
        </div>
        </Card>
      </section>

      {canCreate ? (
        <section
          id="notification-create"
          ref={createSectionRef}
          tabIndex={-1}
          className="scroll-mt-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          <Card>
          <h2 className="mb-3 text-lg font-semibold">Create Notification</h2>
          <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" onSubmit={onCreateNotification}>
            <FormInput
              label="Title"
              required
              value={form.title}
              onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
            />
            <FormInput
              as="select"
              label="Priority"
              value={form.priority}
              onChange={(event) => setForm((prev) => ({ ...prev, priority: event.target.value }))}
            >
              {PRIORITY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </FormInput>
            <FormInput
              as="select"
              label="Scope"
              value={form.scope}
              onChange={(event) => setForm((prev) => ({ ...prev, scope: event.target.value }))}
            >
              {scopeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </FormInput>
            <FormInput
              as="textarea"
              className="sm:col-span-2 xl:col-span-2"
              label="Message"
              required
              value={form.message}
              onChange={(event) => setForm((prev) => ({ ...prev, message: event.target.value }))}
            />
            {canSelectTargetUser ? (
              <FormInput
                as="select"
                label="Target User"
                value={form.target_user_id}
                onChange={(event) => setForm((prev) => ({ ...prev, target_user_id: event.target.value }))}
              >
                <option value="">Global Notification</option>
                {userOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </FormInput>
            ) : null}
            <div className="flex items-end">
              <button type="submit" className="btn-primary w-full" disabled={submitting}>
                {submitting ? 'Creating...' : 'Create'}
              </button>
            </div>
          </form>
          </Card>
        </section>
      ) : null}

      <Card className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Notification Center</h2>
          <div className="flex items-center gap-2">
            <button className="btn-secondary" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - limit))}>
              Prev
            </button>
            {highlightedNotificationId ? (
              <button
                className="btn-secondary"
                onClick={() => {
                  const next = new URLSearchParams(searchParams);
                  next.delete('highlight');
                  setSearchParams(next, { replace: true });
                }}
              >
                Clear Highlight
              </button>
            ) : null}
            <span className="text-xs text-slate-500">skip: {skip}</span>
            <button className="btn-secondary" onClick={() => setSkip(skip + limit)}>
              Next
            </button>
            <select className="input w-24" value={limit} onChange={(event) => setLimit(Number(event.target.value))}>
              {[10, 20, 50].map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loading ? <p className="text-sm text-slate-500">Loading notifications...</p> : null}
        {error ? (
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm text-rose-600">{error}</p>
            <button type="button" className="btn-secondary" onClick={() => loadNotifications(skip, limit, filters)}>
              Retry
            </button>
          </div>
        ) : null}

        <div className="space-y-3">
          {rows.length === 0 && !loading ? (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800/40 dark:text-slate-300">
              No notifications found for the current filters.
            </div>
          ) : null}

          {rows.map((item) => {
            const delivery = deliveryBreakdown(item);
            return (
              <div
                key={item.id}
                id={`notification-card-${item.id}`}
                className={`rounded-2xl border p-4 ${
                  item.is_read
                    ? 'border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900'
                    : 'border-brand-200 bg-brand-50/40 dark:border-brand-700/60 dark:bg-brand-900/10'
                } ${highlightedNotificationId === item.id ? 'ring-2 ring-brand-400 ring-offset-2 ring-offset-white dark:ring-brand-500 dark:ring-offset-slate-950' : ''}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">{item.title}</h3>
                      {item.public_id ? <Badge variant="default">{item.public_id}</Badge> : null}
                      <Badge variant={priorityVariant(item.priority)}>{item.priority || 'normal'}</Badge>
                      <Badge variant={item.is_read ? 'default' : 'info'}>{item.is_read ? 'Read' : 'Unread'}</Badge>
                      <Badge>{item.scope || 'general'}</Badge>
                    </div>
                    <p className="text-sm text-slate-700 dark:text-slate-200">{item.message}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Created {formatTimestamp(item.created_at)}
                      {item.target_user_id ? ` | Target: ${item.target_user_label || userLabelById[item.target_user_id] || item.target_user_id}` : ' | Target: Global'}
                    </p>
                    {delivery.totalRecipients > 0 || delivery.sentCount > 0 || delivery.failedCount > 0 || delivery.skippedCount > 0 ? (
                      <div className="flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                        {delivery.totalRecipients > 0 ? (
                          <span className="rounded-md border border-slate-200 px-2 py-1 dark:border-slate-700">
                            Read {delivery.readCount}/{delivery.totalRecipients}
                          </span>
                        ) : null}
                        {delivery.sentCount > 0 ? (
                          <span className="rounded-md border border-slate-200 px-2 py-1 dark:border-slate-700">
                            Email sent {delivery.sentCount}
                          </span>
                        ) : null}
                        {delivery.failedCount > 0 ? (
                          <span className="rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-rose-700 dark:border-rose-900/60 dark:bg-rose-900/20 dark:text-rose-300">
                            Email failed {delivery.failedCount}
                          </span>
                        ) : null}
                        {delivery.skippedCount > 0 ? (
                          <span className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-amber-700 dark:border-amber-900/60 dark:bg-amber-900/20 dark:text-amber-300">
                            Email skipped {delivery.skippedCount}
                          </span>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                  {!item.is_read ? (
                    <button className="btn-secondary" onClick={() => onMarkRead(item.id)}>
                      Mark Read
                    </button>
                  ) : null}
                  {canManageCommunicationOps ? (
                    <button className="btn-secondary" onClick={() => loadDeliveryDetails(item.id, { openModal: true })}>
                      View delivery
                    </button>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </Card>
      <CommunicationDeliveryModal
        open={deliveryOpen}
        onClose={() => {
          setDeliveryOpen(false);
          setDeliveryError('');
          setRetryingDeliveryTarget('');
        }}
        onRefresh={() => loadDeliveryDetails(deliveryNotificationId)}
        onExport={exportCurrentDeliveryCsv}
        onRetryAllEmail={() => retryDeliveryEmail()}
        onRetryRecipientEmail={(item) => retryDeliveryEmail(item)}
        loading={deliveryLoading || exportingDelivery}
        retryingTarget={retryingDeliveryTarget}
        error={deliveryError}
        details={deliveryDetails}
        title="Notification Delivery"
      />
    </div>
  );
}
