import { useState, useRef, useEffect } from 'react'

type Message = { role: 'user' | 'assistant'; content: string }

const API_BASE = '/api'
const COURSE_OPTIONS = ['MDS', 'CPSC 330']

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [course, setCourse] = useState(COURSE_OPTIONS[0])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    setInput('')
    setError(null)
    setMessages((m) => [...m, { role: 'user', content: text }])
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text }),
      })
      if (!res.ok) throw new Error(`Request failed: ${res.status}`)
      const data = await res.json()
      const reply = data.refused
        ? (data.refusal_reason || 'No answer available.')
        : (data.answer || '')
      const withCitations = data.citations?.length
        ? `${reply}\n\nSources: ${data.citations.map((c: { source?: string }) => c.source).filter(Boolean).join(', ')}`
        : reply
      setMessages((m) => [...m, { role: 'assistant', content: withCitations }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  const isExpanded = messages.length > 0

  return (
    <div
      className={`flex flex-col h-full rounded-xl bg-black/20 backdrop-blur-sm overflow-hidden transition-all duration-300 ease-out ${
        isExpanded ? 'min-h-[70vh] w-full max-w-4xl' : 'w-full max-w-md'
      }`}
    >
      <div
        className={`overflow-y-auto space-y-5 p-4 shrink-0 transition-all duration-300 ease-out ${
          isExpanded ? 'max-h-[60vh] opacity-100' : 'max-h-0 opacity-0 overflow-hidden p-0'
        }`}
      >
        {messages.length === 0 && (
          <p className="text-zinc-500 text-center py-16 text-lg">Ask a question about UBC policies.</p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-5 py-3 text-lg leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white rounded-br-md'
                  : 'bg-green-600 text-white rounded-bl-md'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-green-600 text-white rounded-2xl rounded-bl-md px-5 py-3 text-lg">
              ...
            </div>
          </div>
        )}
        {error && (
          <p className="text-red-400 text-base">{error}</p>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 p-3 shrink-0">
        <select
          value={course}
          onChange={(e) => setCourse(e.target.value)}
          className="rounded-lg border border-zinc-700 bg-zinc-800/80 text-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-600 shrink-0"
          disabled={loading}
        >
          {COURSE_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your question..."
          className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800/80 text-zinc-100 px-3 py-2 text-sm placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-zinc-600"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-zinc-700 text-zinc-100 px-3 py-2 text-sm hover:bg-zinc-600 disabled:opacity-50 transition-colors shrink-0"
        >
          Send
        </button>
      </form>
    </div>
  )
}
