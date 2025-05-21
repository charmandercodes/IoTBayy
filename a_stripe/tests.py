from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch
from django.contrib.auth.models import User
from a_stripe.models import CheckoutSession, PastOrder, ShippingInfo
from unittest.mock import patch, MagicMock

class ShopSearchTests(TestCase):

    @patch('a_stripe.views.stripe.Product.list')
    def test_202_filter_unrelated_products(self, mock_stripe_list):
        mock_stripe_list.return_value = {
            'data': [
                {'name': 'Raspberry Pi'},
                {'name': 'Flipper'},
                {'name': 'Bangle.js'},
                {'name': 'Rubber Ducky'},
            ]
        }

        response = self.client.get(reverse('shop'), {'q': 'flipper'})
        self.assertNotContains(response, 'Raspberry Pi')
        self.assertNotContains(response, 'Bangle.js')
        self.assertNotContains(response, 'Rubber Ducky')

    @patch('a_stripe.views.stripe.Product.list')
    def test_203_display_specific_products(self, mock_stripe_list):
        mock_stripe_list.return_value = {
            'data': [
                {'name': 'Raspberry Pi'},
                {'name': 'Flipper'},
                {'name': 'Bangle.js'},
                {'name': 'Rubber Ducky'},
            ]
        }

        response = self.client.get(reverse('shop'), {'q': 'Flipper'})
        self.assertContains(response, 'Flipper')

# Ecommerce 

class ShopViewTests(TestCase):
    """Tests for general shop navigation and product viewing"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpassword123'
        )
        
        # Mock product data that will be used across tests
        self.mock_products = {
            'data': [
                {
                    'id': 'prod_test123',
                    'name': 'Test Product',
                    'description': 'This is a test product',
                    'metadata': {
                        'category': 'shop',
                        'sku': 'TST-001',
                    },
                    'images': ['https://example.com/image.jpg'],
                },
                {
                    'id': 'prod_test456',
                    'name': 'Sale Product',
                    'description': 'This is a sale product',
                    'metadata': {
                        'category': 'shop',
                        'sku': 'SL-001',
                        'on_sale': 'true'
                    },
                    'images': ['https://example.com/sale.jpg'],
                }
            ]
        }
        
        # Mock price data
        self.mock_price = {
            'unit_amount': 1999,
            'currency': 'usd',
            'id': 'price_test123'
        }
    
    @patch('a_stripe.views.stripe.Price.list')
    @patch('a_stripe.views.stripe.Product.list')
    def test_200_navigate_website(self, mock_product_list, mock_price_list):
        mock_product_list.return_value = self.mock_products
        mock_price_response = MagicMock()
        mock_price_response.data = [self.mock_price]
        mock_price_list.return_value = mock_price_response

        response = self.client.get(reverse('shop'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'a_stripe/shop.html')

    @patch('a_stripe.views.stripe.Price.list')
    @patch('a_stripe.views.stripe.Product.list')
    def test_201_view_product_catalog(self, mock_product_list, mock_price_list):
        """Test 201 - Users can view the product catalog"""
        mock_product_list.return_value = self.mock_products
        mock_price_response = MagicMock()
        mock_price_response.data = [self.mock_price]
        mock_price_list.return_value = mock_price_response
        
        response = self.client.get(reverse('shop'))
        self.assertEqual(response.status_code, 200)
        
        # Check if products are in the context
        self.assertTrue('products' in response.context)
        self.assertEqual(len(response.context['products']), 2)


    @patch('stripe.Product.retrieve')
    @patch('a_stripe.views.get_product_details')
    def test_206_view_detailed_product_description(self, mock_get_product_details, mock_product_retrieve):
        """Test 206 - Users can view detailed description of each product"""
        # Setup the mock returns
        mock_product = self.mock_products['data'][0]
        mock_product_retrieve.return_value = mock_product
        
        product_details = {
            'id': mock_product['id'],
            'name': mock_product['name'],
            'description': mock_product['description'],
            'image': mock_product['images'][0],
            'price': 19.99,
            'currency': 'USD',
            'in_cart': False
        }
        mock_get_product_details.return_value = product_details
        
        # Test viewing a product detail page
        response = self.client.get(reverse('product', args=[mock_product['id']]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'a_stripe/product.html')
        
        # Check if the product details are in the context
        self.assertTrue('product' in response.context)
        self.assertEqual(response.context['product']['name'], 'Test Product')
        self.assertEqual(response.context['product']['description'], 'This is a test product')


class CartAndCheckoutTests(TestCase):
    """Tests for cart functionality and checkout process"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpassword123'
        )
        
        # Mock product data
        self.product_id = 'prod_test123'
        self.mock_product = {
            'id': self.product_id,
            'name': 'Test Product',
            'description': 'This is a test product',
            'metadata': {
                'category': 'shop',
                'sku': 'TST-001',
            },
            'images': ['https://example.com/image.jpg'],
        }
        
        # Mock product details returned by get_product_details
        self.product_details = {
            'id': self.product_id,
            'name': 'Test Product',
            'description': 'This is a test product',
            'image': 'https://example.com/image.jpg',
            'price': 19.99,
            'currency': 'USD',
            'in_cart': False
        }
        
        # Mock session data
        self.session = self.client.session
        self.session['cart'] = {}
        self.session.save()

    @patch('stripe.Product.retrieve')
    @patch('a_stripe.views.get_product_details')
    def test_601_add_products_to_cart(self, mock_get_product_details, mock_product_retrieve):
        """Test 601 - Users can add products to a shopping cart"""
        # Setup mocks
        mock_product_retrieve.return_value = self.mock_product
        mock_get_product_details.return_value = self.product_details
        
        # Add a product to cart
        response = self.client.post(reverse('add_to_cart', args=[self.product_id]))
        self.assertEqual(response.status_code, 200)
        
        # Check if HX-Trigger header is present (for cart update)
        self.assertEqual(response.headers.get('HX-Trigger'), 'hx_menu_cart')
        
        # Check session to confirm item was added
        cart = self.client.session.get('cart', {})
        self.assertIn(self.product_id, cart)

    def test_cart_view(self):
        """Test viewing the cart page"""
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'a_stripe/cart.html')
        
        # Check if quantity range is in context (for quantity dropdown)
        self.assertTrue('quantity_range' in response.context)
        self.assertEqual(list(response.context['quantity_range']), list(range(1, 11)))

    @patch('a_stripe.views.get_product_details')
    @patch('a_stripe.views.stripe.Product.retrieve')
    def test_update_cart_quantity(self, mock_product_retrieve, mock_get_product_details):
        """Test updating product quantity in cart"""
        mock_product_retrieve.return_value = self.mock_product
        mock_get_product_details.return_value = {
            'id': self.product_id,
            'name': 'Test Product',
            'description': 'This is a test product',
            'image': 'https://example.com/image.jpg',
            'price': 19.99,
            'currency': 'USD',
            'in_cart': False
        }

        response = self.client.post(
            reverse('update_checkout', args=[self.product_id]),
            {'quantity': 3}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('HX-Trigger'), 'hx_menu_cart')
        self.assertEqual(response.context['product']['total_price'], 59.97)


