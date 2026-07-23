from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.emailing import leader_payment_confirmation, leader_registration_received
from core.models import (
    Announcement,
    EventConfiguration,
    LeaderRegistration,
    Marks,
    Participant,
    ProblemStatement,
    Review,
    Team,
    Track,
)


VIT_CAMPUSES = (
    'VIT Chennai',
    'VIT Vellore',
    'VIT Bhopal',
    'VIT-AP',
)

# Team-leader registration form categories currently confirmed by the core team.
# 6 further categories are pending; add them here and to LeaderRegistration.
REGISTRATION_FIELD_LABELS = {
    'first_name': 'first name',
    'last_name': 'last name',
    'email': 'email ID',
    'college': 'college',
    'department': 'department',
    'reg_number': 'registration number',
    'graduation_year': 'graduation year',
    'city': 'city',
}

DEFAULT_TRACKS = [
    {
        'name': 'Aviation & Space Tech',
        'description': 'Build intelligent systems for aerospace, autonomous flight and satellite technologies.',
        'icon': 'fa-rocket',
    },
    {
        'name': 'Embedded Systems',
        'description': 'Create real-time hardware-software systems for devices, automation and edge computing.',
        'icon': 'fa-microchip',
    },
    {
        'name': 'Healthcare & Assistive Tech',
        'description': 'Design technologies that improve access, rehabilitation and quality of life.',
        'icon': 'fa-heart-pulse',
    },
    {
        'name': 'Sustainable Smart Infrastructure',
        'description': 'Engineer resilient cities through smart energy, mobility and monitoring.',
        'icon': 'fa-leaf',
    },
    {
        'name': 'Communication & Cyber Physical Systems',
        'description': 'Develop secure networks and intelligent connected infrastructure.',
        'icon': 'fa-satellite-dish',
    },
]

TRACK_ICON_MAP = {
    'artificial intelligence': 'fa-brain',
    'machine learning': 'fa-robot',
    'healthcare': 'fa-heart-pulse',
    'fintech': 'fa-chart-line',
    'cybersecurity': 'fa-shield-halved',
    'iot': 'fa-microchip',
    'web': 'fa-globe',
    'sustainability': 'fa-leaf',
    'robotics': 'fa-gears',
}

INFORMATION_PAGES = {
    'schedule': ('Review Schedule', 'Every checkpoint is designed to turn momentum into measurable progress.'),
    'prizes': ('Prizes & Recognition', 'The prize pool and sponsor awards will be announced here.'),
    'guidelines': ('Guidelines', 'Build boldly. Work fairly. Leave every space better than you found it.'),
    'theme': ('Theme', 'Same problem. Different view. Better answer.'),
    'contact': ('Contact the OC', 'Have a question? The organising committee is here to help.'),
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
        'tracks': build_home_track_cards(published_tracks) if published_tracks else build_default_track_cards(),
    }
    return render(request, 'parallax/home.html', context)


def about(request):
    context = {
        'core_members': [],
    }
    return render(request, 'parallax/about.html', context)


def tracks(request):
    published_tracks = list(Track.objects.filter(is_published=True).order_by('name'))
    context = {'tracks': published_tracks or build_default_track_cards()}
    return render(request, 'parallax/tracks.html', context)


def faq(request):
    return render(request, 'parallax/faq.html')


