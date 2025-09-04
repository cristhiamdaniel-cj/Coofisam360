import api from './api';

export async function listPresupuesto(params = {}) {
  const { data } = await api.get('/api/v1/finanzas/presupuesto/', { params });
  return data?.items ?? [];
}

export async function upsertPresupuesto(payload) {
  const { data } = await api.post('/api/v1/finanzas/presupuesto/', payload);
  return data;
}

