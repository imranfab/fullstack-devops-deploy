from django.urls import path
#imported this auth_views
from django.contrib.auth import views as auth_views

from gpt import views

urlpatterns = [
    path("", views.gpt_root_view),
    path("title/", views.get_title),
    path("question/", views.get_answer),
    path("conversation/", views.get_conversation),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    

]