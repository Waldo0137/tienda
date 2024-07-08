from purchase.models import PurchaseProduct
from report.forms import *

from django.views.generic import ListView, View
from django.views.generic.edit import FormView
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Sum
from xhtml2pdf import pisa
import datetime
import uuid
import io
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
MONTH_NAMES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


def is_leap_year(year):
    
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def is_valid_day(year, month, day):
    
    if month in [4, 6, 9, 11]:
        return day <= 30
    elif month == 2:
        if is_leap_year(year):
            return day <= 29
        else:
            return day <= 28
    else:
        return day <= 31



class PurchaseReportView(LoginRequiredMixin, PermissionRequiredMixin,ListView):
    model = PurchaseProduct
    template_name = 'report/purchase_report.html'
    context_object_name = 'purchases'
    form_class = PurchaseReportForm
    permission_required = 'report.view_purchase' 

    def get_queryset(self):
        queryset = super().get_queryset()
        form = self.form_class(self.request.GET)

        if form.is_valid():
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            supplier = form.cleaned_data.get('supplier')

            if start_date:
                queryset = queryset.filter(date_added__gte=start_date)
            if end_date:
                queryset = queryset.filter(date_added__lte=end_date)
            if supplier:
                queryset = queryset.filter(supplier__name__icontains=supplier)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.form_class(self.request.GET)
        context['form'] = form

        queryset = self.get_queryset()

        
        grouped_data = {}
        for item in queryset:
            key = (item.supplier, item.date_added.date())
            if key not in grouped_data:
                grouped_data[key] = {
                    'supplier': item.supplier,
                    'date_added': item.date_added,
                    'products': {},
                    'total': 0,
                    'total_items_bought': 0
                }

            product_name = item.product.name
            if product_name not in grouped_data[key]['products']:
                grouped_data[key]['products'][product_name] = {
                    'qty': 0,
                    'cost': 0
                }

            grouped_data[key]['products'][product_name]['qty'] += item.qty
            grouped_data[key]['products'][product_name]['cost'] += item.cost

            grouped_data[key]['total'] += item.total
            grouped_data[key]['total_items_bought'] += item.qty

        
        purchase_data = []
        for key, data in grouped_data.items():
            purchase_data.append({
                'supplier': data['supplier'],
                'date_added': data['date_added'],
                'product_list': data['products'],
                'grand_total': data['total'],
                'total_items_bought': data['total_items_bought'],
            })

        
        total_suppliers = queryset.values('supplier').distinct().count()
        total_items_comprados = queryset.aggregate(total=Sum('qty'))['total']
        total_costos = queryset.aggregate(total=Sum('total'))['total']

        context['page_title'] = 'Purchase Transactions'
        context['purchase_data'] = purchase_data
        context['total_suppliers'] = total_suppliers
        context['total_items_comprados'] = total_items_comprados
        context['total_costos'] = self.format_total(total_costos)

        return context

    def format_total(self, total):
        return f"{total:,.2f}"


class GeneratePDFPurchaseView(View):
    def get(self, request, *args, **kwargs):
        user = request.user  

        form = YearReportForm(request.GET)
        if form.is_valid():
            year = form.cleaned_data['year']
            start_date = datetime.datetime(year, 1, 1)
            end_date = datetime.datetime(year, 12, 31, 23, 59, 59)
            purchase_data = PurchaseProduct.objects.filter(date_added__range=(start_date, end_date)).order_by('date_added')
        else:
            purchase_data = PurchaseProduct.objects.order_by('date_added').all()

        total_suppliers = PurchaseProduct.objects.values('supplier').distinct().count()
        total_items_comprados = 0
        total_costos = sum(purchase.total for purchase in purchase_data)

        purchase_details = []

        for purchase in purchase_data:
            items = PurchaseProduct.objects.filter(id=purchase.id)
            products_list = {}
            total_items = 0  

            for item in items:
                product_name = item.product.name
                if product_name in products_list:
                    products_list[product_name] += item.cost
                else:
                    products_list[product_name] = item.cost
                total_items_comprados += item.qty
                total_items += item.qty  

            purchase_details.append({
                'supplier': purchase.supplier,
                'date_added': purchase.date_added,
                'products_list': products_list,
                'grand_total': purchase.total,
                'total_items_bought': total_items  
            })

        current_date = datetime.datetime.now()
        unique_key = str(uuid.uuid4())

        
        html_string = render_to_string('report/purchase_pdf.html', {
            'purchase_data': purchase_details,
            'total_suppliers': total_suppliers,
            'total_items_comprados': total_items_comprados,
            'total_costos': total_costos,
            'current_date': current_date,
            'username': user.username,  
            'unique_key': unique_key,  
        })

        
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            io.BytesIO(html_string.encode("UTF-8")), dest=pdf_buffer, encoding='UTF-8')

        
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html_string + '</pre>')

        
        filename = f"reporte_compras_general_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_buffer.getvalue())

        return response




