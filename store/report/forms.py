from django import forms
from pos.models import Sales
from datetime import datetime
from django import forms

from purchase.models import *
MONTH_NAMES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]


MONTH_CHOICES = [(str(i), month) for i, month in enumerate(MONTH_NAMES, 1)]


DAYS_OF_WEEK = {
    'Monday': 'Lunes',
    'Tuesday': 'Martes',
    'Wednesday': 'Miércoles',
    'Thursday': 'Jueves',
    'Friday': 'Viernes',
    'Saturday': 'Sábado',
    'Sunday': 'Domingo'
}

class SalesReportForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    customer = forms.CharField(max_length=100, required=False)


class YearMonthForm(forms.Form):
    year = forms.IntegerField(label="Año", min_value=1900, max_value=2100)
    month = forms.ChoiceField(label="Mes", choices=MONTH_CHOICES)


class YearForm(forms.Form):
    year = forms.IntegerField(label="Año", min_value=1900, max_value=2100)


class DayForm(forms.Form):
    year = forms.IntegerField(label="Año", min_value=1900, max_value=2100)
    month = forms.ChoiceField(label="Mes", choices=MONTH_CHOICES)
    day = forms.IntegerField(label="Día", min_value=1, max_value=31)


class DateRangeForm(forms.Form):
    fecha_desde = forms.DateField(label="Fecha desde", widget=forms.DateInput(attrs={'type': 'date'}))
    fecha_hasta = forms.DateField(label="Fecha hasta", widget=forms.DateInput(attrs={'type': 'date'}))


class ReportForm(forms.Form):
    pass

class MonthReportForm(forms.Form):
    year = forms.IntegerField(label='Año', min_value=1900, max_value=datetime.now().year)
    month = forms.IntegerField(label='Mes', min_value=1, max_value=12)

class DayReportForm(forms.Form):
    year = forms.IntegerField(label='Año', min_value=1900, max_value=datetime.now().year)
    month = forms.IntegerField(label='Mes', min_value=1, max_value=12)
    day = forms.IntegerField(label='Día', min_value=1, max_value=31)

class PurchaseReportForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'type': 'date'}))
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all(), required=False)


class YearReportForm(forms.Form):
    current_year = datetime.now().year
    YEAR_CHOICES = [(year, year) for year in range(current_year - 10, current_year + 1)]

    year = forms.ChoiceField(choices=YEAR_CHOICES, required=True, label="Seleccione el Año", widget=forms.Select)

class MonthYearReportForm(forms.Form):
    year = forms.IntegerField(min_value=2000, max_value=timezone.now().year, label='Año')
    month = forms.IntegerField(min_value=1, max_value=12, label='Mes')

class DayMonthYearReportForm(forms.Form):
    year = forms.IntegerField(min_value=2000, max_value=timezone.now().year, label='Año')
    month = forms.IntegerField(min_value=1, max_value=12, label='Mes')
    day = forms.IntegerField(min_value=1, max_value=31, label='Día')  # Nota: No valida días específicos para cada mes

class DayTramoForm(forms.Form):
    start_year = forms.IntegerField(label='Año Inicio', min_value=2023)
    start_month = forms.ChoiceField(label='Mes Inicio', choices=[
        ('', 'Mes'),
        (1, 'Enero'),
        (2, 'Febrero'),
        (3, 'Marzo'),
        (4, 'Abril'),
        (5, 'Mayo'),
        (6, 'Junio'),
        (7, 'Julio'),
        (8, 'Agosto'),
        (9, 'Septiembre'),
        (10, 'Octubre'),
        (11, 'Noviembre'),
        (12, 'Diciembre'),
    ])
    start_day = forms.IntegerField(label='Día Inicio', min_value=1, max_value=31)

    end_year = forms.IntegerField(label='Año Fin', min_value=2023)
    end_month = forms.ChoiceField(label='Mes Fin', choices=[
        ('', 'Mes'),
        (1, 'Enero'),
        (2, 'Febrero'),
        (3, 'Marzo'),
        (4, 'Abril'),
        (5, 'Mayo'),
        (6, 'Junio'),
        (7, 'Julio'),
        (8, 'Agosto'),
        (9, 'Septiembre'),
        (10, 'Octubre'),
        (11, 'Noviembre'),
        (12, 'Diciembre'),
    ])
    end_day = forms.IntegerField(label='Día Fin', min_value=1, max_value=31)

