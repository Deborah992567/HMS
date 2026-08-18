import React, {useState} from 'react'
import FormField from './FormField'

export default function ConsentForm({onCreate}){
  const [patientId, setPatientId] = useState('')
  const [grantedTo, setGrantedTo] = useState('')
  const [scope, setScope] = useState('')
  const [errors, setErrors] = useState({})

  function validate(){
    const e = {}
    if(!patientId || isNaN(Number(patientId))) e.patientId = 'Patient ID required and must be a number'
    if(!grantedTo) e.grantedTo = 'granted_to required'
    return e
  }

  function submit(e){
    e.preventDefault()
    const eobj = validate()
    setErrors(eobj)
    if(Object.keys(eobj).length) return
    onCreate({patient_id: Number(patientId), granted_to: grantedTo, scope})
    setPatientId(''); setGrantedTo(''); setScope('')
  }

  return (
    <form onSubmit={submit} className="grid gap-2">
      <FormField label="Patient ID" value={patientId} onChange={setPatientId} placeholder="Patient ID" error={errors.patientId} />
      <FormField label="Granted To (provider:ID)" value={grantedTo} onChange={setGrantedTo} placeholder="provider:ID" error={errors.grantedTo} />
      <FormField label="Scope" value={scope} onChange={setScope} placeholder="Scope" />
      <button type="submit" className="bg-blue-600 text-white px-3 py-1 rounded">Grant Consent</button>
    </form>
  )
}
