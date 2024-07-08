from purchase.models import PurchaseProduct  # Importa el modelo PurchaseProduct
from pos.models import Sales, salesItems
from inventory.models import Products
from report.forms import *
from datetime import datetime
from decimal import Decimal
import io
import uuid

from django.conf import settings
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views.generic import ListView, View, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User
from django.core.mail import send_mail, BadHeaderError
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib import messages
from django.utils import timezone

from xhtml2pdf import pisa

import openpyxl

class ProfitReportView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Sales
    template_name = 'report/profit_report.html'
    context_object_name = 'sales'
    form_class = SalesReportForm
    permission_required = 'report.view_profit' 

    def get_queryset(self):
        queryset = super().get_queryset()
        form = self.form_class(self.request.GET)

        if form.is_valid():
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')

            if start_date:
                queryset = queryset.filter(date_added__gte=start_date)
            if end_date:
                queryset = queryset.filter(date_added__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sales = self.get_queryset()

        total_ingresos = self.calculate_total_ingresos(sales)
        total_costos = self.calculate_total_costos(sales)

        total_ingresos_decimal = Decimal(total_ingresos) if total_ingresos is not None else Decimal('0')
        total_costos_decimal = Decimal(total_costos) if total_costos is not None else Decimal('0')

        total_ganancia = total_ingresos_decimal - total_costos_decimal

        context['total_ingresos'] = total_ingresos_decimal
        context['total_costos'] = total_costos_decimal
        context['total_ganancia'] = total_ganancia

        sales_data = self.get_sales_data(sales)
        context['sales_data'] = sales_data

        return context

    def calculate_total_ingresos(self, sales_queryset):
        total_ingresos = sales_queryset.aggregate(total=Sum('grand_total'))['total']
        return total_ingresos or Decimal('0')

    def calculate_total_costos(self, sales_queryset):
        total_costos = Decimal('0')
        sales_items = salesItems.objects.filter(sale__in=sales_queryset)

        for item in sales_items:
            purchase_product = PurchaseProduct.objects.filter(product=item.product).first()
            if purchase_product:
                costo_producto = purchase_product.cost
                total_costos += costo_producto * Decimal(item.qty)

        return total_costos

    def get_sales_data(self, sales_queryset):
        sales_data = []
        for sale in sales_queryset:
            sale_cost = self.calculate_sale_cost(sale)
            sale_profit = Decimal(sale.grand_total) - sale_cost if sale.grand_total is not None else Decimal('0')
            for item in sale.salesitems_set.all():
                purchase_product = PurchaseProduct.objects.filter(product=item.product).first()
                cost_per_unit = Decimal(purchase_product.cost) if purchase_product else Decimal('0')
                qty_comprada = sum([pp.qty for pp in PurchaseProduct.objects.filter(product=item.product)])

                # Añadir entrada de venta
                sales_data.append({
                    'date_added': sale.date_added,
                    'product_name': item.product.name,
                    'qty_vendida': item.qty,
                    'qty_comprada': 0,
                    'cost': cost_per_unit,
                    'venta_total': Decimal(item.qty) * Decimal(item.product.price),  # Venta total por producto
                    'costo_total': sale_cost,
                    'ganancia': sale_profit,
                })


                if purchase_product:
                    sales_data.append({
                        'date_added': purchase_product.date_added,
                        'product_name': item.product.name,
                        'qty_vendida': 0,
                        'qty_comprada': qty_comprada,
                        'cost': cost_per_unit,
                        'venta_total': 0,
                        'costo_total': qty_comprada * cost_per_unit,
                        'ganancia': -qty_comprada * cost_per_unit,
                    })


        sales_data.sort(key=lambda x: x['date_added'])

        return sales_data

    def calculate_sale_cost(self, sale):
        sale_cost = Decimal('0')
        for item in sale.salesitems_set.all():
            purchase_product = PurchaseProduct.objects.filter(product=item.product).first()
            if purchase_product:
                costo_producto = Decimal(purchase_product.cost)
                sale_cost += costo_producto * Decimal(item.qty)
        return sale_cost
    


class GeneratePDFProfitView(View):
    def get(self, request, *args, **kwargs):
        form = SalesReportForm(request.GET or None)
        sales_queryset = self.get_queryset(form)

        total_ingresos = self.calculate_total_ingresos(sales_queryset)
        total_costos = self.calculate_total_costos(sales_queryset)
        total_ingresos_decimal = Decimal(total_ingresos)
        total_costos_decimal = Decimal(total_costos)
        total_ganancia = total_ingresos_decimal - total_costos_decimal


        sales_data, total_utilidades = self.get_sales_data_and_utilities(sales_queryset)

        current_date = datetime.now()
        username = request.user.username
        unique_key = str(uuid.uuid4())

        context = {
            'sales_data': sales_data,
            'total_ingresos': total_ingresos,
            'total_costos': total_costos,
            'total_ganancia': total_ganancia,
            'total_utilidades': total_utilidades,
            'current_date': current_date,
            'username': username,
            'unique_key': unique_key,
        }

        html_string = render_to_string('report/profit_pdf.html', context)

        pdf_file = self.render_pdf(html_string)
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_ganancias_general_{current_date.strftime("%Y%m%d_%H%M%S")}.pdf"'

        return response

    def get_queryset(self, form):
        queryset = Sales.objects.all()

        if form.is_valid():
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')

            if start_date:
                queryset = queryset.filter(date_added__gte=start_date)
            if end_date:
                queryset = queryset.filter(date_added__lte=end_date)

        return queryset

    def calculate_total_ingresos(self, sales_queryset):
        total_ingresos = sales_queryset.aggregate(total=Sum('grand_total'))['total'] or Decimal('0')
        return total_ingresos

    def calculate_total_costos(self, sales_queryset):
        total_costos = Decimal('0')

        for sale in sales_queryset:
            for item in sale.salesitems_set.all():
                purchase_product = PurchaseProduct.objects.filter(product=item.product).first()
                if purchase_product:
                    costo_producto = purchase_product.cost
                    qty_comprada = sum([pp.qty for pp in PurchaseProduct.objects.filter(product=item.product)])
                    costo_total = costo_producto * Decimal(qty_comprada)
                    total_costos += costo_total

        return total_costos

    
    def get_sales_data_and_utilities(self, sales_queryset):
        sales_data = []
        total_utilidades = Decimal(0)
        
        for sale in sales_queryset:
            sale_cost = self.calculate_sale_cost(sale)
            sale_profit = Decimal(sale.grand_total) - sale_cost
            products_list = []

            for item in sale.salesitems_set.all():
                purchase_product = PurchaseProduct.objects.filter(product=item.product).first()
                if purchase_product:
                    cost_per_unit = purchase_product.cost
                    qty_comprada = sum([pp.qty for pp in PurchaseProduct.objects.filter(product=item.product)])
                    total_qty_vendida = item.qty
                    total_qty_comprada = qty_comprada

                    product_ganancia = (Decimal(item.qty) * sale_profit) / Decimal(total_qty_vendida)
                    
                    total_gasto_compras = cost_per_unit * Decimal(total_qty_comprada)    
                    
                    ganancia_bruta = (sale_cost + product_ganancia) - total_gasto_compras
                    total_utilidades += ganancia_bruta
                    products_list.append({
                        'product_name': item.product.name,
                        'cost_per_unit': cost_per_unit,
                        'total_qty_vendida': total_qty_vendida,
                        'total_qty_comprada': total_qty_comprada,
                        'product_ganancia': product_ganancia,
                        'ganancia_estado': 'Positiva' if product_ganancia > 0 else ('Negativa' if product_ganancia < 0 else 'Neutra'),
                        
                        'total_gasto_compras': total_gasto_compras,
                        'ganancia_bruta': ganancia_bruta,
                    })
            
            sales_data.append({
                'date_added': sale.date_added,
                'products_list': products_list,
                'venta_total': Decimal(sale.grand_total),
                'costo_total': sale_cost,
                'ganancia_total': sale_profit,
            })

        return sales_data,total_utilidades

    def calculate_sale_cost(self, sale):
        sale_cost = Decimal('0')
        for item in sale.salesitems_set.all():
            purchase_product = PurchaseProduct.objects.filter(product=item.product).first()
            if purchase_product:
                costo_producto = purchase_product.cost
                sale_cost += costo_producto * Decimal(item.qty)
        return sale_cost

    def render_pdf(self, html_string):
        pdf_file = io.BytesIO()
        pisa.CreatePDF(io.BytesIO(html_string.encode("UTF-8")), dest=pdf_file, encoding='UTF-8')
        pdf_file.seek(0)
        return pdf_file

    

class YearlyPDFProfitView(FormView):
    form_class = YearForm
    template_name = 'report/profit_pdf_year.html'

    def form_valid(self, form):
        year = form.cleaned_data['year']

        # Obtener las ventas filtradas por año
        sales_queryset = Sales.objects.filter(date_added__year=year)

        # Calcular totales
        total_ingresos = sales_queryset.aggregate(total=Sum('grand_total'))['total'] or 0
        total_costos = self.calculate_total_costos(sales_queryset)
        total_ingresos_decimal = Decimal(total_ingresos)
        total_costos_decimal = Decimal(total_costos)
        total_ganancia = total_ingresos_decimal - total_costos_decimal

        sales_data, total_utilidades = self.get_sales_data_and_utilities(sales_queryset)


        current_date = timezone.now()
        username = self.request.user.username
        unique_key = uuid.uuid4()

    
        context = {
            'sales_data': sales_data,
            'total_ingresos': total_ingresos,
            'total_costos': total_costos,
            'total_ganancia': total_ganancia,
            'total_utilidades': total_utilidades,
            'current_date': current_date,
            'username': username,
            'unique_key': unique_key,
            'year': year,
        }

    
        html_string = render_to_string(self.template_name, context)

    
        pdf_file = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.BytesIO(html_string.encode("UTF-8")), dest=pdf_file, encoding='UTF-8')

        if pisa_status.err:
            return HttpResponse('Hubo errores al generar el PDF.')

        pdf_file.seek(0)

    
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_ganancias_anual_{current_date.strftime("%Y%m%d_%H%M%S")}.pdf"'

        return response

    def calculate_total_costos(self, sales_queryset):
        total_costos = 0

        for sale in sales_queryset:
            sale_cost = self.calculate_sale_cost(sale)
            total_costos += sale_cost

        return total_costos

    def get_sales_data_and_utilities(self, sales_queryset):
        sales_data = []
        total_utilidades = Decimal(0)

        for sale in sales_queryset:
            sale_items = salesItems.objects.filter(sale=sale)
            products_list = []

            for item in sale_items:
                purchase_product = PurchaseProduct.objects.filter(product=item.product).first()

                if purchase_product:
                    cost_per_unit = purchase_product.cost
                    total_qty_comprada = PurchaseProduct.objects.filter(product=item.product).aggregate(total_qty=Sum('qty'))['total_qty'] or 0
                    total_qty_vendida = item.qty
                    total_gasto_compras = cost_per_unit * total_qty_comprada
                    
    
                    product_ganancia = Decimal(sale.grand_total) - (cost_per_unit * total_qty_vendida)
                    
    
                    costo_total = self.calculate_sale_cost(sale)

    
                    ganancia_bruta = (costo_total + product_ganancia) - total_gasto_compras
                    total_utilidades += ganancia_bruta
                    products_list.append({
                        'product_name': item.product.name,
                        'cost_per_unit': cost_per_unit,
                        'total_qty_vendida': total_qty_vendida,
                        'total_qty_comprada': total_qty_comprada,
                        'product_ganancia': product_ganancia,
                        'ganancia_estado': 'Positiva' if product_ganancia > 0 else ('Negativa' if product_ganancia < 0 else 'Neutra'),
                        'total_gasto_compras': total_gasto_compras,
                        'ganancia_bruta': ganancia_bruta,
                    })

            sales_data.append({
                'date_added': sale.date_added,
                'products_list': products_list,
                'venta_total': Decimal(sale.grand_total),
                'costo_total': self.calculate_sale_cost(sale),
                'ganancia_total': Decimal(sale.grand_total) - self.calculate_sale_cost(sale),
            })

        return sales_data, total_utilidades

    def calculate_sale_cost(self, sale):
        sale_cost = 0

        for item in sale.salesitems_set.all():
            purchase_product = PurchaseProduct.objects.filter(product=item.product).first()

            if purchase_product:
                sale_cost += purchase_product.cost * item.qty

        return sale_cost


