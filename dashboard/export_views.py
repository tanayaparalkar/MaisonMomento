import csv
from django.http import HttpResponse
from .decorators import staff_member_required
from django.utils import timezone
from django.db.models import Sum

from apps.sales.models import Order
from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.inventory.services import get_inventory_summary

@staff_member_required
def export_data(request):
    """
    Synchronously generates CSV exports for different dashboard datasets.
    """
    export_type = request.GET.get('type')
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="maison_momento_{export_type}_{timestamp}.csv"'
    
    writer = csv.writer(response)
    
    if export_type == "orders":
        writer.writerow(['Order Number', 'Date', 'Customer Email', 'Status', 'Payment Status', 'Total'])
        orders = Order.objects.select_related('customer').all().order_by('-created_at')
        for order in orders:
            writer.writerow([
                order.order_number, 
                order.created_at.strftime("%Y-%m-%d %H:%M"),
                order.customer.email if order.customer else 'Guest',
                order.get_order_status_display(),
                order.get_payment_status_display(),
                order.total
            ])
            
    elif export_type == "inventory":
        writer.writerow(['SKU', 'Product Name', 'Category', 'Stock', 'Status', 'Price'])
        products = Product.objects.select_related('category').all().order_by('name')
        for product in products:
            writer.writerow([
                product.sku,
                product.name,
                product.category.name if product.category else '—',
                product.stock,
                product.inventory_status_label,
                product.price
            ])
            
    elif export_type == "customers":
        writer.writerow(['ID', 'Name', 'Email', 'Joined', 'Total Orders', 'Total Spent'])
        customers = Customer.objects.prefetch_related('orders').all().order_by('-created_at')
        for customer in customers:
            writer.writerow([
                customer.id,
                customer.full_name,
                customer.email,
                customer.created_at.strftime("%Y-%m-%d"),
                customer.number_of_orders,
                customer.total_spent
            ])
            
    elif export_type == "sales_summary":
        writer.writerow(['Metric', 'Value'])
        
        # Simple aggregated summary
        total_orders = Order.objects.count()
        total_revenue = Order.objects.filter(payment_status='paid').aggregate(t=Sum('total'))['t'] or 0
        
        inventory_summary = get_inventory_summary()
        
        writer.writerow(['Total Orders (All Time)', total_orders])
        writer.writerow(['Total Revenue (Paid)', total_revenue])
        writer.writerow(['Total Active Products', inventory_summary['total_products']])
        writer.writerow(['Out of Stock Products', inventory_summary['out_of_stock_count']])
        
    else:
        writer.writerow(['Error: Unknown export type requested.'])

    return response
