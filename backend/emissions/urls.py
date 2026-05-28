from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'records', views.EmissionRecordViewSet, basename='emissionrecord')

urlpatterns = [
    path('', include(router.urls)),
    path('bulk-approve/', views.bulk_approve, name='bulk-approve'),
    path('stats/', views.emission_stats, name='emission-stats'),
]
