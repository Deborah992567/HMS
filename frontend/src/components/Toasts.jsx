import React, {useEffect} from 'react'

export default function Toasts({toasts, onRemove}){
  useEffect(()=>{
    if(!toasts || !toasts.length) return
    const timers = toasts.map(t=> setTimeout(()=> onRemove(t.id), 4000))
    return ()=> timers.forEach(clearTimeout)
  },[toasts])

  return (
    <div className="toasts">
      {toasts.map(t=> (
        <div key={t.id} className={`toast ${t.type||'info'}`}>
          {t.message}
        </div>
      ))}
    </div>
  )
}
