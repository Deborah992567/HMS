import React from 'react'

export default function FormField({label, value, onChange, type='text', placeholder='', error, textarea=false}){
  return (
    <label className="block mb-2">
      {label && <div className="text-sm text-slate-700 mb-1">{label}</div>}
      {textarea ? (
        <textarea value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder} className="w-full p-2 border rounded" />
      ) : (
        <input type={type} value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder} className="w-full p-2 border rounded" />
      )}
      {error && <div className="text-red-600 text-sm mt-1">{error}</div>}
    </label>
  )
}
