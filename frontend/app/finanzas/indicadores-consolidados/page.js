"use client";
import { useEffect, useState } from 'react';

export default function IndicadoresConsolidadosPage() {
  const base = process.env.NEXT_PUBLIC_API_BASE || '';
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      const token = localStorage.getItem('authToken');
      const res = await fetch(`${base}/api/v1/finanzas/indicadores/consolidados/?year=${year}&month=${month}`, {
        headers: { Authorization: `Token ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `Error ${res.status}`);
      setItems((data.items || []).map(addFormats));
      setError('');
    } catch (e) { setError(e.message); }
  }

  useEffect(() => { load(); }, []);

  function addFormats(r){
    const f = (n)=> (n==null? '' : Number(n).toFixed(2));
    return {
      ...r,
      _fmt: {
        actual: f(r.valor_mes_actual),
        dic_anterior: f(r.valor_dic_anterior),
        aa: f(r.valor_mes_aa),
        aa2: f(r.valor_mes_aa2),
        aa3: f(r.valor_mes_aa3),
      }
    };
  }

  async function saveAnalisis(indicador, analisis){
    try{
      setSaving(true);
      const token = localStorage.getItem('authToken');
      const res = await fetch(`${base}/api/v1/finanzas/indicadores/analisis/`, {
        method:'POST',
        headers:{ 'Content-Type':'application/json', Authorization:`Token ${token}` },
        body: JSON.stringify({ indicador, anio: year, mes: month, analisis })
      });
      const data = await res.json().catch(()=>({}));
      if(!res.ok) throw new Error(data.error || `Error ${res.status}`);
    }catch(e){ setError(e.message); }
    finally{ setSaving(false); }
  }

  return (
    <div>
      <h1 className="coofi-title">INDICADORES CONSOLIDADOS</h1>
      <div style={{display:'flex', gap:12, margin:'8px 0'}}>
        <label>Año: <input type="number" value={year} onChange={e=>setYear(parseInt(e.target.value||"0"))} /></label>
        <label>Mes: <input type="number" value={month} onChange={e=>setMonth(parseInt(e.target.value||"0"))} /></label>
        <button onClick={load}>Actualizar</button>
        {saving && <span>Guardando…</span>}
      </div>
      {error && <p style={{color:'crimson'}}>{error}</p>}
      <div className="coofi-card" style={{overflowX:'auto'}}>
        <table className="coofi-table" style={{minWidth: 1000}}>
          <thead>
            <tr>
              <th>Nombre Indicador</th>
              <th>Fórmula</th>
              <th>Mes Actual</th>
              <th>Dic Año Anterior</th>
              <th>Mes Año Anterior</th>
              <th>Mes -2 Años</th>
              <th>Mes -3 Años</th>
              <th>Análisis</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((r, idx) => (
              <tr key={idx}>
                <td>{r.nombre_indicador}</td>
                <td><code>{r.formula_indicador}</code></td>
                <td className="num">{r._fmt.actual}</td>
                <td className="num">{r._fmt.dic_anterior}</td>
                <td className="num">{r._fmt.aa}</td>
                <td className="num">{r._fmt.aa2}</td>
                <td className="num">{r._fmt.aa3}</td>
                <td>
                  <textarea defaultValue={r.analisis || ''} onBlur={(e)=>{ r._newAnalisis = e.target.value; }} rows={2} style={{width:'100%'}} />
                </td>
                <td>
                  <button onClick={()=> saveAnalisis(r.nombre_indicador, r._newAnalisis ?? r.analisis)}>Guardar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
