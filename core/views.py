from datetime import date
from decimal import Decimal, InvalidOperation
from django.shortcuts import render
from .google_sheet import get_role, get_all_teams
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
from django.http import Http404, request
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from core.models import (
    Announcement,
    EventConfiguration,
    Marks,
    Participant,
    ProblemStatement,
    Review,
    Sponsor,
    Team,
    Track,
)
DEFAULT_TRACKS = [
    {
        'name': 'Aviation & Space Tech',
        'description': 'Build intelligent systems for aerospace, autonomous flight and satellite technologies.',
        'icon': 'fa-rocket',
    },
    {
        'name': 'Internet of Things',
        'description': 'Create real-time hardware-software systems for devices, automation and edge computing.',
        'icon': 'fa-microchip',
    },
    {
        'name': 'Healthcare & Assistive Tech',
        'description': 'Design technologies that improve access, rehabilitation and quality of life.',
        'icon': 'fa-heart-pulse',
    },
    {
        'name': 'Artificial Intelligence & Machine Learning',
        'description': 'Engineer resilient cities through smart energy, mobility and monitoring.',
        'icon': 'fa-robot',
    },
    {
        'name': 'Communication & Networking',
        'description': 'Develop secure networks and intelligent connected infrastructure.',
        'icon': 'fa-satellite-dish',
    },
]
TRACK_ICON_MAP = {
    'Artificial intelligence': 'fa-brain',
    'Machine learning': 'fa-robot',
    'healthcare': 'fa-heart-pulse',
    'iot': 'fa-microchip',
    'web': 'fa-globe',
    'robotics': 'fa-gears',
}
INFORMATION_PAGES = {
    'schedule': ('Review Schedule', 'Every checkpoint is designed to turn momentum into measurable progress.'),
    'prizes': ('Prizes & Recognition','  '),
    'guidelines': ('Guidelines', 'Build boldly. Work fairly. Leave every space better than you found it.'),
    'theme': ('Theme', 'Same problem. Different view. Better answer.'),
    'contact': ('Contact the OC', 'Have a question? The organising committee is here to help.'),
}
def home(request):
    published_tracks = list(
        Track.objects.filter(is_published=True)
        .select_related('prize')
        .annotate(team_total=Count('teams'))
        .order_by('name')
    )
    reviews = Review.objects.all().order_by('scheduled_at')
    active_sponsors = Sponsor.objects.filter(
        is_active=True
    ).order_by(
        'display_order',
        'name'
    )
    context = {
        'stats': build_home_stats(reviews),
        'tracks': (
            build_home_track_cards(published_tracks)
            if published_tracks
            else build_default_track_cards()
        ),

    'title_sponsors': active_sponsors.filter(sponsor_type__iexact="Title Sponsor"),
    'technical_sponsors': active_sponsors.filter(sponsor_type__iexact="Technical Sponsor"),
    'co_powered_sponsors': active_sponsors.filter(sponsor_type__iexact="Co-Powered"),
    'sponsors': active_sponsors,
    'announcements': Announcement.objects.all()
    .order_by('-is_pinned', '-created_at')[:6],
    }
    return render(request, 'parallax/home.html', context)
def about(request):
    context = {
        'core_members': [],
    }
    return render(request, 'parallax/about.html', context)
from django.db.models import Prefetch
def tracks(request):
    published_tracks = (
        Track.objects.filter(is_published=True)
        .prefetch_related(
            Prefetch(
                'problem_statement_slots',
                queryset=ProblemStatement.objects.filter(
                    is_active=True
                ).order_by('code', 'title'),
                to_attr='public_problem_statements',
            )
        )
        .order_by('name')
    )
    for track in published_tracks:
        print(track.name, len(track.public_problem_statements))
    context = {
        'tracks': published_tracks,
    }
    return render(request, 'parallax/tracks.html', context)
def information(request, page):
    if page not in INFORMATION_PAGES:
        from django.http import Http404
        raise Http404("Page not found")
    if page not in INFORMATION_PAGES:
        from django.http import Http404
        raise Http404("Page not found")
    return render(
    request,
    'parallax/information.html',
    {
        'page': page,
        'heading': INFORMATION_PAGES[page][0],
        'tagline': INFORMATION_PAGES[page][1],
        'reviews': Review.objects.all().order_by('scheduled_at'),
    }
)
def team_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("admin_panel")
        return redirect("participant_dashboard")
    return render(
        request,
        "parallax/team_login.html",
        {
            "google_login_enabled": getattr(
                settings,
                "GOOGLE_OAUTH_CONFIGURED",
                False,
            )
        },
    )
