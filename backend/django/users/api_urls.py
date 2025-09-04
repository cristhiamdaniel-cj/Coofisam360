from django.urls import path
from . import api_views
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('status/', api_views.api_status, name='api-status'),
    path('test/', api_views.api_test_data, name='api-test'),
    path('users/', api_views.UserListView.as_view(), name='api-user-list'),
    path('users/<int:pk>/', api_views.UserDetailView.as_view(), name='api-user-detail'),
    path('profile/', api_views.user_profile, name='api-user-profile'),

    # Auth (token)
    path('auth/token/', obtain_auth_token, name='api-token-auth'),

    # Finanzas (módulo financiero)
    path('finanzas/tree/', api_views.finanzas_tree, name='api-finanzas-tree'),
    path('finanzas/upload/', api_views.finanzas_upload, name='api-finanzas-upload'),
    path('finanzas/files/', api_views.finanzas_files, name='api-finanzas-files'),
    path('finanzas/sample/', api_views.finanzas_sample, name='api-finanzas-sample'),
    path('finanzas/indicadores/spec/', api_views.finanzas_indicadores_spec, name='api-finanzas-indicadores-spec'),
    path('finanzas/indicadores/', api_views.finanzas_indicadores_list, name='api-finanzas-indicadores-list'),
    path('finanzas/indicadores/series/', api_views.finanzas_indicadores_series, name='api-finanzas-indicadores-series'),
    path('finanzas/cupos/spec/', api_views.finanzas_cupos_spec, name='api-finanzas-cupos-spec'),
    path('finanzas/cupos/', api_views.finanzas_cupos, name='api-finanzas-cupos'),
    path('finanzas/cupos-credito/spec/', api_views.finanzas_cupos_credito_spec, name='api-finanzas-cupos-credito-spec'),
    path('finanzas/cupos-credito/', api_views.CuposCreditoView.as_view(), name='api-finanzas-cupos-credito-list'),
    path('finanzas/presupuesto/spec/', api_views.finanzas_presupuesto_spec, name='api-finanzas-presupuesto-spec'),
    path('finanzas/presupuesto/', api_views.PresupuestoView.as_view(), name='api-finanzas-presupuesto-list'),
    path('finanzas/presupuesto/upload/', api_views.PresupuestoUploadView.as_view(), name='api-finanzas-presupuesto-upload'),
    path('finanzas/indicadores/consolidados/', api_views.finanzas_indicadores_consolidados, name='api-finanzas-indicadores-consolidados'),
    path('finanzas/indicadores/analisis/', api_views.IndicadoresAnalisisView.as_view(), name='api-finanzas-indicadores-analisis'),
]
