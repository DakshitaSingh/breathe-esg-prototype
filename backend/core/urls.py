# backend/core/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from emissions.views import OrganizationViewSet, DataBatchViewSet, EmissionRecordViewSet

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet)
router.register(r'batches', DataBatchViewSet)
router.register(r'records', EmissionRecordViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),  # <-- Fixed this line here
    path('api/', include(router.urls)),
]