import api from './api';

// Categorías = Oficinas (finanzas.oficinas_mes)
// Lista oficinas por periodo y filtro opcional
export async function listCategories(params = {}) {
  const { data } = await api.get('/api/v1/finanzas/oficinas/', { params });
  // backend responde { items: [...], count }
  return data?.items ?? data;
}

// Obtiene una oficina por código (y opcionalmente año/mes)
export async function getCategory(codigo, params = {}) {
  const { data } = await api.get(`/api/v1/finanzas/oficinas/${encodeURIComponent(codigo)}/`, { params });
  return data;
}

// Guarda (upsert) datos de una oficina para (codigo, anio, mes)
export async function saveCategory(payload = {}) {
  const { data } = await api.post('/api/v1/finanzas/oficinas/', payload);
  return data;
}

