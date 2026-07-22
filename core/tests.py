from django.test import RequestFactory, SimpleTestCase

from . import views


class RegistrationPageTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_registration_pages_render(self):
        page_specs = [
            ('/registration/', views.registration_index),
            ('/registration/leader/', views.registration_leader),
            ('/registration/member/', views.registration_member),
            ('/registration/payment/', views.registration_payment),
            ('/registration/event-hub/', views.registration_event_hub),
            ('/registration/proof-upload/', views.registration_proof),
            ('/registration/review/', views.registration_review),
        ]

        for path, view in page_specs:
            with self.subTest(path=path):
                request = self.factory.get(path)
                response = view(request)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.content)
