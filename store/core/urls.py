from . import views
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic.base import RedirectView
from django.urls import path
from .views import register_user
# urls.py



urlpatterns = [
    path('redirect-admin', RedirectView.as_view(url="/admin"),name="redirect-admin"),
    path('', views.home, name="home-page"),
    path('login', auth_views.LoginView.as_view(template_name = 'core/login.html',redirect_authenticated_user=True), name="login"),
    path('userlogin', views.login_user, name="login-user"),
    path('logout', views.logoutuser, name="logout"),
    path('register/', register_user, name='register_user'),
    
    
    path('password_reset/', views.password_reset_request, name="password_reset"),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm, name="password_reset_confirm"),
]
