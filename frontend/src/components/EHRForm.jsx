import React, {useState} from 'react'
import FormField from './FormField'

export default function EHRForm({onCreate}){
  const [patientId, setPatientId] = useState('')
  const [diagnosis, setDiagnosis] = useState('')
  const [medication, setMedication] = useState('')
  const [notes, setNotes] = useState('')
  const [errors, setErrors] = useState({})

  function validate(){
    const e = {}
    if(!patientId || isNaN(Number(patientId))) e.patientId = 'Patient ID required and must be a number'
    if(!diagnosis) e.diagnosis = 'Diagnosis is required'
    return e
  }

  function submit(e){
    e.preventDefault()
    const eobj = validate()
    setErrors(eobj)
    if(Object.keys(eobj).length) return
    onCreate({patient_id: Number(patientId), diagnosis, medication, notes})
    setPatientId(''); setDiagnosis(''); setMedication(''); setNotes('')
  }

  return (
    <form onSubmit={submit} className="grid gap-2">
      <FormField label="Patient ID" value={patientId} onChange={setPatientId} placeholder="Patient ID" error={errors.patientId} />
      <FormField label="Diagnosis" value={diagnosis} onChange={setDiagnosis} placeholder="Diagnosis" error={errors.diagnosis} />
      <FormField label="Medication" value={medication} onChange={setMedication} placeholder="Medication" />
      <FormField label="Notes" value={notes} onChange={setNotes} placeholder="Notes" textarea />
      <button type="submit" className="bg-blue-600 text-white px-3 py-1 rounded">Create EHR</button>
    </form>
  )
}
