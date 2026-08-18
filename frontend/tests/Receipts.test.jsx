import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import Receipts from '../src/components/Receipts'

describe('Receipts form', ()=>{
  it('validates and calls onCreate', ()=>{
    const onCreate = vi.fn()
    const { getByPlaceholderText, getByText } = render(<Receipts onCreate={onCreate} />)
    const bid = getByPlaceholderText('Billing ID')
    const amt = getByPlaceholderText('Amount')
    fireEvent.change(bid, { target: { value: '10' } })
    fireEvent.change(amt, { target: { value: '50' } })
    fireEvent.click(getByText('Create Receipt'))
    expect(onCreate).toHaveBeenCalled()
  })
})
