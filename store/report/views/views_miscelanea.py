from purchase.models import * 
from pos.models import *
from inventory.models import *
from report.forms import *

import io
from xhtml2pdf import pisa
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import User
from django.core.mail import send_mail, BadHeaderError
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template, render_to_string
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, FormView

import openpyxl
from openpyxl import Workbook

class MixReportView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Sales
    template_name = 'report/miscelanea_report.html'
    context_object_name = 'sales'
    form_class = SalesReportForm
    permission_required = 'report.view_mix' 
    
class SupplierPDFView(View):
    def get(self, request, *args, **kwargs):
        suppliers = Supplier.objects.all()

        template = get_template('report/mix_suppliers_pdf.html') 
        context = {
            'suppliers': suppliers,
            'current_date': timezone.now(),
        }
        html = template.render(context)
        
        current_date = datetime.now()
        # Convertir HTML a PDF
        pdf_file = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_file)

        if pisa_status.err:
            return HttpResponse('Error al generar el PDF')

        # Configurar la respuesta HTTP con el PDF generado
        pdf_file.seek(0)
        filename = f"lista_proveedores_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response


class SupplierProductPDFView(View):
    def get(self, request, *args, **kwargs):
        suppliers = Supplier.objects.prefetch_related('purchaseproduct_set__product').all()
        context = {
            'suppliers': suppliers,
            'current_date': timezone.now(),
        }
        template = get_template('report/mix_supplier_product_pdf.html')  # Ajusta el nombre del template según tu estructura
        html = template.render(context)
        
        current_date = datetime.now()
        
        pdf_file = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_file)

        if pisa_status.err:
            return HttpResponse('Error al generar el PDF')

        
        pdf_file.seek(0)
        filename = f"lista_proveedores_productos_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        

        return response


class ProductPDFView(View):
    def get(self, request, *args, **kwargs):
        products = Products.objects.all().order_by('name')


        template = get_template('report/mix_products_pdf.html')  
        context = {
            'products': products,
            'current_date': timezone.now(),
        }
        html = template.render(context)

        current_date = datetime.now()
        # Convertir HTML a PDF
        pdf_file = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_file)

        if pisa_status.err:
            return HttpResponse('Error al generar el PDF')

        
        pdf_file.seek(0)
        filename = f"lista_productos_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

class ProductPDFQtyView(View):
    def get(self, request, *args, **kwargs):
        products = Products.objects.all().order_by('name')

        
        template = get_template('report/mix_productsqty_pdf.html') 
        context = {
            'products': products,
            'current_date': timezone.now(),
        }
        html = template.render(context)

        current_date = datetime.now()
        
        pdf_file = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_file)

        if pisa_status.err:
            return HttpResponse('Error al generar el PDF')

        
        pdf_file.seek(0)
        filename = f"lista_productos_detalles_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response
    
    
class MixPDFSalesDayView(FormView):
    template_name = 'report/mix_day_pdf.html'
    form_class = DayForm

    def form_valid(self, form):
        year = int(form.cleaned_data['year'])
        month = int(form.cleaned_data['month'])
        day = int(form.cleaned_data['day'])

        
        start_date = datetime(year, month, day, 3, 0, 0)
        end_date = start_date + timedelta(days=1)

        month_name = MONTH_NAMES[month - 1]
        
        day_name_english = start_date.strftime('%A')  
        day_name = DAYS_OF_WEEK[day_name_english]  
        
        if not self.is_valid_day(year, month, day):
            messages.error(self.request, "La fecha ingresada no es válida.")
            return self.form_invalid(form)

        
        sales = Sales.objects.filter(date_added__gte=start_date, date_added__lt=end_date)
        total_clientes = sales.values('id').distinct().count()
        total_items_vendidos = salesItems.objects.filter(sale__in=sales).aggregate(total=Sum('qty'))['total']
        total_ingresos = sales.aggregate(total=Sum('grand_total'))['total']

        sale_details = []
        total_net_profit = Decimal(0)
        for sale in sales:
            items = salesItems.objects.filter(sale=sale)
            products_list = {}
            net_profit_total = Decimal(0)
            for item in items:
                product_name = item.product.name
                products_list[product_name] = {
                    'qty': item.qty,
                    'price': item.product.price,
                    'cost': item.product.cost,
                }
                item_profit = Decimal(item.qty) * (item.product.price - item.product.cost)
                net_profit_total += item_profit
            total_net_profit += net_profit_total
            sale_details.append({
                'cliente': sale.cliente,
                'date_added': sale.date_added,
                'products_list': products_list,
                'grand_total': sale.grand_total,
                'net_profit': net_profit_total
            })

        current_date = datetime.now()
        unique_key = str(uuid.uuid4())

        html_string = render_to_string('report/mix_day_pdf.html', {
            'sale_data': sale_details,
            'total_clientes': total_clientes,
            'total_items_vendidos': total_items_vendidos,
            'total_ingresos': total_ingresos,
            'total_net_profit': total_net_profit,
            'current_date': current_date,
            'username': self.request.user.username,
            'unique_key': unique_key,
            'year': year,
            'month_name': month_name,
            'day': day,
            'day_name':day_name,
        })

        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            io.BytesIO(html_string.encode("UTF-8")), 
            dest=pdf_buffer, 
            encoding='UTF-8'
        )

        if pisa_status.err:
            return HttpResponse('Hubo errores al generar el PDF.')

        filename = f"reporte_cierreventas_diario_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_buffer.getvalue())

        return response

    def is_valid_day(self, year, month, day):
        try:
            datetime(year, month, day)
            return True
        except ValueError:
            return False


