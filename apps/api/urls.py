from django.urls import path, include

urlpatterns = [
    path('identity/',  include('apps.identity.api.urls')),
    path('financials/', include('apps.financials.api.urls')),
]