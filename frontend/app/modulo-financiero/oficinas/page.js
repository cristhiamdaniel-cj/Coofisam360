"use client";
import { useEffect, useState } from 'react';
import { listCategories, saveCategory, getCategory } from '../../../lib/financialService';

export default function OficinasPage(){
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth()+1);
  const [q, setQ] = useState("");
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [edits, setEdits] = useState({}); // codigo -> { nombre, fecha, asociados, entidades, poblacion }

  async function load(){
    setLoading(true);
    try{
      const data = await listCategories({ year, month, q, limit: 500 });
      setItems(Array.isArray(data)? data : (data?.items||[]));
      setError("");
      setEdits({});
    }catch(e){ setError(e.message||'Error'); }
    finally{ setLoading(false); }
  }

  useEffect(()=>{ load(); }, []);

  function onEdit(codigo, field, value){
    setEdits(prev => ({ ...prev, [codigo]: { ...(prev[codigo]||{}), [field]: value } }));
  }

  async function onSave(r){
    try{
      const payload = {
        codigo: r.codigo,
        anio: year,
        mes: month,
        nombre: (edits[r.codigo]?.nombre ?? r.nombre) || undefined,
        fecha: (edits[r.codigo]?.fecha ?? r.fecha) || undefined,
        asociados: toInt(edits[r.codigo]?.asociados ?? r.asociados),
        entidades: toInt(edits[r.codigo]?.entidades ?? r.entidades),
        poblacion: toInt(edits[r.codigo]?.poblacion ?? r.poblacion),
      };
      await saveCategory(payload);
      await load();
    }catch(e){ setError(e.message||'Error al guardar'); }
  }

  return (
    <div>
      <h1 className="coofi-title">OFICINAS · MES</h1>
      <div style={{display:'flex', gap:12, margin:'8px 0'}}>
        <label>Año: <input type="number" value={year} onChange={e=>setYear(parseInt(e.target.value||'0'))} /></label>
        <label>Mes: <input type="number" value={month} onChange={e=>setMonth(parseInt(e.target.value||'0'))} /></label>
        <input placeholder="Buscar (código/nombre)" value={q} onChange={e=>setQ(e.target.value)} style={{minWidth:220}} />
        <button onClick={load}>{loading? 'Cargando…' : 'Actualizar'}</button>
      </div>
      {error && <p style={{color:'crimson'}}>{error}</p>}

      <div className="coofi-card" style={{overflowX:'auto'}}>
        <table className="coofi-table" style={{minWidth: 1000}}>
          <thead>
            <tr>
              <th>Código</th>
              <th>Nombre</th>
              <th>Fecha Apertura</th>
              <th>Asociados</th>
              <th>Entidades</th>
              <th>Población</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((r, idx)=>{
              const e = edits[r.codigo]||{};
              return (
                <tr key={r.id || r.codigo || idx}>
                  <td>{r.codigo}</td>
                  <td>
                    <input value={(e.nombre?? r.nombre) || ''} onChange={ev=>onEdit(r.codigo,'nombre', ev.target.value)} />
                  </td>
                  <td>
                    <input value={(e.fecha?? fmtDateISO(r.fecha)) || ''} onChange={ev=>onEdit(r.codigo,'fecha', ev.target.value)} placeholder="YYYY-MM-DD" />
                  </td>
                  <td><input className="num" value={e.asociados ?? r.asociados ?? 0} onChange={ev=>onEdit(r.codigo,'asociados', ev.target.value)} /></td>
                  <td><input className="num" value={e.entidades ?? r.entidades ?? 0} onChange={ev=>onEdit(r.codigo,'entidades', ev.target.value)} /></td>
                  <td><input className="num" value={e.poblacion ?? r.poblacion ?? 0} onChange={ev=>onEdit(r.codigo,'poblacion', ev.target.value)} /></td>
                  <td>
                    <button onClick={()=>onSave(r)}>Guardar</button>
                  </td>
                </tr>
              );
            })}
            {!loading && items.length===0 && (
              <tr><td colSpan={7} style={{textAlign:'center', padding:12}}>Sin registros.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function toInt(v){
  if(v==null || v==='') return undefined;
  const n = Number(String(v).replace(/\./g,'').replace(/,/g,'.').replace(/[^\d.-]/g,''));
  return Number.isFinite(n)? Math.trunc(n) : undefined;
}

function fmtDateISO(v){
  try{
    if(!v) return '';
    const d = new Date(v);
    if(Number.isNaN(d.getTime())) return String(v);
    const dd = String(d.getDate()).padStart(2,'0');
    const mm = String(d.getMonth()+1).padStart(2,'0');
    const yy = d.getFullYear();
    return `${yy}-${mm}-${dd}`;
  }catch(_){ return String(v||''); }
}

