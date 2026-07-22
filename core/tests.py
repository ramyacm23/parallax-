from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from . import views
from .models import EventConfiguration, Participant, Team, Track


User = get_user_model()


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


class DashboardFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.track = Track.objects.create(
            name='Artificial Intelligence',
            description='AI prototypes and applied intelligence builds.',
            problem_statements='Legacy AI prompt',
            problem_statements_set_one='AI Problem 1\nAI Problem 2',
            problem_statements_set_two='AI Problem 3\nAI Problem 4',
            is_published=True,
        )

    def create_user_with_participant(self, username, is_staff=False, is_profile_complete=True):
        user = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='test-pass-123',
            is_staff=is_staff,
        )
        participant = Participant.objects.create(
            user=user,
            full_name=username.replace('_', ' ').title(),
            email=user.email,
            phone_number='9876543210',
            college_name='VIT Chennai',
            reg_number='23BCE1234' if is_profile_complete else None,
            is_profile_complete=is_profile_complete,
        )
        return user, participant

    def test_team_login_redirects_staff_user_to_oc_dashboard(self):
        staff_user = User.objects.create_user(
            username='oc_member',
            email='oc_member@example.com',
            password='test-pass-123',
            is_staff=True,
        )
        self.client.force_login(staff_user)

        response = self.client.get(reverse('team_login'))

        self.assertRedirects(response, reverse('admin_panel'), fetch_redirect_response=False)

    def test_register_team_creates_team_code_and_assigns_leader(self):
        user, participant = self.create_user_with_participant('team_leader')
        self.client.force_login(user)

        response = self.client.post(
            reverse('register_team'),
            {
                'action': 'create_team',
                'team_name': 'Nebula Builders',
                'track': str(self.track.id),
                'invoice_number': 'INV-2048',
            },
        )

        participant.refresh_from_db()
        self.assertRedirects(response, reverse('participant_dashboard'), fetch_redirect_response=False)
        self.assertTrue(participant.is_team_leader)
        self.assertIsNotNone(participant.team)
        self.assertTrue(participant.team.team_code.startswith('TEAM'))

    def test_join_team_uses_existing_team_code(self):
        leader_user, leader_participant = self.create_user_with_participant('leader_user')
        team = Team.objects.create(team_name='Solar Forge', leader=leader_participant, track=self.track)
        leader_participant.team = team
        leader_participant.is_team_leader = True
        leader_participant.save(update_fields=['team', 'is_team_leader'])

        member_user, member_participant = self.create_user_with_participant('member_user')
        self.client.force_login(member_user)

        response = self.client.post(
            reverse('register_team'),
            {
                'action': 'join_team',
                'team_code': team.team_code,
            },
        )

        member_participant.refresh_from_db()
        self.assertRedirects(response, reverse('participant_dashboard'), fetch_redirect_response=False)
        self.assertEqual(member_participant.team, team)
        self.assertFalse(member_participant.is_team_leader)

    def test_problem_statement_release_rules_are_enforced(self):
        configuration = EventConfiguration(event_start_date=date(2026, 8, 18))
        before_window = date(2026, 8, 13)
        set_one_day = date(2026, 8, 14)

        self.assertFalse(configuration.can_release_set_one(today=before_window))
        self.assertTrue(configuration.can_release_set_one(today=set_one_day))

        with self.assertRaisesMessage(ValueError, 'Problem Statement Set 1 must be released before Set 2.'):
            configuration.update_problem_set_release(
                2,
                True,
                current_time=timezone.make_aware(datetime(2026, 8, 16, 10, 0)),
            )

    def test_oc_team_management_can_confirm_payment(self):
        staff_user, _ = self.create_user_with_participant('staff_owner', is_staff=True)
        leader_user, leader_participant = self.create_user_with_participant('leader_for_team')
        team = Team.objects.create(team_name='Orbit Works', leader=leader_participant, track=self.track)
        leader_participant.team = team
        leader_participant.is_team_leader = True
        leader_participant.save(update_fields=['team', 'is_team_leader'])

        self.client.force_login(staff_user)

        response = self.client.post(
            reverse('admin_teams'),
            {
                'team_id': team.id,
                'action': 'confirm_payment',
            },
        )

        team.refresh_from_db()
        self.assertRedirects(response, reverse('admin_teams'), fetch_redirect_response=False)
        self.assertTrue(team.payment_confirmed)
        self.assertIsNotNone(team.payment_confirmed_at)
