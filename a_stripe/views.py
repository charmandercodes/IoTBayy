from django.http import HttpResponse
import stripe
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from a_stripe.models import CheckoutSession, PastOrder, UserPayment
from django.http import HttpResponseRedirect
stripe.api_key = settings.STRIPE_TEST_KEY
from .utils import create_checkout_session, get_product_details
from .cart import Cart
from .forms import *
import logging
logger = logging.getLogger(__name__)

# Create your views here.

def shop_view(request):
    products_list = stripe.Product.list()
    products = []

    for product in products_list['data']:
        if product.get('metadata', {}).get('category') == "shop":
            products.append(get_product_details(product))

            
    return render(request, 'a_stripe/shop.html', {'products': products})

def product_view(request, product_id):

    product = stripe.Product.retrieve(product_id)
    product_details = get_product_details(product)

    cart = Cart(request)
    product_details['in_cart'] = product_id in cart.cart_session

    return render(request, 'a_stripe/product.html', {'product': product_details})

def hx_menu_cart(request):
    return render(request, 'a_stripe/partials/menu-cart.html')


def add_to_cart(request, product_id):
    cart = Cart(request)
    cart.add(product_id)

    product = stripe.Product.retrieve(product_id)
    product_details = get_product_details(product)
    product_details['in_cart'] = product_id in cart.cart_session

    response = render(request, 'a_stripe/partials/cart-button.html', {'product': product_details})
    response['HX-Trigger'] = 'hx_menu_cart'
    return response


@login_required
def checkout_view(request):
    # Try to get existing shipping info for the user
    shipping_info = ShippingInfo.objects.filter(user=request.user).first()
    
    if request.method == 'POST':
        # Use the instance parameter to update existing info if it exists
        form = ShippingForm(request.POST, instance=shipping_info)
        if form.is_valid():
            try:
                shipping_info = form.save(commit=False)
                shipping_info.user = request.user
                shipping_info.email = form.cleaned_data['email'].lower()
                shipping_info.save()
                
                cart = Cart(request)
                
                checkout_session = create_checkout_session(cart, shipping_info.email)
                
                CheckoutSession.objects.create(
                    checkout_id=checkout_session.id,
                    shipping_info=shipping_info,
                    total_cost=cart.get_total_cost()
                )
                
                if not checkout_session.url:
                    return HttpResponse("ERROR: Checkout session URL is empty!")
                
                return HttpResponseRedirect(checkout_session.url)
                
            except Exception as e:
                cart = Cart(request)
                context = {
                    'cart': cart,
                    'form': form,
                    'error': f'Unable to process payment: {str(e)}'
                }
                return render(request, 'a_stripe/checkout.html', context)
    else:
        # For GET requests, pre-fill the form with existing info or just the email
        if shipping_info:
            form = ShippingForm(instance=shipping_info)
        else:
            form = ShippingForm(initial={'email': request.user.email})
    
    cart = Cart(request)
    context = {
        'cart': cart,
        'form': form
    }
    return render(request, 'a_stripe/checkout.html', context)

def payment_successful(request):
    checkout_session_id = request.GET.get('session_id', None)
    customer = None  # Default if session retrieval fails

    if checkout_session_id:
        session = stripe.checkout.Session.retrieve(checkout_session_id)
        customer_id = session.customer
        customer = stripe.Customer.retrieve(customer_id)

        # Fetch line items for the session
        line_items = stripe.checkout.Session.list_line_items(session.id)

        # Save Stripe Customer ID to user profile if authenticated
        if request.user.is_authenticated:
            profile = request.user.profile
            if not profile.stripe_customer_id:
                profile.stripe_customer_id = customer_id
                profile.save()

        # Mark checkout session as paid in dev mode (optional)
        if settings.DEBUG:
            checkout = CheckoutSession.objects.get(checkout_id=checkout_session_id)
            checkout.has_paid = True
            checkout.save()
        # Save each line item to the PastOrder model
        for line_item in line_items.data:
            product_name = line_item.description  # Product name
            price = line_item.amount_total / 100.0  # Stripe amount is in cents
            currency = session.currency  # Currency from the session
            quantity = line_item.quantity  # Product quantity
            product_image = line_item.image if 'image' in line_item else None  # Product image URL if available

            # Create PastOrder instance for each product in the checkout session
            PastOrder.objects.create(
                user=request.user,
                stripe_checkout_id=session.id,
                stripe_product_id=line_item.price.product,
                product_name=product_name,
                price=price,
                currency=currency,
                quantity=quantity,
                product_image=product_image,
            )

        # Clear cart session after successful payment
        if settings.CART_SESSION_ID in request.session:
            del request.session[settings.CART_SESSION_ID]

    return render(request, 'a_stripe/payment_successful.html', {'customer': customer})


def remove_from_cart(request,product_id):
    cart = Cart(request)
    cart.remove(product_id)
    return redirect(reverse('cart'))

def cart_view(request):
    quantity = list(range(1,11))
    return render(request, 'a_stripe/cart.html', {'quantity_range': quantity})

def update_checkout(request, product_id):
    quantity = int(request.POST.get('quantity', 1))
    cart = Cart(request)
    cart.add(product_id, quantity)

    product = stripe.Product.retrieve(product_id)

    product_details = get_product_details(product)

    product_details['total_price'] = product_details['price'] * quantity

    response = render(request, 'a_stripe/partials/checkout-total.html', {'product': product_details})
    response['HX-Trigger'] = 'hx_menu_cart'
    return response


def payment_cancelled(request):
    return render(request, 'a_stripe/payment_cancelled.html')  

@require_POST
@csrf_exempt
def stripe_webhook(request):
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    payload = request.body
    signature_header = request.META['HTTP_STRIPE_SIGNATURE']
    try:
        event = stripe.Webhook.construct_event(
            payload, signature_header, endpoint_secret
        )
    except:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        checkout_session_id = session.get('id')
        user_payment = UserPayment.objects.get(stripe_checkout_id=checkout_session_id)
        user_payment.has_paid = True
        user_payment.save()
    
    return HttpResponse(status=200)



    

