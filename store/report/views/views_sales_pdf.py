import io
import json
import sys
import uuid
from collections import deque
from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.db.models import Count, Sum
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.template.loader import get_template, render_to_string
from django.utils import timezone
from django.views.generic import FormView, ListView, View
from django.views.generic.edit import FormView

from openpyxl import Workbook
from openpyxl.styles import Alignment
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from xhtml2pdf import pisa

from inventory.models import *
from pos.models import *
from report.forms import SalesReportForm, YearMonthForm, YearForm, DayForm, DateRangeForm, MONTH_CHOICES, MONTH_NAMES

# Constantes globales

MONTH_NAMES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


# Funciones auxiliares
def is_leap_year(year):
    """
    Función para verificar si un año es bisiesto.
    """
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def is_valid_day(year, month, day):
    """
    Función para verificar si el día es válido para el mes y el año dados.
    """
    if month in [4, 6, 9, 11]:
        return day <= 30
    elif month == 2:
        if is_leap_year(year):
            return day <= 29
        else:
            return day <= 28
    else:
        return day <= 31

class SalesReportView(LoginRequiredMixin, PermissionRequiredMixin,ListView):
    model = Sales
    template_name = 'report/sales_report.html'
    context_object_name = 'sales'
    form_class = SalesReportForm
    permission_required = 'report.view_sales' 

    def get_queryset(self):
        # Obtenemos todas las ventas inicialmente
        queryset = super().get_queryset()
        form = self.form_class(self.request.GET)

        # Filtramos las ventas según los datos del formulario
        if form.is_valid():
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            customer = form.cleaned_data.get('customer')

            if start_date:
                queryset = queryset.filter(date_added__gte=start_date)
            if end_date:
                queryset = queryset.filter(date_added__lte=end_date)
            if customer:
                queryset = queryset.filter(customer__icontains=customer)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.form_class(self.request.GET)

        context['form'] = form

        # Calcular el conteo general de clientes
        total_clientes = self.get_queryset().values('id').distinct().count()

        # Calcular la cantidad total de ítems vendidos
        total_items_vendidos = salesItems.objects.filter(sale__in=self.get_queryset()).aggregate(total=Sum('qty'))['total']

        # Calcular la cantidad total de ingresos
        total_ingresos = self.get_queryset().aggregate(total=Sum('grand_total'))['total']
        total_ingresos = self.format_total(total_ingresos)

        # Obtener todas las ventas ordenadas por fecha
        sales = self.get_queryset()

        # Preparar los datos de ventas
        sale_data = []
        for sale in sales:
            data = {}
            for field in sale._meta.get_fields(include_parents=False):
                if field.related_model is None:
                    data[field.name] = getattr(sale, field.name)

            items = salesItems.objects.filter(sale=sale).all()
            products_list = {}
            for item in items:
                product_name = item.product.name
                if product_name in products_list:
                    products_list[product_name] += item.qty
                else:
                    products_list[product_name] = item.qty

            data['products_list'] = products_list
            data['total_items_sold'] = sum(products_list.values())

            if 'tax_amount' in data:
                data['tax_amount'] = format(float(data['tax_amount']), '.2f')

            sale_data.append(data)

        # Agregar los cálculos al contexto
        context['page_title'] = 'Sales Transactions'
        context['sale_data'] = sale_data
        context['total_clientes'] = total_clientes
        context['total_items_vendidos'] = total_items_vendidos
        context['total_ingresos'] = total_ingresos

        return context

    def format_total(self, total):
        # Implementa tu lógica de formato aquí
        return total

