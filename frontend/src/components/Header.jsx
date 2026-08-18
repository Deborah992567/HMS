import React from 'react'

export default function Header({onNav}){
  return (
    <header style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
      <h1 style={{margin:0}}>HMS</h1>
      <nav>
        <button onClick={()=>onNav('home')}>Home</button>
        <button onClick={()=>onNav('patients')}>Patients</button>
        <button onClick={()=>onNav('blockchain')}>Blockchain</button>
        <button onClick={()=>onNav('payments')}>Payments</button>
        <button onClick={()=>onNav('receipts')}>Receipts</button>
      </nav>
    </header>
  )
}
