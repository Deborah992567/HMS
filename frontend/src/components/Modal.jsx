import React from 'react'

export default function Modal({children, onClose}){
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center" onClick={onClose}>
      <div className="bg-white p-4 rounded shadow max-w-lg w-full" onClick={e=>e.stopPropagation()}>
        <button className="float-right text-xl" onClick={onClose}>×</button>
        {children}
      </div>
    </div>
  )
}
