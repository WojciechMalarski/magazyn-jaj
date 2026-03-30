from django.contrib import admin
from .models import Breakage, Client, DailyIntake, DailyIntakeItem, InventoryAdjustment, InventoryMovement, Sale, SaleItem

admin.site.register(Client)
admin.site.register(DailyIntake)
admin.site.register(DailyIntakeItem)
admin.site.register(Sale)
admin.site.register(SaleItem)
admin.site.register(Breakage)
admin.site.register(InventoryAdjustment)
admin.site.register(InventoryMovement)
