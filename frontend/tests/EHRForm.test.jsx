import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import EHRForm from '../src/components/EHRForm'

describe('EHRForm', ()=>{
  it('validates and submits payload', ()=>{
    const onCreate = vi.fn()
    const { getByPlaceholderText, getByText } = render(<EHRForm onCreate={onCreate} />)
    const pid = getByPlaceholderText('Patient ID')
    const diag = getByPlaceholderText('Diagnosis')
    fireEvent.change(pid, { target: { value: '1' } })
    fireEvent.change(diag, { target: { value: 'Flu' } })
    fireEvent.click(getByText('Create EHR'))
    expect(onCreate).toHaveBeenCalled()
  })
})
