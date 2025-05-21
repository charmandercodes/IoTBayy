from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.core import mail
from a_stripe.models import PastOrder
from a_users.models import Profile  # Assuming you have a Profile model
from datetime import datetime

# Authentication

class UserAccountTests(TestCase):

    def setUp(self):
        self.password = "TestPassword123!"
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password=self.password)

    def test_100_user_has_account(self):
        self.assertEqual(User.objects.count(), 1)

    def test_101_register_account(self):
        response = self.client.post(reverse('account_signup'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'NewStrongPassword!123',
            'password2': 'NewStrongPassword!123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_102_login_success(self):
        login = self.client.login(username="testuser", password=self.password)
        self.assertTrue(login)

    def test_103_login_failure_shows_error(self):
        response = self.client.post(reverse('account_login'), {
            'login': 'testuser@gmail.com',
            'password': 'wrongpassword'
        })
        self.assertContains(response, "The email address and/or password you specified are not correct.", status_code=200)

    def test_104_update_account_details(self):
        self.client.login(username="testuser", password=self.password)
        response = self.client.post(reverse('profile-edit'), {
            'bio': 'Updated Bio',
            'location': 'Updated City'
        })
        self.assertRedirects(response, reverse('profile'))

    def test_105_login_is_secure(self):
        self.assertNotEqual(self.user.password, self.password)
        self.assertTrue(self.user.password.startswith('pbkdf2_'))

    def test_107_password_reset_link_sent(self):
        response = self.client.post(reverse('account_reset_password'), {
            'email': self.user.email
        })
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Password Reset', mail.outbox[0].subject)

    def test_108_logout(self):
        self.client.login(username="testuser", password=self.password)
        response = self.client.get(reverse('account_logout'))
        self.assertEqual(response.status_code, 200)

    def test_301_customer_service_staff_login(self):
        staff = User.objects.create_user(username='staff', password='staffpass', is_staff=True)
        login = self.client.login(username='staff', password='staffpass')
        self.assertTrue(login)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)


# Past Orders

class PastOrderTests(TestCase):

    def setUp(self):
        self.client = Client()

        # Create user and profile
        self.user = User.objects.create_user(username='testuser1', password='pass123')

        # Create test orders
        self.order1 = PastOrder.objects.create(
            user=self.user,
            product_name="Flipper Zero",
            product_image="https://example.com/flipper.jpg",
            price=199.99,
            quantity=1,
            created_at=datetime(2023, 1, 1)
        )

        self.order2 = PastOrder.objects.create(
            user=self.user,
            product_name="Raspberry Pi",
            product_image="https://example.com/pi.jpg",
            price=49.99,
            quantity=2,
            created_at=datetime(2023, 3, 1)
        )

    def test_109_view_purchase_history(self):
        """Test 109 - View my purchase history"""
        self.client.login(username='testuser1', password='pass123')
        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Flipper Zero")
        self.assertContains(response, "Raspberry Pi")
        self.assertContains(response, "$199.99")
        self.assertContains(response, "$49.99")

    def test_304_search_order_by_order_number(self):
        """Test 304 - Search for an order by order ID"""
        self.client.login(username='testuser1', password='pass123')
        response = self.client.get(reverse('profile'), {'q': str(self.order1.id)})
        # Only show matching order
        self.assertContains(response, "Flipper Zero")
        self.assertNotContains(response, "Raspberry Pi")

    def test_703_track_orders_per_product(self):
        """Test 703 - Filter purchase history for a specific product"""
        self.client.login(username='testuser1', password='pass123')
        response = self.client.get(reverse('profile'), {'product': 'raspberry pi'})

        self.assertContains(response, "Raspberry Pi")
        self.assertNotContains(response, "Flipper Zero")
