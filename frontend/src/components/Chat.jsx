import React, { useEffect, useRef, useState } from 'react'

const starters = ['How do I register a patient?', 'Explain the audit trail', 'What can I do in the patient portal?']

export default function Chat({ apiBase = '/api' }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('checking')
  const [error, setError] = useState('')
  const [model, setModel] = useState('')
  const inputRef = useRef(null)
  const feedRef = useRef(null)

  useEffect(() => {
    let active = true
    fetch(`${apiBase}/assistant/health`).then(response => response.ok ? response.json() : Promise.reject()).then(data => { if (active) { setStatus('ready'); setModel(data.models?.[0]?.name || '') } }).catch(() => active && setStatus('offline'))
    return () => { active = false }
  }, [apiBase])

  useEffect(() => { feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' }) }, [messages, loading])

  async function send(value = input) {
    const content = value.trim()
    if (!content || loading) return
    const userMessage = { role: 'user', content }
    const conversation = [...messages, userMessage]
    setMessages(conversation); setInput(''); setLoading(true); setError('')
    try {
      const response = await fetch(`${apiBase}/assistant/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ messages: conversation, ...(model && { model }) }) })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.detail || 'The assistant is unavailable right now.')
      const reply = body.output || body.message?.content || body.response
      if (!reply) throw new Error('The assistant returned an empty response.')
      setMessages(current => [...current, { role: 'assistant', content: reply }]); setStatus('ready')
    } catch (err) { setError(err.message); setStatus('offline') } finally { setLoading(false) }
  }

  return <section className="assistant-card" aria-label="Careflow AI assistant">
    <header className="assistant-header"><div className="assistant-avatar" aria-hidden="true">✦</div><div><h2>Careflow Assistant</h2><p><span className={`status-dot ${status}`} />{status === 'ready' ? 'Private local assistant is ready' : status === 'checking' ? 'Checking local connection…' : 'Local assistant is offline'}</p></div>{messages.length > 0 && <button className="clear-chat" onClick={() => { setMessages([]); setError(''); inputRef.current?.focus() }}>Clear chat</button>}</header>
    <div className="chat-feed" ref={feedRef} aria-live="polite">
      {messages.length === 0 ? <div className="chat-welcome"><div className="welcome-icon">✦</div><h3>How can I help today?</h3><p>I can guide you through Careflow and answer general questions. I cannot access or disclose patient records.</p><div className="starter-list">{starters.map(starter => <button key={starter} onClick={() => send(starter)} disabled={loading}>{starter}</button>)}</div></div> : messages.map((message, index) => <div className={`chat-message ${message.role}`} key={`${message.role}-${index}`}><span>{message.role === 'assistant' ? 'AI' : 'You'}</span><p>{message.content}</p></div>)}
      {loading && <div className="chat-message assistant thinking"><span>AI</span><p><i /><i /><i /></p></div>}
    </div>
    {error && <p className="chat-error" role="alert">{error} Start Ollama, then try again.</p>}
    <div className="chat-composer"><textarea ref={inputRef} value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send() } }} placeholder="Message the assistant…" rows="1" disabled={loading} aria-label="Message the assistant" /><button className="send-button" onClick={() => send()} disabled={!input.trim() || loading} aria-label="Send message">↑</button></div>
    <p className="chat-disclaimer">For urgent medical concerns, contact local emergency services.</p>
  </section>
}
