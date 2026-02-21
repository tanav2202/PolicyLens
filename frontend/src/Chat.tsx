import { useState, useRef, useEffect } from 'react'

type Message = { role: 'user' | 'assistant'; content: string }

const API_BASE = '/api'

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [courses, setCourses] = useState<string[]>([])
  const [course, setCourse] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
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
    setMessages((m) => [...m, { role: 'user', content: text }, { role: 'assistant', content: '' }])
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/query/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
            const sources = payload.citations.map((c: { source?: string }) => c.source).filter(Boolean).join(', ')
            setMessages((m) => {
              const next = [...m]
              const last = next[next.length - 1]
              if (last?.role === 'assistant')
                next[next.length - 1] = { ...last, content: last.content + `\n\nSources: ${sources}` }
              return next
            })
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
      setMessages((m) => (m.length && m[m.length - 1].role === 'assistant' && !m[m.length - 1].content ? m.slice(0, -1) : m))
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
          disabled={loading || courses.length === 0}
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
