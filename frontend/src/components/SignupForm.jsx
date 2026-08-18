import React, {useState} from 'react'
import FormField from './FormField'

export default function SignupForm({onRegister, apiBase='/api'}){
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState({})

  function validate(){
    const e = {}
    if(!name) e.name = 'Name is required'
    if(!email || !email.includes('@')) e.email = 'Valid email required'
    if(password.length < 8) e.password = 'Use at least 8 characters'
    return e
  }

  async function submit(ev){
    ev.preventDefault()
    const e = validate()
    setErrors(e)
    if(Object.keys(e).length) return
    try{
      const res = await fetch(`${apiBase}/patients/register`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name, email, password})})
      if(!res.ok) throw new Error('Registration failed')
      const body = await res.json()
      setName(''); setEmail(''); setPassword('')
      if(onRegister) onRegister(body)
    }catch(err){
      setErrors({form: err.message})
    }
  }

  return (
    <form onSubmit={submit} className="max-w-md border p-4 rounded bg-white shadow">
      <h3 className="text-lg font-semibold mb-2">Register as Patient</h3>
      {errors.form && <div className="text-red-600 mb-2">{errors.form}</div>}
      <FormField label="Full name" value={name} onChange={setName} placeholder="Jane Doe" error={errors.name} />
      <FormField label="Email" value={email} onChange={setEmail} placeholder="you@example.com" error={errors.email} />
      <FormField label="Create password" type="password" value={password} onChange={setPassword} placeholder="At least 8 characters" error={errors.password} />
      <div className="flex gap-2 mt-2">
        <button type="submit" className="bg-blue-600 text-white px-3 py-1 rounded">Register</button>
      </div>
    </form>
  )
}
