from django.core.management.base import BaseCommand
from django.utils import timezone
from core.emailing import send_event_email
from core.models import Team


class Command(BaseCommand):
    help = 'Send the two-day-before Parallax reminder to approved team leaders.'

    def handle(self, *args, **options):
        teams = Team.objects.filter(status='APPROVED').select_related('leader')
        for team in teams:
            send_event_email(
                'Parallax 2026 is in two days',
                f'Hi {team.leader.full_name},\n\nParallax begins in two days. Your team code is {team.team_code}. '
                'Please check your dashboard for the latest review and venue information.\n\nParallax OC',
                team.leader.email,
            )
        self.stdout.write(self.style.SUCCESS(f'Sent reminders to {teams.count()} approved team leaders.'))
