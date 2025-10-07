"use client";
import { useEffect, useState } from "react";

export default function IndicadoresComparativaPage() {
  const base = process.env.NEXT_PUBLIC_API_BASE || "";
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [edits, setEdits] = useState({}); // id -> texto de análisis
  const [year, setYear] = useState(2024);
  const [month, setMonth] = useState(1);
  const [qIndicador, setQIndicador] = useState("");

  const [savingRow, setSavingRow] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const token = localStorage.getItem("authToken");
      const params = new URLSearchParams();
      if (year) params.set("year", String(year));
      if (month) params.set("month", String(month));
      if (qIndicador) params.set("indicador", qIndicador);
      
      const url = `${base}/api/v1/indicadores/comparativa/?${params.toString()}`;
      console.log('🔍 DEBUG - URL:', url);
      console.log('🔍 DEBUG - Params:', { year, month, qIndicador });
      
      const res = await fetch(url, {
        headers: token ? { Authorization: `Token ${token}` } : {},
      });
      const ct = res.headers.get('content-type') || '';
      const body = ct.includes('application/json') ? await res.json() : await res.text();
      if (!res.ok) {
        const msg = ct.includes('application/json')
          ? (body.error || body.detail || JSON.stringify(body))
          : `${res.status} ${res.statusText} — ${String(body).slice(0,180)}`;
        throw new Error(msg);
      }
      const data = body;
      console.log('🔍 DEBUG - Response:', data);
      const rows = Array.isArray(data) ? data : data.items || [];
      console.log('🔍 DEBUG - Rows:', rows.length, 'items');
      const mapped = rows.map(mapRow);
      console.log('🔍 DEBUG - Mapped:', mapped.length, 'items');
      setItems(mapped);
      setEdits({});
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Recargar automáticamente cuando cambien año o mes
  useEffect(() => {
    if (year && month) {
      load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, month]);

  // Edición por fila: solo guardar análisis

  async function saveRow(r){
    try{
      setSavingRow(true);
      const token = localStorage.getItem("authToken");
      // Clave de negocio: indicador + periodo (YYYY-MM) del filtro actual
      const periodoFiltro = `${year}-${String(month).padStart(2,'0')}`;
      const analisisValue = ((edits[r.id] ?? r.analisis) ?? '').trim();
      const payload = {
        nombre_indicador: r.indicador,
        anio: year,
        mes: month,
        periodo: periodoFiltro,
        // Enviar "" explícito para borrar; si se desea no tocar, omitir la key
        analisis: analisisValue,
      };
      const res = await fetch(`${base}/api/v1/indicadores/comparativa/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token? { Authorization:`Token ${token}` } : {}) },
        body: JSON.stringify(payload),
      });
      const ct = res.headers.get('content-type') || '';
      const body = ct.includes('application/json') ? await res.json().catch(()=>({})) : await res.text();
      if(!res.ok){
        const msg = ct.includes('application/json') ? (body.error || body.detail || JSON.stringify(body)) : `${res.status} ${res.statusText}`;
        throw new Error(msg);
      }
      // Optimistic UI: reflejar de una
      setItems(prev => prev.map(it => (it.id === r.id ? { ...it, analisis: (payload.analisis ?? '').toString() } : it)));
      setEdits(prev => ({ ...prev, [r.id]: '' }));
      await load();
    }catch(e){ setError(e.message); }
    finally{ setSavingRow(false); }
  }

  return (
    <div>
      <h1 className="coofi-title">Indicadores · Comparativa (TEST)</h1>
      
      <div style={{ 
        background: "#f0f8ff", 
        padding: "8px 12px", 
        borderRadius: "4px", 
        marginBottom: "12px",
        border: "1px solid #d0e7ff"
      }}>
        <strong>Período consultado:</strong> {year} - {month ? ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'][month - 1] : 'Seleccione mes'}
        <br />
        <small style={{ color: "#666" }}>
          Parámetros enviados: year={year}, month={month}
        </small>
      </div>

      <div style={{ display: "flex", gap: 12, margin: "8px 0", alignItems: "center" }}>
        <label>
          Año:{" "}
          <select
            value={year}
            onChange={(e) => setYear(parseInt(e.target.value))}
            style={{ width: 100 }}
          >
            <option value={2020}>2020</option>
            <option value={2021}>2021</option>
            <option value={2022}>2022</option>
            <option value={2023}>2023</option>
            <option value={2024}>2024</option>
            <option value={2025}>2025</option>
          </select>
        </label>
        <label>
          Mes:{" "}
          <select
            value={month}
            onChange={(e) => setMonth(parseInt(e.target.value))}
            style={{ width: 120 }}
          >
            <option value={1}>Enero</option>
            <option value={2}>Febrero</option>
            <option value={3}>Marzo</option>
            <option value={4}>Abril</option>
            <option value={5}>Mayo</option>
            <option value={6}>Junio</option>
            <option value={7}>Julio</option>
            <option value={8}>Agosto</option>
            <option value={9}>Septiembre</option>
            <option value={10}>Octubre</option>
            <option value={11}>Noviembre</option>
            <option value={12}>Diciembre</option>
          </select>
        </label>
        <input
          placeholder="Filtrar indicador (opcional)"
          value={qIndicador}
          onChange={(e) => setQIndicador(e.target.value)}
          style={{ minWidth: 240 }}
        />
        <button onClick={load} disabled={loading}>
          {loading ? "Cargando…" : "Consultar"}
        </button>
      </div>

      {error && (
        <p style={{ color: "crimson", margin: "8px 0" }}>Error: {error}</p>
      )}

      <div className="coofi-card" style={{ overflowX: "auto", marginTop: 12 }}>
        <table className="coofi-table" style={{ minWidth: 900 }}>
          <thead>
            <tr>
              <th>Indicador</th>
              <th>Alcance</th>
              <th>Fecha</th>
              <th>Periodo</th>
              <th>Mes Actual</th>
              <th>Dic Año Ant.</th>
              <th>Mes -1 Año</th>
              <th>Mes -2 Años</th>
              <th>Análisis</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r, idx) => (
              <tr key={r.id || idx}>
                <td>{r.indicador}</td>
                <td>{r.alcance}</td>
                <td>{fmtDate(r.fecha)}</td>
                <td>{r.periodo || ''}</td>
                <td className="num">{fmtNum(r.mesActual)}</td>
                <td className="num">{fmtNum(r.diciembre1a)}</td>
                <td className="num">{fmtNum(r.mes1a)}</td>
                <td className="num">{fmtNum(r.mes2a)}</td>
                <td>
                  <textarea
                    value={edits[r.id] ?? r.analisis ?? ''}
                    onChange={(e)=> setEdits(prev => ({...prev, [r.id]: e.target.value}))}
                    rows={2}
                    style={{width:'100%'}}
                  />
                </td>
                <td>
                  <button onClick={()=> saveRow(r)} disabled={savingRow}>Guardar</button>
                </td>
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={8} style={{ textAlign: "center", padding: 12 }}>
                  Sin registros.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function mapRow(r) {
  const [yy, mm] = (()=>{
    try{
      const d = new Date(r.fecha);
      if(!Number.isNaN(d.getTime())) return [d.getFullYear(), d.getMonth()+1];
      const m = String(r.fecha||'').match(/(\d{4})-(\d{2})/);
      if(m) return [parseInt(m[1]), parseInt(m[2])];
    }catch(_){/*ignore*/}
    return [undefined, undefined];
  })();
  const periodo = (yy && mm)? `${yy}-${String(mm).padStart(2,'0')}` : undefined;
  return {
    id: r.id,
    fecha: r.fecha,
    periodo,
    indicador: str(r.indicador ?? r.nombre_indicador ?? r.nombre),
    alcance: str(r.alcance ?? r.descripcion ?? r.scope),
    mesActual: toNum(r.mesActual ?? r.valor_indicador),
    diciembre1a: toNum(r.diciembre1a ?? r.anio_menos_1_dic ?? r.mes_de_diciembre_fijo),
    mes1a: toNum(r.mes1a ?? r.valor_indicador_2),
    mes2a: toNum(r.mes2a ?? r.valor_indicador_3),
    analisis: str(r.analisis ?? r.analysis),
    _anio: yy,
    _mes: mm,
  };
}

function toNum(v) {
  if (v == null || v === "") return 0;
  const n = Number(String(v).replace(/\./g, "").replace(/,/g, "."));
  return Number.isFinite(n) ? n : 0;
}

// no se requiere convertir números al guardar análisis

function str(v) {
  return (v ?? "").toString();
}

function fmtNum(n) {
  try {
    return Intl.NumberFormat("es-CO").format(n ?? 0);
  } catch {
    return String(n ?? 0);
  }
}

function fmtDate(v) {
  if (!v) return "";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return String(v);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yy = d.getFullYear();
  return `${dd}/${mm}/${yy}`;
}
