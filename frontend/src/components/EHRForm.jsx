import React, {useState} from 'react'

export default function EHRForm({onCreate}){
  const [patientId, setPatientId] = useState('')
  const [diagnosis, setDiagnosis] = useState('')
  const [medication, setMedication] = useState('')
  const [notes, setNotes] = useState('')

  function submit(e){
    e.preventDefault()
    onCreate({patient_id: Number(patientId), diagnosis, medication, notes})
  }

  return (
    <form onSubmit={submit} style={{display:'grid',gap:8}}>
      <input placeholder="Patient ID" value={patientId} onChange={e=>setPatientId(e.target.value)} />
      <input placeholder="Diagnosis" value={diagnosis} onChange={e=>setDiagnosis(e.target.value)} />
      <input placeholder="Medication" value={medication} onChange={e=>setMedication(e.target.value)} />
      <textarea placeholder="Notes" value={notes} onChange={e=>setNotes(e.target.value)} />
      <button type="submit">Create EHR</button>
    </form>
  )
}
