import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_event_email(subject, message, recipient):
    """Single, safe entry point for participant emails.

    Sends are best-effort: while real credentials/templates are owned by Akash,
    a mail failure must never break the registration or payment flow.
    """
    if not recipient:
        return
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=True)
    except Exception:  # pragma: no cover - defensive; placeholder emailing
        logger.exception('Failed to send event email to %s', recipient)


# --- Leader registration funnel placeholders (real templates owned by Akash) ---

def leader_registration_received(registration):
    """Placeholder: fired when a team leader completes the registration form."""
    send_event_email(
        'Parallax 2026 - registration received',
        f'Hi {registration.first_name},\n\nWe have received your Parallax 2026 team-leader '
        'registration. Complete your payment to confirm your slot.\n\nParallax OC',
        registration.email,
    )


def leader_payment_confirmation(registration):
    """Placeholder: fired after a leader's payment is confirmed."""
    send_event_email(
        'Parallax 2026 - payment confirmed',
        f'Hi {registration.first_name},\n\nYour payment for Parallax 2026 has been confirmed. '
        'See you at the event!\n\nParallax OC',
        registration.email,
    )


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
