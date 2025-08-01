from django.urls import path
from chat import views
from chat.views import (
    upload_file,
    list_uploaded_files,
    delete_uploaded_file,
)

urlpatterns = [
    # -------------------------------
    #  Root / Basic Health Check
    # -------------------------------
    path("", views.chat_root_view, name="chat_root_view"),
    
    # -------------------------------
    #  Conversations
    # -------------------------------
    path("conversations/", views.get_conversations, name="get_conversations"),
    path("conversations_branched/", views.get_conversations_branched, name="get_branched_conversations"),
    path("conversation_branched/<uuid:pk>/", views.get_conversation_branched, name="get_branched_conversation"),
    path("conversations/add/", views.add_conversation, name="add_conversation"),
    path("conversations/<uuid:pk>/", views.conversation_manage, name="conversation_manage"),
    path("conversations/<uuid:pk>/change_title/", views.conversation_change_title, name="conversation_change_title"),
    path("conversations/<uuid:pk>/add_message/", views.conversation_add_message, name="conversation_add_message"),
    path("conversations/<uuid:pk>/add_version/", views.conversation_add_version, name="conversation_add_version"),
    path(
        "conversations/<uuid:pk>/switch_version/<uuid:version_id>/",
        views.conversation_switch_version,
        name="conversation_switch_version",
    ),
    path("conversations/<uuid:pk>/delete/", views.conversation_soft_delete, name="conversation_delete"),
    path("conversations/summaries/", views.get_conversation_summaries, name="conversation-summaries"),

    # -------------------------------
    #  Versions
    # -------------------------------
    path("versions/<uuid:pk>/add_message/", views.version_add_message, name="version_add_message"),

    # -------------------------------
    #  File Upload and Management
    # -------------------------------
    path("files/upload/", upload_file, name="upload-file"),
    path("files/", list_uploaded_files, name="list-uploaded-files"),
    path("files/<int:pk>/delete/", delete_uploaded_file, name="delete-uploaded-file"),
]
