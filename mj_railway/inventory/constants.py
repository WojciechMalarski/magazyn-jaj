SIZE_CHOICES = [
    ('3', '3'),
    ('2B', '2B'),
    ('2A', '2A'),
    ('1B', '1B'),
    ('1A', '1A'),
    ('S', 'S'),
    ('SS', 'SS'),
]

PAYMENT_METHOD_CHOICES = [
    ('cash', 'Gotówka'),
    ('bank', 'Przelew'),
    ('bank_due', 'Przelew z terminem płatności'),
]

MOVEMENT_TYPE_CHOICES = [
    ('intake', 'Przyjęcie'),
    ('sale', 'Sprzedaż'),
    ('adjustment_plus', 'Korekta +'),
    ('adjustment_minus', 'Korekta -'),
]
