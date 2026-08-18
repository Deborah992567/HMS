import React, {useState} from 'react'

export default function PrescriptionForm({onCreate}){
  const [patientId, setPatientId] = useState('')
  const [doctorId, setDoctorId] = useState('')
  const [medication, setMedication] = useState('')
  const [dosage, setDosage] = useState('')
  const [instructions, setInstructions] = useState('')

  function submit(e){
    e.preventDefault()
    onCreate({patient_id: Number(patientId), doctor_id: Number(doctorId), medication, dosage, instructions})
  }

  return (
    <form onSubmit={submit} style={{display:'grid',gap:8}}>
      <input placeholder="Patient ID" value={patientId} onChange={e=>setPatientId(e.target.value)} />
      <input placeholder="Doctor ID" value={doctorId} onChange={e=>setDoctorId(e.target.value)} />
      <input placeholder="Medication" value={medication} onChange={e=>setMedication(e.target.value)} />
      <input placeholder="Dosage" value={dosage} onChange={e=>setDosage(e.target.value)} />
      <input placeholder="Instructions" value={instructions} onChange={e=>setInstructions(e.target.value)} />
      <button type="submit">Create Prescription</button>
    </form>
  )
}
