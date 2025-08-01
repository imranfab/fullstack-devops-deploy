from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.decorators import api_view

# Simple root endpoint to verify the app is running
@api_view(["GET"])
def root_view(request):
    return JsonResponse({"message": "App works!"})

urlpatterns = [
    path("admin/", admin.site.urls),  # Admin site
    path("chat/", include("chat.urls")),  # Chat app URLs
    path("gpt/", include("gpt.urls")),  # GPT app URLs
    path("auth/", include("authentication.urls")),  # Authentication URLs
    path("", root_view),  # Root endpoint
]

# Serve static files during development
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
