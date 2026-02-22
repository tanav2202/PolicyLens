import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, BookOpen, AlertCircle, Loader2, FileDown, ChevronDown } from 'lucide-react'

export type Message = { role: 'user' | 'assistant'; content: string; intent?: string; slots_used?: Record<string, unknown> }

const API_BASE = '/api'
const COURSE_NOT_FOUND = 'Course not found'
const DEFAULT_COURSES = ['MDS', 'CPSC 330']

const markdownComponents: import('react-markdown').Components = {
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  h1: ({ children }) => <h1 className="text-xl font-semibold text-zinc-100 mt-4 mb-2 first:mt-0">{children}</h1>,
  h2: ({ children }) => <h2 className="text-lg font-semibold text-zinc-100 mt-3 mb-1.5 first:mt-0">{children}</h2>,
  h3: ({ children }) => <h3 className="text-base font-semibold text-zinc-200 mt-2 mb-1 first:mt-0">{children}</h3>,
  ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-0.5 text-zinc-300">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-0.5 text-zinc-300">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  code: ({ className, children, ...props }) => {
    const isInline = !className
    if (isInline) {
      return <code className="px-1.5 py-0.5 rounded bg-zinc-700/80 text-zinc-200 text-[0.9em] font-mono" {...props}>{children}</code>
    }
    return <code className={`block p-3 rounded-lg bg-zinc-800/90 text-zinc-200 text-sm font-mono overflow-x-auto ${className || ''}`} {...props}>{children}</code>
  },
  pre: ({ children }) => <pre className="mb-2 rounded-lg overflow-hidden">{children}</pre>,
  a: ({ href, children }) => <a href={href ?? '#'} target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2">{children}</a>,
  blockquote: ({ children }) => <blockquote className="border-l-2 border-zinc-600 pl-3 my-2 text-zinc-400 italic">{children}</blockquote>,
  strong: ({ children }) => <strong className="font-semibold text-zinc-200">{children}</strong>,
  em: ({ children }) => <em className="italic text-zinc-300">{children}</em>,
  hr: () => <hr className="border-zinc-600 my-3" />,
  table: ({ children }) => <div className="overflow-x-auto my-2"><table className="min-w-full border border-zinc-600 rounded-lg border-collapse">{children}</table></div>,
  thead: ({ children }) => <thead className="bg-zinc-800/80">{children}</thead>,
  tbody: ({ children }) => <tbody className="text-zinc-300">{children}</tbody>,
  tr: ({ children }) => <tr className="border-b border-zinc-600 last:border-0">{children}</tr>,
  th: ({ children }) => <th className="text-left px-3 py-2 text-zinc-200 font-medium">{children}</th>,
  td: ({ children }) => <td className="px-3 py-2">{children}</td>,
}

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
  const [extractCourseName, setExtractCourseName] = useState('')
  const [extractUrl, setExtractUrl] = useState('')
  const [extractLoading, setExtractLoading] = useState(false)
  const [extractMessage, setExtractMessage] = useState<string | null>(null)
  const [streamingReply, setStreamingReply] = useState<string | null>(null)
  const draftRef = useRef('')
  const ignoreNextChangeRef = useRef(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const courseOptions = courses.length > 0 ? [...courses, COURSE_NOT_FOUND] : [...DEFAULT_COURSES, COURSE_NOT_FOUND]

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingReply])

  function fetchCourses() {
    return fetch(`${API_BASE}/courses`)
      .then((r) => r.json())
      .then((d) => {
        const raw = Array.isArray(d.courses) ? d.courses : (d.courses ? [d.courses] : [])
        const list = raw.filter((c: string) => c && String(c).trim() && c !== COURSE_NOT_FOUND).map((c: string) => String(c).trim())
        const toSet = list.length > 0 ? list : DEFAULT_COURSES
        setCourses(toSet)
        if (course === '' || course === COURSE_NOT_FOUND) setCourse(toSet[0])
      })
      .catch(() => {
        setCourses(DEFAULT_COURSES)
        if (course === '' || course === COURSE_NOT_FOUND) setCourse(DEFAULT_COURSES[0])
      })
  }

  useEffect(() => {
    fetchCourses()
  }, [])

  async function handleExtract(e: React.FormEvent) {
    e.preventDefault()
    const name = extractCourseName.trim()
    const url = extractUrl.trim()
    if (!name || !url) {
      setExtractMessage('Please enter both course name and URL.')
      return
    }
    setExtractMessage(null)
    setExtractLoading(true)
    try {
      const res = await fetch(`${API_BASE}/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ course_name: name, url }),
      })
      const data = await res.json()
      if (data.ok) {
        setExtractMessage(data.message || 'Extraction started. Refreshing course list.')
        setExtractCourseName('')
        setExtractUrl('')
        fetchCourses()
      } else {
        setExtractMessage(data.error || 'Extraction failed.')
      }
    } catch (err) {
      setExtractMessage(err instanceof Error ? err.message : 'Request failed.')
    } finally {
      setExtractLoading(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return
    const courseForQuery = course === COURSE_NOT_FOUND ? undefined : course

    setInput('')
    setError(null)
    setStreamingReply(null)
    setHistoryIndex(-1)
    setInputHistory((h) => (h[h.length - 1] === text ? h : [...h, text]))
    const userMsg: Message = { role: 'user', content: text }
    onMessagesChange([...messages, userMsg])
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/query/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text, course: courseForQuery || undefined }),
      })
      if (!res.ok) throw new Error(`Request failed: ${res.status}`)
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) throw new Error('No response body')
      let buffer = ''
      let content = ''
      let doneIntent: string | undefined
      let doneSlots: Record<string, unknown> | undefined
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'chunk' && typeof data.content === 'string') {
              content += data.content
              setStreamingReply(content)
            } else if (data.type === 'citations' && Array.isArray(data.citations)) {
              const sources = data.citations.map((c: { source?: string }) => c.source).filter(Boolean).join(', ')
              if (sources) content += `\n\nSources: ${sources}`
              setStreamingReply(content)
            } else if (data.type === 'done') {
              doneIntent = data.intent
              doneSlots = data.slots_used
            }
          } catch (_) {}
        }
      }
      onMessagesChange([...messages, userMsg, { role: 'assistant', content, intent: doneIntent, slots_used: doneSlots }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
      onMessagesChange([...messages, userMsg, { role: 'assistant', content: 'Sorry, something went wrong.' }])
    } finally {
      setLoading(false)
      setStreamingReply(null)
    }
  }

  const isExpanded = messages.length > 0
  const displayMessages: Message[] =
    loading && streamingReply !== null ? [...messages, { role: 'assistant', content: streamingReply }] : messages

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
    <motion.div
      layout
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={`flex flex-col rounded-2xl overflow-hidden max-h-[85vh] w-full min-w-0 ${
        isExpanded ? 'max-w-4xl' : 'max-w-md'
      } bg-zinc-900/40 backdrop-blur-xl shadow-glass border border-zinc-700/50`}
    >
      <motion.div
        layout
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className={`flex-1 min-h-0 overflow-y-auto overflow-x-hidden space-y-4 p-5 ${isExpanded ? 'opacity-100' : 'max-h-0 opacity-0 overflow-hidden p-0'}`}
      >
        <AnimatePresence mode="wait">
          {displayMessages.length === 0 && (
            <motion.div
              key="empty"
              className="text-center py-20"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
            >
              <p className="text-zinc-400 text-lg font-medium">Ask a question about UBC policies.</p>
              <p className="text-zinc-600 text-sm mt-2">Due dates, instructors, links, and more.</p>
            </motion.div>
          )}
        </AnimatePresence>
        {displayMessages.map((msg, i) => (
          <motion.div
            key={`${i}-${msg.role}-${msg.content.slice(0, 20)}`}
            layout
            className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
          >
            <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'user' ? (
                <motion.div
                  className="max-w-[85%] rounded-2xl rounded-br-md px-4 py-3 text-[15px] leading-relaxed chat-message bg-white/5 backdrop-blur-md text-white"
                  whileHover={{ scale: 1.01 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                >
                  {msg.content}
                </motion.div>
              ) : (
                <motion.div
                  className="max-w-[90%] text-[15px] leading-relaxed chat-message chat-markdown text-zinc-300"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                    {msg.content}
                  </ReactMarkdown>
                </motion.div>
              )}
            </div>
            {msg.role === 'assistant' && msg.intent === 'due_date' && course && (
              <a
                href={
                  msg.slots_used?.assessment
                    ? `${API_BASE}/export/ics?course=${encodeURIComponent(course)}&assessments=${encodeURIComponent(String(msg.slots_used.assessment))}`
                    : `${API_BASE}/export/ics?course=${encodeURIComponent(course)}`
                }
                download="policy_dates.ics"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 text-sm text-zinc-400 hover:text-zinc-200 underline"
              >
                Add to Calendar
              </a>
            )}
          </motion.div>
        ))}
        {loading && (streamingReply === null || streamingReply === '') && (
          <motion.div
            className="flex items-center gap-2 text-zinc-500 text-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <Loader2 className="h-4 w-4 animate-spin shrink-0" />
            <span>Thinking…</span>
          </motion.div>
        )}
        {error && (
          <motion.p
            className="flex items-center gap-2 text-red-400/90 text-sm font-medium"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </motion.p>
        )}
        <div ref={bottomRef} />
      </motion.div>

      <div className="shrink-0 min-w-0 border-t border-white/10 bg-white/5 backdrop-blur-lg p-4 space-y-3">
        {course === COURSE_NOT_FOUND && (
          <form onSubmit={handleExtract} className="flex flex-col gap-2 p-3 rounded-xl bg-white/5 border border-white/10">
            <p className="text-zinc-400 text-sm font-medium">Add a course by extracting policy from a URL</p>
            <input
              type="text"
              value={extractCourseName}
              onChange={(e) => setExtractCourseName(e.target.value)}
              placeholder="Course name (e.g. CPSC 330)"
              className="rounded-xl border border-white/20 bg-white/10 backdrop-blur-sm text-zinc-100 px-4 py-2.5 text-sm placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              disabled={extractLoading}
            />
            <input
              type="url"
              value={extractUrl}
              onChange={(e) => setExtractUrl(e.target.value)}
              placeholder="URL for course policies"
              className="rounded-xl border border-white/20 bg-white/10 backdrop-blur-sm text-zinc-100 px-4 py-2.5 text-sm placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              disabled={extractLoading}
            />
            <div className="flex items-center gap-2">
              <motion.button
                type="submit"
                disabled={extractLoading}
                className="rounded-xl bg-indigo-500/80 text-white px-4 py-2 text-sm font-semibold hover:bg-indigo-600 disabled:opacity-50 flex items-center gap-2"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {extractLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileDown className="h-4 w-4" />}
                {extractLoading ? 'Extracting…' : 'Extract policy'}
              </motion.button>
              {extractMessage && (
                <span className="text-zinc-400 text-sm">{extractMessage}</span>
              )}
            </div>
          </form>
        )}
        <form onSubmit={handleSubmit} className="flex gap-2 min-w-0 w-full max-w-full items-stretch">
          <div className="relative shrink-0 w-[140px] min-w-[120px]">
            <BookOpen className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500 pointer-events-none" />
            <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500 pointer-events-none" />
            <select
              value={course}
              onChange={(e) => setCourse(e.target.value)}
              className="w-full rounded-xl border border-white/20 bg-white/10 backdrop-blur-sm text-zinc-200 pl-9 pr-9 py-2.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 appearance-none cursor-pointer"
              disabled={loading}
            >
              {courseOptions.length === 0 ? (
                <option>Loading…</option>
              ) : (
                courseOptions.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))
              )}
            </select>
          </div>
          <input
            type="text"
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleInputKeyDown}
            placeholder="Ask about due dates, instructors, links…"
            className="flex-1 min-w-0 w-0 rounded-xl border border-white/20 bg-white/10 backdrop-blur-sm text-zinc-100 px-4 py-2.5 text-sm placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50"
            disabled={loading}
          />
          <motion.button
            type="submit"
            disabled={loading || course === COURSE_NOT_FOUND}
            className="rounded-xl bg-white/15 backdrop-blur-sm border border-white/20 text-white px-4 py-2.5 text-sm font-semibold hover:bg-white/25 disabled:opacity-50 transition-colors shrink-0 min-w-[88px] flex items-center justify-center gap-1.5"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
          >
            <Send className="h-4 w-4 shrink-0" />
            <span>Send</span>
          </motion.button>
        </form>
      </div>
    </motion.div>
  )
}
