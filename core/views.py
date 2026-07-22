from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.models import Announcement, EventConfiguration, Marks, Participant, Review, Team, Track


VIT_CAMPUSES = (
    'VIT Chennai',
    'VIT Vellore',
    'VIT Bhopal',
    'VIT-AP',
)

TRACK_ICON_MAP = {
    'artificial intelligence': 'AI',
    'machine learning': 'ML',
    'healthcare': 'HC',
    'fintech': 'FT',
    'cybersecurity': 'CY',
    'iot': 'IOT',
    'web': 'WEB',
    'sustainability': 'ESG',
    'robotics': 'BOT',
}


def home(request):
    published_tracks = list(
        Track.objects.filter(is_published=True).select_related('prize').annotate(team_total=Count('teams')).order_by('name')
    )
    reviews = Review.objects.all().order_by('scheduled_at')

    context = {
        'announcements': Announcement.objects.filter(is_pinned=True).order_by('-created_at'),
        'reviews': reviews,
        'stats': build_home_stats(reviews),
        'tracks': build_home_track_cards(published_tracks),
    }
    return render(request, 'parallax/home.html', context)


def about(request):
    return render(request, 'parallax/about.html')


def tracks(request):
    published_tracks = Track.objects.filter(is_published=True).order_by('name')
    context = {'tracks': published_tracks}
    return render(request, 'parallax/tracks.html', context)


def faq(request):
    return render(request, 'parallax/faq.html')


def team_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_panel')

        participant = ensure_participant_record(request.user)
        if participant.team:
            return redirect('participant_dashboard')
        if not participant.is_profile_complete:
            return redirect('profile_complete')
        return redirect('register_team')

    return render(request, 'parallax/team_login.html')


def registration_index(request):
    return render(request, 'parallax/registration/index.html')


def registration_leader(request):
    return render(request, 'parallax/registration/leader.html')


def registration_member(request):
    return render(request, 'parallax/registration/member.html')


def registration_payment(request):
    return render(request, 'parallax/registration/payment.html')


def registration_event_hub(request):
    return render(request, 'parallax/registration/event_hub.html')


def registration_proof(request):
    return render(request, 'parallax/registration/proof_upload.html')


def registration_review(request):
    return render(request, 'parallax/registration/review.html')


@login_required(login_url='team_login')
def profile_complete(request):
    if request.user.is_staff:
        return redirect('admin_panel')

    participant = ensure_participant_record(request.user)

    if request.method == 'POST':
        phone = request.POST.get('phone_number', '').strip()
        college_choice = request.POST.get('college_name', '').strip()
        other_college_name = request.POST.get('other_college_name', '').strip()
        reg_num = request.POST.get('reg_number', '').strip()
        college_name = resolve_college_name(college_choice, other_college_name)
        requires_reg_number = college_requires_registration_number(college_choice, college_name)

        if not phone or not college_name:
            messages.error(request, 'Phone number and college name are required.')
        elif requires_reg_number and not reg_num:
            messages.error(request, 'Registration number is required for VIT campuses.')
        else:
            participant.phone_number = phone
            participant.college_name = college_name
            participant.reg_number = reg_num or None
            participant.is_profile_complete = True
            participant.save()
            messages.success(request, 'Profile completed successfully. You can now create or join a team.')
            return redirect('register_team')

    context = {
        'participant': participant,
        'vit_campuses': VIT_CAMPUSES,
    }
    return render(request, 'parallax/profile_complete.html', context)


@login_required(login_url='team_login')
def register_team(request):
    if request.user.is_staff:
        return redirect('admin_panel')

    participant = ensure_participant_record(request.user)

    if not participant.is_profile_complete:
        return redirect('profile_complete')

    if participant.team:
        return redirect('participant_dashboard')

    published_tracks = Track.objects.filter(is_published=True).order_by('name')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_team':
            team_name = request.POST.get('team_name', '').strip()
            track_id = request.POST.get('track', '').strip()
            invoice_number = request.POST.get('invoice_number', '').strip()

            if not team_name or not track_id:
                messages.error(request, 'Team name and track are required to create a team.')
            elif Team.objects.filter(team_name__iexact=team_name).exists():
                messages.error(request, 'A team with this name already exists. Please choose another name.')
            else:
                track = get_object_or_404(Track, id=track_id, is_published=True)
                team = Team.objects.create(
                    team_name=team_name,
                    leader=participant,
                    track=track,
                    invoice_number=invoice_number or None,
                    status='PENDING',
                )
                participant.team = team
                participant.is_team_leader = True
                participant.save(update_fields=['team', 'is_team_leader'])
                messages.success(
                    request,
                    f'Team created successfully. Share team code {team.team_code} with your teammates.',
                )
                return redirect('participant_dashboard')

        elif action == 'join_team':
            team_code = request.POST.get('team_code', '').strip().upper()
            team = Team.objects.filter(team_code=team_code).first()

            if not team:
                messages.error(request, 'We could not find a team with that team code.')
            else:
                participant.team = team
                participant.is_team_leader = False
                participant.save(update_fields=['team', 'is_team_leader'])
                messages.success(request, f'You joined {team.team_name} successfully.')
                return redirect('participant_dashboard')

        else:
            messages.error(request, 'Choose a valid onboarding action to continue.')

    context = {
        'participant': participant,
        'tracks': published_tracks,
    }
    return render(request, 'parallax/register_team.html', context)