def information(request, page):
    if page not in INFORMATION_PAGES:
        raise Http404('Information page not found.')

    heading, tagline = INFORMATION_PAGES[page]
    context = {
        'page': page,
        'heading': heading,
        'tagline': tagline,
        'reviews': Review.objects.all().order_by('scheduled_at'),
        'tracks': build_default_track_cards(),
    }
    return render(request, 'parallax/information.html', context)


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
    """Step 1 - the team leader fills the registration form."""
    if request.method == 'POST':
        form_values = {key: request.POST.get(key, '').strip() for key in REGISTRATION_FIELD_LABELS}

        missing = [label for key, label in REGISTRATION_FIELD_LABELS.items() if not form_values[key]]
        graduation_year = None
        if form_values['graduation_year']:
            try:
                graduation_year = int(form_values['graduation_year'])
            except ValueError:
                missing.append('a valid graduation year')

        if missing:
            messages.error(request, 'Please complete all fields: ' + ', '.join(missing) + '.')
            return render(request, 'parallax/registration/leader.html', {'form_values': form_values})

        registration, _ = LeaderRegistration.objects.update_or_create(
            email=form_values['email'],
            defaults={
                'user': request.user if request.user.is_authenticated else None,
                'first_name': form_values['first_name'],
                'last_name': form_values['last_name'],
                'college': form_values['college'],
                'department': form_values['department'],
                'reg_number': form_values['reg_number'],
                'graduation_year': graduation_year,
                'city': form_values['city'],
            },
        )

        if not registration.registration_email_sent:
            leader_registration_received(registration)  # placeholder - Akash owns real email
            registration.registration_email_sent = True
            registration.save(update_fields=['registration_email_sent', 'updated_at'])

        request.session['leader_registration_id'] = registration.id
        messages.success(request, 'Registration saved. Choose how you would like to pay.')
        return redirect('registration_payment')

    return render(request, 'parallax/registration/leader.html', {'form_values': {}})


def _current_leader_registration(request):
    registration_id = request.session.get('leader_registration_id')
    if not registration_id:
        return None
    return LeaderRegistration.objects.filter(id=registration_id).first()


def registration_member(request):
    return render(request, 'parallax/registration/member.html')


def registration_payment(request):
    """Step 2 - payment choice: pay later or continue to the event hub."""
    registration = _current_leader_registration(request)
    if registration is None:
        messages.info(request, 'Please complete the team leader registration first.')
        return redirect('registration_leader')

    if request.method == 'POST':
        choice = request.POST.get('payment_choice')
        if choice == 'pay_later':
            registration.payment_status = LeaderRegistration.PAYMENT_PAY_LATER
            registration.save(update_fields=['payment_status', 'updated_at'])
            messages.success(request, 'Saved. You can complete the payment later from the event hub.')
            return redirect('registration_payment')
        if choice == 'go_to_payment':
            return redirect('registration_event_hub')
        messages.error(request, 'Choose a payment option to continue.')

    context = {
        'registration': registration,
        'event_hub_url': getattr(settings, 'EVENT_HUB_URL', '#'),
    }
    return render(request, 'parallax/registration/payment.html', context)