class GeneratePDFSalesView(View):
    def get(self, request, *args, **kwargs):
        user = request.user  # Obtiene el usuario autenticado

        sale_data = Sales.objects.order_by('date_added').all()

        total_clientes = Sales.objects.values('id').distinct().count()
        total_items_vendidos = 0
        total_ingresos = sum(sale.grand_total for sale in sale_data)

        sale_details = []

        for sale in sale_data:
            items = salesItems.objects.filter(sale=sale)
            products_list = {}

            for item in items:
                product_name = item.product.name
                if product_name in products_list:
                    products_list[product_name] += item.qty
                else:
                    products_list[product_name] = item.qty
                total_items_vendidos += item.qty

            sale_details.append({
                'cliente': sale.cliente,
                'date_added': sale.date_added,
                'products_list': products_list,
                'grand_total': sale.grand_total,
                'total_items_sold': sum(products_list.values())
            })

        current_date = datetime.now()
        unique_key = str(uuid.uuid4())

        # Renderiza el HTML de la plantilla con los datos
        html_string = render_to_string('report/sales_pdf.html', {
            'sale_data': sale_details,
            'total_clientes': total_clientes,
            'total_items_vendidos': total_items_vendidos,
            'total_ingresos': total_ingresos,
            'current_date': current_date,
            'username': user.username,  # Añade el nombre del usuario al contexto
            'unique_key': unique_key,  # Añade la clave única al contexto
        })

        # Crear una respuesta HTTP con el PDF
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            io.BytesIO(html_string.encode("UTF-8")), dest=pdf_buffer, encoding='UTF-8')

        # Si hay errores, muestra una cadena de errores en el PDF
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html_string + '</pre>')

        # Generar nombre del archivo con fecha y hora
        filename = f"reporte_ventas_general_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_buffer.getvalue())

        return response
# Asumiendo que tienes un formulario YearForm definido

class GeneratePDFSalesYearView(FormView):
    form_class = YearForm  # Asegúrate de tener definido tu formulario YearForm
    template_name = 'report/sales_pdf_year.html'  # Asegúrate de que la ruta sea correcta

    def form_valid(self, form):
        year = form.cleaned_data['year']
        # Filtrar las ventas por año y obtener los totales directamente
        sales = Sales.objects.filter(date_added__year=year)
        total_clientes = sales.values('cliente').distinct().count()
        total_items_vendidos = salesItems.objects.filter(sale__in=sales).aggregate(total=Sum('qty'))['total']
        total_ingresos = sales.aggregate(total=Sum('grand_total'))['total']

        # Detalles de las ventas para el informe
        sale_details = []
        for sale in sales:
            items = salesItems.objects.filter(sale=sale)
            products_list = {}
            for item in items:
                product_name = item.product.name
                products_list[product_name] = products_list.get(product_name, 0) + item.qty
            sale_details.append({
                'cliente': sale.cliente,
                'date_added': sale.date_added,
                'products_list': products_list,
                'grand_total': sale.grand_total,
                'total_items_sold': sum(products_list.values())
            })

        # Generación del PDF usando xhtml2pdf
        current_date = timezone.now()
        unique_key = str(uuid.uuid4())
        html_string = render_to_string('report/sales_pdf_year.html', {
            'sale_data': sale_details,
            'total_clientes': total_clientes,
            'total_items_vendidos': total_items_vendidos,
            'total_ingresos': total_ingresos,
            'current_date': current_date,
            'username': self.request.user.username,
            'unique_key': unique_key,
            'year': year,
        })

        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.BytesIO(html_string.encode("UTF-8")), dest=pdf_buffer, encoding='UTF-8')

        if pisa_status.err:
            return HttpResponse('Hubo errores al generar el PDF.')

        filename = f"reporte_ventas_anual_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_buffer.getvalue())

        return response


class GeneratePDFSalesMonthView(FormView):
    form_class = YearMonthForm
    template_name = 'report/sales_report.html'

    def form_valid(self, form):
        year = form.cleaned_data['year']
        month = form.cleaned_data['month']
        
        try:
            month = int(month)
            month_name = MONTH_CHOICES[month - 1][1]
        except ValueError:
            return HttpResponseBadRequest("El año o el mes proporcionados no son válidos.")

        sales = Sales.objects.filter(date_added__year=year, date_added__month=month)
        total_clientes = sales.values('id').distinct().count()
        total_items_vendidos = salesItems.objects.filter(sale__in=sales).aggregate(total=Sum('qty'))['total']
        total_ingresos = sales.aggregate(total=Sum('grand_total'))['total']

        sale_details = []
        for sale in sales:
            items = salesItems.objects.filter(sale=sale)
            products_list = {}
            for item in items:
                product_name = item.product.name
                products_list[product_name] = products_list.get(product_name, 0) + item.qty
            sale_details.append({
                'cliente': sale.cliente,
                'date_added': sale.date_added,
                'products_list': products_list,
                'grand_total': sale.grand_total,
                'total_items_sold': sum(products_list.values())
            })

        current_date = datetime.now()
        unique_key = str(uuid.uuid4())

        html_string = render_to_string('report/sales_pdf_month.html', {
            'sale_data': sale_details,
            'total_clientes': total_clientes,
            'total_items_vendidos': total_items_vendidos,
            'total_ingresos': total_ingresos,
            'current_date': current_date,
            'username': self.request.user.username,
            'unique_key': unique_key,
            'year': year,
            'month': month_name,
        })

        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.BytesIO(html_string.encode("UTF-8")), dest=pdf_buffer, encoding='UTF-8')

        if pisa_status.err:
            return HttpResponse('Hubo errores al generar el PDF.')

        filename = f"reporte_ventas_mensual_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_buffer.getvalue())

        return response


