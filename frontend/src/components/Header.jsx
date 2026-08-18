import React from 'react'

const baseItems = [['home', 'Overview'], ['book', 'Patient portal'], ['patients', 'Patients'], ['receipts', 'Receipts'], ['assistant', 'Assistant']]

export default function Header({ page, signedIn, patientSignedIn, isAdmin, onNav, onLogout }) {
  const items = patientSignedIn ? [['home', 'Overview'], ['book', 'Patient portal']] : [...baseItems, ...(isAdmin ? [['admin', 'Admin'], ['blockchain', 'Audit trail']] : [])]
  return <header className="topbar"><button className="brand" onClick={() => onNav('home')} aria-label="HMS home"><span className="brand-mark">+</span><span>care<span>flow</span></span></button><nav>{items.map(([key, label]) => <button key={key} className={page === key ? 'active' : ''} onClick={() => onNav(key)}>{label}</button>)}</nav><div className="header-action">{signedIn || patientSignedIn ? <button className="button subtle" onClick={onLogout}>Sign out</button> : <button className="button primary" onClick={() => onNav('home')}>Staff sign in</button>}</div></header>
}
