import { useState } from 'react'

export async function copyText(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  // Repli pour les navigateurs sans API presse-papiers.
  const ta = document.createElement('textarea')
  ta.value = text
  ta.setAttribute('readonly', '')
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  const ok = document.execCommand('copy')
  ta.remove()
  if (!ok) throw new Error('copie impossible')
}

type Status = 'idle' | 'copied' | 'error'

export function ShareButton({ title, text }: { title: string; text: string }) {
  const [status, setStatus] = useState<Status>('idle')
  const canShare = typeof navigator.share === 'function'

  async function copy() {
    try {
      await copyText(text)
      setStatus('copied')
    } catch {
      setStatus('error')
    }
  }

  async function share() {
    try {
      await navigator.share({ title, text })
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') return
      await copy()
    }
  }

  return (
    <div className="share">
      {canShare && (
        <button type="button" className="btn btn--primary" onClick={share}>
          Liste de courses → Notes
        </button>
      )}
      <button type="button" className={canShare ? 'btn' : 'btn btn--primary'} onClick={copy}>
        {status === 'copied' ? 'Copié !' : 'Copier la liste'}
      </button>
      {status === 'error' && <p role="alert" className="share__error">Copie impossible : sélectionne la liste à la main.</p>}
    </div>
  )
}
