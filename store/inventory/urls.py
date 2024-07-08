from . import views
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic.base import RedirectView
from .views import *
app_name = 'inventory'
urlpatterns = [
    path('category/', CategoryList.as_view(), name='category_list'),
    path('category/new/', CategoryCreate.as_view(), name='category_create'),
    path('category/edit/<int:pk>/', CategoryUpdate.as_view(), name='category_update'),
    path('category/delete/<int:pk>/', CategoryDelete.as_view(), name='category_delete'),
    path('category/<int:pk>/products/', CategoryProductsList.as_view(), name='category_products'),

    
    path('products/', ProductList.as_view(), name='product_list'),
    path('products/new/', ProductCreate.as_view(), name='product_create'),
    path('products/edit/<int:pk>/', ProductUpdate.as_view(), name='product_update'),
    path('products/delete/<int:pk>/', ProductDelete.as_view(), name='product_delete'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    
]