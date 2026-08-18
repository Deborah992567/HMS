import React from 'react'

export default function Header({onNav}){
  return (
    <header className="flex justify-between items-center">
      <h1 className="m-0 text-xl font-semibold">HMS</h1>
      <nav className="space-x-2">
        <button className="px-2 py-1 rounded hover:bg-slate-100" onClick={()=>onNav('home')}>Home</button>
        <button className="px-2 py-1 rounded hover:bg-slate-100" onClick={()=>onNav('patients')}>Patients</button>
        <button className="px-2 py-1 rounded hover:bg-slate-100" onClick={()=>onNav('blockchain')}>Blockchain</button>
        <button className="px-2 py-1 rounded hover:bg-slate-100" onClick={()=>onNav('payments')}>Payments</button>
        <button className="px-2 py-1 rounded hover:bg-slate-100" onClick={()=>onNav('receipts')}>Receipts</button>
        <button className="px-2 py-1 rounded hover:bg-slate-100" onClick={()=>onNav('register')}>Register</button>
      </nav>
    </header>
  )
}