def registration_event_hub(request):
    """Steps 3 & 4 - hand off to the external event hub and handle the return."""
    registration = _current_leader_registration(request)
    if registration is None:
        messages.info(request, 'Please complete the team leader registration first.')
        return redirect('registration_leader')

    # Step 4: the event hub redirects back with ?status=paid once payment is done.
    if request.GET.get('status') == 'paid':
        if registration.payment_status != LeaderRegistration.PAYMENT_PAID:
            registration.payment_status = LeaderRegistration.PAYMENT_PAID
            registration.save(update_fields=['payment_status', 'updated_at'])
        if not registration.payment_email_sent:
            leader_payment_confirmation(registration)  # placeholder - Akash owns real email
            registration.payment_email_sent = True
            registration.save(update_fields=['payment_email_sent', 'updated_at'])
        messages.success(request, 'Payment confirmed. Welcome to Parallax 2026!')
        return redirect('registration_payment')

    context = {
        'registration': registration,
        'event_hub_url': getattr(settings, 'EVENT_HUB_URL', '#'),
    }
    return render(request, 'parallax/registration/event_hub.html', context)


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
    if request.user.is_staff:
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

        action = request.POST.get('action', '').strip()

        if action == 'book_problem_statement':
            problem_statement_id = request.POST.get('problem_statement', '').strip()
            if not problem_statement_id:
                messages.error(request, 'Select a problem statement to book.')
                return redirect('participant_dashboard')

            with transaction.atomic():
                problem_statement = (
                    ProblemStatement.objects.select_for_update()
                    .filter(id=problem_statement_id, is_active=True, track__is_problem_live=True)
                    .first()
                )
                if problem_statement is None:
                    messages.error(request, 'That problem statement is not available for booking.')
                    return redirect('participant_dashboard')

                already_booked = problem_statement.booked_teams.exclude(pk=team.pk).count()
                if problem_statement.slot_capacity and already_booked >= problem_statement.slot_capacity:
                    messages.error(
                        request,
                        'All slots for this problem statement are filled. Please choose another one.',
                    )
                    return redirect('participant_dashboard')

                team.problem_statement = problem_statement
                team.track = problem_statement.track
                team.save(update_fields=['problem_statement', 'track', 'updated_at'])

            messages.success(request, f'Slot booked for "{problem_statement.title}".')
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
    problem_statement_sets = get_released_problem_statement_sets(team.track, event_config)
    review_score_count = marks.count()

    bookable_problem_statements = list(
        ProblemStatement.objects.filter(is_active=True, track__is_problem_live=True)
        .select_related('track')
        .annotate(booked_total=Count('booked_teams'))
        .order_by('track__name', 'code', 'title')
    )

    context = {
        'participant': participant,
        'team': team,
        'team_members': team_members,
        'marks': marks,
        'review_score_count': review_score_count,
        'announcements': announcements,
        'tracks': Track.objects.filter(is_published=True).order_by('name'),
        'event_config': event_config,
        'problem_statement_sets': problem_statement_sets,
        'released_problem_set_count': len(problem_statement_sets),
        'bookable_problem_statements': bookable_problem_statements,
        'booked_problem_statement': team.problem_statement,
        'progress_items': build_participant_progress(team, participant, problem_statement_sets, review_score_count),
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

    track_summary = list(Track.objects.annotate(team_total=Count('teams')).order_by('-team_total', 'name'))
    most_chosen_track = next((track for track in track_summary if track.team_total), None)
    recent_teams = Team.objects.select_related('leader', 'track').annotate(participant_total=Count('members')).order_by(
        '-created_at'
    )[:8]

    total_leader_registrations = LeaderRegistration.objects.count()
    total_leaders_paid = LeaderRegistration.objects.filter(
        payment_status=LeaderRegistration.PAYMENT_PAID
    ).count()
    total_leaders_pay_later = LeaderRegistration.objects.filter(
        payment_status=LeaderRegistration.PAYMENT_PAY_LATER
    ).count()

    problem_statement_summary = list(
        ProblemStatement.objects.select_related('track')
        .annotate(booked_total=Count('booked_teams'))
        .order_by('track__name', 'code', 'title')
    )

    context = {
        'configuration': configuration,
        'pending_teams': Team.objects.filter(status='PENDING').count(),
        'approved_teams': Team.objects.filter(status='APPROVED').count(),
        'total_registered_participants': Participant.objects.filter(team__isnull=False).count(),
        'total_payment_confirmed_participants': Participant.objects.filter(team__payment_confirmed=True).count(),
        'total_registered_teams': Team.objects.count(),
        'total_payment_confirmed_teams': Team.objects.filter(payment_confirmed=True).count(),
        'total_leader_registrations': total_leader_registrations,
        'total_leaders_paid': total_leaders_paid,
        'total_leaders_pay_later': total_leaders_pay_later,
        'problem_statement_summary': problem_statement_summary,
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

    teams = (
        Team.objects.select_related('leader', 'track')
        .prefetch_related('members__user')
        .annotate(participant_total=Count('members'))
        .order_by('-created_at')
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


@login_required(login_url='team_login')
def admin_tracks(request):
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action', 'toggle_track')

        if action == 'add_problem_statement':
            track = get_object_or_404(Track, id=request.POST.get('track_id'))
            title = request.POST.get('title', '').strip()
            if not title:
                messages.error(request, 'Problem statement title is required.')
            else:
                ProblemStatement.objects.create(
                    track=track,
                    code=request.POST.get('code', '').strip(),
                    title=title,
                    description=request.POST.get('description', '').strip(),
                    slot_capacity=_parse_positive_int(request.POST.get('slot_capacity')),
                )
                messages.success(request, f'Problem statement "{title}" added.')
            return redirect('admin_tracks')

        if action == 'update_slot_capacity':
            problem_statement = get_object_or_404(
                ProblemStatement, id=request.POST.get('problem_statement_id')
            )
            problem_statement.slot_capacity = _parse_positive_int(request.POST.get('slot_capacity'))
            problem_statement.is_active = request.POST.get('is_active') == 'on'
            problem_statement.save(update_fields=['slot_capacity', 'is_active', 'updated_at'])
            messages.success(request, f'Slots updated for "{problem_statement.title}".')
            return redirect('admin_tracks')

        track = get_object_or_404(Track, id=request.POST.get('track_id'))
        field = request.POST.get('field')
        if field in {'is_published', 'is_problem_live'}:
            setattr(track, field, not getattr(track, field))
            track.save(update_fields=[field, 'updated_at'])

        return redirect('admin_tracks')

    context = {
        'tracks': Track.objects.annotate(team_total=Count('teams')).order_by('name'),
        'problem_statements': (
            ProblemStatement.objects.select_related('track')
            .annotate(booked_total=Count('booked_teams'))
            .order_by('track__name', 'code', 'title')
        ),
    }
    return render(request, 'parallax/admin/tracks.html', context)


def _parse_positive_int(raw_value):
    try:
        return max(int(raw_value), 0)
    except (TypeError, ValueError):
        return 0


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


def build_default_track_cards():
    cards = []

    for index, track in enumerate(DEFAULT_TRACKS, start=1):
        cards.append(
            {
                'index': index,
                'name': track['name'],
                'icon': track['icon'],
                'description': track['description'],
                'prize': 'To be announced',
                'tag': 'Open for teams',
            }
        )

    return cards


def build_home_track_cards(published_tracks):
    cards = []

    for index, track in enumerate(published_tracks, start=1):
        normalized_name = track.name.strip().lower()
        prize = track.prize if hasattr(track, 'prize') else None
        cards.append(
            {
                'index': index,
                'name': track.name,
                'icon': TRACK_ICON_MAP.get(normalized_name, 'fa-bolt'),
                'description': track.description,
                'prize': prize.first_place if prize else 'To be announced',
                'tag': f'{track.team_total} teams',
            }
        )

    return cards


def get_released_problem_statement_sets(track, configuration):
    if not track or not track.is_problem_live:
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


def build_participant_progress(team, participant, problem_statement_sets, review_score_count):
    progress_items = [
        {
            'label': 'Profile',
            'state': 'Complete',
            'tone': 'success',
            'description': 'Your participant profile is complete and linked to the team space.',
        },
        {
            'label': 'Team Access',
            'state': team.team_code,
            'tone': 'info',
            'description': f'You are currently part of {team.team_name}.',
        },
        {
            'label': 'Track Selection',
            'state': team.track.name if team.track else 'Pending',
            'tone': 'success' if team.track else 'pending',
            'description': 'The team leader can update the selected track until payment is confirmed.',
        },
        {
            'label': 'Review Status',
            'state': team.get_status_display(),
            'tone': 'success' if team.status == 'APPROVED' else 'danger' if team.status == 'REJECTED' else 'pending',
            'description': 'This is the current organizer review status of your team registration.',
        },
        {
            'label': 'Payment Reference',
            'state': 'Submitted' if team.invoice_number else 'Pending',
            'tone': 'success' if team.invoice_number else 'pending',
            'description': 'Participants only see whether the reference is submitted. Full payment details stay with OC.',
        },
        {
            'label': 'Payment Confirmation',
            'state': 'Confirmed' if team.payment_confirmed else 'Pending OC Check',
            'tone': 'success' if team.payment_confirmed else 'pending',
            'description': 'OC members confirm event hub payments from the organizer dashboard.',
        },
        {
            'label': 'Problem Statements',
            'state': f'{len(problem_statement_sets)} Set(s) Live' if problem_statement_sets else 'Awaiting Release',
            'tone': 'success' if problem_statement_sets else 'pending',
            'description': 'Released statements for your selected track appear here automatically.',
        },
        {
            'label': 'Evaluation',
            'state': f'{review_score_count} Review(s) Scored' if review_score_count else 'No Scores Yet',
            'tone': 'info' if review_score_count else 'pending',
            'description': 'Review marks are shown here only for your own team progress tracking.',
        },
    ]

    if participant.is_team_leader:
        progress_items.append(
            {
                'label': 'Leader Controls',
                'state': 'Enabled',
                'tone': 'info',
                'description': 'You can update the team name, track, and payment reference for your own team only.',
            }
        )

    return progress_items
