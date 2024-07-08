import json
import logging
from datetime import date, datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Sum
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.messages.views import SuccessMessageMixin

from .models import Category, Products
from purchase.models import PurchaseProduct
from .forms import ProductsForm, CategoryForm

logger = logging.getLogger(__name__)


from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

class CategoryProductsList(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):

    model = Category
    template_name = "inventory/category_list_link.html"
    context_object_name = "products"
    permission_required = 'inventory.view_category'
    
    def get_queryset(self):
        self.category = get_object_or_404(Category, id=self.kwargs['pk'])
        return Products.objects.filter(category=self.category)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context
    
class CategoryList(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):

    model = Category
    template_name = "inventory/category_list.html"
    context_object_name = "categories"
    permission_required = 'inventory.view_category'
    
    def get_queryset(self):
        return Category.objects.annotate(product_count=Count('products'))
    
class CategoryCreate(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    model = Category
    template_name = "inventory/category_create.html"
    form_class = CategoryForm
    success_url = reverse_lazy('inventory:category_list')
    permission_required = 'inventory.add_category'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        category_name = form.instance.name
        messages.success(self.request, f"Categoria '{category_name}' creado exitosamente.")
        return response

    def form_invalid(self, form):
        logger.error("Error creating category: %s", form.errors)
        messages.error(self.request, "Hubo un error al crear el categoria. Por favor, intente de nuevo.")
        return self.render_to_response(self.get_context_data(form=form))
    
class CategoryUpdate(LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView):
    model = Category
    template_name = "inventory/category_update.html"
    form_class = CategoryForm
    success_url = reverse_lazy('inventory:category_list')
    permission_required = 'inventory.change_category'

    def form_valid(self, form):
        category_name = self.get_object().name
        response = super().form_valid(form)
        messages.success(self.request, f"Categoría '{category_name}' actualizada exitosamente.")
        return response

    def form_invalid(self, form):
        category_name = self.get_object().name
        messages.error(self.request, f"No se pudo actualizar la categoría '{category_name}'. Por favor corrige los errores.")
        return super().form_invalid(form)
    
class CategoryDelete(LoginRequiredMixin, SuccessMessageMixin,PermissionRequiredMixin, generic.DeleteView):
    model = Category
    template_name = "inventory/category_delete.html"
    success_url = reverse_lazy('inventory:category_list')
    permission_required = 'inventory.delete_category'
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        category_name = self.object.name
        success_message = f"Categoria '{category_name}' eliminado exitosamente."
        messages.success(self.request, success_message)
        return self.delete(request, *args, **kwargs)



class ProductDetailView(LoginRequiredMixin, PermissionRequiredMixin, generic.DetailView):
    model = Products
    template_name = "inventory/product_details.html"
    context_object_name = "product"
    permission_required = 'inventory.view_products'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        
        purchase_products = PurchaseProduct.objects.filter(product=product)
        logger.debug(f"Purchase products count: {purchase_products.count()}")

        cantidad_historica = sum([pp.qty for pp in purchase_products])
        logger.debug(f"Cantidad histórica calculada: {cantidad_historica}")

        context['cantidad_historica'] = cantidad_historica
        return context
    
class ProductList(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    model = Products
    template_name = "inventory/product_list.html"
    context_object_name = "products"
    permission_required = 'inventory.view_products'
    
class ProductCreate(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    model = Products
    template_name = "inventory/product_create.html"
    form_class = ProductsForm
    success_url = reverse_lazy('inventory:product_list')
    permission_required = 'inventory.add_products'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        product_name = form.instance.name
        messages.success(self.request, f"Producto '{product_name}' creado exitosamente.")
        return response

    def form_invalid(self, form):
        logger.error("Error creating product: %s", form.errors)
        messages.error(self.request, "Hubo un error al crear el producto. Por favor, intente de nuevo.")
        return self.render_to_response(self.get_context_data(form=form))
    
class ProductUpdate(LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView):
    model = Products
    template_name = "inventory/product_update.html"
    form_class = ProductsForm
    success_url = reverse_lazy('inventory:product_list')
    permission_required = 'inventory.change_products'
    
    def form_valid(self, form):
        product_name = self.get_object().name
        response = super().form_valid(form)
        messages.success(self.request, f"Producto '{product_name}' actualizado exitosamente.")
        return response
    
    def form_invalid(self, form):
        logger.error("Error updating product: %s", form.errors)
        messages.error(self.request, "Hubo un error al actualizar el producto. Por favor, intente de nuevo.")
        return self.render_to_response(self.get_context_data(form=form))

class ProductDelete(LoginRequiredMixin, SuccessMessageMixin,PermissionRequiredMixin,  generic.DeleteView):
    model = Products
    template_name = "inventory/product_delete.html"
    success_url = reverse_lazy('inventory:product_list')
    permission_required = 'inventory.delete_products'
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        product_name = self.object.name
        success_message = f"Producto '{product_name}' eliminado exitosamente."
        messages.success(self.request, success_message)
        return self.delete(request, *args, **kwargs)
    