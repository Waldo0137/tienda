from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Sum
from inventory.models import Products
from django.db import transaction
from django.db import models, transaction
from decimal import Decimal
from django.core.exceptions import ValidationError
class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_info = models.TextField(blank=True)
    date_added = models.DateTimeField(default=timezone.now, editable=False)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    
    
class PurchaseProduct(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    product = models.ForeignKey(Products, on_delete=models.SET_NULL, null=True)
    cost = models.DecimalField(max_digits=18, decimal_places=8, default=0)
    qty = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    total = models.DecimalField(max_digits=18, decimal_places=8, editable=False, default=0)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.qty <= 0:
            raise ValidationError("The quantity must be greater than zero.")
        if self.cost <= 0:
            raise ValidationError("The cost must be greater than zero.")

    def save(self, *args, **kwargs):
        self.clean()
        self.total = self.cost * self.qty
        
        with transaction.atomic():
            
            if self.pk:
            
                previous_instance = PurchaseProduct.objects.get(pk=self.pk)
                quantity_difference = self.qty - previous_instance.qty
            else:
                quantity_difference = self.qty
            super().save(*args, **kwargs)

            # Actualizar el producto asociado
            if self.product:
                self.product.update_quantity_on_purchase(quantity_difference)
                self.product.update_cost(self.cost)
                
                
    def delete(self, *args, **kwargs):
        with transaction.atomic():
            if self.product:
                # Actualizar el producto asociado antes de eliminar la compra
                self.product.decrease_quantity(self.qty)
                self.product.update_cost_after_deletion(self.cost)
            super().delete(*args, **kwargs)
            
    def __str__(self):
        return f"{self.product} de {self.supplier} - {self.qty} @ {self.cost} cada uno"

    