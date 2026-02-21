import { useState, useEffect, useCallback, useRef } from 'react'
import Chat from './Chat'
import AnimatedBackground from './AnimatedBackground'
import Sidebar, { type ChatItem } from './Sidebar'

const STORAGE_KEY = 'policylens_chats'

function loadChats(): ChatItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const data = JSON.parse(raw)
    return Array.isArray(data) ? data : []
  } catch {
    return []
  }
}

function saveChats(chats: ChatItem[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats))
  } catch {
    // ignore
  }
}

function App() {
  const [chats, setChats] = useState<ChatItem[]>(() => loadChats())
  const [currentChatId, setCurrentChatId] = useState<string | null>(null)
  const [currentMessages, setCurrentMessages] = useState<ChatItem['messages']>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const currentChatIdRef = useRef<string | null>(null)

  currentChatIdRef.current = currentChatId

  useEffect(() => {
    saveChats(chats)
  }, [chats])

  const handleNewChat = useCallback(() => {
    currentChatIdRef.current = null
    setCurrentChatId(null)
    setCurrentMessages([])
  }, [])

  const handleSelectChat = useCallback((id: string) => {
    const chat = chats.find((c) => c.id === id)
    if (chat) {
      setCurrentChatId(id)
      setCurrentMessages(chat.messages)
    }
  }, [chats])

  const handleDeleteChat = useCallback((id: string) => {
    setChats((prev) => prev.filter((c) => c.id !== id))
    if (currentChatId === id) {
      currentChatIdRef.current = null
      setCurrentChatId(null)
      setCurrentMessages([])
    }
  }, [currentChatId])

  const handleMessagesChange = useCallback((next: ChatItem['messages']) => {
    setCurrentMessages(next)
    if (next.length === 0) return
    const firstUser = next.find((m) => m.role === 'user')
    const title = firstUser ? firstUser.content.slice(0, 50).trim() || 'New chat' : 'New chat'
    const id = currentChatIdRef.current

    if (id) {
      setChats((prev) =>
        prev.map((c) =>
          c.id === id ? { ...c, messages: next, title: c.messages.length === 0 ? title : c.title } : c
        )
      )
    } else {
      const newId = crypto.randomUUID()
      currentChatIdRef.current = newId
      setCurrentChatId(newId)
      setChats((prev) => [...prev, { id: newId, title, messages: next, createdAt: Date.now() }])
    }
  }, [])

  return (
    <div className="min-h-screen flex flex-col relative">
      <AnimatedBackground />
      <header className="relative z-10 px-4 py-4 sm:px-6 border-b border-zinc-800/50 flex items-center gap-3">
        <button
          type="button"
          onClick={() => setSidebarOpen((o) => !o)}
          className="rounded-lg p-2 text-zinc-400 hover:bg-white/10 hover:text-white transition-colors"
          title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
          aria-label={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {sidebarOpen ? (
              <path d="M15 19l-7-7 7-7" />
            ) : (
              <path d="M9 5l7 7-7 7" />
            )}
          </svg>
        </button>
        <div className="flex items-baseline gap-3">
          <h1 className="font-display text-2xl sm:text-3xl font-semibold tracking-tight text-white">
            PolicyLens
          </h1>
          <span className="text-xs text-zinc-500 font-medium tracking-wide uppercase hidden sm:inline">
            UBC Policy QA
          </span>
        </div>
      </header>
      <div className="relative z-10 flex-1 flex min-h-0">
        {sidebarOpen && (
          <Sidebar
            chats={chats}
            currentChatId={currentChatId}
            onNewChat={handleNewChat}
            onSelectChat={handleSelectChat}
            onDeleteChat={handleDeleteChat}
          />
        )}
        <main className="flex-1 flex flex-col min-h-0 min-w-0 px-4 sm:px-6 py-4 justify-start items-center">
          <Chat messages={currentMessages} onMessagesChange={handleMessagesChange} />
        </main>
      </div>
    </div>
  )
}

export default App