#     @patch('stripe.Product.retrieve')
#     @patch('a_stripe.views.get_product_details')
#     def test_remove_from_cart(self, mock_get_product_details, mock_product_retrieve):
#         """Test removing a product from cart"""
#         # Setup mocks
#         mock_product_retrieve.return_value = self.mock_product
#         mock_get_product_details.return_value = self.product_details
        
#         # First add item to cart
#         self.session = self.client.session
#         self.session['cart'] = {self.product_id: {'quantity': 1}}
#         self.session.save()
        
#         # Then remove it
#         response = self.client.post(reverse('remove_from_cart', args=[self.product_id]))
#         self.assertEqual(response.status_code, 302)  # Should redirect
        
#         # Check if item was removed from session
#         cart = self.client.session.get('cart', {})
#         self.assertNotIn(self.product_id, cart)

#     @patch('a_stripe.views.create_checkout_session')
#     def test_602_checkout_delivery_payment_options(self, mock_create_checkout):
#         """Test 602 - Users can choose delivery/payment options in checkout"""
#         # Login the user
#         self.client.login(username='testuser', password='testpassword123')
        
#         # Setup cart in session
#         session = self.client.session
#         session['cart'] = {self.product_id: {'quantity': 1}}
#         session.save()
        
#         # Access checkout page
#         response = self.client.get(reverse('checkout'))
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'a_stripe/checkout.html')
        
#         # Check if form is in context
#         self.assertTrue('form' in response.context)
        
#         # Check if the email field is pre-filled with user's email
#         self.assertEqual(response.context['form'].initial['email'], 'testuser@example.com')

#     @patch('stripe.checkout.Session')
#     @patch('a_stripe.views.create_checkout_session')
#     def test_603_complete_transaction_with_payment(self, mock_create_checkout, mock_checkout_session):
#         """Test 603 - Users can use card/payment to complete transaction"""
#         # Login the user
#         self.client.login(username='testuser', password='testpassword123')
        
#         # Setup cart in session
#         session = self.client.session
#         session['cart'] = {self.product_id: {'quantity': 1}}
#         session.save()
        
