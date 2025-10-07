
import Image from "next/image";
import Link from "next/link";

export default function Navbar() {
  return (
    <nav className="navbar-container">
      <div className="logo">
        <Image
          src="/logo-coofisam.png" // Path relative to /public
          className="logo-image"
          alt="Company Logo"
          width={200} // required
          height={50} // required
          priority // loads immediately
        />
      </div>
      <div className="separator"></div>
      <div className="navbar-box px-8">
        <p className="navbar-title">Modulos</p>
        <Link href="/modulo-financiero" className="navbar-link">
          01 - Financiera
        </Link>
        <Link href="/modulo-financiero" className="navbar-link">
          02 - Talento y Cultura
        </Link>
        <Link href="/modulo-financiero" className="navbar-link">
          03 - Cartera
        </Link>
        <Link href="/modulo-financiero" className="navbar-link">
          04 - Crédito
        </Link>
        <Link href="/modulo-financiero" className="navbar-link">
          05 - Comercial
        </Link>
        <Link href="/modulo-financiero" className="navbar-link">
          06 - Gestion Documental
        </Link>
        <Link href="/modulo-financiero" className="navbar-link">
          07 - Ingenieria Organizacional
        </Link>
        <Link href="/modulo-financiero" className="navbar-link">
          08 - Juridico
        </Link>
        <Link href="/modulo-financiero" className="navbar-link">
          09 - Oficial de Cumplimiento
        </Link>
      </div>
      <p className="logout-button">Salir</p>
    </nav>
  );
}