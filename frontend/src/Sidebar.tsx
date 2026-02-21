export type ChatItem = {
  id: string
  title: string
  messages: { role: 'user' | 'assistant'; content: string }[]
  createdAt: number
}

type Props = {
  chats: ChatItem[]
  currentChatId: string | null
  onNewChat: () => void
  onSelectChat: (id: string) => void
  onDeleteChat: (id: string) => void
}

export default function Sidebar({ chats, currentChatId, onNewChat, onSelectChat, onDeleteChat }: Props) {
  const sorted = [...chats].sort((a, b) => b.createdAt - a.createdAt)

  return (
    <aside className="w-60 shrink-0 flex flex-col border-r border-zinc-800/80 bg-zinc-950/60 backdrop-blur-sm">
      <button
        type="button"
        onClick={onNewChat}
        className="m-3 rounded-lg border border-white/20 bg-white/10 px-4 py-2.5 text-sm font-medium text-zinc-200 hover:bg-white/15 transition-colors flex items-center gap-2"
      >
        <span className="text-lg">+</span>
        New chat
      </button>
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        <p className="px-2 py-1 text-xs font-medium text-zinc-500 uppercase tracking-wider">Previous chats</p>
        <ul className="space-y-0.5 mt-1">
          {sorted.map((chat) => (
            <li key={chat.id} className="group flex items-center gap-0.5 rounded-lg hover:bg-white/5">
              <button
                type="button"
                onClick={() => onSelectChat(chat.id)}
                className={`flex-1 min-w-0 rounded-lg px-3 py-2.5 text-left text-sm truncate transition-colors ${
                  currentChatId === chat.id
                    ? 'bg-white/15 text-white'
                    : 'text-zinc-400 hover:bg-white/10 hover:text-zinc-200'
                }`}
                title={chat.title}
              >
                {chat.title || 'New chat'}
              </button>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onDeleteChat(chat.id) }}
                className="shrink-0 rounded p-1.5 text-zinc-500 hover:bg-red-500/20 hover:text-red-400 transition-colors"
                title="Delete chat"
                aria-label="Delete chat"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                  <line x1="10" y1="11" x2="10" y2="17" />
                  <line x1="14" y1="11" x2="14" y2="17" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
        {sorted.length === 0 && (
          <p className="px-2 py-4 text-zinc-600 text-sm">No previous chats yet.</p>
        )}
      </div>
    </aside>
  )
}