class YearlyPDFPurchaseView(FormView):
    form_class = YearReportForm
    template_name = 'report/purchase_pdf_year.html'  

    def form_valid(self, form):
        year = form.cleaned_data['year']
        
        purchases = PurchaseProduct.objects.filter(date_added__year=year)
        total_suppliers = purchases.values('supplier').distinct().count()
        total_items_comprados = purchases.aggregate(total=Sum('qty'))['total']
        total_costos = purchases.aggregate(total=Sum('total'))['total']

        
        purchase_details = []
        for purchase in purchases:
            items = PurchaseProduct.objects.filter(id=purchase.id)
            total_items = 0 
            products_list = {}
            for item in items:
                
                product_name = item.product.name
                if product_name in products_list:
                    products_list[product_name] += item.cost
                else:
                    products_list[product_name] = item.cost
                total_items_comprados += item.qty
                total_items += item.qty 
            purchase_details.append({
                'supplier': purchase.supplier,
                'date_added': purchase.date_added,
                'products_list': products_list,
                'grand_total': purchase.total,
                'total_items_bought': total_items
            })

        current_date = timezone.now()
        unique_key = str(uuid.uuid4())
        html_string = render_to_string('report/purchase_pdf_year.html', {
            'purchase_data': purchase_details,
            'total_suppliers': total_suppliers,
            'total_items_comprados': total_items_comprados,
            'total_costos': total_costos,
            'current_date': current_date,
            'username': self.request.user.username,
            'unique_key': unique_key,
            'year': year,
        })

        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.BytesIO(html_string.encode("UTF-8")), dest=pdf_buffer, encoding='UTF-8')

        if pisa_status.err:
            return HttpResponse('Hubo errores al generar el PDF.')

        filename = f"reporte_compras_anual_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_buffer.getvalue())

        return response



class MonthlyPDFPurchaseView(FormView):
    form_class = MonthYearReportForm
    template_name = 'report/purchase_pdf_month.html'  

    def form_valid(self, form):
        year = form.cleaned_data['year']
        month = form.cleaned_data['month']
        
        try:
            month = int(month)
            month_name = MONTH_CHOICES[month - 1][1]
        except ValueError:
            return HttpResponseBadRequest("El año o el mes proporcionados no son válidos.")

        
        purchases = PurchaseProduct.objects.filter(date_added__year=year, date_added__month=month)
        total_suppliers = purchases.values('supplier').distinct().count()
        total_items_comprados = purchases.aggregate(total=Sum('qty'))['total']
        total_costos = purchases.aggregate(total=Sum('total'))['total']

        
        purchase_details = []
        for purchase in purchases:
            items = PurchaseProduct.objects.filter(id=purchase.id)
            total_items = 0
            products_list = {}
            for item in items:
                product_name = item.product.name
                if product_name in products_list:
                    products_list[product_name] += item.cost
                else:
                    products_list[product_name] = item.cost
                total_items_comprados += item.qty
                total_items += item.qty
            purchase_details.append({
                'supplier': purchase.supplier,
                'date_added': purchase.date_added,
                'products_list': products_list,
                'grand_total': purchase.total,
                'total_items_bought': total_items
            })

        
        current_date = timezone.now()
        unique_key = str(uuid.uuid4())
        html_string = render_to_string('report/purchase_pdf_month.html', {
            'purchase_data': purchase_details,
            'total_suppliers': total_suppliers,
            'total_items_comprados': total_items_comprados,
            'total_costos': total_costos,
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

        filename = f"reporte_compras_mensual_{year}_{month}_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_buffer.getvalue())

        return response




class DailyPDFPurchaseView(FormView):
    form_class = DayMonthYearReportForm  
    template_name = 'report/purchase_pdf_day.html'  

    def form_valid(self, form):
        year = form.cleaned_data['year']
        month = form.cleaned_data['month']
        day = form.cleaned_data['day']
        
        month_name = MONTH_NAMES[int(month) - 1]
        
        if not self.is_valid_day(year, int(month), day):
            messages.error(self.request, "La fecha ingresada no es válida.")
            return self.form_invalid(form)
        
        
        purchases = PurchaseProduct.objects.filter(date_added__year=year, date_added__month=month, date_added__day=day)
        total_suppliers = purchases.values('supplier').distinct().count()
        total_items_comprados = purchases.aggregate(total=Sum('qty'))['total']
        total_costos = purchases.aggregate(total=Sum('total'))['total']

        
        purchase_details = []
        for purchase in purchases:
            items = PurchaseProduct.objects.filter(id=purchase.id)
            total_items = 0
            products_list = {}
            for item in items:
                product_name = item.product.name
                if product_name in products_list:
                    products_list[product_name] += item.cost
                else:
                    products_list[product_name] = item.cost
                total_items_comprados += item.qty
                total_items += item.qty
            purchase_details.append({
                'supplier': purchase.supplier,
                'date_added': purchase.date_added,
                'products_list': products_list,
                'grand_total': purchase.total,
                'total_items_bought': total_items
            })

        
        current_date = timezone.now()
        unique_key = str(uuid.uuid4())
        html_string = render_to_string('report/purchase_pdf_day.html', {
            'purchase_data': purchase_details,
            'total_suppliers': total_suppliers,
            'total_items_comprados': total_items_comprados,
            'total_costos': total_costos,
            'current_date': current_date,
            'username': self.request.user.username,
            'unique_key': unique_key,
            'year': year,
            'month': month_name,
            'day': day,
        })

        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.BytesIO(html_string.encode("UTF-8")), dest=pdf_buffer, encoding='UTF-8')

        if pisa_status.err:
            return HttpResponse('Hubo errores al generar el PDF.')

        filename = f"reporte_compras_diario_{year}_{month}_{day}_{current_date.strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_buffer.getvalue())

        return response

    def is_valid_day(self, year, month, day):
        try:
            datetime.datetime(year, month, day)
            return True
        except ValueError:
            return False