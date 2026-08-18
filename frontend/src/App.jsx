import React, {useEffect, useState} from 'react'

const apiBase = import.meta.env.VITE_API_BASE || '/api'

function App(){
  const [chain, setChain] = useState(null)
  const [billingId, setBillingId] = useState('')

  async function loadChain(){
    const res = await fetch(`${apiBase}/blockchain/chain`)
    setChain(await res.json())
  }

  useEffect(()=>{ loadChain() }, [])

  async function simulatePayment(e){
    e.preventDefault()
    if(!billingId) return alert('Enter billing id')
    const res = await fetch(`${apiBase}/payments/simulate`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({billing_id: Number(billingId)})
    })
    const body = await res.json()
    alert(body.message || JSON.stringify(body))
    loadChain()
  }

  return (
    <div className="app">
      <h1>HMS Dashboard (React)</h1>
      <section>
        <h2>Simulate Payment</h2>
        <form onSubmit={simulatePayment}>
          <input value={billingId} onChange={e=>setBillingId(e.target.value)} placeholder="Billing ID" />
          <button type="submit">Simulate Payment</button>
        </form>
      </section>
      <section>
        <h2>Blockchain</h2>
        <pre>{chain ? JSON.stringify(chain, null, 2) : 'Loading...'}</pre>
        <button onClick={loadChain}>Refresh Chain</button>
      </section>
    </div>
  )
}

export default App
