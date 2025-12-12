from django.urls import path

from . import api_views

app_name = "talento_cultura_api"

urlpatterns = [
    path("ascensos/", api_views.AscensosView.as_view(), name="ascensos"),
    path("bonos-mensual/", api_views.BonosMensualView.as_view(), name="bonos-mensual"),
    path("bono-cumple/", api_views.BonoCumpleView.as_view(), name="bono-cumple"),
    path("clima-laboral/", api_views.ClimaLaboralView.as_view(), name="clima-laboral"),
    path("desempeno/", api_views.DesempenoView.as_view(), name="desempeno"),
    path("egresos/", api_views.EgresosView.as_view(), name="egresos"),
    path("rol-lider/", api_views.RolLiderView.as_view(), name="rol-lider"),
    path("control-disciplinario/", api_views.ControlDisciplinarioView.as_view(), name="control-disciplinario"),
    path("control-disciplinario/<int:id>/", api_views.ControlDisciplinarioView.as_view(), name="control-disciplinario-detail"),
    path("capacitacion-mensual/", api_views.CapacitacionMensualView.as_view(), name="capacitacion-mensual"),
    path("capacitacion-mensual/<int:id>/", api_views.CapacitacionMensualView.as_view(), name="capacitacion-mensual-detail"),
    path("formacion-participacion/", api_views.FormacionParticipacionView.as_view(), name="formacion-participacion"),
    path("formacion-participacion/<int:id>/", api_views.FormacionParticipacionView.as_view(), name="formacion-participacion-detail"),
    path("satisfaccion-aprendizaje/", api_views.SatisfaccionAprendizajeView.as_view(), name="satisfaccion-aprendizaje"),
    path("satisfaccion-aprendizaje/<int:id>/", api_views.SatisfaccionAprendizajeView.as_view(), name="satisfaccion-aprendizaje-detail"),
    path("transferencia-conocimiento/", api_views.TransferenciaConocimientoView.as_view(), name="transferencia-conocimiento"),
    path("transferencia-conocimiento/<int:id>/", api_views.TransferenciaConocimientoView.as_view(), name="transferencia-conocimiento-detail"),
    path("accidentalidad/", api_views.AccidentalidadView.as_view(), name="accidentalidad"),
    path("ausentismo/", api_views.AusentismoView.as_view(), name="ausentismo"),
    path("enfermedad-laboral/", api_views.EnfermedadLaboralView.as_view(), name="enfermedad-laboral"),
    path("plan-trabajo/", api_views.PlanTrabajoView.as_view(), name="plan-trabajo"),
    path("programa-capacitaciones/", api_views.ProgramaCapacitacionesView.as_view(), name="programa-capacitaciones"),
    path("reporte-ministerio/", api_views.ReporteMinisterioView.as_view(), name="reporte-ministerio"),
    path("restricciones-laborales/", api_views.RestriccionesLaboralesView.as_view(), name="restricciones-laborales"),
    path("empleados/", api_views.EmpleadosView.as_view(), name="empleados"),
]
