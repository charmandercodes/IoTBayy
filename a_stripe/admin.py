from django.contrib import admin
from .models import *

# Register your models here.

admin.site.register(ShippingInfo)
admin.site.register(CheckoutSession)
admin.site.register(UserPayment)
admin.site.register(PastOrder)