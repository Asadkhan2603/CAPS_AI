const MOCK_MESSAGES = [
  { id: 1, sender: 'Teacher', text: 'Welcome to the new communication hub.', time: '09:10' },
  { id: 2, sender: 'Student', text: 'Can we get clarification on grading rubric?', time: '09:14' },
  { id: 3, sender: 'Teacher', text: 'Yes, I will publish details in announcements.', time: '09:17' }
];

export default function ChatWindow({ restrictedComposer }) {
  return (
    <section className="flex min-h-[420px] flex-1 flex-col rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Chat Window</h3>

      <div className="flex-1 space-y-2 overflow-y-auto">
        {MOCK_MESSAGES.map((message) => (
          <div key={message.id} className="rounded-xl border border-slate-200 p-2 text-sm dark:border-slate-800">
            <p className="font-medium text-slate-900 dark:text-slate-100">{message.sender}</p>
            <p className="text-slate-600 dark:text-slate-300">{message.text}</p>
            <p className="text-[11px] text-slate-400">{message.time}</p>
          </div>
        ))}
      </div>

      <div className="mt-3 border-t border-slate-200 pt-3 dark:border-slate-800">
        <textarea
          className="input min-h-20"
          placeholder={restrictedComposer ? 'Message creation is restricted for your role.' : 'Type a message...'}
          disabled={restrictedComposer}
        />
        <button className="btn-primary mt-2" type="button" disabled={restrictedComposer}>
          Send
        </button>
      </div>
    </section>
  );
}
