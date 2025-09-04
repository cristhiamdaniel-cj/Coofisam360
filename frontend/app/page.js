import Link from 'next/link'

export default function HomePage() {
  return (
    <div>
      <h1>Frontend Finanzas</h1>
      <p>Configura la variable <code>NEXT_PUBLIC_API_BASE</code> en Vercel.</p>
      <ul>
        <li><Link href="/login">Login (obtener Token)</Link></li>
        <li><Link href="/finanzas/cupos-credito">Cupos de Crédito</Link></li>
        <li><Link href="/finanzas/presupuesto">Presupuesto</Link></li>
        <li><Link href="/finanzas/indicadores-consolidados">Indicadores Consolidados</Link></li>
      </ul>
    </div>
  )
}

