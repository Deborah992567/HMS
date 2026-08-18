import React, {useEffect} from 'react'

export default function Toasts({toasts, onRemove}){
  useEffect(()=>{
    if(!toasts || !toasts.length) return
    const timers = toasts.map(t=> setTimeout(()=> onRemove(t.id), 4000))
    return ()=> timers.forEach(clearTimeout)
  },[toasts])

  return (
    <div className="fixed bottom-4 right-4 space-y-2">
      {toasts.map(t=> (
        <div key={t.id} className={`px-4 py-2 rounded shadow ${t.type==='error' ? 'bg-red-600 text-white' : t.type==='success' ? 'bg-green-600 text-white' : 'bg-slate-800 text-white'}`}>
          {t.message}
        </div>
      ))}
    </div>
  )
}
