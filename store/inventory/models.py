import unicodedata
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone


from decimal import Decimal
class Category(models.Model):
    name = models.TextField()
    description = models.TextField()
    status = models.IntegerField(default=1) 
    date_added = models.DateTimeField(default=timezone.now) 
    date_updated = models.DateTimeField(auto_now=True) 

    def __str__(self):
        return self.name
    
    def check_and_update_status(self):
        if self.pk:  
            if self.products_set.filter(status=1).count() == 0:
                self.status = 0
            else:
                self.status = 1
            
            Category.objects.filter(pk=self.pk).update(status=self.status)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.check_and_update_status() 
        

class Products(models.Model):
    STATUS_INACTIVE = 0
    STATUS_ACTIVE = 1
    STATUS_CHOICES = [
        (STATUS_INACTIVE, 'Inactivo'),
        (STATUS_ACTIVE, 'Activo'),
    ]

    code = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=18, decimal_places=8, default=0)
    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['name']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.name

    def update_quantity_on_sale(self, quantity_sold):
        quantity_sold = int(quantity_sold)
        if self.quantity >= quantity_sold:
            self.quantity -= quantity_sold
            self.save(update_fields=['quantity'])
            return True
        return False

    def increase_quantity(self, quantity_added):
        self.quantity += quantity_added
        self.save(update_fields=['quantity'])
        self.update_status()
    # 1last copy
    def decrease_quantity(self, quantity_removed):
        self.quantity -= quantity_removed
        if self.quantity < 0:
            self.quantity = 0
        self.save(update_fields=['quantity'])
        self.update_status()
        
    def update_quantity_on_purchase(self, quantity_difference):
        self.quantity += quantity_difference
        if self.quantity < 0:
            self.quantity = 0
        self.save(update_fields=['quantity'])
        self.update_status()

    def update_cost(self, new_cost):
        self.cost = new_cost
        self.save(update_fields=['cost'])
        self.update_status()

    def clean(self):
        super().clean()
        if self.price <= Decimal('0'):
            raise ValidationError("El precio debe ser mayor que cero.")
        if self.cost < Decimal('0'):
            raise ValidationError("El costo no puede ser negativo.")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.update_status()
        
    def update_status(self):
        if self.quantity > 0 and self.cost > Decimal('0') and self.price > Decimal('0'):
            if self.status != self.STATUS_ACTIVE:
                self.status = self.STATUS_ACTIVE
                self.save(update_fields=['status'])
        else:
            if self.status != self.STATUS_INACTIVE:
                self.status = self.STATUS_INACTIVE
                self.save(update_fields=['status'])

    def update_cost_after_deletion(self, cost_removed):
        self.cost = self.calculate_new_cost_after_deletion(cost_removed)
        self.save(update_fields=['cost'])
        self.update_status()
    
    def calculate_new_cost_after_deletion(self, cost_removed):
        return max(self.cost - cost_removed, Decimal('0'))
    
    @property
    def last_purchase(self):
        return self.purchaseproduct_set.order_by('-date_added').first()

    @property
    def last_purchase_cost(self):
        last_purchase = self.last_purchase
        return last_purchase.cost if last_purchase else Decimal('0')

    @property
    def last_purchase_quantity(self):
        last_purchase = self.last_purchase
        return last_purchase.quantity if last_purchase else 0

    @property
    def profit_margin(self):
        if self.cost > 0:
            return (self.price - self.cost) / self.cost
        return None
    # !no funciono porbar solo la eliminacion don pruchase