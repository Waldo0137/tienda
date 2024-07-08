from django.contrib import admin

from .models import Category, Products
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'status', 'date_added', 'date_updated')
    search_fields = ('name', 'description')
    list_filter = ('status', 'date_added', 'date_updated')

class ProductsAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'price', 'status', 'quantity', 'date_added', 'date_updated')
    search_fields = ('code', 'name', 'description')
    list_filter = ('status', 'category', 'date_added', 'date_updated')
    

admin.site.register(Category, CategoryAdmin)
admin.site.register(Products, ProductsAdmin)