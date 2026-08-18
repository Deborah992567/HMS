import React, {useEffect, useState} from 'react'
import Header from './components/Header'
import EHRForm from './components/EHRForm'
import PrescriptionForm from './components/PrescriptionForm'
import ConsentForm from './components/ConsentForm'
import Receipts from './components/Receipts'
import Toasts from './components/Toasts'

const apiBase = import.meta.env.VITE_API_BASE || '/api'

function apiFetch(path, opts = {}){
  const token = localStorage.getItem('token')
  const headers = opts.headers || {}
  if(token){ headers['Authorization'] = `Bearer ${token}` }
  return fetch(`${apiBase}${path}`, {...opts, headers})
}

function App(){
  const [page, setPage] = useState('home')
  const [chain, setChain] = useState(null)
  const [billingId, setBillingId] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [patients, setPatients] = useState([])
  const [ehrs, setEhrs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [receipts, setReceipts] = useState([])
  const [toasts, setToasts] = useState([])

  function showToast(message, type='info'){
    const id = Date.now() + Math.random()
    setToasts(t=>[...t, {id, message, type}])
  }

  function removeToast(id){ setToasts(t => t.filter(x => x.id !== id)) }

  useEffect(()=>{ loadChain() }, [])

  async function login(e){
    e.preventDefault()
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    const res = await fetch(`${apiBase}/token`, {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body: form.toString()})
    if(!res.ok){ showToast('Login failed', 'error'); return }
    const body = await res.json()
    localStorage.setItem('token', body.access_token)
    showToast('Logged in', 'success')
  }

  async function loadChain(){
    try{
      setError(null)
      setLoading(true)
      const res = await fetch(`${apiBase}/blockchain/chain`)
      if(!res.ok) throw new Error('Failed to load chain')
      setChain(await res.json())
    }catch(err){ setError(err.message) }
    finally{ setLoading(false) }
  }

  async function simulatePayment(e){
    e.preventDefault()
    if(!billingId) return showToast('Enter billing id', 'error')
    const res = await apiFetch('/payments/simulate', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({billing_id: Number(billingId)})})
    const body = await res.json()
    showToast(body.message || 'Payment simulated', 'success')
    loadChain()
  }

  async function loadPatients(){
    try{
      setError(null)
      setLoading(true)
      const res = await apiFetch('/patients/')
      if(!res.ok) throw new Error('Failed to load patients')
      setPatients(await res.json())
      setPage('patients')
    }catch(err){ setError(err.message) }
    finally{ setLoading(false) }
  }

  async function loadEHRs(patientId){
    try{
      setError(null)
      setLoading(true)
      const res = await apiFetch(`/patients/${patientId}/ehr`)
      if(!res.ok) throw new Error('Failed to load EHRs')
      setEhrs(await res.json())
      setPage('ehrs')
    }catch(err){ setError(err.message) }
    finally{ setLoading(false) }
  }

  async function loadReceipts(){
    try{
      setError(null)
      setLoading(true)
      const res = await apiFetch('/receipts/')
      if(!res.ok) throw new Error('Failed to load receipts')
      setReceipts(await res.json())
      setPage('receipts')
    }catch(err){ setError(err.message) }
    finally{ setLoading(false) }
  }

  function logout(){ localStorage.removeItem('token'); showToast('Logged out','info') }

  return (
    <div className="app container mx-auto p-4">
      <Header onNav={p=>{ if(p==='patients') loadPatients(); else setPage(p)}} />

      {page === 'home' && (
        <section className="max-w-md">
          <h2 className="text-lg font-medium mb-2">Login</h2>
          <form onSubmit={login} className="space-y-2">
            <input placeholder="email" value={email} onChange={e=>setEmail(e.target.value)} className="w-full p-2 border rounded" />
            <input placeholder="password" type="password" value={password} onChange={e=>setPassword(e.target.value)} className="w-full p-2 border rounded" />
            <button type="submit" className="bg-blue-600 text-white px-3 py-1 rounded">Login</button>
          </form>
        </section>
      )}

      {page === 'patients' && (
        <section>
          <h2 className="text-lg font-medium mb-2">Patients</h2>
          {loading ? <p>Loading patients...</p> : (
            <ul className="space-y-2">
              {patients.map(p=> (<li key={p.id} className="flex justify-between items-center p-2 border rounded">{p.name} — <button className="text-sm px-2 py-1 bg-slate-100 rounded" onClick={()=>loadEHRs(p.id)}>View EHRs</button></li>))}
            </ul>
          )}
          {error && <p className="text-red-600">{error}</p>}
        </section>
      )}

      {page === 'ehrs' && (
        <section>
          <h2 className="text-lg font-medium mb-2">EHR Records</h2>
          <pre className="bg-slate-50 p-2 rounded">{JSON.stringify(ehrs, null, 2)}</pre>
          <h3 className="mt-4 text-md font-semibold">Create new EHR</h3>
          <EHRForm onCreate={async (payload)=>{
            const res = await apiFetch('/ehr/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})
            if(res.ok){ alert('EHR created'); } else { alert('Failed to create EHR') }
          }} />
        </section>
      )}

      {page === 'payments' && (
        <section>
          <h2 className="text-lg font-medium mb-2">Simulate Payment</h2>
          <form onSubmit={simulatePayment} className="flex gap-2 items-center">
            <input value={billingId} onChange={e=>setBillingId(e.target.value)} placeholder="Billing ID" className="p-2 border rounded" />
            <button type="submit" className="bg-green-600 text-white px-3 py-1 rounded">Simulate Payment</button>
          </form>
          <h3 className="mt-4 text-md font-semibold">Create Prescription</h3>
          <PrescriptionForm onCreate={async (p)=>{
            const res = await apiFetch('/prescriptions/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(p)})
            if(res.ok) alert('Prescription created'); else alert('Failed to create')
          }} />
          <h3 className="mt-4 text-md font-semibold">Grant Consent</h3>
          <ConsentForm onCreate={async (c)=>{
            const res = await apiFetch('/consents/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(c)})
            if(res.ok) alert('Consent granted'); else alert('Failed to grant')
          }} />
          <h3 className="mt-4 text-md font-semibold">Create Receipt</h3>
          <Receipts onCreate={async (r)=>{
            const res = await apiFetch('/receipts/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(r)})
            if(res.ok) alert('Receipt created'); else alert('Failed')
          }} />
        </section>
      )}

      {page === 'blockchain' && (
        <section>
          <h2 className="text-lg font-medium mb-2">Blockchain</h2>
          {loading ? <p>Loading chain...</p> : <pre className="bg-slate-50 p-2 rounded">{chain ? JSON.stringify(chain, null, 2) : 'No chain'}</pre>}
          {error && <p className="text-red-600">{error}</p>}
          <button className="mt-2 px-3 py-1 bg-slate-100 rounded" onClick={loadChain}>Refresh Chain</button>
        </section>
      )}

      {page === 'receipts' && (
        <section>
          <h2 className="text-lg font-medium mb-2">Receipts</h2>
          <button className="px-2 py-1 bg-slate-100 rounded" onClick={loadReceipts}>Refresh Receipts</button>
          {loading ? <p>Loading...</p> : (
            <ul className="space-y-2 mt-2">
              {receipts.map(r=> (
                <li key={r.id} className="p-2 border rounded">{r.billing_id} — ${r.amount} — anchor: {r.anchor_id || 'n/a'}</li>
              ))}
            </ul>
          )}
          {error && <p className="text-red-600">{error}</p>}
        </section>
      )}

      <Toasts toasts={toasts} onRemove={removeToast} />
    </div>
  )
}

export default App
