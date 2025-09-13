import Link from 'next/link';

export default function HomePage() {
  return (
    <div>
      <section className="home-hero">
        <div className="home-hero-inner">
          <div className="home-logo">
            {/* Muestra el logo si existe en /public */}
            <img src="/logo-coofisam.png" alt="Coofisam" />
          </div>
          <h1 className="home-title">Coofisam360 · Finanzas</h1>
          <p className="home-subtitle">Indicadores, presupuesto y cupos de crédito en un solo lugar.</p>
        </div>
      </section>

      <section className="home-grid">
        <Link href="/login" className="home-card">
          <span className="icon" aria-hidden>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M10 3H5a2 2 0 00-2 2v14a2 2 0 002 2h5" stroke="currentColor" strokeWidth="1.6"/><path d="M13 17l4-5-4-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/><path d="M17 12H9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>
          </span>
          <span className="title">Ingresar</span>
          <span className="desc">Obtén tu token para acceder a los módulos.</span>
        </Link>

        <Link href="/modulo-financiero/cupos-credito" className="home-card">
          <span className="icon" aria-hidden>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3 7h18v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" stroke="currentColor" strokeWidth="1.6"/><path d="M3 7l2.5-3h13L21 7" stroke="currentColor" strokeWidth="1.6"/><path d="M8 12h8M8 15h5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>
          </span>
          <span className="title">Cupos de Crédito</span>
          <span className="desc">Consulta y administra los cupos de crédito.</span>
        </Link>

        <Link href="/finanzas/presupuesto" className="home-card">
          <span className="icon" aria-hidden>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/><rect x="6" y="4" width="4" height="4" rx="1" fill="currentColor"/><rect x="6" y="10" width="4" height="4" rx="1" fill="currentColor"/><rect x="6" y="16" width="4" height="4" rx="1" fill="currentColor"/></svg>
          </span>
          <span className="title">Presupuesto</span>
          <span className="desc">Carga y seguimiento del presupuesto financiero.</span>
        </Link>

        <Link href="/finanzas/indicadores-consolidados" className="home-card">
          <span className="icon" aria-hidden>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 19V5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/><path d="M4 19h16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/><rect x="7" y="10" width="3" height="6" rx="1" fill="currentColor"/><rect x="11" y="7" width="3" height="9" rx="1" fill="currentColor"/><rect x="15" y="12" width="3" height="4" rx="1" fill="currentColor"/></svg>
          </span>
          <span className="title">Indicadores</span>
          <span className="desc">Consolidado y análisis de indicadores clave.</span>
        </Link>

        <Link href="/modulo-financiero/oficinas" className="home-card">
          <span className="icon" aria-hidden>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3 7h18v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" stroke="currentColor" strokeWidth="1.6"/><path d="M3 7l2-3h14l2 3" stroke="currentColor" strokeWidth="1.6"/><path d="M7 11h4M7 15h7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>
          </span>
          <span className="title">Oficinas (Mes)</span>
          <span className="desc">Consulta y edita datos de oficinas.</span>
        </Link>

        {/* Enlaces a ETL y Carga Balance removidos para evitar 404 */}

        <Link href="/modulo-financiero/indicadores-comparativa" className="home-card">
          <span className="icon" aria-hidden>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 4h16v6H4z" stroke="currentColor" strokeWidth="1.6"/><path d="M4 14h16v6H4z" stroke="currentColor" strokeWidth="1.6"/><path d="M8 7h4M8 17h7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>
          </span>
          <span className="title">Indicadores · Comparativa</span>
          <span className="desc">Vista de prueba para endpoint comparativa.</span>
        </Link>
      </section>
    </div>
  );
}