class MonthlyPDFProfitView(FormView):
    form_class = MonthYearReportForm
    template_name = 'report/profit_pdf_month.html'

    def form_valid(self, form):
        year = form.cleaned_data['year']
        month = form.cleaned_data['month']

        
        try:
            month = int(month)
            month_name = MONTH_CHOICES[month - 1][1]
        except ValueError:
            return HttpResponseBadRequest("El año o el mes proporcionados no son válidos.")

    
        sales_queryset = Sales.objects.filter(date_added__year=year, date_added__month=month)


        total_ingresos = sales_queryset.aggregate(total=Sum('grand_total'))['total'] or 0
        total_costos = self.calculate_total_costos(sales_queryset)
        total_ingresos_decimal = Decimal(total_ingresos)
        total_costos_decimal = Decimal(total_costos)
        total_ganancia = total_ingresos_decimal - total_costos_decimal


        sales_data, total_utilidades = self.get_sales_data_and_utilities(sales_queryset)

        current_date = timezone.now()
        username = self.request.user.username
        unique_key = uuid.uuid4()


        context = {
            'sales_data': sales_data,
            'total_ingresos': total_ingresos,
            'total_costos': total_costos,
            'total_ganancia': total_ganancia,
            'total_utilidades': total_utilidades,
            'current_date': current_date,
            'username': username,
            'unique_key': unique_key,
            'year': year,
            'month': month_name,
        }

    
        html_string = render_to_string(self.template_name, context)

    
        pdf_file = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.BytesIO(html_string.encode("UTF-8")), dest=pdf_file, encoding='UTF-8')

        if pisa_status.err:
            return HttpResponse('Hubo errores al generar el PDF.')

        pdf_file.seek(0)

    
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_ganancias_mensual_{current_date.strftime("%Y%m%d_%H%M%S")}.pdf"'

        return response

    def calculate_total_costos(self, sales_queryset):
        total_costos = 0

        for sale in sales_queryset:
            sale_cost = self.calculate_sale_cost(sale)
            total_costos += sale_cost

        return total_costos

    
    def get_sales_data_and_utilities(self, sales_queryset):
        sales_data = []
        total_utilidades = Decimal(0)

        for sale in sales_queryset:
            sale_items = salesItems.objects.filter(sale=sale)
            products_list = []

            for item in sale_items:
                purchase_product = PurchaseProduct.objects.filter(product=item.product).first()

                if purchase_product:
                    cost_per_unit = purchase_product.cost
                    total_qty_comprada = PurchaseProduct.objects.filter(product=item.product).aggregate(total_qty=Sum('qty'))['total_qty'] or 0
                    total_qty_vendida = item.qty
                    total_gasto_compras = cost_per_unit * total_qty_comprada
                    
                
                    product_ganancia = Decimal(sale.grand_total) - (cost_per_unit * total_qty_vendida)
                    
                
                    costo_total = self.calculate_sale_cost(sale)

                
                    ganancia_bruta = (costo_total + product_ganancia) - total_gasto_compras

                    total_utilidades += ganancia_bruta 
                    
                    products_list.append({
                        'product_name': item.product.name,
                        'cost_per_unit': cost_per_unit,
                        'total_qty_vendida': total_qty_vendida,
                        'total_qty_comprada': total_qty_comprada,
                        'product_ganancia': product_ganancia,
                        'ganancia_estado': 'Positiva' if product_ganancia > 0 else ('Negativa' if product_ganancia < 0 else 'Neutra'),
                        'total_gasto_compras': total_gasto_compras,
                        'ganancia_bruta': ganancia_bruta,
                    })

            sales_data.append({
                'date_added': sale.date_added,
                'products_list': products_list,
                'venta_total': Decimal(sale.grand_total),
                'costo_total': self.calculate_sale_cost(sale),
                'ganancia_total': Decimal(sale.grand_total) - self.calculate_sale_cost(sale),
            })

        return sales_data, total_utilidades

    def calculate_sale_cost(self, sale):
        sale_cost = 0

        for item in sale.salesitems_set.all():
            purchase_product = PurchaseProduct.objects.filter(product=item.product).first()

            if purchase_product:
                sale_cost += purchase_product.cost * item.qty

        return sale_cost


