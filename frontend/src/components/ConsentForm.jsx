import React, {useState} from 'react'

export default function ConsentForm({onCreate}){
  const [patientId, setPatientId] = useState('')
  const [grantedTo, setGrantedTo] = useState('')
  const [scope, setScope] = useState('')

  function submit(e){
    e.preventDefault()
    onCreate({patient_id: Number(patientId), granted_to: grantedTo, scope})
  }

  return (
    <form onSubmit={submit} style={{display:'grid',gap:8}}>
      <input placeholder="Patient ID" value={patientId} onChange={e=>setPatientId(e.target.value)} />
      <input placeholder="Granted To (provider:ID)" value={grantedTo} onChange={e=>setGrantedTo(e.target.value)} />
      <input placeholder="Scope" value={scope} onChange={e=>setScope(e.target.value)} />
      <button type="submit">Grant Consent</button>
    </form>
  )
}
