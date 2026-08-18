import React from 'react'

export default function FormField({label, value, onChange, type='text', placeholder='', error, textarea=false}){
  return (
    <label style={{display:'block',marginBottom:8}}>
      {label && <div style={{fontSize:12,color:'#333',marginBottom:4}}>{label}</div>}
      {textarea ? (
        <textarea value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder} />
      ) : (
        <input type={type} value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder} />
      )}
      {error && <div style={{color:'red',fontSize:12,marginTop:4}}>{error}</div>}
    </label>
  )
}
