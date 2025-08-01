from django.urls import path
from . import views

urlpatterns = [
    path('', views.gemini_root_view),  # Root endpoint
    path('title/', views.get_title),  # Generate short title from chat
    path('answer/', views.get_answer),  # Get answer from GPT
    path('conversation/', views.get_conversation),  # Get full conversation
    path('rag/', views.rag_generate),  # Retrieval-augmented generation
    path('file/upload/', views.file_upload),  # Upload file (basic)
    path('file/upload/secure/', views.file_upload_with_role_permission),  # Secure file upload with role check
    path('file/access/', views.file_access),  # Access file with permission
    path('file/delete/', views.file_delete),  # Delete uploaded file
]
