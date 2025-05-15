from django.forms import ModelForm
from django import forms
from .models import ShippingInfo

class ShippingForm(ModelForm):
    class Meta:
        model = ShippingInfo
        exclude = ['user']  # Fixed typo
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone (optional)'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
            'address_line_one': forms.TextInput(attrs={'placeholder': 'Address Line 1'}),
            'address_line_two': forms.TextInput(attrs={'placeholder': 'Address Line 2 (optional)'}),
            'city': forms.TextInput(attrs={'placeholder': 'City'}),
            'zip_code': forms.TextInput(attrs={'placeholder': 'Zip Code'}),
        }
