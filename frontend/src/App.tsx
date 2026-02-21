import Chat from './Chat'
import AnimatedBackground from './AnimatedBackground'

function App() {
  return (
    <div className="min-h-screen flex flex-col relative">
      <AnimatedBackground />
      <header className="relative z-10 border-b border-zinc-800 px-6 py-5">
        <h1 className="font-display text-4xl font-semibold tracking-tight text-zinc-100">PolicyLens</h1>
      </header>
      <main className="relative z-10 flex-1 flex flex-col min-h-0 max-w-4xl w-full mx-auto p-6 items-center">
        <Chat />
      </main>
    </div>
  )
}

export default App
