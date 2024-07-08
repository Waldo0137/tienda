from django import forms
from .models import Supplier, PurchaseProduct
from inventory.models import *

from django.core.exceptions import ValidationError
class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_info']
        labels = {
            'name': 'Nombres y Apellidos(Persona/Empresa)',
            'contact_info': 'Informacion de Proveedor',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombres y Apellido / Empresa S.A.    ',
            }),
            'contact_info': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese información:\n Dirección\n Teléfono\n Rubro\n Etc',
                'rows': 6,  
            }),
        }
        error_messages = {
            'name': {
                'required': 'El nombre del proveedor es obligatorio.',
                'max_length': 'El nombre no puede exceder los 100 caracteres.',
            },
            'contact_info': {
                'required': 'La información de contacto es obligatoria.',
                'max_length': 'La información de contacto no puede exceder los 200 caracteres.',
            },
        }

class PurchaseForm(forms.ModelForm):
    class Meta:
        model = PurchaseProduct
        fields = ['supplier', 'product','cost','qty']
        labels = {
            'supplier': 'Proveedor',
            'product': 'Productos',
            'cost': 'Costo',
            'qty':'Cantidad',
        }
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el monto total',
            }),
            'qty': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el monto total',
            }),
        }
        error_messages = {
            'qty': {
                'required': 'El cantidad es obligatorio.',
                'invalid': 'Ingrese un cantidad válida.',
            },
            'cost':{
                'required': 'El costo debe tener 8 decimales.',
                'invalid': 'Ingrese un monto válido.',
            }
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ordenar el queryset de category alfabéticamente
        self.fields['supplier'].queryset = Supplier.objects.all().order_by('name')
        self.fields['product'].queryset = Products.objects.all().order_by('name')
    