#         # Mock checkout session creation
#         mock_session = MagicMock()
#         mock_session.id = 'cs_test123'
#         mock_session.url = 'https://checkout.stripe.com/test'
#         mock_create_checkout.return_value = mock_session
        
#         # Submit checkout form
#         checkout_data = {
#             'email': 'testuser@example.com',
#             'full_name': 'Test User',
#             'address': '123 Test St',
#             'city': 'Test City',
#             'state': 'TS',
#             'zipcode': '12345',
#             'country': 'US',
#         }
        
#         response = self.client.post(reverse('checkout'), checkout_data)
        
#         # Should redirect to Stripe
#         self.assertEqual(response.status_code, 302)
#         self.assertEqual(response.url, 'https://checkout.stripe.com/test')
        
#         # Verify checkout session was created in database
#         self.assertTrue(CheckoutSession.objects.filter(checkout_id='cs_test123').exists())

#     @patch('stripe.checkout.Session.retrieve')
#     @patch('stripe.Customer.retrieve')
#     @patch('stripe.checkout.Session.list_line_items')
#     def test_600_complete_purchase_online_easily(self, mock_list_line_items, mock_customer_retrieve, mock_session_retrieve):
#         """Test 600 - Users can complete purchase online easily (successful payment)"""
#         # Login the user
#         self.client.login(username='testuser', password='testpassword123')
        
#         # Create a shipping info record
#         shipping_info = ShippingInfo.objects.create(
#             user=self.user,
#             full_name='Test User',
#             email='testuser@example.com',
#             address='123 Test St',
#             city='Test City',
#             state='TS',
#             zipcode='12345',
#             country='US'
#         )
        
#         # Create a checkout session
#         checkout_session = CheckoutSession.objects.create(
#             checkout_id='cs_test123',
#             shipping_info=shipping_info,
#             total_cost=19.99
#         )
        
#         # Mock Stripe API responses
#         mock_session = MagicMock()
#         mock_session.id = 'cs_test123'
#         mock_session.customer = 'cus_test123'
#         mock_session.currency = 'usd'
#         mock_session_retrieve.return_value = mock_session
        
#         mock_customer = MagicMock()
#         mock_customer.id = 'cus_test123'
#         mock_customer.email = 'testuser@example.com'
#         mock_customer_retrieve.return_value = mock_customer
        
#         # Mock line items
#         mock_line_item = MagicMock()
#         mock_line_item.description = 'Test Product'
#         mock_line_item.amount_total = 1999  # In cents
#         mock_line_item.quantity = 1
#         mock_line_item.price = MagicMock()
#         mock_line_item.price.product = self.product_id
        
#         mock_line_items = MagicMock()
#         mock_line_items.data = [mock_line_item]
#         mock_list_line_items.return_value = mock_line_items
        
#         # Test successful payment page
#         response = self.client.get(
#             reverse('payment_successful'),
#             {'session_id': 'cs_test123'}
#         )
        
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'a_stripe/payment_successful.html')
        
#         # Check if a PastOrder was created
#         self.assertTrue(
#             PastOrder.objects.filter(
#                 user=self.user,
#                 stripe_checkout_id='cs_test123',
#                 stripe_product_id=self.product_id
#             ).exists()
#         )
        
#         # Check if cart was cleared after successful payment
#         self.assertNotIn('cart', self.client.session)


# class StripeWebhookTest(TestCase):
#     """Test Stripe webhook handling"""
    
#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.create_user(
#             username='testuser',
#             email='testuser@example.com',
#             password='testpassword123'
#         )
        
#         # Create a UserPayment for webhook testing
#         self.user_payment = UserPayment.objects.create(
#             user=self.user,
#             stripe_checkout_id='cs_test123',
#             has_paid=False
#         )
    
#     @patch('stripe.Webhook.construct_event')
#     def test_webhook_checkout_completed(self, mock_construct_event):
#         """Test webhook handling for checkout.session.completed event"""
#         # Mock the event data
#         event_data = {
#             'type': 'checkout.session.completed',
#             'data': {
#                 'object': {
#                     'id': 'cs_test123'
#                 }
#             }
#         }
#         mock_construct_event.return_value = event_data
        
#         # Send webhook request
#         response = self.client.post(
#             reverse('stripe_webhook'),
#             data=json.dumps(event_data),
#             content_type='application/json',
#             HTTP_STRIPE_SIGNATURE='test_signature'
#         )
        
#         self.assertEqual(response.status_code, 200)
        
#         # Check if the payment was marked as paid
#         self.user_payment.refresh_from_db()
#         self.assertTrue(self.user_payment.has_paid)
