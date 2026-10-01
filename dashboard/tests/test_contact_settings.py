from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from dashboard.models import BusinessSettings
from dashboard.forms import BusinessSettingsForm


class BusinessSettingsModelTests(TestCase):
    def test_singleton_behavior(self):
        s1 = BusinessSettings.get_settings()
        self.assertEqual(s1.pk, 1)

        # Trying to save another record with different pk still enforces pk=1
        s2 = BusinessSettings(
            business_name="Second Attempt",
            business_email="other@test.com",
            primary_phone="+1 555 123 4567"
        )
        s2.save()
        self.assertEqual(BusinessSettings.objects.count(), 1)
        self.assertEqual(BusinessSettings.objects.first().business_name, "Second Attempt")

    def test_phone_properties(self):
        s = BusinessSettings.get_settings()
        s.primary_phone = "+33 (1) 40-20-50-50"
        s.secondary_phone = "+91 98765 43210"
        s.whatsapp_number = "+33 6 12 34 56 78"
        s.save()

        self.assertEqual(s.primary_phone_tel, "+33140205050")
        self.assertEqual(s.secondary_phone_tel, "+919876543210")
        self.assertEqual(s.whatsapp_url, "https://wa.me/33612345678")


class BusinessSettingsFormTests(TestCase):
    def test_valid_form(self):
        form_data = {
            "business_name": "Maison Moménto Paris",
            "business_email": "concierge@maisonmomento.com",
            "primary_phone": "+33 1 40 20 50 50",
            "secondary_phone": "+33 1 40 20 50 51",
            "whatsapp_number": "+33 6 12 34 56 78",
            "instagram_url": "instagram.com/maisonmomento",  # auto-normalizes
            "facebook_url": "https://facebook.com/maisonmomento",
            "linkedin_url": "",
            "twitter_url": "",
            "business_address": "15 Rue de la Paix\n75002 Paris\nFrance",
            "business_hours": "Mon-Fri: 10am - 7pm",
            "google_maps_url": "https://maps.google.com/?q=Paris",
        }
        form = BusinessSettingsForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["instagram_url"], "https://instagram.com/maisonmomento")

    def test_invalid_email(self):
        form_data = {
            "business_name": "Maison Moménto",
            "business_email": "invalid-email-string",
            "primary_phone": "+33 1 40 20 50 50",
            "business_address": "Address",
            "business_hours": "Hours",
        }
        form = BusinessSettingsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("business_email", form.errors)

    def test_invalid_phone(self):
        form_data = {
            "business_name": "Maison Moménto",
            "business_email": "valid@email.com",
            "primary_phone": "123",  # Too short
            "business_address": "Address",
            "business_hours": "Hours",
        }
        form = BusinessSettingsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("primary_phone", form.errors)


class ContactSettingsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username="staff_admin",
            email="staff@maison.com",
            password="securepassword123",
            is_staff=True,
            is_active=True
        )
        self.regular_user = User.objects.create_user(
            username="customer_user",
            email="customer@maison.com",
            password="securepassword123",
            is_staff=False,
            is_active=True
        )

    def test_contact_settings_access_control(self):
        url = reverse("dashboard:contact_settings")

        # Anonymous user redirected to login
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.url)

        # Regular user redirected to login
        self.client.login(username="customer_user", password="securepassword123")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)

        # Staff user gets 200
        self.client.login(username="staff_admin", password="securepassword123")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Contact Information")
        self.assertContains(res, "Business Identity")

    def test_contact_settings_post_updates_storefront(self):
        self.client.login(username="staff_admin", password="securepassword123")
        post_url = reverse("dashboard:contact_settings")

        post_data = {
            "business_name": "Maison Moménto Haute Parfumerie",
            "business_email": "contact@momento-luxury.com",
            "primary_phone": "+33 9 87 65 43 21",
            "secondary_phone": "+33 1 23 45 67 89",
            "whatsapp_number": "+33 7 00 11 22 33",
            "instagram_url": "https://instagram.com/maison_momento_official",
            "facebook_url": "https://facebook.com/maisonmomentoofficial",
            "linkedin_url": "",
            "twitter_url": "",
            "business_address": "8 Place Vendôme\n75001 Paris\nFrance",
            "business_hours": "Monday – Friday: 9:00 AM – 8:00 PM\nSaturday: 10:00 AM – 6:00 PM\nSunday: By Private Appointment",
            "google_maps_url": "https://maps.google.com/?q=Place+Vendome",
        }

        res = self.client.post(post_url, data=post_data, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Contact information updated successfully")

        # Verify DB singleton updated
        settings = BusinessSettings.get_settings()
        self.assertEqual(settings.business_name, "Maison Moménto Haute Parfumerie")
        self.assertEqual(settings.business_email, "contact@momento-luxury.com")
        self.assertEqual(settings.primary_phone, "+33 9 87 65 43 21")

        # Verify Storefront Contact page immediately reflects DB changes
        contact_res = self.client.get(reverse("contact"))
        self.assertEqual(contact_res.status_code, 200)
        self.assertContains(contact_res, "contact@momento-luxury.com")
        self.assertContains(contact_res, "mailto:contact@momento-luxury.com")
        self.assertContains(contact_res, "+33 9 87 65 43 21")
        self.assertContains(contact_res, "tel:+33987654321")
        self.assertContains(contact_res, "+33 1 23 45 67 89")
        self.assertContains(contact_res, "8 Place Vendôme")
        self.assertContains(contact_res, "75001 Paris")
        self.assertContains(contact_res, "By Private Appointment")
        self.assertContains(contact_res, "https://instagram.com/maison_momento_official")
        # Ensure Twitter is NOT rendered by default because twitter_url was empty
        self.assertNotContains(contact_res, 'aria-label="X / Twitter"')

        # Verify Storefront Footer (on home / products) also immediately reflects changes
        home_res = self.client.get(reverse("catalog:product_list"))
        self.assertEqual(home_res.status_code, 200)
        self.assertContains(home_res, "Maison Moménto Haute Parfumerie")
        self.assertContains(home_res, "https://instagram.com/maison_momento_official")
        self.assertContains(home_res, "mailto:contact@momento-luxury.com")
        self.assertContains(home_res, "tel:+33987654321")
        self.assertNotContains(home_res, 'aria-label="Twitter"')
