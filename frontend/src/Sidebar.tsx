import { motion } from 'framer-motion'
import { MessageSquarePlus, MessageSquare, Trash2 } from 'lucide-react'

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
    <motion.aside
      initial={false}
      className="w-60 shrink-0 flex flex-col border-r border-zinc-800/80 bg-zinc-950/60 backdrop-blur-sm"
    >
      <motion.button
        type="button"
        onClick={onNewChat}
        className="m-3 rounded-lg border border-white/20 bg-white/10 px-4 py-2.5 text-sm font-medium text-zinc-200 hover:bg-white/15 transition-colors flex items-center gap-2"
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <MessageSquarePlus className="h-4 w-4 shrink-0" />
        New chat
      </motion.button>
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        <p className="px-2 py-1 text-xs font-medium text-zinc-500 uppercase tracking-wider">Previous chats</p>
        <ul className="space-y-0.5 mt-1">
          {sorted.map((chat, i) => (
            <motion.li
              key={chat.id}
              layout
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03, duration: 0.2 }}
              className="group flex items-center gap-0.5 rounded-lg hover:bg-white/5"
            >
              <button
                type="button"
                onClick={() => onSelectChat(chat.id)}
                className={`flex-1 min-w-0 rounded-lg px-3 py-2.5 text-left text-sm truncate transition-colors flex items-center gap-2 ${
                  currentChatId === chat.id
                    ? 'bg-white/15 text-white'
                    : 'text-zinc-400 hover:bg-white/10 hover:text-zinc-200'
                }`}
                title={chat.title}
              >
                <MessageSquare className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
                {chat.title || 'New chat'}
              </button>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onDeleteChat(chat.id) }}
                className="shrink-0 rounded p-1.5 text-zinc-500 hover:bg-red-500/20 hover:text-red-400 transition-colors"
                title="Delete chat"
                aria-label="Delete chat"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </motion.li>
          ))}
        </ul>
        {sorted.length === 0 && (
          <p className="px-2 py-4 text-zinc-600 text-sm">No previous chats yet.</p>
        )}
      </div>
    </motion.aside>
  )
}