from django.shortcuts import redirect
def registration_index(request):
    return redirect("https://eventhubcc.vit.ac.in/EventHub/#:~:text=Parallax")
from django.shortcuts import redirect
from django.conf import settings
def registration_event_hub(request):
    return redirect(settings.EVENT_HUB_URL)
@login_required
def participant_dashboard(request):
    if request.user.is_staff:
        return redirect("admin_panel")
    participant = Participant.objects.filter(user=request.user).first()
    if participant is None:
        return redirect("access_denied")
    team = participant.team
    track_id = None
    if request.method == "POST":
        team_name = request.POST.get("team_name")
        if team_name is not None:
            team_name = team_name.strip()
            if not team_name:
                messages.error(request, "Team name cannot be empty.")
            else:
                team.team_name = team_name
                team.save(update_fields=["team_name"])
                messages.success(request, "Team name saved successfully.")
            return redirect("participant_dashboard")
        track_id = request.POST.get("track")
        problem_statement_id = request.POST.get("problem_statement")
        if problem_statement_id:
            problem_statement = get_object_or_404(
                ProblemStatement,
                id=problem_statement_id,
                is_published=True,
                is_active=True,
            )
            if (
                team.problem_statement_id != problem_statement.id
                and problem_statement.is_full
            ):
                messages.error(
                    request,
                    "This problem statement's slots are filled.",
                )
            else:
                team.problem_statement = problem_statement
                team.save(update_fields=["problem_statement"])
                messages.success(
                    request,
                    "Problem statement selected successfully.",
                )
            return redirect("participant_dashboard")    
    if track_id:      
        track = get_object_or_404(Track, id=track_id)
        team.track = track
        team.save(update_fields=["track"])
        messages.success(request, "Track selected successfully.")
        return redirect("participant_dashboard")
    needs_team_name = not bool((team.team_name or "").strip())
    tracks = Track.objects.filter(is_published=True)
    problem_statements = ProblemStatement.objects.filter(is_published=True)
    announcements = Announcement.objects.all().order_by("-created_at")
    reviews = Review.objects.all().order_by("scheduled_at")

    def split_lines(raw_text):
        if not raw_text:
            return []
        return [line.strip() for line in raw_text.splitlines() if line.strip()]

    timeline = build_participant_timeline(team)
    context = {
    "needs_team_name": needs_team_name,
    "team": {
        "name": team.team_name,
        "id": team.team_code,
        "leader_name": team.leader.full_name if team.leader else "",
        "leader_email": team.leader.email if team.leader else "",
        "college": participant.college_name,
        "track_id": team.track.id if team.track else None,
        "problem_statement_id": team.problem_statement_id,
        "problem_statement_code": team.problem_statement.code if team.problem_statement else None,
        "problem_statement_title": team.problem_statement.title if team.problem_statement else None,
    },
    "registration": {
        "status": team.status.lower(),
    },
    "tracks": Track.objects.filter(
        is_published=True
    ),
    "tracks_json": [
        {"id": t.id, "name": t.name, "description": t.description}
        for t in Track.objects.filter(is_published=True)
    ],
    "track": {
        "released": bool(team.track),
        "name": team.track.name if team.track else None,
        "public_problem_statements": [
            {
                "id": ps.id,
                "code": ps.code,
                "title": ps.title,
                "description": ps.description,
                "context": ps.context,
                "expected_impact": ps.impact,
                "minimum_requirements": split_lines(ps.min_requirements),
                "dependencies": split_lines(ps.dependencies),
                "slot_capacity": ps.slot_capacity,
                "slots_available": ps.slots_available,
                "is_full": ps.is_full,
                "slots_label": f"[{ps.slots_available}/{ps.slot_capacity}]",
            }
            for ps in ProblemStatement.objects.filter(
                track=team.track,
                is_published=True,
                is_active=True,
            )
        ] if team.track else [],
    },
    "marks": [
        {
            "round": mark.review.name,
            "score": mark.score,
            "weightage": f"{mark.review.weightage}%",
            "remarks": mark.remarks,
            "last_updated": mark.updated_at.strftime("%d %b %Y"),
        }
        for mark in Marks.objects.filter(team=team).select_related("review")
    ],
    "members": [
        {
            "name": member.full_name,
            "role": "Leader" if member.is_team_leader else "Member",
            "email": member.email,
            "phone": member.phone_number,
            "is_leader": member.is_team_leader,
        }
        for member in team.members.all()
    ],
    "announcements": [
        {
            "title": a.title,
            "message": a.body,
            "timestamp": a.created_at.strftime("%d %b %Y"),
            "tag": "general",
        }
        for a in Announcement.objects.all().order_by("-created_at")
    ],
    "downloads": {
        "rulebook_url": None,
        "schedule_url": None,
        "resources_url": None,
        "certificates_url": None,
        "certificates_enabled": False,
    },
    "timeline": timeline,
    "urls": {
        "home": reverse("home"),
        "set_team_name": reverse("participant_dashboard"),
        "select_track": reverse("participant_dashboard"),
        "select_problem_statement": reverse("participant_dashboard"),
        "logout": reverse("account_logout"),
    },
    }
    return render(request, "parallax/dashboard.html", context)
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
        'problem_statement_summary': problem_statement_summary,
        'most_chosen_track': most_chosen_track,
        'configuration': configuration,
        'track_summary': track_summary,
        'recent_teams': recent_teams,
    }
    return render(request, 'parallax/admin/dashboard.html', context)
