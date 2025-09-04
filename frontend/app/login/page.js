"use client";
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const base = process.env.NEXT_PUBLIC_API_BASE || '';

  async function onSubmit(e) {
    e.preventDefault();
    setError('');
    try {
      const res = await fetch(`${base}/api/v1/auth/token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Credenciales inválidas');
      }
      const data = await res.json();
      localStorage.setItem('authToken', data.token);
      router.push('/');
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div style={{maxWidth: 420}}>
      <h2>Iniciar sesión</h2>
      <form onSubmit={onSubmit}>
        <div style={{marginBottom: 8}}>
          <label>Usuario</label>
          <input value={username} onChange={e=>setUsername(e.target.value)} style={{width:'100%'}} />
        </div>
        <div style={{marginBottom: 8}}>
          <label>Contraseña</label>
          <input type="password" value={password} onChange={e=>setPassword(e.target.value)} style={{width:'100%'}} />
        </div>
        <button type="submit">Ingresar</button>
      </form>
      {error && <p style={{color:'crimson'}}>{error}</p>}
      <p style={{marginTop: 16, color:'#555'}}>Backend base: <code>{base || '(mismo origen)'}</code></p>
    </div>
  );
}