class DailyPDFProfitView(FormView):
    form_class = DayMonthYearReportForm
    template_name = 'report/profit_pdf_day.html'

    def form_valid(self, form):
        year = form.cleaned_data['year']
        month = form.cleaned_data['month']
        day = form.cleaned_data['day']
        
        try:
            month = int(month)
            month_name = MONTH_CHOICES[month - 1][1]
        except ValueError:
            return HttpResponseBadRequest("El año o el mes proporcionados no son válidos.")

        
        sales_queryset = Sales.objects.filter(date_added__year=year, date_added__month=month, date_added__day=day)

        
        total_ingresos = sales_queryset.aggregate(total=Sum('grand_total'))['total'] or 0
        total_costos = self.calculate_total_costos(sales_queryset)
        total_ingresos_decimal = Decimal(total_ingresos)
        total_costos_decimal = Decimal(total_costos)
        total_ganancia = total_ingresos_decimal - total_costos_decimal


        
        sales_data, total_utilidades = self.get_sales_data_and_utilities(sales_queryset)

        
        current_date = timezone.now()
        username = self.request.user.username
        unique_key = uuid.uuid4()

        
        context = {
            'sales_data': sales_data,
            'total_ingresos': total_ingresos,
            'total_costos': total_costos,
            'total_ganancia': total_ganancia,
            'total_utilidades': total_utilidades,
            'current_date': current_date,
            'username': username,
            'unique_key': unique_key,
            'year': year,
            'month': month_name,
            'day': day,
        }

    
        html_string = render_to_string(self.template_name, context)

    
        pdf_file = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.BytesIO(html_string.encode("UTF-8")), dest=pdf_file, encoding='UTF-8')

        if pisa_status.err:
            return HttpResponse('Hubo errores al generar el PDF.')

        pdf_file.seek(0)

    
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_ganancias_diaria_{current_date.strftime("%Y%m%d_%H%M%S")}.pdf"'

        return response

    def calculate_total_costos(self, sales_queryset):
        total_costos = 0

        for sale in sales_queryset:
            sale_cost = self.calculate_sale_cost(sale)
            total_costos += sale_cost

        return total_costos

    def get_sales_data_and_utilities(self, sales_queryset):
        sales_data = []
        total_utilidades = Decimal(0)

        for sale in sales_queryset:
            sale_items = salesItems.objects.filter(sale=sale)
            products_list = []

            for item in sale_items:
                purchase_product = PurchaseProduct.objects.filter(product=item.product).first()

                if purchase_product:
                    cost_per_unit = purchase_product.cost
                    total_qty_comprada = PurchaseProduct.objects.filter(product=item.product).aggregate(total_qty=Sum('qty'))['total_qty'] or 0
                    total_qty_vendida = item.qty
                    total_gasto_compras = cost_per_unit * total_qty_comprada
                    
    
                    product_ganancia = Decimal(sale.grand_total) - (cost_per_unit * total_qty_vendida)
                    
    
                    costo_total = self.calculate_sale_cost(sale)

    
                    ganancia_bruta = (costo_total + product_ganancia) - total_gasto_compras

                    total_utilidades += ganancia_bruta  

                    products_list.append({
                        'product_name': item.product.name,
                        'cost_per_unit': cost_per_unit,
                        'total_qty_vendida': total_qty_vendida,
                        'total_qty_comprada': total_qty_comprada,
                        'product_ganancia': product_ganancia,
                        'ganancia_estado': 'Positiva' if product_ganancia > 0 else ('Negativa' if product_ganancia < 0 else 'Neutra'),
                        'total_gasto_compras': total_gasto_compras,
                        'ganancia_bruta': ganancia_bruta,
                    })

            sales_data.append({
                'date_added': sale.date_added,
                'products_list': products_list,
                'venta_total': Decimal(sale.grand_total),
                'costo_total': self.calculate_sale_cost(sale),
                'ganancia_total': Decimal(sale.grand_total) - self.calculate_sale_cost(sale),
            })

        return sales_data, total_utilidades
    
    def calculate_sale_cost(self, sale):
        sale_cost = 0

        for item in sale.salesitems_set.all():
            purchase_product = PurchaseProduct.objects.filter(product=item.product).first()

            if purchase_product:
                sale_cost += purchase_product.cost * item.qty

        return sale_cost
