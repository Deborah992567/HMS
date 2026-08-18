import React, {useState} from 'react'
import FormField from './FormField'

export default function Receipts({onCreate}){
  const [billingId, setBillingId] = useState('')
  const [amount, setAmount] = useState('')
  const [errors, setErrors] = useState({})

  function validate(){
    const e = {}
    if(!billingId || isNaN(Number(billingId))) e.billingId = 'Billing ID required and must be a number'
    if(!amount || isNaN(Number(amount))) e.amount = 'Amount required and must be a number'
    return e
  }

  function submit(e){
    e.preventDefault()
    const eobj = validate()
    setErrors(eobj)
    if(Object.keys(eobj).length) return
    onCreate({billing_id: Number(billingId), amount: Number(amount)})
    setBillingId(''); setAmount('')
  }

  return (
    <form onSubmit={submit} className="grid gap-2">
      <FormField label="Billing ID" value={billingId} onChange={setBillingId} placeholder="Billing ID" error={errors.billingId} />
      <FormField label="Amount" value={amount} onChange={setAmount} placeholder="Amount" error={errors.amount} />
      <button type="submit" className="bg-blue-600 text-white px-3 py-1 rounded">Create Receipt</button>
    </form>
  )
}
