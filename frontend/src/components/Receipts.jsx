import React, {useState} from 'react'

export default function Receipts({onCreate}){
  const [billingId, setBillingId] = useState('')
  const [amount, setAmount] = useState('')

  function submit(e){
    e.preventDefault()
    onCreate({billing_id: Number(billingId), amount: Number(amount)})
  }

  return (
    <form onSubmit={submit} style={{display:'grid',gap:8}}>
      <input placeholder="Billing ID" value={billingId} onChange={e=>setBillingId(e.target.value)} />
      <input placeholder="Amount" value={amount} onChange={e=>setAmount(e.target.value)} />
      <button type="submit">Create Receipt</button>
    </form>
  )
}
