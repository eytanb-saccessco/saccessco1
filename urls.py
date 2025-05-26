from django.urls import path, include

urlpatterns = [
    # ... other paths
    path('saccessco/', include('saccessco.urls')),
]