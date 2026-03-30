from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

from .constants import SIZE_CHOICES
from .models import Breakage, Client, DailyIntake, InventoryAdjustment, Sale, SaleItem
from .utils import from_trays, to_trays


class DateInput(forms.DateInput):
    input_type = 'date'


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'nip', 'is_active']


class DailyIntakeForm(forms.ModelForm):
    class Meta:
        model = DailyIntake
        fields = ['laying_date', 'notes']
        widgets = {'laying_date': DateInput()}


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['sale_date', 'client', 'invoice_number', 'payment_method', 'due_date', 'notes']
        widgets = {'sale_date': DateInput(), 'due_date': DateInput()}


class SaleItemForm(forms.ModelForm):
    quantity_in_trays = forms.IntegerField(required=False, widget=forms.HiddenInput())
    crates = forms.IntegerField(min_value=0, required=False, initial=0, label='Skrzynki')
    trays = forms.IntegerField(min_value=0, max_value=11, required=False, initial=0, label='Wkładki')

    class Meta:
        model = SaleItem
        fields = ['size', 'quantity_in_trays', 'crates', 'trays', 'price_per_crate']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qty = getattr(self.instance, 'quantity_in_trays', 0) or 0
        crates, trays = from_trays(qty)
        self.fields['crates'].initial = crates
        self.fields['trays'].initial = trays
        self.fields['quantity_in_trays'].initial = qty

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('DELETE'):
            return cleaned

        crates = cleaned.get('crates') or 0
        trays = cleaned.get('trays') or 0
        qty = to_trays(crates, trays)
        if qty <= 0:
            raise ValidationError('Podaj ilość większą od zera.')

        cleaned['quantity_in_trays'] = qty
        price = cleaned.get('price_per_crate') or Decimal('0')
        cleaned['line_total'] = (Decimal(qty) / Decimal('12') * price).quantize(Decimal('0.01'))
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.quantity_in_trays = self.cleaned_data.get('quantity_in_trays', 0)
        instance.line_total = self.cleaned_data.get('line_total', Decimal('0.00'))
        if commit:
            instance.save()
        return instance


SaleItemFormSet = inlineformset_factory(
    Sale,
    SaleItem,
    form=SaleItemForm,
    extra=3,
    can_delete=True,
)


class BreakageForm(forms.ModelForm):
    crates = forms.IntegerField(min_value=0, initial=0)
    trays = forms.IntegerField(min_value=0, max_value=11, initial=0)

    class Meta:
        model = Breakage
        fields = ['breakage_date', 'crates', 'trays', 'notes']
        widgets = {'breakage_date': DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            crates, trays = from_trays(self.instance.quantity_in_trays)
            self.fields['crates'].initial = crates
            self.fields['trays'].initial = trays

    def clean(self):
        cleaned = super().clean()
        cleaned['quantity_in_trays'] = to_trays(cleaned.get('crates') or 0, cleaned.get('trays') or 0)
        return cleaned


class InventoryAdjustmentForm(forms.ModelForm):
    crates = forms.IntegerField(min_value=0, initial=0)
    trays = forms.IntegerField(min_value=0, max_value=11, initial=0)

    class Meta:
        model = InventoryAdjustment
        fields = ['adjustment_date', 'size', 'adjustment_type', 'crates', 'trays', 'reason']
        widgets = {'adjustment_date': DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            crates, trays = from_trays(self.instance.quantity_in_trays)
            self.fields['crates'].initial = crates
            self.fields['trays'].initial = trays

    def clean(self):
        cleaned = super().clean()
        qty = to_trays(cleaned.get('crates') or 0, cleaned.get('trays') or 0)
        if qty <= 0:
            raise ValidationError('Podaj ilość większą od zera.')
        cleaned['quantity_in_trays'] = qty
        return cleaned


class IntakeItemsForm(forms.Form):
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))
    laying_date = forms.DateField(widget=DateInput())

    def __init__(self, *args, initial_quantities=None, **kwargs):
        super().__init__(*args, **kwargs)
        initial_quantities = initial_quantities or {}
        for code, _ in SIZE_CHOICES:
            crates, trays = from_trays(initial_quantities.get(code, 0))
            self.fields[f'{code}_crates'] = forms.IntegerField(min_value=0, required=False, initial=crates, label=f'{code} skrzynki')
            self.fields[f'{code}_trays'] = forms.IntegerField(min_value=0, max_value=11, required=False, initial=trays, label=f'{code} wkładki')

    def items_payload(self):
        payload = []
        for code, _ in SIZE_CHOICES:
            crates = self.cleaned_data.get(f'{code}_crates') or 0
            trays = self.cleaned_data.get(f'{code}_trays') or 0
            payload.append({'size': code, 'quantity_in_trays': to_trays(crates, trays)})
        return payload