@login_required(login_url='team_login')
def participant_dashboard(request):
    if request.user.is_staff and not hasattr(request.user, 'participant'):
        return redirect('admin_panel')

    participant = ensure_participant_record(request.user)

    if not participant.is_profile_complete:
        return redirect('profile_complete')

    if not participant.team:
        return redirect('register_team')

    team = participant.team

    if request.method == 'POST':
        if not participant.is_team_leader:
            messages.error(request, 'Only the team leader can update team controls.')
            return redirect('participant_dashboard')

        team_name = request.POST.get('team_name', '').strip()
        track_id = request.POST.get('track', '').strip()
        invoice_number = request.POST.get('invoice_number', '').strip()

        if not team_name or not track_id:
            messages.error(request, 'Team name and track are required.')
            return redirect('participant_dashboard')

        if Team.objects.filter(team_name__iexact=team_name).exclude(pk=team.pk).exists():
            messages.error(request, 'Another team already uses that team name.')
            return redirect('participant_dashboard')

        next_track = get_object_or_404(Track, id=track_id, is_published=True)
        if team.payment_confirmed and team.track_id != next_track.id:
            messages.error(request, 'Track cannot be changed after payment has been confirmed.')
            return redirect('participant_dashboard')

        team.team_name = team_name
        team.track = next_track
        team.invoice_number = invoice_number or None
        team.save()
        messages.success(request, 'Team details updated successfully.')
        return redirect('participant_dashboard')

    team_members = team.members.select_related('user').order_by('-is_team_leader', 'full_name')
    marks = Marks.objects.filter(team=team).select_related('review', 'graded_by').order_by('review__scheduled_at')
    announcements = Announcement.objects.all().order_by('-is_pinned', '-created_at')
    event_config = EventConfiguration.get_solo()

    context = {
        'participant': participant,
        'team': team,
        'team_members': team_members,
        'marks': marks,
        'announcements': announcements,
        'tracks': Track.objects.filter(is_published=True).order_by('name'),
        'event_config': event_config,
        'problem_statement_sets': get_released_problem_statement_sets(team.track, event_config),
    }
    return render(request, 'parallax/dashboard.html', context)


@login_required(login_url='team_login')
def admin_panel(request):
    if not request.user.is_staff:
        return redirect('home')

    configuration = EventConfiguration.get_solo()

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()

        if action == 'update_event_date':
            raw_date = request.POST.get('event_start_date', '').strip()
            if not raw_date:
                messages.error(request, 'Event start date is required.')
            else:
                try:
                    configuration.event_start_date = date.fromisoformat(raw_date)
                    configuration.save(update_fields=['event_start_date', 'updated_at'])
                    messages.success(request, 'Event start date updated successfully.')
                except ValueError:
                    messages.error(request, 'Enter a valid event start date.')
            return redirect('admin_panel')

        if action in {'toggle_set_one', 'toggle_set_two'}:
            release = request.POST.get('release') == 'true'
            set_number = 1 if action == 'toggle_set_one' else 2

            try:
                configuration.update_problem_set_release(set_number, release, current_time=timezone.now())
                configuration.save()
                state_label = 'released' if release else 'hidden'
                messages.success(request, f'Problem Statement Set {set_number} is now {state_label}.')
            except ValueError as error:
                messages.error(request, str(error))

            return redirect('admin_panel')

    track_summary = list(
        Track.objects.annotate(team_total=Count('teams')).order_by('-team_total', 'name')
    )
    most_chosen_track = next((track for track in track_summary if track.team_total), None)
    recent_teams = Team.objects.select_related('leader', 'track').annotate(participant_total=Count('members')).order_by(
        '-created_at'
    )[:8]

    context = {
        'configuration': configuration,
        'total_registered_participants': Participant.objects.filter(team__isnull=False).count(),
        'total_payment_confirmed_participants': Participant.objects.filter(team__payment_confirmed=True).count(),
        'total_registered_teams': Team.objects.count(),
        'total_payment_confirmed_teams': Team.objects.filter(payment_confirmed=True).count(),
        'most_chosen_track': most_chosen_track,
        'track_summary': track_summary,
        'recent_teams': recent_teams,
    }
    return render(request, 'parallax/admin/dashboard.html', context)


