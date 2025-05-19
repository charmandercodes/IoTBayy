from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from a_stripe.models import PastOrder, UserPayment
from .forms import *
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from allauth.account.utils import send_email_confirmation
from django.contrib.auth import logout
import stripe
from django.conf import settings
stripe.api_key = settings.STRIPE_TEST_KEY

# Create your views here.

def profile_view(request, username=None):
    # Resolve profile
    if username:
        profile = get_object_or_404(User, username=username).profile
    else:
        try:
            profile = request.user.profile
        except:
            return redirect('account_login')

    # Start with all past orders
    past_orders = PastOrder.objects.filter(user=request.user)

    # Optional: filter by order ID (search by number)
    query = request.GET.get('q')
    if query:
        past_orders = past_orders.filter(id=query)

    # Optional: filter by product name (case-insensitive)
    product_filter = request.GET.get('product')
    if product_filter:
        past_orders = past_orders.filter(product_name__icontains=product_filter)

    # Final ordering
    past_orders = past_orders.order_by('-created_at')

    context = {
        'profile': profile,
        'past_orders': past_orders,
    }

    return render(request, 'a_users/profile.html', context)

@login_required
def profile_edit_view(request):

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    form = ProfileForm(instance=request.user.profile)

    # set onboarding to true if the user is going to be sent to the onboarding page

    if request.path == reverse('profile-onboarding'):
        onboarding = True
    # else set onboarding to false
    else:
        onboarding = False

    # return the form and onboarding status to the template

    
    return render(request, 'a_users/profile_edit.html', {'form': form, 'onboarding': onboarding})


@login_required
def profile_settings_view(request):
    return render(request, 'a_users/profile_settings.html')

@login_required
def profile_emailchange(request):
    if request.htmx:
        form = EmailForm(request.POST, instance=request.user)
        return render(request, 'partials/email_form.html', {'form': form})
    
    if request.method == 'POST':
        form = EmailForm(request.POST, instance=request.user)
        if form.is_valid():
            
            # Check if email already exists
            email = form.cleaned_data['email']
            if User.objects.filter(email=email).exclude(id=request.user.id).exists():
                messages.warning(request, f'{email} is already in use.')

                return redirect('profile-settings')

            form.save()

            # Then signal updates emailaddress and set verified to False

            send_email_confirmation(request, request.user)

            return redirect('profile-settings')
        else:
            messages.error(request, 'Invalid email address')
            return redirect('profile-settings')

    return redirect('home')

@login_required
def profile_emailverify(request):
    send_email_confirmation(request, request.user)
    return redirect('profile-settings')


@login_required
def profile_delete_view(request):
    user = request.user
    if request.method == 'POST':
        logout(request)
        user.delete()
        messages.success(request, 'Account deleted')
        return redirect('home')
    return render(request, 'a_users/profile_delete.html')