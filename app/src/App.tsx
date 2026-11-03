import { useEffect, useState } from 'react'
import { Canvas } from './Canvas'
import { Home } from './Home'

/** #/p/<slug> é o canvas; #/p/<slug>/f/<código> é o mesmo canvas recortado a partir de um nó (uma vista). */
function rota() {
  const m = location.hash.match(/^#\/p\/([a-z0-9-]+)(?:\/f\/([A-Z]+-\d+(?:\/v\d+(?:\.\d+)?)?))?/)
  return m ? { slug: m[1], vista: m[2] || null } : null
}

export default function App() {
  const [r, setR] = useState(rota)
  const slug = r?.slug
  useEffect(() => {
    const mudou = () => setR(rota())
    window.addEventListener('hashchange', mudou)
    return () => window.removeEventListener('hashchange', mudou)
  }, [])
  useEffect(() => {
    document.title = r?.vista ? `${r.vista} · Neo Stitch` : slug ? `${slug} · Neo Stitch` : 'Neo Stitch'
  }, [slug, r?.vista])
  return slug ? <Canvas key={`${slug}/${r?.vista || ''}`} slug={slug} raiz={r?.vista || undefined} /> : <Home />
}
