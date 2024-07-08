from django.urls import path
from .views.views_sales_pdf import *
from .views.views_sales_excel import *
from .views.views_purchase_pdf import *
from .views.views_purchase_excel import *
from .views.views_profit_pdf import *
from .views.views_profit_excel import *
from .views.views_miscelanea import *
from .views.views_mix_excel import *
app_name = 'report'

urlpatterns = [
    # Reportes PDF
    path('sales_report/', SalesReportView.as_view(), name='sales_report'),
    path('generate-pdf-sales/', GeneratePDFSalesView.as_view(), name='generate_pdf_sales'),
    path('generate-pdf-sales-year/', GeneratePDFSalesYearView.as_view(), name='generate_pdf_sales_year'),
    path('generate-pdf-sales-month/', GeneratePDFSalesMonthView.as_view(), name='generate_pdf_sales_month'),
    path('generatepdf_sales_day/', GeneratePDFSalesDayView.as_view(), name='generatepdf_sales_day'),
    path('sales-report-custom/', SalesReportCustomView.as_view(), name='sales_report_custom'),

    # # Reportes Excel
    path('generate_excel_sales/', GenerateExcelSalesView.as_view(), name='generate_excel_sales'),
    path('generate_excel_sales_year/', GenerateExcelSalesYearView.as_view(), name='generate_excel_sales_year'),
    path('generate_excel_sales_month/', GenerateExcelSalesMonthView.as_view(), name='generate_excel_sales_month'),
    path('generate_excel_sales_day/', GenerateExcelSalesDayView.as_view(), name='generate_excel_sales_day'),
    
    #Reporte Compras    
    path('reporte_compras/', PurchaseReportView.as_view(), name='reporte_compras'),
    path('generate-pdf-purchase/', GeneratePDFPurchaseView.as_view(), name='purchase_pdf'),
    path('generate-pdf-purchase-year/', YearlyPDFPurchaseView.as_view(), name='purchase_year_pdf'),
    path('generate-pdf-purchase-month/', MonthlyPDFPurchaseView.as_view(), name='purchase_month_pdf'),
    path('generate-pdf-purchase-day/', DailyPDFPurchaseView.as_view(), name='purchase_day_pdf'),
    
    path('generate-excel-purchase/', GenerateExcelPurchaseView.as_view(), name='purchase_excel'),
    path('generate-excel-purchase-year/', ExcelPurchaseYearView.as_view(), name='purchase_year_excel'),
    path('generate-excel-purchase-month/', ExcelPurchaseMonthView.as_view(), name='purchase_month_excel'),
    path('generate-excel-purchase-day/', ExcelPurchaseDayView.as_view(), name='purchase_day_excel'),
    
    #Reporte Ganancias
    path('profit-report/', ProfitReportView.as_view(), name='profit_report'),
    path('generate-pdf-profit/', GeneratePDFProfitView.as_view(), name='profit_pdf'),
    path('generate-pdf-profit-year/', YearlyPDFProfitView.as_view(), name='profit_year_pdf'),
    path('generate-pdf-profit-month/', MonthlyPDFProfitView.as_view(), name='profit_month_pdf'),
    path('generate-pdf-profit-day/', DailyPDFProfitView.as_view(), name='profit_day_pdf'),
    
    path('generate-excel-profit/', GenerateExcelProfitView.as_view(), name='profit_excel'),
    path('generate-excel-profit-year/', YearlyExcelProfitView.as_view(), name='profit_year_excel'),
    path('generate-excel-profit-month/', MonthlyExcelProfitView.as_view(), name='profit_month_excel'),
    path('generate-excel-profit-day/', DailyExcelProfitView.as_view(), name='profit_day_excel'),
    
    # miscelanea report
    path('mix-report/', MixReportView.as_view(), name='mix_report'),
    path('supplier-pdf/', SupplierPDFView.as_view(), name='supplier_pdf'),
    path('supplier-product-pdf/', SupplierProductPDFView.as_view(), name='supplier_product_pdf'),
    path('product-pdf/', ProductPDFView.as_view(), name='product_pdf'),
    path('productqty-pdf/', ProductPDFQtyView.as_view(), name='productqty_pdf'),
    
    path('supplier-excel/', SupplierExcelView.as_view(), name='supplier_excel'),
    path('supplier-product-excel/', SupplierProductExcelView.as_view(), name='supplier_product_excel'),
    path('product-excel/', ProductExcelView.as_view(), name='product_excel'),
    path('product-qty-excel/', ProductQtyExcelView.as_view(), name='productqty_excel'),
    
    path('mix-sales-pdf/', MixPDFSalesDayView.as_view(), name='mix_sales_pdf'),
    path('mix-tramo-sales-pdf/', MixTramoPDFSalesDayView.as_view(), name='mixtramo_sales_pdf'),
    
    path('mix-day-excel/', MixExcelSalesDayView.as_view(), name='mix_sales_excel'),
    path('mix-section-day-excel/', MixTramoExcelSalesDayView.as_view(), name='mix_sectionsales_excel'),
]