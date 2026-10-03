import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ShareButton } from './ShareButton'

const nav = navigator as unknown as Record<string, unknown>
let writeText: ReturnType<typeof vi.fn>

beforeEach(() => {
  writeText = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
})

afterEach(() => {
  delete nav.share
  delete nav.clipboard
})

function setShare(impl: () => Promise<void>) {
  const share = vi.fn(impl)
  Object.defineProperty(navigator, 'share', { value: share, configurable: true })
  return share
}

describe('ShareButton', () => {
  it('sans feuille de partage : seul « Copier » est proposé', async () => {
    render(<ShareButton title="T" text="liste" />)
    expect(screen.queryByRole('button', { name: /Notes/ })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Copier la liste' }))
    await screen.findByText('Copié !')
    expect(writeText).toHaveBeenCalledWith('liste')
  })

  it('ouvre la feuille de partage iOS avec le texte', async () => {
    const share = setShare(async () => {})
    render(<ShareButton title="T" text="liste" />)
    fireEvent.click(screen.getByRole('button', { name: 'Liste de courses → Notes' }))
    await waitFor(() => expect(share).toHaveBeenCalledWith({ title: 'T', text: 'liste' }))
    expect(writeText).not.toHaveBeenCalled()
  })

  it('partage annulé : ni copie ni erreur', async () => {
    const share = setShare(async () => {
      throw new DOMException('annulé', 'AbortError')
    })
    render(<ShareButton title="T" text="liste" />)
    fireEvent.click(screen.getByRole('button', { name: 'Liste de courses → Notes' }))
    await waitFor(() => expect(share).toHaveBeenCalled())
    expect(writeText).not.toHaveBeenCalled()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('partage en échec : repli sur la copie', async () => {
    setShare(async () => {
      throw new DOMException('refusé', 'NotAllowedError')
    })
    render(<ShareButton title="T" text="liste" />)
    fireEvent.click(screen.getByRole('button', { name: 'Liste de courses → Notes' }))
    await screen.findByText('Copié !')
    expect(writeText).toHaveBeenCalledWith('liste')
  })
})
