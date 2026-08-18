import React from 'react'

const items = [['home', 'Overview'], ['patients', 'Patients'], ['payments', 'Care & billing'], ['receipts', 'Receipts'], ['blockchain', 'Audit trail']]

export default function Header({ page, signedIn, onNav, onLogout }) {
  return <header className="topbar"><button className="brand" onClick={() => onNav('home')} aria-label="HMS home"><span className="brand-mark">+</span><span>care<span>flow</span></span></button><nav>{items.map(([key, label]) => <button key={key} className={page === key ? 'active' : ''} onClick={() => onNav(key)}>{label}</button>)}</nav><div className="header-action">{signedIn ? <button className="button subtle" onClick={onLogout}>Sign out</button> : <button className="button primary" onClick={() => onNav('home')}>Staff sign in</button>}</div></header>
}