class SalesReportCustomView(FormView):
    form_class = DateRangeForm
    template_name = 'report/sales_report.html'

    def form_valid(self, form):
        fecha_desde = form.cleaned_data['fecha_desde']
        fecha_hasta = form.cleaned_data['fecha_hasta']

        if fecha_desde > fecha_hasta:
            return HttpResponseBadRequest("La fecha de inicio no puede ser mayor que la fecha de fin.")

        sales = Sales.objects.filter(date_added__range=(fecha_desde, fecha_hasta))
        total_clientes = sales.values('id').distinct().count()
        total_items_vendidos = salesItems.objects.filter(sale__in=sales).aggregate(total=Sum('qty'))['total']
        total_ingresos = sales.aggregate(total=Sum('grand_total'))['total']

        sale_details = []
        for sale in sales:
            items = salesItems.objects.filter(sale=sale)
            products_list = {}
            for item in items:
                product_name = item.product.name
                products_list[product_name] = products_list.get(product_name, 0) + item.qty
            sale_details.append({
                'cliente': sale.cliente,
                'date_added': sale.date_added,
                'products_list': products_list,
                'grand_total': sale.grand_total,
                'total_items_sold': sum(products_list.values())
            })

        current_date = datetime.now()
        unique_key = str(uuid.uuid4())

        html_string = render_to_string('posApp/sales_pdf_custom.html', {
            'sale_data': sale_details,
            'total_clientes': total_clientes,
            'total_items_vendidos': total_items_vendidos,
            'total_ingresos': total_ingresos,
            'current_date': current_date,
            'username': self.request.user.username,
            'unique_key': unique_key,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
        })

        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.BytesIO(html_string.encode("UTF-8")), dest=pdf_buffer, encoding='UTF-8')

        if pisa_status.err:
            return HttpResponse('Hubo errores al generar el PDF.')

        filename = f"reporte_ventas_personalizado_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_buffer.getvalue())

        return  



class GeneratePDFSalesDayView(FormView):
    template_name = 'report/sales_report.html'
    form_class = DayForm

    def form_valid(self, form):
        year = form.cleaned_data['year']
        month = form.cleaned_data['month']
        day = form.cleaned_data['day']

        month_name = MONTH_NAMES[int(month) - 1]

        # Validar la fecha
        if not self.is_valid_day(year, int(month), day):
            messages.error(self.request, "La fecha ingresada no es válida.")
            return self.form_invalid(form)

        sales = Sales.objects.filter(date_added__year=year, date_added__month=month, date_added__day=day)
        total_clientes = sales.values('id').distinct().count()
        total_items_vendidos = salesItems.objects.filter(sale__in=sales).aggregate(total=Sum('qty'))['total']
        total_ingresos = sales.aggregate(total=Sum('grand_total'))['total']

        sale_details = []
        for sale in sales:
            items = salesItems.objects.filter(sale=sale)
            products_list = {}
            for item in items:
                product_name = item.product.name
                products_list[product_name] = products_list.get(product_name, 0) + item.qty
            sale_details.append({
                'cliente': sale.cliente,
                'date_added': sale.date_added,
                'products_list': products_list,
                'grand_total': sale.grand_total,
                'total_items_sold': sum(products_list.values())
            })

        current_date = datetime.now()
        unique_key = str(uuid.uuid4())

        html_string = render_to_string('report/sales_pdf_day.html', {
            'sale_data': sale_details,
            'total_clientes': total_clientes,
            'total_items_vendidos': total_items_vendidos,
            'total_ingresos': total_ingresos,
            'current_date': current_date,
            'username': self.request.user.username,
            'unique_key': unique_key,
            'year': year,
            'month_name': month_name,
            'day': day,
        })

        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            io.BytesIO(html_string.encode("UTF-8")), 
            dest=pdf_buffer, 
            encoding='UTF-8'
        )

        if pisa_status.err:
            return HttpResponse('Hubo errores al generar el PDF.')

        filename = f"reporte_ventas_diario_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"
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