@login_required(login_url='team_login')
def admin_teams(request):
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        team_id = request.POST.get('team_id')
        action = request.POST.get('action')
        team = get_object_or_404(Team, id=team_id)

        if action == 'approve':
            team.status = 'APPROVED'
            team.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'{team.team_name} marked as approved.')
        elif action == 'reject':
            team.status = 'REJECTED'
            team.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'{team.team_name} marked as rejected.')
        elif action == 'confirm_payment':
            team.payment_confirmed = True
            team.save()
            messages.success(request, f'Payment confirmed for {team.team_name}.')
        elif action == 'unconfirm_payment':
            team.payment_confirmed = False
            team.save()
            messages.success(request, f'Payment confirmation removed for {team.team_name}.')

        return redirect('admin_teams')

    teams = Team.objects.select_related('leader', 'track').annotate(participant_total=Count('members')).order_by(
        '-created_at'
    )
    context = {'teams': teams}
    return render(request, 'parallax/admin/teams.html', context)


@login_required(login_url='team_login')
def admin_marks(request):
    if not request.user.is_staff:
        return redirect('home')

    reviews = Review.objects.annotate(team_total=Count('marks')).order_by('scheduled_at')
    marks = Marks.objects.select_related('team', 'review', 'graded_by').order_by('-updated_at')
    context = {
        'reviews': reviews,
        'marks': marks,
    }
    return render(request, 'parallax/admin/marks.html', context)


@login_required(login_url='team_login')
def admin_announcements(request):
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        is_pinned = request.POST.get('is_pinned') == 'on'
        send_email = request.POST.get('send_email') == 'on'

        if not title or not body:
            messages.error(request, 'Announcement title and body are required.')
        else:
            Announcement.objects.create(
                title=title,
                body=body,
                is_pinned=is_pinned,
                send_email=send_email,
                created_by=request.user,
            )
            messages.success(request, 'Announcement created successfully.')
            return redirect('admin_announcements')

    announcements = Announcement.objects.all().order_by('-created_at')
    context = {'announcements': announcements}
    return render(request, 'parallax/admin/announcements.html', context)


def ensure_participant_record(user):
    default_email = user.email or f'{user.username}@parallax.local'
    participant, _ = Participant.objects.get_or_create(
        user=user,
        defaults={
            'full_name': user.get_full_name() or user.username,
            'email': default_email,
            'is_profile_complete': False,
        },
    )
    return participant


def resolve_college_name(college_choice, other_college_name):
    if college_choice == 'OTHER':
        return other_college_name
    return college_choice


def college_requires_registration_number(college_choice, college_name):
    return college_choice in VIT_CAMPUSES or college_name in VIT_CAMPUSES


def build_home_stats(reviews):
    total_teams = Team.objects.count()
    total_participants = Participant.objects.filter(team__isnull=False).count()
    published_tracks = Track.objects.filter(is_published=True).count()

    return [
        {'number': total_teams or 0, 'label': 'Registered Teams'},
        {'number': total_participants or 0, 'label': 'Participants'},
        {'number': published_tracks or 0, 'label': 'Live Tracks'},
        {'number': reviews.count() or 0, 'label': 'Review Milestones'},
    ]


def build_home_track_cards(published_tracks):
    cards = []

    for index, track in enumerate(published_tracks, start=1):
        normalized_name = track.name.strip().lower()
        prize = track.prize if hasattr(track, 'prize') else None
        cards.append(
            {
                'index': index,
                'name': track.name,
                'icon': TRACK_ICON_MAP.get(normalized_name, 'TRK'),
                'description': track.description,
                'prize': prize.first_place if prize else 'To be announced',
                'tag': f'{track.team_total} teams',
            }
        )

    return cards


def get_released_problem_statement_sets(track, configuration):
    if not track:
        return []

    released_sets = []

    if configuration.set_one_released:
        released_sets.append(
            {
                'label': 'Problem Statement Set 1',
                'released_at': configuration.set_one_released_at,
                'items': parse_problem_statement_text(track.problem_statements_set_one or track.problem_statements),
            }
        )

    if configuration.set_two_released:
        released_sets.append(
            {
                'label': 'Problem Statement Set 2',
                'released_at': configuration.set_two_released_at,
                'items': parse_problem_statement_text(track.problem_statements_set_two),
            }
        )

    return released_sets


def parse_problem_statement_text(raw_text):
    cleaned_items = [line.strip('- ').strip() for line in raw_text.splitlines() if line.strip()]
    if cleaned_items:
        return cleaned_items
    return ['Problem statements for this set have not been added yet.']
