from django.urls import path
from . import api_views
from rest_framework.authtoken.views import obtain_auth_token
from django.urls import path
from .api_views import mi_perfil
from django.urls import path
from .api_views import mi_perfil, PerfilUsuarioListView

urlpatterns = [
    path("me/", api_views.me, name="api-me"),
    path("perfiles/", PerfilUsuarioListView.as_view(), name="perfil-list"),
    path('status/', api_views.api_status, name='api-status'),
    path('test/', api_views.api_test_data, name='api-test'),
    path('users/', api_views.UserListView.as_view(), name='api-user-list'),
    path('users/<int:pk>/', api_views.UserDetailView.as_view(), name='api-user-detail'),
    path('profile/', api_views.user_profile, name='api-user-profile'),

    # Auth (token)
    path('auth/token/', obtain_auth_token, name='api-token-auth'),
    
    # Login personalizado con respuesta JSON completa
    path('auth/login/', api_views.custom_login, name='api-custom-login'),
    
    # Alias para compatibilidad con el frontend actual
    path('login/', api_views.custom_login, name='api-login'),
    
    # Endpoint específico para el frontend de Coofisam
    path('auth/', api_views.custom_login, name='api-auth'),

    # Finanzas (módulo financiero)
    path('finanzas/tree/', api_views.finanzas_tree, name='api-finanzas-tree'),
    path('finanzas/upload/', api_views.finanzas_upload, name='api-finanzas-upload'),
    path('finanzas/files/', api_views.finanzas_files, name='api-finanzas-files'),
    path('finanzas/download/', api_views.finanzas_download, name='api-finanzas-download'),
    path('finanzas/delete/', api_views.finanzas_delete, name='api-finanzas-delete'),
    path('finanzas/sample/', api_views.finanzas_sample, name='api-finanzas-sample'),
    path('finanzas/indicadores/spec/', api_views.finanzas_indicadores_spec, name='api-finanzas-indicadores-spec'),
    path('finanzas/indicadores/', api_views.finanzas_indicadores_list, name='api-finanzas-indicadores-list'),
    path('finanzas/indicadores/series/', api_views.finanzas_indicadores_series, name='api-finanzas-indicadores-series'),
    path('finanzas/cupos/spec/', api_views.finanzas_cupos_spec, name='api-finanzas-cupos-spec'),
    path('finanzas/cupos/', api_views.finanzas_cupos, name='api-finanzas-cupos'),
    path('finanzas/cupos-credito/spec/', api_views.finanzas_cupos_credito_spec, name='api-finanzas-cupos-credito-spec'),
    path('finanzas/cupos-credito/', api_views.CuposCreditoView.as_view(), name='api-finanzas-cupos-credito-list'),
    path('finanzas/presupuesto/spec/', api_views.finanzas_presupuesto_spec, name='api-finanzas-presupuesto-spec'),
    # Rutas específicas deben ir antes de la ruta dinámica <str:id>/ para evitar colisiones
    path('finanzas/presupuesto/upload/', api_views.PresupuestoUploadView.as_view(), name='api-finanzas-presupuesto-upload'),
    path('finanzas/presupuesto/upload-simple/', api_views.PresupuestoUploadSimpleView.as_view(), name='api-finanzas-presupuesto-upload-simple'),
    path('finanzas/presupuesto/execute-file/', api_views.PresupuestoExecuteFileView.as_view(), name='api-finanzas-presupuesto-execute-file'),
    path('finanzas/presupuesto/files/', api_views.presupuesto_files, name='api-finanzas-presupuesto-files'),
    path('finanzas/presupuesto/', api_views.PresupuestoView.as_view(), name='api-finanzas-presupuesto-list'),
    path('finanzas/presupuesto/<str:id>/', api_views.PresupuestoView.as_view(), name='api-finanzas-presupuesto-detail'),
    path('finanzas/presupuesto-completo/', api_views.presupuesto_completo, name='api-finanzas-presupuesto-completo'),
    path('finanzas/presupuesto-app/', api_views.presupuesto_app, name='api-finanzas-presupuesto-app'),
    path('finanzas/cuentas-disponibles/', api_views.cuentas_disponibles, name='api-finanzas-cuentas-disponibles'),
    path('finanzas/indicadores/consolidados/', api_views.finanzas_indicadores_consolidados, name='api-finanzas-indicadores-consolidados'),
    path('finanzas/indicadores/analisis/', api_views.IndicadoresAnalisisView.as_view(), name='api-finanzas-indicadores-analisis'),
    # Indicadores (tabla comparativa propia)
    path('indicadores/comparativa/', api_views.indicadores_comparativa, name='api-indicadores-comparativa'),
    path('indicadores/disponibles/', api_views.indicadores_disponibles, name='api-indicadores-disponibles'),

    # Oficinas (finanzas.oficinas_mes)
    path('finanzas/oficinas/', api_views.OficinasView.as_view(), name='api-finanzas-oficinas-list'),
    path('finanzas/oficinas/<str:codigo>/', api_views.OficinaView.as_view(), name='api-finanzas-oficina-detail'),
    path('finanzas/oficinas-disponibles/', api_views.oficinas_disponibles, name='api-finanzas-oficinas-disponibles'),
    
    # Análisis Explicativo
    path('analisis/explicativo/', api_views.AnalisisExplicativoView.as_view(), name='api-analisis-explicativo'),
    path('analisis/explicativo/<int:id>/', api_views.AnalisisExplicativoView.as_view(), name='api-analisis-explicativo-detail'),
    
    # Ejecución Presupuestal PUC 6 dígitos
    path('finanzas/ejecucion-presupuestal/', api_views.EjecucionPresupuestalView.as_view(), name='api-finanzas-ejecucion-presupuestal'),
    path('finanzas/ejecucion-presupuestal/upload/', api_views.EjecucionPresupuestalUploadView.as_view(), name='api-finanzas-ejecucion-presupuestal-upload'),
    path('finanzas/ejecucion-presupuestal/files/', api_views.ejecucion_presupuestal_files, name='api-finanzas-ejecucion-presupuestal-files'),
    path('finanzas/ejecucion-presupuestal/<int:id>/', api_views.EjecucionPresupuestalView.as_view(), name='api-finanzas-ejecucion-presupuestal-detail'),

    # Crédito
    path('credito/radicaciones/', api_views.credito_radicaciones, name='api-credito-radicaciones'),
    path('credito/campanias-oficina/', api_views.credito_campanias_oficina, name='api-credito-campanias-oficina'),
    path('credito/campanias/', api_views.credito_campanias, name='api-credito-campanias'),
    path('cartera/asignacion-llamadas/', api_views.cartera_asignacion_llamadas, name='api-cartera-asignacion-llamadas'),
    path('cartera/gestion-llamadas/', api_views.cartera_gestion_llamadas, name='api-cartera-gestion-llamadas'),
    path('cartera/link-llamadas/', api_views.cartera_link_llamadas, name='api-cartera-link-llamadas'),
    path('cartera/link-visitas/', api_views.cartera_link_visitas, name='api-cartera-link-visitas'),
    path('cartera/seguimiento-campanas/', api_views.cartera_seguimiento_campanas, name='api-cartera-seguimiento-campanas'),
    path('cartera/gestiones/', api_views.cartera_gestiones, name='api-cartera-gestiones'),

    # Ingeniería organizacional
    path('ing-org/encuesta-satisfaccion/', api_views.ing_org_encuesta_satisfaccion, name='api-ingorg-encuesta-satisfaccion'),
    path('ing-org/documentos/', api_views.ing_org_documentos, name='api-ingorg-documentos'),
    path('ing-org/solicitudes/', api_views.ing_org_solicitudes, name='api-ingorg-solicitudes'),

    # ETL: población de tablas base
    path('finanzas/etl/populate/', api_views.finanzas_etl_populate, name='api-finanzas-etl-populate'),
]
