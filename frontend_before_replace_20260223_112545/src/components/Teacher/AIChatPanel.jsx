import { useMemo } from 'react';

export default function AIChatPanel({
  messages = [],
  inputValue,
  onInputChange,
  onSend,
  onClear,
  sending = false
}) {
  const renderedMessages = useMemo(
    () =>
      messages.map((message, index) => ({
        id: `${message.role}-${message.timestamp || index}-${index}`,
        role: message.role,
        content: message.content,
        timestamp: message.timestamp
      })),
    [messages]
  );

  return (
    <div className="flex h-full min-h-[560px] flex-col rounded-2xl border border-slate-200 bg-white shadow-soft dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800">
        <h2 className="text-lg font-semibold">AI Evaluation Chat</h2>
        <button className="btn-secondary !px-3 !py-1 text-xs" onClick={onClear} disabled={sending}>
          Clear Chat
        </button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {renderedMessages.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Start a conversation with AI to get rubric-aligned grading suggestions.
          </p>
        ) : null}
        {renderedMessages.map((message) => (
          <div
            key={message.id}
            className={`max-w-[92%] rounded-xl px-3 py-2 text-sm ${
              message.role === 'teacher'
                ? 'ml-auto bg-brand-600 text-white'
                : message.role === 'ai'
                  ? 'mr-auto bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100'
                  : 'mr-auto bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200'
            }`}
          >
            <p className="whitespace-pre-wrap">{message.content}</p>
            {message.timestamp ? (
              <p className="mt-1 text-[11px] opacity-75">{new Date(message.timestamp).toLocaleString()}</p>
            ) : null}
          </div>
        ))}
        {sending ? (
          <div className="mr-auto inline-flex items-center gap-2 rounded-xl bg-slate-100 px-3 py-2 text-sm dark:bg-slate-800">
            <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-brand-500 [animation-delay:-0.2s]" />
            <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-brand-500 [animation-delay:-0.1s]" />
            <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-brand-500" />
          </div>
        ) : null}
      </div>

      <form
        className="border-t border-slate-200 p-4 dark:border-slate-800"
        onSubmit={(event) => {
          event.preventDefault();
          onSend();
        }}
      >
        <textarea
          className="input min-h-[84px] w-full resize-y"
          value={inputValue}
          onChange={(event) => onInputChange(event.target.value)}
          placeholder="Ask AI to evaluate, compare with rubric, or suggest marks..."
        />
        <div className="mt-3 flex justify-end">
          <button className="btn-primary !px-4 !py-2" type="submit" disabled={sending || !inputValue?.trim()}>
            {sending ? 'Sending...' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
}