@login_required(login_url='team_login')
def admin_teams(request):
    if not request.user.is_staff:
        return redirect('home')
    teams = []
    for row in get_all_teams():
        team = {
        "team_id": row.get("Team ID", ""),
        "team_name": row.get("Team Name", ""),
        "leader_name": row.get("Lead Name", ""),
        "registration_email": row.get("Registration Email", ""),
        "phone_number": row.get("Phone number ", ""),   # note the trailing space
        "college_name": row.get("Collage name", ""),
        "track": row.get("Track", ""),
        "members": row.get("Members", ""),
            }
        teams.append(team)
    selected_track_id = request.GET.get("track", "").strip()
    if selected_track_id:
        selected_track = Track.objects.filter(id=selected_track_id).first()
        if selected_track:
            teams = [
                team
                for team in teams
                if team["track"].strip().lower()
                == selected_track.name.strip().lower()
            ]
    context = {
        "teams": teams,
        "tracks": Track.objects.order_by("name"),
        "selected_track_id": selected_track_id,
    }
    return render(request, "parallax/admin/teams.html", context)
@login_required(login_url='team_login')
def admin_marks(request):
    if not request.user.is_staff:
        return redirect('home')
    reviews = Review.objects.annotate(team_total=Count('marks')).order_by('scheduled_at')
    marks = Marks.objects.select_related('team', 'review', 'graded_by').order_by('-updated_at')
    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        if action == 'create_round':
            name = request.POST.get('name', '').strip()
            if not name:
                messages.error(request, 'Round name is required.')
            else:
                Review.objects.create(
                    name=name,
                    weightage=_parse_positive_int(request.POST.get('weightage')),
                    max_marks=_parse_positive_int(request.POST.get('max_marks')) or 100,
                )
                messages.success(request, f'Round "{name}" created.')
            return redirect('admin_marks')
        if action == 'delete_round':
            review = get_object_or_404(
                Review,
                id=request.POST.get('review_id')
            )
            round_name = review.name
            review.delete()
            messages.success(
                request,
                f'Round "{round_name}" deleted successfully.'
            )
            return redirect('admin_marks')
        if action == 'award_marks':
            review = get_object_or_404(Review, id=request.POST.get('review_id'))
            team = get_object_or_404(Team, id=request.POST.get('team_id'))
            raw_score = request.POST.get('score', '').strip()   
            if not raw_score:
                messages.error(request, 'Enter a score.')
                return redirect('admin_marks')
            Marks.objects.update_or_create(
                team=team,
                review=review,
                defaults={
                'score': raw_score,
                'remarks': request.POST.get('remarks', '').strip(),
                'graded_by': request.user,
                }
            )
            messages.success(
                request,
                f'Marks saved for {team.team_name} - {review.name}.'
            )
            return redirect('admin_marks')
    reviews = Review.objects.annotate(team_total=Count('marks')).order_by('scheduled_at', 'name')
    teams = Team.objects.select_related('track').order_by('team_name')
    marks = Marks.objects.select_related('team', 'review', 'graded_by').order_by('-updated_at')
    total_weightage = sum(review.weightage for review in reviews)
    context = {
        'reviews': reviews,
        'teams': teams,
        'marks': marks,
        'total_weightage': total_weightage,
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
    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        if action == "add_problem_statement":
            track = get_object_or_404(
                Track,
                id=request.POST.get("track_id")
            )
            title = request.POST.get("title", "").strip()
            if not title:
                messages.error(request, "Problem title is required.")
                return redirect("admin_tracks")
            ProblemStatement.objects.create(
                track=track,
                code=request.POST.get("code", "").strip(),
                title=title,
                description=_limit_text(
                    request.POST.get("statement")
                ),
                context=_limit_text(
                    request.POST.get("context")
                ),
                min_requirements=_limit_text(
                    request.POST.get("minimum_requirements")
                ),
                dependencies=_limit_text(
                    request.POST.get("dependencies")
                ),
                slot_capacity=_parse_positive_int(
                    request.POST.get("slot_capacity")
                ),
                is_active=True,
                is_published=request.POST.get("is_published") == "on",
            )
            messages.success(
                request,
                "Problem statement added successfully."
            )
            return redirect("admin_tracks")
        if action == "edit_problem_statement":
            ps = get_object_or_404(
                ProblemStatement,
                id=request.POST.get("problem_statement_id")
            )
            ps.track_id = request.POST.get("track_id")
            ps.code = request.POST.get("code", "").strip()
            ps.title = request.POST.get("title", "").strip()
            ps.description = _limit_text(
                request.POST.get("statement")
            )
            ps.context = _limit_text(
                request.POST.get("context")
            )
            ps.min_requirements = _limit_text(
                request.POST.get("minimum_requirements")
            )
            ps.dependencies = _limit_text(
                request.POST.get("dependencies")
            )
            ps.slot_capacity = _parse_positive_int(
                request.POST.get("slot_capacity")
            )
            ps.is_published = (
                request.POST.get("is_published") == "on"
            )
            ps.save()
            messages.success(
                request,
                "Problem statement updated."
            )
            return redirect("admin_tracks")
        if action == "delete_problem_statement":
            ps = get_object_or_404(
                ProblemStatement,
                id=request.POST.get("problem_statement_id")
            )
            ps.delete()
            messages.success(
                request,
                "Problem statement deleted."
            )
            return redirect("admin_tracks")
        if action == "toggle_problem_published":
            ps = get_object_or_404(
                ProblemStatement,
                id=request.POST.get("problem_statement_id")
            )
            ps.is_published = not ps.is_published
            ps.save(update_fields=[
                "is_published",
                "updated_at"
            ])
            return redirect("admin_tracks")
        if action == "toggle_track":
            track = get_object_or_404(
                Track,
                id=request.POST.get("track_id")
            )
            field = request.POST.get("field")
            if field in [
                "is_published",
                "is_problem_live"
            ]:
                setattr(
                    track,
                    field,
                    not getattr(track, field)
                )
                track.save(
                    update_fields=[
                        field,
                        "updated_at"
                    ]
                )
            return redirect("admin_tracks")
    tracks = (
        Track.objects
        .prefetch_related(
            Prefetch(
                "problem_statement_slots",
                queryset=ProblemStatement.objects.order_by(
                    "code",
                    "title"
                ),
                to_attr="public_problem_statements"
            )
        )
        .order_by("name")
    )
    problem_statements = (
        ProblemStatement.objects
        .select_related("track")
        .order_by(
            "track__name",
            "code",
            "title"
        )
    )
    context = {
        "tracks": tracks,
        "problem_statements": problem_statements,
    }
    return render(
        request,
        "parallax/admin/tracks.html",
        context
    )
@login_required(login_url='team_login')
def admin_sponsors(request):
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()

        if action == 'delete_sponsor':
            sponsor = get_object_or_404(
                Sponsor,
                id=request.POST.get('sponsor_id')
            )
            sponsor.delete()
            messages.success(request, 'Sponsor deleted successfully.')
            return redirect('admin_sponsors')

        name = request.POST.get('name', '').strip()
        sponsor_type = request.POST.get('sponsor_type', '').strip()

        if not name or not sponsor_type:
            messages.error(request, 'Sponsor name and sponsor category are required.')
            return redirect('admin_sponsors')

        if action == 'edit_sponsor':
            sponsor = get_object_or_404(
                Sponsor,
                id=request.POST.get('sponsor_id')
            )
        else:
            sponsor = Sponsor()

        sponsor.name = name
        sponsor.sponsor_type = sponsor_type
        sponsor.tagline = request.POST.get('tagline', '').strip()
        sponsor.display_order = _parse_positive_int(
            request.POST.get('display_order')
        )
        sponsor.is_active = request.POST.get('is_active') == 'on'

        if request.FILES.get('logo'):
            sponsor.logo = request.FILES['logo']

        sponsor.save()

        messages.success(request, f'Sponsor "{name}" saved.')
        return redirect('admin_sponsors')

    context = {
        'sponsors': Sponsor.objects.all().order_by('display_order', 'name'),
    }

    return render(request, 'parallax/admin/sponsors.html', context)
@login_required(login_url='team_login')
def _admin_tracks_redirect(request):
    params = {}
    selected_track_id = request.POST.get('return_track') or request.GET.get('track')
    search_query = request.POST.get('return_q') or request.GET.get('q')
    if selected_track_id:
        params['track'] = selected_track_id
    if search_query:
        params['q'] = search_query
    url = reverse('admin_tracks')
    if params:
        return f'{url}?{urlencode(params)}'
    return url
def _limit_text(raw_value, limit=500):
    return (raw_value or '').strip()[:limit]
def _parse_positive_int(raw_value):
    try:
        return max(int(raw_value), 0)
    except (TypeError, ValueError):
        return 0
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
def build_participant_timeline(team):
    """Eight-step participant journey for the dashboard "Your Progress" strip.

    Stage labels and the current-stage logic mirror what the frontend
    previously hardcoded, so the UI can render straight from this data.
    """
    stages = [
        "Online Registration & Payment",
        "Domain & Problem Statement",
        "Offline Registration at Venue",
        "Hackathon Inauguration",
        "Round 1 (Student Review)",
        "Round 2 (Faculty Review)",
        "Final Review (Industry Review)",
        "Closing Ceremony & Prize Distribution",
    ]

    marks_count = Marks.objects.filter(team=team).count()

    # Registration & payment is done once the team exists -> Domain & PS is next.
    current_index = 1
    if team.track_id:
        current_index = max(current_index, 2)
    if team.status == "APPROVED":
        current_index = max(current_index, 4)
    current_index += marks_count
    current_index = min(current_index, len(stages))

    timeline = []
    for index, stage in enumerate(stages):
        if index < current_index:
            status = "done"
        elif index == current_index:
            status = "active"
        else:
            status = "upcoming"
        timeline.append(
            {
                "stage": stage,
                "status": status,
                "date": team.created_at.strftime("%d %b %Y") if index == 0 else None,
            }
        )
    return timeline
def access_denied(request):
    return render(request, "parallax/access_denied.html")
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.auth import get_user_model
from django.http import HttpResponse

def bootstrap_admin(request):
    User = get_user_model()

    user, created = User.objects.get_or_create(
        username="mkirt",
        defaults={
            "email": "kirthiksudharsan.m2025@vitstudent.ac.in"
        }
    )

    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.set_password("mkirt")
    user.save()

    return HttpResponse(
        f"""
        Username: {user.username}<br>
        Staff: {user.is_staff}<br>
        Superuser: {user.is_superuser}<br>
        Active: {user.is_active}<br>
        Password reset successfully.
        """
    )
from django.shortcuts import get_object_or_404, redirect
def delete_announcement(request, announcement_id):
    if request.method == "POST":
        announcement = get_object_or_404(Announcement, id=announcement_id)
        announcement.delete()
    return redirect("announcements")
