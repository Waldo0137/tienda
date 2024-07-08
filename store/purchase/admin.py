from django.contrib import admin

from .models import Supplier, PurchaseProduct

class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_info', 'date_added', 'date_updated')
    search_fields = ('name', 'contact_info')
    list_filter = ('date_added', 'date_updated')

class PurchaseProductAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'product', 'cost', 'qty', 'total', 'date_added', 'date_updated')
    search_fields = ('supplier__name', 'product__name')
    list_filter = ('supplier', 'product', 'date_added', 'date_updated')
    list_editable = ('cost', 'qty')
    readonly_fields = ('total',)

admin.site.register(Supplier, SupplierAdmin)
admin.site.register(PurchaseProduct, PurchaseProductAdmin)
