import { useState, useRef, useEffect } from 'react'

export type Message = { role: 'user' | 'assistant'; content: string }

const API_BASE = '/api'

type Props = {
  messages: Message[]
  onMessagesChange: (messages: Message[]) => void
}

export default function Chat({ messages, onMessagesChange }: Props) {
  const [input, setInput] = useState('')
  const [courses, setCourses] = useState<string[]>([])
  const [course, setCourse] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [inputHistory, setInputHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const draftRef = useRef('')
  const ignoreNextChangeRef = useRef(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    fetch(`${API_BASE}/courses`)
      .then((r) => r.json())
      .then((d) => {
        const list = d.courses || []
        setCourses(list)
        if (list.length > 0 && !course) setCourse(list[0])
      })
      .catch(() => setCourses([]))
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    setInput('')
    setError(null)
<<<<<<< Updated upstream
    setMessages((m) => [...m, { role: 'user', content: text }, { role: 'assistant', content: '' }])
=======
    setHistoryIndex(-1)
    setInputHistory((h) => (h[h.length - 1] === text ? h : [...h, text]))
    const userMsg: Message = { role: 'user', content: text }
    onMessagesChange([...messages, userMsg])
>>>>>>> Stashed changes
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/query/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
<<<<<<< Updated upstream
        body: JSON.stringify({ question: text, course: course || undefined }),
      })
      if (!res.ok) throw new Error(`Request failed: ${res.status}`)
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) throw new Error('No response body')

      let buffer = ''
      const processData = (dataLine: string) => {
        if (!dataLine.startsWith('data: ')) return
        try {
          const payload = JSON.parse(dataLine.slice(6))
          if (payload.type === 'chunk') {
            setMessages((m) => {
              const next = [...m]
              const last = next[next.length - 1]
              if (last?.role === 'assistant')
                next[next.length - 1] = { ...last, content: last.content + (payload.content ?? '') }
              return next
            })
          } else if (payload.type === 'citations' && payload.citations?.length) {
            // Citations kept in DB/API only; do not show sources in user-facing output
          }
        } catch {
          // ignore parse errors for partial chunks
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop() ?? ''
        for (const event of events) {
          const dataLine = event.split('\n').find((l) => l.startsWith('data: '))
          if (dataLine) processData(dataLine)
        }
      }
      if (buffer.trim()) {
        const dataLine = buffer.split('\n').find((l) => l.startsWith('data: '))
        if (dataLine) processData(dataLine)
      }
=======
        body: JSON.stringify({ question: text, course }),
      })
      if (!res.ok) throw new Error(`Request failed: ${res.status}`)
      const data = await res.json()
      const reply = data.refused
        ? (data.refusal_reason || 'No answer available.')
        : (data.answer || '')
      const withCitations = data.citations?.length
        ? `${reply}\n\nSources: ${data.citations.map((c: { source?: string }) => c.source).filter(Boolean).join(', ')}`
        : reply
      onMessagesChange([...messages, userMsg, { role: 'assistant', content: withCitations }])
>>>>>>> Stashed changes
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
      setMessages((m) => (m.length && m[m.length - 1].role === 'assistant' && !m[m.length - 1].content ? m.slice(0, -1) : m))
    } finally {
      setLoading(false)
    }
  }

  const isExpanded = messages.length > 0

  function handleInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (inputHistory.length === 0) return
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (historyIndex === -1) draftRef.current = input
      const next = historyIndex === -1 ? inputHistory.length - 1 : Math.max(0, historyIndex - 1)
      setHistoryIndex(next)
      ignoreNextChangeRef.current = true
      setInput(inputHistory[next])
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIndex === -1) return
      const next = historyIndex + 1
      if (next >= inputHistory.length) {
        setHistoryIndex(-1)
        setInput(draftRef.current)
      } else {
        setHistoryIndex(next)
        setInput(inputHistory[next])
      }
      ignoreNextChangeRef.current = true
    }
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (ignoreNextChangeRef.current) {
      ignoreNextChangeRef.current = false
      return
    }
    setHistoryIndex(-1)
    draftRef.current = e.target.value
    setInput(e.target.value)
  }

  return (
    <div
      className={`flex flex-col rounded-2xl overflow-hidden transition-all duration-300 ease-out max-h-[85vh] ${
        isExpanded ? 'w-full max-w-4xl overflow-y-auto' : 'w-full max-w-md'
      } bg-zinc-900/40 backdrop-blur-xl shadow-glass border border-zinc-700/50`}
    >
      <div
        className={`space-y-4 p-5 transition-all duration-300 ease-out ${
          isExpanded ? 'opacity-100' : 'max-h-0 opacity-0 overflow-hidden p-0'
        }`}
      >
        {messages.length === 0 && (
          <div className="text-center py-20">
            <p className="text-zinc-400 text-lg font-medium">Ask a question about UBC policies.</p>
            <p className="text-zinc-600 text-sm mt-2">Due dates, instructors, links, and more.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'user' ? (
              <div className="max-w-[85%] rounded-2xl rounded-br-md px-4 py-3 text-[15px] leading-relaxed chat-message bg-white/5 backdrop-blur-md text-white">
                {msg.content}
              </div>
            ) : (
              <div className="max-w-[90%] text-[15px] leading-relaxed chat-message text-zinc-300">
                {msg.content}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <p className="text-zinc-500 text-sm">Thinking…</p>
        )}
        {error && (
          <p className="text-red-400/90 text-sm font-medium">{error}</p>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 p-4 shrink-0 border-t border-white/10 bg-white/5 backdrop-blur-lg">
        <select
          value={course}
          onChange={(e) => setCourse(e.target.value)}
<<<<<<< Updated upstream
          className="rounded-lg border border-zinc-700 bg-zinc-800/80 text-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-600 shrink-0"
          disabled={loading || courses.length === 0}
=======
          className="rounded-xl border border-white/20 bg-white/10 backdrop-blur-sm text-zinc-200 px-4 py-2.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 shrink-0"
          disabled={loading}
>>>>>>> Stashed changes
        >
          {courses.length === 0 ? (
            <option>No courses</option>
          ) : (
            courses.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))
          )}
        </select>
        <input
          type="text"
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleInputKeyDown}
          placeholder="Ask about due dates, instructors, links…"
          className="flex-1 rounded-xl border border-white/20 bg-white/10 backdrop-blur-sm text-zinc-100 px-4 py-2.5 text-sm placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-white/15 backdrop-blur-sm border border-white/20 text-white px-5 py-2.5 text-sm font-semibold hover:bg-white/25 disabled:opacity-50 transition-colors shrink-0"
        >
          Send
        </button>
      </form>
    </div>
  )
}
