from django.urls import path,include
from .views import chat_with_gpt
from gpt import views

urlpatterns = [
    path("", views.gpt_root_view),
    path("title/", views.get_title),
    path("question/", views.get_answer),
    path("conversation/", views.get_conversation),
    #path("api/gpt/", include("gpt.urls")),
    path("chat/", chat_with_gpt)
]
