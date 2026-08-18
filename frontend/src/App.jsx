import React, {useEffect, useState} from 'react'
import Header from './components/Header'
import EHRForm from './components/EHRForm'
import PrescriptionForm from './components/PrescriptionForm'
import ConsentForm from './components/ConsentForm'
import Receipts from './components/Receipts'

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

  useEffect(()=>{ loadChain() }, [])

  async function login(e){
    e.preventDefault()
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    const res = await fetch(`${apiBase}/token`, {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body: form.toString()})
    if(!res.ok){ alert('Login failed'); return }
    const body = await res.json()
    localStorage.setItem('token', body.access_token)
    alert('Logged in')
  }

  async function loadChain(){
    const res = await fetch(`${apiBase}/blockchain/chain`)
    setChain(await res.json())
  }

  async function simulatePayment(e){
    e.preventDefault()
    if(!billingId) return alert('Enter billing id')
    const res = await apiFetch('/payments/simulate', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({billing_id: Number(billingId)})})
    const body = await res.json()
    alert(body.message || JSON.stringify(body))
    loadChain()
  }

  async function loadPatients(){
    const res = await apiFetch('/patients/')
    if(res.ok) setPatients(await res.json())
    setPage('patients')
  }

  async function loadEHRs(patientId){
    const res = await apiFetch(`/patients/${patientId}/ehr`)
    if(res.ok) setEhrs(await res.json())
    setPage('ehrs')
  }

  function logout(){ localStorage.removeItem('token'); alert('Logged out') }

  return (
    <div className="app">
      <Header onNav={p=>{ if(p==='patients') loadPatients(); else setPage(p)}} />

      {page === 'home' && (
        <section>
          <h2>Login</h2>
          <form onSubmit={login}>
            <input placeholder="email" value={email} onChange={e=>setEmail(e.target.value)} />
            <input placeholder="password" type="password" value={password} onChange={e=>setPassword(e.target.value)} />
            <button type="submit">Login</button>
          </form>
        </section>
      )}

      {page === 'patients' && (
        <section>
          <h2>Patients</h2>
          <ul>
            {patients.map(p=> (<li key={p.id}>{p.name} — <button onClick={()=>loadEHRs(p.id)}>View EHRs</button></li>))}
          </ul>
        </section>
      )}

      {page === 'ehrs' && (
        <section>
          <h2>EHR Records</h2>
          <pre>{JSON.stringify(ehrs, null, 2)}</pre>
          <h3>Create new EHR</h3>
          <EHRForm onCreate={async (payload)=>{
            const res = await apiFetch('/ehr/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})
            if(res.ok){ alert('EHR created'); } else { alert('Failed to create EHR') }
          }} />
        </section>
      )}

      {page === 'payments' && (
        <section>
          <h2>Simulate Payment</h2>
          <form onSubmit={simulatePayment}>
            <input value={billingId} onChange={e=>setBillingId(e.target.value)} placeholder="Billing ID" />
            <button type="submit">Simulate Payment</button>
          </form>
          <h3>Create Prescription</h3>
          <PrescriptionForm onCreate={async (p)=>{
            const res = await apiFetch('/prescriptions/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(p)})
            if(res.ok) alert('Prescription created'); else alert('Failed to create')
          }} />
          <h3>Grant Consent</h3>
          <ConsentForm onCreate={async (c)=>{
            const res = await apiFetch('/consents/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(c)})
            if(res.ok) alert('Consent granted'); else alert('Failed to grant')
          }} />
          <h3>Create Receipt</h3>
          <Receipts onCreate={async (r)=>{
            const res = await apiFetch('/receipts/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(r)})
            if(res.ok) alert('Receipt created'); else alert('Failed')
          }} />
        </section>
      )}

      {page === 'blockchain' && (
        <section>
          <h2>Blockchain</h2>
          <pre>{chain ? JSON.stringify(chain, null, 2) : 'Loading...'}</pre>
          <button onClick={loadChain}>Refresh Chain</button>
        </section>
      )}

      {page === 'receipts' && (
        <section>
          <h2>Receipts</h2>
          <p>Use the API directly to create/list receipts.</p>
        </section>
      )}

    </div>
  )
}

export default App
