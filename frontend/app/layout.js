import './globals.css';

export const metadata = {
  title: 'Coofisam360 · Módulo Financiero',
  description: 'Coofisam360 - Gestión Financiera',
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body className="coofi-body">
        <div className="coofi-layout">
          <aside className="coofi-sidebar">
            <div className="coofi-brand">
              <div className="coofi-logo" aria-hidden />
              <div className="coofi-brand-text">coofisam</div>
            </div>
            <div className="coofi-mod-title">MÓDULOS</div>
            <nav className="coofi-nav">
              <a href="/finanzas/cupos-credito" className="coofi-nav-item">01 - Financiera</a>
              <a href="/finanzas/presupuesto" className="coofi-nav-item">02 - Presupuesto</a>
              <a className="coofi-nav-item" href="#">03 - Cartera</a>
              <a className="coofi-nav-item" href="#">04 - Crédito</a>
              <a className="coofi-nav-item" href="#">05 - Comercial</a>
              <a className="coofi-nav-item" href="#">06 - Gestión Documental</a>
              <a className="coofi-nav-item" href="#">07 - Talento y Cultura</a>
              <a className="coofi-nav-item" href="#">08 - Jurídico</a>
              <a className="coofi-nav-item" href="#">09 - Oficial de Cumplimiento</a>
            </nav>
            <div className="coofi-sidebar-exit">
              <a href="/login">Salir</a>
            </div>
          </aside>

          <main className="coofi-main">
            {children}
          </main>
        </div>
        <footer className="coofi-footer">© {new Date().getFullYear()} Coofisam. Todos los derechos reservados.</footer>
      </body>
    </html>
  );
}
