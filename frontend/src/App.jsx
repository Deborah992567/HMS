import React, { useEffect, useState } from 'react'
import Header from './components/Header'
import EHRForm from './components/EHRForm'
import PrescriptionForm from './components/PrescriptionForm'
import ConsentForm from './components/ConsentForm'
import Receipts from './components/Receipts'
import Toasts from './components/Toasts'
import SignupForm from './components/SignupForm'

const apiBase = import.meta.env.VITE_API_BASE || '/api'

async function readResponse(response) {
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || body.message || 'Something went wrong. Please try again.')
  return body
}

function apiFetch(path, options = {}) {
  const token = localStorage.getItem('hms_token')
  const headers = { ...options.headers }
  if (token) headers.Authorization = `Bearer ${token}`
  return fetch(`${apiBase}${path}`, { ...options, headers })
}

const EmptyState = ({ message }) => <div className="empty-state">{message}</div>

export default function App() {
  const [page, setPage] = useState('home')
  const [token, setToken] = useState(() => localStorage.getItem('hms_token'))
  const [patientToken, setPatientToken] = useState(() => localStorage.getItem('hms_patient_token'))
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [patients, setPatients] = useState([])
  const [selectedPatient, setSelectedPatient] = useState(null)
  const [ehrs, setEhrs] = useState([])
  const [receipts, setReceipts] = useState([])
  const [chain, setChain] = useState(null)
  const [billingId, setBillingId] = useState('')
  const [doctors, setDoctors] = useState([])
  const [services, setServices] = useState([])
  const [appointmentDate, setAppointmentDate] = useState('')
  const [doctorId, setDoctorId] = useState('')
  const [serviceId, setServiceId] = useState('')
  const [patientAppointments, setPatientAppointments] = useState([])
  const [patientBills, setPatientBills] = useState([])
  const [patientEmail, setPatientEmail] = useState('')
  const [patientPassword, setPatientPassword] = useState('')
  const [adminDoctors, setAdminDoctors] = useState([])
  const [adminServices, setAdminServices] = useState([])
  const [loading, setLoading] = useState(false)
  const [toasts, setToasts] = useState([])

  const showToast = (message, type = 'info') => setToasts(items => [...items, { id: Date.now() + Math.random(), message, type }])
  const removeToast = id => setToasts(items => items.filter(item => item.id !== id))
  const request = async (path, options) => readResponse(await apiFetch(path, options))

  const loadChain = async () => { setLoading(true); try { setChain(await readResponse(await fetch(`${apiBase}/blockchain/chain`))) } catch (error) { showToast(error.message, 'error') } finally { setLoading(false) } }
  const loadPatients = async () => { setLoading(true); try { setPatients(await request('/patients/')); setPage('patients') } catch (error) { showToast(error.message, 'error') } finally { setLoading(false) } }
  const loadEhrs = async patient => { setLoading(true); try { setEhrs(await request(`/patients/${patient.id}/ehr`)); setSelectedPatient(patient); setPage('ehrs') } catch (error) { showToast(error.message, 'error') } finally { setLoading(false) } }
  const loadReceipts = async () => { setLoading(true); try { setReceipts(await request('/receipts/')); setPage('receipts') } catch (error) { showToast(error.message, 'error') } finally { setLoading(false) } }
  const loadBookingData = async () => { setLoading(true); try { const [doctorData, serviceData] = await Promise.all([readResponse(await fetch(`${apiBase}/doctors/`)), readResponse(await fetch(`${apiBase}/services/`))]); setDoctors(doctorData); setServices(serviceData); if (patientToken) { const headers = { Authorization: `Bearer ${patientToken}` }; const [appointments, bills] = await Promise.all([readResponse(await fetch(`${apiBase}/patient/appointments/`, { headers })), readResponse(await fetch(`${apiBase}/patient/billing/`, { headers }))]); setPatientAppointments(appointments); setPatientBills(bills) } setPage('book') } catch (error) { showToast(error.message, 'error') } finally { setLoading(false) } }
  const loadAdmin = async () => { setLoading(true); try { const [doctorData, serviceData] = await Promise.all([request('/doctors/'), request('/services/')]); setAdminDoctors(doctorData); setAdminServices(serviceData); setPage('admin') } catch (error) { showToast('Admin access required: ' + error.message, 'error') } finally { setLoading(false) } }

  useEffect(() => { loadChain() }, [])

  async function login(event) {
    event.preventDefault()
    try {
      const form = new URLSearchParams({ username: email, password })
      const result = await readResponse(await fetch(`${apiBase}/token`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: form }))
      localStorage.setItem('hms_token', result.access_token); setToken(result.access_token); setPassword(''); showToast('You are signed in.', 'success')
    } catch (error) { showToast(error.message, 'error') }
  }

  async function patientLogin(event) {
    event.preventDefault()
    try { const form = new URLSearchParams({ username: patientEmail, password: patientPassword }); const result = await readResponse(await fetch(`${apiBase}/patients/token`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: form })); localStorage.setItem('hms_patient_token', result.access_token); setPatientToken(result.access_token); setPatientPassword(''); showToast('Welcome to your patient portal.', 'success'); loadBookingData() } catch (error) { showToast(error.message, 'error') }
  }

  async function bookAppointment(event) {
    event.preventDefault()
    if (!patientToken) return showToast('Please sign in to book an appointment.', 'error')
    try { await readResponse(await fetch(`${apiBase}/patient/appointments/`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${patientToken}` }, body: JSON.stringify({ date: appointmentDate, doctor_id: Number(doctorId), service_id: serviceId ? Number(serviceId) : null }) })); showToast('Appointment booked successfully.', 'success'); setAppointmentDate(''); loadBookingData() } catch (error) { showToast(error.message, 'error') }
  }

  async function payPatientBill(id) {
    try { const result = await readResponse(await fetch(`${apiBase}/patient/payments/simulate`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${patientToken}` }, body: JSON.stringify(id) })); showToast(result.message, 'success'); loadBookingData() } catch (error) { showToast(error.message, 'error') }
  }
  async function editService(service) {
    const name = window.prompt('Service name', service.name)
    if (!name) return
    const duration = Number(window.prompt('Duration in minutes', service.duration_minutes)) || service.duration_minutes
    try { await request(`/services/${service.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...service, name, duration_minutes: duration }) }); showToast('Service updated.', 'success'); loadAdmin() } catch (error) { showToast(error.message, 'error') }
  }
  async function deleteService(id) {
    if (!window.confirm('Delete this service?')) return
    try { await request(`/services/${id}`, { method: 'DELETE' }); showToast('Service deleted.', 'success'); loadAdmin() } catch (error) { showToast(error.message, 'error') }
  }
  async function editDoctor(doctor) {
    const name = window.prompt('Doctor name', doctor.name)
    if (!name) return
    const specialty = window.prompt('Specialty', doctor.specialty || '')
    try { await request(`/doctors/${doctor.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, specialty }) }); showToast('Doctor updated.', 'success'); loadAdmin() } catch (error) { showToast(error.message, 'error') }
  }
  async function deleteDoctor(id) {
    if (!window.confirm('Delete this doctor?')) return
    try { await request(`/doctors/${id}`, { method: 'DELETE' }); showToast('Doctor deleted.', 'success'); loadAdmin() } catch (error) { showToast(error.message, 'error') }
  }

  async function simulatePayment(event) {
    event.preventDefault()
    if (!billingId || Number(billingId) < 1) return showToast('Enter a valid billing ID.', 'error')
    try { const result = await request('/payments/simulate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Number(billingId)) }); showToast(result.message, 'success'); setBillingId(''); loadChain() } catch (error) { showToast(error.message, 'error') }
  }

  async function submit(path, payload, message, after) {
    try { await request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); showToast(message, 'success'); if (after) after() } catch (error) { showToast(error.message, 'error') }
  }

  const navigate = next => { if (next === 'patients') return loadPatients(); if (next === 'receipts') return loadReceipts(); if (next === 'book') return loadBookingData(); if (next === 'admin') return loadAdmin(); if (next === 'blockchain') { setPage(next); return loadChain() } setPage(next) }
  const logout = () => { localStorage.removeItem('hms_token'); setToken(null); setPage('home'); showToast('You have been signed out.') }

  return <div className="app-shell">
    <Header page={page} signedIn={Boolean(token)} onNav={navigate} onLogout={logout} />
    <main className="main-content">
      {page === 'home' && <section className="hero-grid"><div className="hero-copy"><p className="eyebrow">Connected care, simplified</p><h1>Hospital operations, all in one calm workspace.</h1><p className="lede">Manage patients, clinical records, payments and verifiable receipt history from a single secure dashboard.</p><div className="hero-actions"><button className="button primary" onClick={() => navigate(token ? 'patients' : 'register')}>{token ? 'Open patient directory' : 'Register a patient'}</button><button className="button secondary" onClick={() => navigate('blockchain')}>View audit chain</button></div></div><aside className="login-card"><p className="eyebrow">{token ? 'Session active' : 'Staff access'}</p>{token ? <><h2>Welcome back</h2><p>You can now access the patient, clinical and finance workspaces based on your assigned role.</p><button className="button primary full" onClick={() => navigate('patients')}>Go to patients</button></> : <form onSubmit={login}><h2>Sign in</h2><label>Work email<input required type="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="name@hospital.com" /></label><label>Password<input required type="password" value={password} onChange={event => setPassword(event.target.value)} placeholder="••••••••" /></label><button className="button primary full" type="submit">Sign in securely</button><p className="form-note">New patient? <button type="button" className="text-button" onClick={() => navigate('register')}>Create a patient profile</button></p></form>}</aside></section>}
      {page === 'register' && <section className="page-section narrow"><div className="section-heading"><p className="eyebrow">Patient intake</p><h1>Create a patient profile</h1><p>Start a new patient record. Clinical staff can access it after signing in.</p></div><SignupForm apiBase={apiBase} onRegister={() => { showToast('Patient profile created.', 'success'); setPage('home') }} /></section>}
      {page === 'book' && <section className="page-section"><div className="section-heading"><p className="eyebrow">Patient portal</p><h1>Appointments and payments</h1><p>Book care, track upcoming visits and securely pay your own bills.</p></div>{!patientToken ? <article className="form-card" style={{maxWidth: 480}}><h2>Patient sign in</h2><form onSubmit={patientLogin}><label>Email<input required type="email" value={patientEmail} onChange={e => setPatientEmail(e.target.value)} placeholder="you@example.com" /></label><label>Password<input required type="password" value={patientPassword} onChange={e => setPatientPassword(e.target.value)} placeholder="Your password" /></label><button className="button primary full">Access patient portal</button></form><p className="form-note">Need an account? <button className="text-button" onClick={() => navigate('register')}>Register as a patient</button></p></article> : <><div className="record-layout"><article className="form-card"><h2>New appointment</h2><form onSubmit={bookAppointment}><label>Service<select required value={serviceId} onChange={e => { setServiceId(e.target.value); setDoctorId('') }}><option value="">Select a service</option>{services.map(service => <option key={service.id} value={service.id}>{service.name} · {service.duration_minutes} min</option>)}</select></label><label>Doctor<select required value={doctorId} onChange={e => setDoctorId(e.target.value)}><option value="">Choose a doctor</option>{doctors.filter(doctor => !serviceId || doctor.specialty === services.find(service => service.id === Number(serviceId))?.name).map(doctor => <option key={doctor.id} value={doctor.id}>{doctor.name}</option>)}</select></label><label>Date and time<input required type="datetime-local" value={appointmentDate} onChange={e => setAppointmentDate(e.target.value)} /></label><button className="button primary full">Book appointment</button></form></article><div><h2>Your appointments</h2>{loading ? <EmptyState message="Loading booking options…" /> : patientAppointments.length ? patientAppointments.map(appointment => <article className="record-card" key={appointment.id}><span className="record-id">APPOINTMENT #{appointment.id}</span><h3>{new Date(appointment.date).toLocaleString()}</h3><p>Doctor #{appointment.doctor_id} · {appointment.status}</p></article>) : <EmptyState message="You have no upcoming appointments." />}</div></div><div className="section-heading" style={{marginTop: 46}}><p className="eyebrow">Your billing</p><h2>Pay outstanding bills</h2></div>{patientBills.length ? <div className="data-grid">{patientBills.map(bill => <article className="patient-card" key={bill.id}><div className="avatar">$</div><div><h3>${Number(bill.amount).toFixed(2)}</h3><p>Bill #{bill.id}</p><span>{bill.status}</span></div>{bill.status === 'paid' ? <span className="anchor">Paid</span> : <button className="button primary" onClick={() => payPatientBill(bill.id)}>Pay now</button>}</article>)}</div> : <EmptyState message="You have no bills at the moment." />}</>}</section>}
      {page === 'admin' && <section className="page-section"><div className="section-heading"><p className="eyebrow">Administration</p><h1>Doctors and services</h1><p>Manage the demo directory and replace it with your real hospital information.</p></div><div className="record-layout"><article className="form-card"><h2>Services ({adminServices.length})</h2>{adminServices.map(service => <div className="record-card" key={service.id}><h3>{service.name}</h3><p>{service.duration_minutes} minutes</p><button className="text-button" onClick={() => editService(service)}>Edit</button> · <button className="text-button" onClick={() => deleteService(service.id)}>Delete</button></div>)}</article><article className="form-card"><h2>Doctors ({adminDoctors.length})</h2>{adminDoctors.slice(0, 40).map(doctor => <div className="record-card" key={doctor.id}><h3>{doctor.name}</h3><p>{doctor.specialty || 'General'}</p><button className="text-button" onClick={() => editDoctor(doctor)}>Edit</button> · <button className="text-button" onClick={() => deleteDoctor(doctor.id)}>Delete</button></div>)}</article></div></section>}
      {page === 'patients' && <section className="page-section"><div className="section-heading row"><div><p className="eyebrow">Patient directory</p><h1>Patients</h1><p>Select a patient to review their clinical record.</p></div><button className="button secondary" onClick={loadPatients}>Refresh</button></div>{loading ? <EmptyState message="Loading patients…" /> : patients.length ? <div className="data-grid">{patients.map(patient => <article className="patient-card" key={patient.id}><div className="avatar">{patient.name.slice(0, 1).toUpperCase()}</div><div><h3>{patient.name}</h3><p>{patient.email}</p><span>Patient #{patient.id}</span></div><button className="button secondary" onClick={() => loadEhrs(patient)}>Open record</button></article>)}</div> : <EmptyState message="No patients are available yet." />}</section>}
      {page === 'ehrs' && <section className="page-section"><div className="section-heading row"><div><p className="eyebrow">Clinical record</p><h1>{selectedPatient?.name || 'Patient'}’s EHR</h1><p>Patient #{selectedPatient?.id} · {ehrs.length} record{ehrs.length === 1 ? '' : 's'}</p></div><button className="button secondary" onClick={() => selectedPatient && loadEhrs(selectedPatient)}>Refresh</button></div><div className="record-layout"><div>{ehrs.length ? ehrs.map(record => <article className="record-card" key={record.id}><span className="record-id">RECORD #{record.id}</span><h3>{record.diagnosis}</h3><p><strong>Medication:</strong> {record.medication || 'Not recorded'}</p>{record.notes && <p className="notes">{record.notes}</p>}</article>) : <EmptyState message="No clinical records have been created for this patient." />}</div><aside className="form-card"><h2>New clinical record</h2><EHRForm onCreate={payload => submit('/ehr/', payload, 'Clinical record created.', () => selectedPatient && loadEhrs(selectedPatient))} /></aside></div></section>}
      {page === 'payments' && <section className="page-section"><div className="section-heading"><p className="eyebrow">Billing & care actions</p><h1>Payments and documentation</h1><p>Record a confirmed payment, issue a receipt, or add a prescription and consent record.</p></div><div className="workflow-grid"><article className="form-card"><h2>Simulate payment</h2><p className="card-copy">Marks the billing record paid and writes a confirmation to the local audit chain.</p><form onSubmit={simulatePayment}><label>Billing ID<input inputMode="numeric" value={billingId} onChange={event => setBillingId(event.target.value)} placeholder="e.g. 101" /></label><button className="button primary full" type="submit">Confirm payment</button></form></article><article className="form-card"><h2>Issue receipt</h2><Receipts onCreate={payload => submit('/receipts/', payload, 'Receipt created and anchored.', loadReceipts)} /></article><article className="form-card"><h2>Create prescription</h2><PrescriptionForm onCreate={payload => submit('/prescriptions/', payload, 'Prescription created.')} /></article><article className="form-card"><h2>Grant consent</h2><ConsentForm onCreate={payload => submit('/consents/', payload, 'Consent recorded.')} /></article></div></section>}
      {page === 'receipts' && <section className="page-section"><div className="section-heading row"><div><p className="eyebrow">Payment history</p><h1>Receipts</h1><p>Each issued receipt is linked to a billing record and may be anchored to the audit chain.</p></div><button className="button secondary" onClick={loadReceipts}>Refresh</button></div>{loading ? <EmptyState message="Loading receipts…" /> : receipts.length ? <div className="receipt-table"><div className="table-head"><span>Receipt</span><span>Billing</span><span>Amount</span><span>Issued</span><span>Audit anchor</span></div>{receipts.map(receipt => <div className="table-row" key={receipt.id}><span>#{receipt.id}</span><span>#{receipt.billing_id}</span><strong>${Number(receipt.amount).toFixed(2)}</strong><span>{new Date(receipt.timestamp).toLocaleDateString()}</span><span className="anchor">{receipt.anchor_id ? 'Anchored' : 'Pending'}</span></div>)}</div> : <EmptyState message="No receipts have been issued yet." />}</section>}
      {page === 'blockchain' && <section className="page-section"><div className="section-heading row"><div><p className="eyebrow">Tamper-evident audit trail</p><h1>Blockchain activity</h1><p>Local proof-of-work blocks record clinical and payment events for this demo.</p></div><button className="button secondary" onClick={loadChain}>Refresh chain</button></div>{loading ? <EmptyState message="Loading audit chain…" /> : chain ? <div className="chain-list">{chain.chain?.slice().reverse().map(block => <article className="block-card" key={block.index}><div><span className="record-id">BLOCK #{block.index}</span><h3>{block.transactions?.length || 0} transaction{block.transactions?.length === 1 ? '' : 's'}</h3></div><dl><div><dt>Proof</dt><dd>{block.proof}</dd></div><div><dt>Previous hash</dt><dd title={block.previous_hash}>{String(block.previous_hash).slice(0, 18)}…</dd></div></dl></article>)}</div> : <EmptyState message="The audit chain is not available." />}</section>}
    </main><Toasts toasts={toasts} onRemove={removeToast} />
  </div>
}
