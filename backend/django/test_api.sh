#!/bin/bash
# Test de API Coofisam360

BASE_URL="https://coofisam360.ngrok.io/api/v1"

# Permite pasar USERNAME y PASSWORD como variables de entorno.
# Si no se pasan, usa estos valores por defecto:
USERNAME=${USERNAME:-"subgerenciainnovacion@coofisam.com"}
PASSWORD=${PASSWORD:-"Coofisam123*"}

echo "🔑 Obteniendo token para $USERNAME ..."
TOKEN=$(curl -s -X POST "$BASE_URL/auth/token/" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}" \
  | jq -r .token)

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Error: no se pudo obtener token. Revisa credenciales o endpoint."
  exit 1
fi

echo "✅ Token obtenido: $TOKEN"
echo

echo "👤 Consultando /me/ ..."
curl -s -X GET "$BASE_URL/me/" \
  -H "Authorization: Token $TOKEN" | jq .
echo

echo "📋 Consultando /perfiles/ (requiere staff/superuser) ..."
curl -s -X GET "$BASE_URL/perfiles/" \
  -H "Authorization: Token $TOKEN" | jq .

