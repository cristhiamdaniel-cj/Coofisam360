"use client";
import { useEffect, useState } from 'react';
import { listPresupuesto, upsertPresupuesto } from '../../../lib/presupuesto';

export default function PresupuestoPage() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [form, setForm] = useState({cuenta:'', nombre_cuenta:'', anio:'', mes:'', presupuesto:''});
  const [uploading, setUploading] = useState(false);
  async function load() {
    try {
      const data = await listPresupuesto({ year, month });
      setItems(data);
      setError('');
    } catch (e) { setError(e.message); }
  }

  useEffect(() => { load(); }, []);

  async function onSubmit(e){
    e.preventDefault();
    try{
      await upsertPresupuesto({
        cuenta: form.cuenta,
        anio: form.anio || year,
        mes: form.mes || month,
        presupuesto: form.presupuesto,
      });
      await load();
      setForm({cuenta:'', nombre_cuenta:'', anio:'', mes:'', presupuesto:''});
    }catch(e){ setError(e.message); }
  }

  return (
    <div>
      <h1 className="coofi-title">PRESUPUESTO</h1>
      <div style={{display:'flex', gap:12, margin:'8px 0'}}>
        <label>Año: <input type="number" value={year} onChange={e=>setYear(parseInt(e.target.value||"0"))} /></label>
        <label>Mes: <input type="number" value={month} onChange={e=>setMonth(parseInt(e.target.value||"0"))} /></label>
        <button onClick={load}>Actualizar</button>
      </div>
      {error && <p style={{color:'crimson'}}>{error}</p>}

      <UploadPresupuesto onDone={load} uploading={uploading} setUploading={setUploading} />

      <form onSubmit={onSubmit} style={{margin:'12px 0', display:'grid', gridTemplateColumns:'repeat(5, minmax(160px, 1fr))', gap:8}}>
        <input placeholder="Cuenta (Id_cuenta)" value={form.cuenta} onChange={e=>setForm({...form, cuenta:e.target.value})} />
        <input placeholder="Nombre Cuenta (opcional)" value={form.nombre_cuenta} onChange={e=>setForm({...form, nombre_cuenta:e.target.value})} />
        <input placeholder="Mes" value={form.mes} onChange={e=>setForm({...form, mes:e.target.value})} />
        <input placeholder="Año" value={form.anio} onChange={e=>setForm({...form, anio:e.target.value})} />
        <input placeholder="Presupuesto" value={form.presupuesto} onChange={e=>setForm({...form, presupuesto:e.target.value})} />
        <button type="submit" style={{gridColumn:'1 / -1'}}>Guardar/Actualizar</button>
      </form>
      <div className="coofi-card" style={{overflowX:'auto'}}>
        <table className="coofi-table" style={{minWidth: 700}}>
          <thead>
            <tr>
              <th>Cuenta (Id_cuenta)</th>
              <th>Nombre Cuenta</th>
              <th>Mes</th>
              <th>Año</th>
              <th>Presupuesto</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r, idx) => (
              <tr key={idx}>
                <td>{r.cuenta}</td>
                <td>{r.nombre_cuenta}</td>
                <td>{r.mes}</td>
                <td>{r.anio}</td>
                <td className="num">{Intl.NumberFormat('es-CO').format(r.presupuesto)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UploadPresupuesto({ onDone, uploading, setUploading }){
  const base = process.env.NEXT_PUBLIC_API_BASE || '';
  async function onChange(e){
    const file = e.target.files?.[0];
    if(!file) return;
    const token = localStorage.getItem('authToken');
    const fd = new FormData();
    fd.append('file', file);
    try{
      setUploading(true);
      const res = await fetch(`${base}/api/v1/finanzas/presupuesto/upload/`, {
        method:'POST',
        headers:{ Authorization: `Token ${token}` },
        body: fd
      });
      const data = await res.json();
      if(!res.ok) throw new Error(data.error || `Error ${res.status}`);
      onDone && onDone();
      alert(`Importados: ${data.imported}${data.errors?.length? `
Errores: ${data.errors.length}`:''}`);
    }catch(e){
      alert(e.message);
    }finally{ setUploading(false); e.target.value=''; }
  }
  return (
    <div style={{margin:'12px 0'}}>
      <label style={{display:'inline-block', padding:'8px 12px', background:'#7a0e0e', color:'#fff', borderRadius:6, cursor:'pointer'}}>
        {uploading? 'Cargando…' : 'Cargar Excel/CSV'}
        <input type="file" accept=".xlsx,.xls,.csv" onChange={onChange} style={{display:'none'}} />
      </label>
      <small style={{marginLeft:8, opacity:.7}}>Formato: cuenta, anio, mes, presupuesto</small>
    </div>
  );
}
