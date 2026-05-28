from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'jobs', views.DataIngestionJobViewSet, basename='ingestionjob')

urlpatterns = [
    path('', include(router.urls)),
    path('upload/', views.upload_file, name='upload-file'),
]
