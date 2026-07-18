from django.conf import settings
from django.core.mail import send_mail


def send_event_email(subject, message, recipient):
    """Single, safe entry point for participant emails."""
    if recipient:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)


def registration_confirmation(team):
    send_event_email(
        'Parallax 2026 registration received',
        f'Hi {team.leader.full_name},\n\nYour team “{team.team_name}” has been registered. '
        f'Your team code is {team.team_code}. Status: Pending Approval.\n\nSee beyond. Build beyond.\nParallax OC',
        team.leader.email,
    )


def approval_confirmation(team):
    send_event_email(
        'Your Parallax 2026 team is approved',
        f'Hi {team.leader.full_name},\n\nGreat news: “{team.team_name}” is approved for Parallax 2026. '
        'Please watch your dashboard for challenge releases and review updates.\n\nParallax OC',
        team.leader.email,
    )
