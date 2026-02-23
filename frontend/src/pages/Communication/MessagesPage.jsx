import { useState } from 'react';
import CommunicationTabs from '../../components/communication/CommunicationTabs';
import ConversationList from '../../components/communication/ConversationList';
import ChatWindow from '../../components/communication/ChatWindow';
import { useAuth } from '../../hooks/useAuth';

export default function MessagesPage() {
  const { user } = useAuth();
  const [activeId, setActiveId] = useState('t1');

  return (
    <div className="page-fade">
      <div className="mx-auto max-w-5xl">
        <CommunicationTabs />

        <div className="mb-4">
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Messages</h1>
          <p className="text-sm text-slate-500">Future-ready messaging architecture for direct and group communication.</p>
        </div>

        <div className="flex flex-col gap-3 lg:flex-row">
          <ConversationList activeId={activeId} onSelect={setActiveId} />
          <ChatWindow restrictedComposer={user?.role === 'student'} />
        </div>
      </div>
    </div>
  );
}
