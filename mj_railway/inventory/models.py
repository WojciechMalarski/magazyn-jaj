from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from .constants import MOVEMENT_TYPE_CHOICES, PAYMENT_METHOD_CHOICES, SIZE_CHOICES
from .utils import TRAYS_PER_CRATE, empty_stock_dict, from_trays, to_trays


class Client(models.Model):
    name = models.CharField(max_length=255)
    nip = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DailyIntake(models.Model):
    laying_date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-laying_date', '-id']

    def __str__(self):
        return f'Przyjęcie {self.laying_date}'

    @property
    def total_trays(self):
        return self.items.aggregate(total=Sum('quantity_in_trays')).get('total') or 0


class DailyIntakeItem(models.Model):
    intake = models.ForeignKey(DailyIntake, on_delete=models.CASCADE, related_name='items')
    size = models.CharField(max_length=4, choices=SIZE_CHOICES)
    quantity_in_trays = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('intake', 'size')
        ordering = ['id']

    def __str__(self):
        return f'{self.intake} / {self.size}'


class Sale(models.Model):
    sale_date = models.DateField(default=timezone.localdate)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='sales')
    invoice_number = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    due_date = models.DateField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sale_date', '-id']

    def clean(self):
        if self.payment_method == 'bank_due' and not self.due_date:
            raise ValidationError({'due_date': 'Termin płatności jest wymagany dla przelewu z terminem.'})

    def __str__(self):
        return f'{self.invoice_number} / {self.client}'

    def recompute_total(self):
        total = self.items.aggregate(total=Sum('line_total')).get('total') or Decimal('0.00')
        self.total_amount = total
        self.save(update_fields=['total_amount', 'updated_at'])


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    size = models.CharField(max_length=4, choices=SIZE_CHOICES)
    quantity_in_trays = models.PositiveIntegerField(default=0)
    price_per_crate = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['id']

    def clean(self):
        if self.quantity_in_trays <= 0:
            raise ValidationError({'quantity_in_trays': 'Ilość musi być większa od zera.'})

    def save(self, *args, **kwargs):
        crate_fraction = Decimal(self.quantity_in_trays) / Decimal(TRAYS_PER_CRATE)
        self.line_total = (crate_fraction * self.price_per_crate).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)


class Breakage(models.Model):
    breakage_date = models.DateField(default=timezone.localdate)
    quantity_in_trays = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-breakage_date', '-id']

    def __str__(self):
        return f'Stłuczki {self.breakage_date}'


class InventoryAdjustment(models.Model):
    ADJUSTMENT_TYPES = [('plus', 'Plus'), ('minus', 'Minus')]

    adjustment_date = models.DateField(default=timezone.localdate)
    size = models.CharField(max_length=4, choices=SIZE_CHOICES)
    quantity_in_trays = models.PositiveIntegerField(default=0)
    adjustment_type = models.CharField(max_length=10, choices=ADJUSTMENT_TYPES)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-adjustment_date', '-id']

    def __str__(self):
        return f'Korekta {self.get_adjustment_type_display()} {self.adjustment_date}'


class InventoryMovement(models.Model):
    movement_date = models.DateField(default=timezone.localdate)
    size = models.CharField(max_length=4, choices=SIZE_CHOICES)
    quantity_in_trays = models.IntegerField()
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    reference_type = models.CharField(max_length=30)
    reference_id = models.PositiveIntegerField()
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-movement_date', '-id']

    def __str__(self):
        return f'{self.movement_date} {self.movement_type} {self.size}'


class InventoryService:
    @staticmethod
    def current_stock_by_size():
        stock = empty_stock_dict()
        for row in InventoryMovement.objects.values('size').annotate(total=Sum('quantity_in_trays')):
            stock[row['size']] = row['total'] or 0
        return stock

    @staticmethod
    def available_trays(size: str) -> int:
        return InventoryMovement.objects.filter(size=size).aggregate(total=Sum('quantity_in_trays')).get('total') or 0

    @staticmethod
    @transaction.atomic
    def replace_intake_items(intake: DailyIntake, items_payload: list[dict]):
        InventoryMovement.objects.filter(reference_type='daily_intake', reference_id=intake.id).delete()
        intake.items.all().delete()
        for payload in items_payload:
            qty = payload['quantity_in_trays']
            if qty <= 0:
                continue
            DailyIntakeItem.objects.create(intake=intake, size=payload['size'], quantity_in_trays=qty)
            InventoryMovement.objects.create(
                movement_date=intake.laying_date,
                size=payload['size'],
                quantity_in_trays=qty,
                movement_type='intake',
                reference_type='daily_intake',
                reference_id=intake.id,
                note='Przyjęcie dzienne',
            )

    @staticmethod
    @transaction.atomic
    def replace_sale_items(sale: Sale, items_payload: list[dict]):
        # remove old movements/items
        InventoryMovement.objects.filter(reference_type='sale', reference_id=sale.id).delete()
        sale.items.all().delete()

        # validate stock against current stock without this sale
        stock = InventoryService.current_stock_by_size()
        requested = empty_stock_dict()
        for payload in items_payload:
            qty = payload['quantity_in_trays']
            if qty <= 0:
                continue
            requested[payload['size']] += qty
        for size, qty in requested.items():
            if qty > stock[size]:
                crates, trays = from_trays(stock[size])
                raise ValidationError(f'Brak stanu dla rozmiaru {size}. Dostępne: {crates} skrzynek i {trays} wkładek.')

        for payload in items_payload:
            qty = payload['quantity_in_trays']
            if qty <= 0:
                continue
            SaleItem.objects.create(
                sale=sale,
                size=payload['size'],
                quantity_in_trays=qty,
                price_per_crate=payload['price_per_crate'],
            )
            InventoryMovement.objects.create(
                movement_date=sale.sale_date,
                size=payload['size'],
                quantity_in_trays=-qty,
                movement_type='sale',
                reference_type='sale',
                reference_id=sale.id,
                note=f'Sprzedaż {sale.invoice_number}',
            )
        sale.recompute_total()

    @staticmethod
    @transaction.atomic
    def save_adjustment(adj: InventoryAdjustment):
        if adj.adjustment_type == 'minus' and adj.quantity_in_trays > InventoryService.available_trays(adj.size):
            raise ValidationError(f'Korekta dla rozmiaru {adj.size} spowoduje stan ujemny.')
        InventoryMovement.objects.filter(reference_type='adjustment', reference_id=adj.id).delete()
        qty = adj.quantity_in_trays if adj.adjustment_type == 'plus' else -adj.quantity_in_trays
        InventoryMovement.objects.create(
            movement_date=adj.adjustment_date,
            size=adj.size,
            quantity_in_trays=qty,
            movement_type='adjustment_plus' if adj.adjustment_type == 'plus' else 'adjustment_minus',
            reference_type='adjustment',
            reference_id=adj.id,
            note=adj.reason,
        )
