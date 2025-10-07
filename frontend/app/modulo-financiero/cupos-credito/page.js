"use client";
import { useEffect, useState } from 'react';
import { listCreditQuota } from '../../../lib/creditQuota';

export default function CuposCreditoPage() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await listCreditQuota({ limit: 200 });
        setItems(data);
        setError('');
      } catch (e) { setError(e.message); }
      finally{ setLoading(false); }
    }
    load();
  }, []);

  return (
    <div>
      <h1 className="coofi-title">CUPO CRÉDITOS</h1>
      {error && <p style={{color:'crimson',marginBottom:10}}>Error: {error}</p>}
      <div className="coofi-card">
        <table className="coofi-table">
          <thead>
            <tr>
              <th>Fecha Renovado</th>
              <th>Cuenta</th>
              <th>Entidad Financiera</th>
              <th>Cupo Asignado</th>
              <th>Cupo Ejecutado</th>
              <th>Disponible</th>
              <th>Garantía</th>
              <th>% Utilización</th>
              <th>Plazo</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r, idx) => (
              <tr key={idx}>
                <td>{fmtDate(r.fechaRenovado || r.fecha_renovado)}</td>
                <td>{r.cuenta}</td>
                <td>{r.entidadFinanciera || r.entidad_financiera}</td>
                <td className="num">{Intl.NumberFormat('es-CO').format(r.cupoAsignado || r.cupo_asignado)}</td>
                <td className="num">{Intl.NumberFormat('es-CO').format(r.cupoEjecutado || r.cupo_ejecutado)}</td>
                <td className="num">{Intl.NumberFormat('es-CO').format(r.disponible)}</td>
                <td>{r.garantia}</td>
                <td className="num">{(r.porcentajeUtilizacion ?? r.porcentaje_utilizacion ?? 0)}%</td>
                <td>{r.plazo}</td>
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr><td colSpan={9} style={{textAlign:'center', padding:'18px'}}>Sin registros.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function fmtDate(v){
  if(!v) return '';
  const d = new Date(v);
  if(Number.isNaN(d.getTime())) return v;
  const dd = String(d.getDate()).padStart(2,'0');
  const mm = String(d.getMonth()+1).padStart(2,'0');
  const yy = d.getFullYear();
  return `${dd}/${mm}/${yy}`;
}
