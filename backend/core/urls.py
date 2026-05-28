from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tenants', views.TenantViewSet)
router.register(r'emission-factors', views.EmissionFactorViewSet, basename='emissionfactor')
router.register(r'plants', views.PlantLookupViewSet, basename='plantlookup')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.register_user, name='register'),
    path('me/', views.current_user, name='current-user'),
]
