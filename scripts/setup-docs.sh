#!/bin/bash

# Script simplificado para crear documentación básica de COOFISAM360
# Fecha: $(date +"%Y-%m-%d")

echo "🚀 Configurando documentación básica de COOFISAM360..."

# Crear directorio de documentación si no existe
mkdir -p docs

# Crear archivo de índice principal
cat > docs/INDICE.md << 'EOF'
# 📚 Índice de Documentación - Coofisam360

## Documentación Principal
- [README](../README.md) - Documentación principal del proyecto
- [Guía de Desarrollo](DEVELOPMENT.md) - Flujo de trabajo y comandos

## Módulos del Sistema
- [Gestión de Usuarios](01_gestion_usuarios/README.md)
- [Autenticación y Seguridad](02_autenticacion_seguridad/README.md)
- [Dashboard Principal](03_dashboard_principal/README.md)
- [Gestión de Socios](04_gestion_socios/README.md)
- [Cuentas de Ahorros](05_cuentas_ahorros/README.md)
- [Créditos y Préstamos](06_creditos_prestamos/README.md)
- [Tesorería](07_tesoreria/README.md)
- [Contabilidad](08_contabilidad/README.md)
- [Reportes Financieros](09_reportes_financieros/README.md)
- [Auditoría y Control](10_auditoria_control/README.md)

## Documentación Técnica
- [API Documentation](api.md)
- [Base de Datos](database.md)
- [Deployment](deployment.md)
- [Contributing](contributing.md)

---
*Documentación generada automáticamente - $(date +"%Y-%m-%d")*
EOF

echo "✅ Documentación básica creada en docs/"
echo "📖 Revisa docs/INDICE.md para ver la estructura completa"

