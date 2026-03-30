from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('magazyn/', views.stock_view, name='stock_view'),
    path('klienci/', views.client_list, name='client_list'),
    path('klienci/nowy/', views.client_create, name='client_create'),
    path('klienci/<int:pk>/edytuj/', views.client_edit, name='client_edit'),
    path('przyjecia/', views.intake_list, name='intake_list'),
    path('przyjecia/nowe/', views.intake_create, name='intake_create'),
    path('przyjecia/<int:pk>/edytuj/', views.intake_edit, name='intake_edit'),
    path('sprzedaz/', views.sale_list, name='sale_list'),
    path('sprzedaz/nowa/', views.sale_create, name='sale_create'),
    path('sprzedaz/<int:pk>/edytuj/', views.sale_edit, name='sale_edit'),
    path('stluczki/', views.breakage_list, name='breakage_list'),
    path('stluczki/nowe/', views.breakage_create, name='breakage_create'),
    path('korekty/', views.adjustment_list, name='adjustment_list'),
    path('korekty/nowa/', views.adjustment_create, name='adjustment_create'),
    path('ruchy/', views.movement_list, name='movement_list'),
]