class MixTramoPDFSalesDayView(FormView):
    template_name = 'report/mix_tramo_day_pdf.html'
    form_class = DayTramoForm

    def form_valid(self, form):
        start_year = int(form.cleaned_data['start_year'])
        start_month = int(form.cleaned_data['start_month'])
        start_day = int(form.cleaned_data['start_day'])
        end_year = int(form.cleaned_data['end_year'])
        end_month = int(form.cleaned_data['end_month'])
        end_day = int(form.cleaned_data['end_day'])

        
        if not self.is_valid_date_range(start_year, start_month, start_day, end_year, end_month, end_day):
            messages.error(self.request, "La fecha de inicio no puede ser mayor que la fecha de fin.")
            return self.form_invalid(form)

        
        start_date = datetime(start_year, start_month, start_day, 3, 0, 0)
        end_date = datetime(end_year, end_month, end_day, 3, 0, 0) + timedelta(days=1)
        
        end_date_display = datetime(end_year, end_month, end_day)
        
        if not self.is_valid_day(start_year, start_month, start_day) or not self.is_valid_day(end_year, end_month, end_day):
            messages.error(self.request, "Una de las fechas ingresadas no es válida.")
            return self.form_invalid(form)
        day_name_start_english = start_date.strftime('%A')  
        day_name_start = DAYS_OF_WEEK[day_name_start_english]
        day_name_end_english = end_date_display.strftime('%A')
        day_name_end = DAYS_OF_WEEK[day_name_end_english]  
        
        sales = Sales.objects.filter(date_added__gte=start_date, date_added__lt=end_date)
        total_clientes = sales.values('id').distinct().count()
        total_items_vendidos = salesItems.objects.filter(sale__in=sales).aggregate(total=Sum('qty'))['total']
        total_ingresos = sales.aggregate(total=Sum('grand_total'))['total']

        sale_details = []
        total_net_profit = Decimal(0)
        for sale in sales:
            items = salesItems.objects.filter(sale=sale)
            products_list = {}
            net_profit_total = Decimal(0)
            for item in items:
                product_name = item.product.name
                products_list[product_name] = {
                    'qty': item.qty,
                    'price': item.product.price,
                    'cost': item.product.cost,
                }
                item_profit = Decimal(item.qty) * (item.product.price - item.product.cost)
                net_profit_total += item_profit
            total_net_profit += net_profit_total
            sale_details.append({
                'cliente': sale.cliente,
                'date_added': sale.date_added,
                'products_list': products_list,
                'grand_total': sale.grand_total,
                'net_profit': net_profit_total
            })

        current_date = datetime.now()
        unique_key = str(uuid.uuid4())

        html_string = render_to_string('report/mix_tramo_day_pdf.html', {
            'sale_data': sale_details,
            'total_clientes': total_clientes,
            'total_items_vendidos': total_items_vendidos,
            'total_ingresos': total_ingresos,
            'total_net_profit': total_net_profit,
            'current_date': current_date,
            'username': self.request.user.username,
            'unique_key': unique_key,
            'start_year': start_year,
            'start_month': start_month,
            'start_day': start_day,
            'end_year': end_year,
            'end_month': end_month,
            'end_day': end_day,
            'day_name_start':day_name_start,
            'day_name_end':day_name_end,
        })

        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            io.BytesIO(html_string.encode("UTF-8")), 
            dest=pdf_buffer, 
            encoding='UTF-8'
        )

        if pisa_status.err:
            return HttpResponse('Hubo errores al generar el PDF.')

        filename = f"reporte_ventas_tramo_diario_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_buffer.getvalue())

        return response

    def is_valid_day(self, year, month, day):
        try:
            datetime(year, month, day)
            return True
        except ValueError:
            return False

    def is_valid_date_range(self, start_year, start_month, start_day, end_year, end_month, end_day):
        start_date = datetime(start_year, start_month, start_day)
        end_date = datetime(end_year, end_month, end_day)
        return start_date <= end_date


