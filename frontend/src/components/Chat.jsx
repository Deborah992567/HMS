import React, {useState} from 'react'

export default function Chat(){
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function send(){
    if(!input.trim()) return
    const userMsg = {role: 'user', content: input}
    setMessages(m=>[...m, userMsg])
    setInput('')
    setLoading(true)
    setError(null)
    try{
      const res = await fetch('/api/assistant/chat', {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({messages: [...messages, userMsg]} )})
      if(!res.ok) throw new Error('Assistant unavailable')
      const body = await res.json()
      // attempt to extract text
      const text = body.output || body.text || (body.raw ? body.raw : JSON.stringify(body))
      setMessages(m=>[...m, {role: 'assistant', content: text}])
    }catch(err){
      setError(err.message)
      setMessages(m=>[...m, {role:'assistant', content: 'Assistant error: '+err.message}])
    }finally{
      setLoading(false)
    }
  }

  return (
    <section className="max-w-2xl">
      <h2 className="text-lg font-medium mb-2">AI Assistant (local)</h2>
      <div className="border rounded p-3 mb-2 bg-white" style={{minHeight:200}}>
        {messages.length===0 && <div className="text-slate-500">No messages yet — say hello.</div>}
        {messages.map((m,i)=> (
          <div key={i} className={`mb-2 ${m.role==='assistant' ? 'text-slate-800' : 'text-sky-700'}`}>
            <strong className="capitalize mr-2">{m.role}:</strong>
            <span>{m.content}</span>
          </div>
        ))}
      </div>
      {error && <div className="text-red-600 mb-2">{error}</div>}
      <div className="flex gap-2">
        <input value={input} onChange={e=>setInput(e.target.value)} className="flex-1 p-2 border rounded" placeholder="Ask something..." />
        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={send} disabled={loading}>{loading ? '...' : 'Send'}</button>
      </div>
    </section>
  )
}
