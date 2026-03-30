from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .constants import SIZE_CHOICES
from .forms import BreakageForm, ClientForm, DailyIntakeForm, IntakeItemsForm, InventoryAdjustmentForm, SaleForm, SaleItemFormSet
from .models import Breakage, Client, DailyIntake, InventoryAdjustment, InventoryMovement, InventoryService, Sale
from .utils import from_trays, trays_to_eggs


@login_required
def dashboard(request):
    stock = InventoryService.current_stock_by_size()
    stock_rows = []
    for code, _ in SIZE_CHOICES:
        crates, trays = from_trays(stock.get(code, 0))
        stock_rows.append({'size': code, 'crates': crates, 'trays': trays, 'eggs': trays_to_eggs(stock.get(code, 0))})

    today = timezone.localdate()
    todays_intake_items = InventoryMovement.objects.filter(movement_date=today, movement_type='intake')
    todays_sales = Sale.objects.filter(sale_date=today)
    todays_sales_total = todays_sales.aggregate(total=Sum('total_amount')).get('total') or 0
    production_by_size = {code: 0 for code, _ in SIZE_CHOICES}
    for row in todays_intake_items.values('size').annotate(total=Sum('quantity_in_trays')):
        production_by_size[row['size']] = row['total'] or 0
    production_rows = []
    total_production = 0
    for code, _ in SIZE_CHOICES:
        qty = production_by_size[code]
        total_production += qty
        crates, trays = from_trays(qty)
        production_rows.append({'size': code, 'crates': crates, 'trays': trays, 'eggs': trays_to_eggs(qty)})

    context = {
        'stock_rows': stock_rows,
        'today': today,
        'production_rows': production_rows,
        'total_production': from_trays(total_production),
        'total_production_eggs': trays_to_eggs(total_production),
        'todays_sales_total': todays_sales_total,
        'recent_sales': Sale.objects.select_related('client')[:5],
        'recent_intakes': DailyIntake.objects.all()[:5],
        'recent_breakages': Breakage.objects.all()[:5],
        'recent_adjustments': InventoryAdjustment.objects.all()[:5],
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
def stock_view(request):
    stock = InventoryService.current_stock_by_size()
    rows = []
    for code, _ in SIZE_CHOICES:
        qty = stock.get(code, 0)
        crates, trays = from_trays(qty)
        rows.append({'size': code, 'crates': crates, 'trays': trays, 'eggs': trays_to_eggs(qty)})
    return render(request, 'inventory/stock.html', {'rows': rows})


@login_required
def client_list(request):
    q = request.GET.get('q', '').strip()
    clients = Client.objects.all()
    if q:
        clients = clients.filter(name__icontains=q) | clients.filter(nip__icontains=q)
    return render(request, 'inventory/client_list.html', {'clients': clients.order_by('name'), 'q': q})


@login_required
def client_create(request):
    form = ClientForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Klient został dodany.')
        return redirect('client_list')
    return render(request, 'inventory/form.html', {'title': 'Dodaj klienta', 'form': form})


@login_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = ClientForm(request.POST or None, instance=client)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Klient został zapisany.')
        return redirect('client_list')
    return render(request, 'inventory/form.html', {'title': 'Edytuj klienta', 'form': form})


@login_required
def intake_list(request):
    return render(request, 'inventory/intake_list.html', {'intakes': DailyIntake.objects.all()})


@login_required
def intake_create(request):
    form = IntakeItemsForm(request.POST or None, initial={'laying_date': timezone.localdate()})
    if request.method == 'POST' and form.is_valid():
        intake = DailyIntake.objects.create(laying_date=form.cleaned_data['laying_date'], notes=form.cleaned_data['notes'])
        InventoryService.replace_intake_items(intake, form.items_payload())
        messages.success(request, 'Przyjęcie zostało zapisane.')
        return redirect('intake_list')
    return render(request, 'inventory/intake_form.html', {'title': 'Dodaj przyjęcie', 'form': form, 'sizes': SIZE_CHOICES})


@login_required
def intake_edit(request, pk):
    intake = get_object_or_404(DailyIntake, pk=pk)
    initial_quantities = {item.size: item.quantity_in_trays for item in intake.items.all()}
    form = IntakeItemsForm(request.POST or None, initial={'laying_date': intake.laying_date, 'notes': intake.notes}, initial_quantities=initial_quantities)
    if request.method == 'POST' and form.is_valid():
        intake.laying_date = form.cleaned_data['laying_date']
        intake.notes = form.cleaned_data['notes']
        intake.save()
        InventoryService.replace_intake_items(intake, form.items_payload())
        messages.success(request, 'Przyjęcie zostało zaktualizowane.')
        return redirect('intake_list')
    return render(request, 'inventory/intake_form.html', {'title': 'Edytuj przyjęcie', 'form': form, 'sizes': SIZE_CHOICES})


@login_required
def sale_list(request):
    sale_date = request.GET.get('sale_date')
    sales = Sale.objects.select_related('client').all()
    if sale_date:
        sales = sales.filter(sale_date=sale_date)
    return render(request, 'inventory/sale_list.html', {'sales': sales, 'sale_date': sale_date})


@login_required
def sale_create(request):
    sale = Sale()
    form = SaleForm(request.POST or None, instance=sale, initial={'sale_date': timezone.localdate()})
    formset = SaleItemFormSet(request.POST or None, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        sale = form.save()
        payload = []
        for item_form in formset:
            if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                payload.append({
                    'size': item_form.cleaned_data['size'],
                    'quantity_in_trays': item_form.cleaned_data['quantity_in_trays'],
                    'price_per_crate': item_form.cleaned_data['price_per_crate'],
                })
        try:
            InventoryService.replace_sale_items(sale, payload)
            messages.success(request, 'Sprzedaż została zapisana.')
            return redirect('sale_list')
        except ValidationError as e:
            form.add_error(None, e)
    return render(request, 'inventory/sale_form.html', {'title': 'Dodaj sprzedaż', 'form': form, 'formset': formset})


@login_required
def sale_edit(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    form = SaleForm(request.POST or None, instance=sale)
    formset = SaleItemFormSet(request.POST or None, instance=sale, prefix='items')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        sale = form.save()
        payload = []
        for item_form in formset:
            if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                payload.append({
                    'size': item_form.cleaned_data['size'],
                    'quantity_in_trays': item_form.cleaned_data['quantity_in_trays'],
                    'price_per_crate': item_form.cleaned_data['price_per_crate'],
                })
        try:
            InventoryService.replace_sale_items(sale, payload)
            messages.success(request, 'Sprzedaż została zaktualizowana.')
            return redirect('sale_list')
        except ValidationError as e:
            form.add_error(None, e)
    return render(request, 'inventory/sale_form.html', {'title': 'Edytuj sprzedaż', 'form': form, 'formset': formset})


@login_required
def breakage_list(request):
    return render(request, 'inventory/breakage_list.html', {'breakages': Breakage.objects.all()})


@login_required
def breakage_create(request):
    form = BreakageForm(request.POST or None, initial={'breakage_date': timezone.localdate()})
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.quantity_in_trays = form.cleaned_data['quantity_in_trays']
        obj.save()
        messages.success(request, 'Stłuczki zostały zapisane.')
        return redirect('breakage_list')
    return render(request, 'inventory/form.html', {'title': 'Dodaj stłuczki', 'form': form})


@login_required
def adjustment_list(request):
    return render(request, 'inventory/adjustment_list.html', {'adjustments': InventoryAdjustment.objects.all()})


@login_required
def adjustment_create(request):
    form = InventoryAdjustmentForm(request.POST or None, initial={'adjustment_date': timezone.localdate()})
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.quantity_in_trays = form.cleaned_data['quantity_in_trays']
        obj.save()
        try:
            InventoryService.save_adjustment(obj)
            messages.success(request, 'Korekta została zapisana.')
            return redirect('adjustment_list')
        except ValidationError as e:
            obj.delete()
            form.add_error(None, e)
    return render(request, 'inventory/form.html', {'title': 'Dodaj korektę', 'form': form})


@login_required
def movement_list(request):
    movements = InventoryMovement.objects.all()
    rows = []
    for m in movements:
        crates, trays = from_trays(abs(m.quantity_in_trays))
        rows.append({'obj': m, 'crates': crates, 'trays': trays, 'sign': '+' if m.quantity_in_trays >= 0 else '-'})
    return render(request, 'inventory/movement_list.html', {'rows': rows})
