import React, {useState} from 'react'
import FormField from './FormField'

export default function PrescriptionForm({onCreate}){
  const [patientId, setPatientId] = useState('')
  const [doctorId, setDoctorId] = useState('')
  const [medication, setMedication] = useState('')
  const [dosage, setDosage] = useState('')
  const [instructions, setInstructions] = useState('')
  const [errors, setErrors] = useState({})

  function validate(){
    const e = {}
    if(!patientId || isNaN(Number(patientId))) e.patientId = 'Patient ID required and must be a number'
    if(!doctorId || isNaN(Number(doctorId))) e.doctorId = 'Doctor ID required and must be a number'
    if(!medication) e.medication = 'Medication required'
    return e
  }

  function submit(e){
    e.preventDefault()
    const eobj = validate()
    setErrors(eobj)
    if(Object.keys(eobj).length) return
    onCreate({patient_id: Number(patientId), doctor_id: Number(doctorId), medication, dosage, instructions})
    setPatientId(''); setDoctorId(''); setMedication(''); setDosage(''); setInstructions('')
  }

  return (
    <form onSubmit={submit} className="grid gap-2">
      <FormField label="Patient ID" value={patientId} onChange={setPatientId} placeholder="Patient ID" error={errors.patientId} />
      <FormField label="Doctor ID" value={doctorId} onChange={setDoctorId} placeholder="Doctor ID" error={errors.doctorId} />
      <FormField label="Medication" value={medication} onChange={setMedication} placeholder="Medication" error={errors.medication} />
      <FormField label="Dosage" value={dosage} onChange={setDosage} placeholder="Dosage" />
      <FormField label="Instructions" value={instructions} onChange={setInstructions} placeholder="Instructions" />
      <button type="submit" className="bg-blue-600 text-white px-3 py-1 rounded">Create Prescription</button>
    </form>
  )
}
