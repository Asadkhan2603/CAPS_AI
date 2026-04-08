import { Link } from 'react-router-dom';
import CommunicationTabs from '../../components/communication/CommunicationTabs';

export default function MessagesPage() {
  return (
    <div className="page-fade">
      <div className="mx-auto max-w-5xl">
        <CommunicationTabs />

        <div className="mb-4">
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Messages</h1>
          <p className="text-sm text-slate-500">This surface is intentionally marked as planned until real thread, message, and delivery APIs are shipped.</p>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.3fr_0.9fr]">
          <section className="rounded-3xl border border-amber-200 bg-amber-50 p-6 dark:border-amber-900/50 dark:bg-amber-950/25">
            <div className="inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
              UI Placeholder Only
            </div>
            <h2 className="mt-4 text-xl font-semibold text-slate-900 dark:text-white">Direct messaging is not live yet</h2>
            <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-200">
              The old mock inbox overpromised a working chat system. This page now stays visible as roadmap context only, so users are not encouraged to expect saved conversations or message delivery.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to="/communication/announcements" className="btn-primary">
                Use Announcements
              </Link>
              <Link to="/notifications" className="btn-secondary">
                Open Notifications
              </Link>
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Planned delivery phases</h3>
            <div className="mt-4 space-y-3 text-sm text-slate-700 dark:text-slate-200">
              <div className="rounded-2xl border border-slate-200 p-3 dark:border-slate-800">
                <p className="font-semibold">Phase 1</p>
                <p className="mt-1 text-slate-500">Thread list and message history backed by real APIs.</p>
              </div>
              <div className="rounded-2xl border border-slate-200 p-3 dark:border-slate-800">
                <p className="font-semibold">Phase 2</p>
                <p className="mt-1 text-slate-500">Send, retry, and delivery receipt states.</p>
              </div>
              <div className="rounded-2xl border border-slate-200 p-3 dark:border-slate-800">
                <p className="font-semibold">Phase 3</p>
                <p className="mt-1 text-slate-500">Role-aware direct messages and moderated group channels.</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
