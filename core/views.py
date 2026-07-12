from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Announcement, Marks, Participant, Review, Team, Track


def home(request):
    announcements = Announcement.objects.filter(is_pinned=True).order_by('-created_at')
    reviews = Review.objects.all().order_by('scheduled_at')
    context = {
        'announcements': announcements,
        'reviews': reviews,
    }
    return render(request, 'parallax/home.html', context)


def about(request):
    return render(request, 'parallax/about.html')


def tracks(request):
    published_tracks = Track.objects.filter(is_published=True)
    context = {'tracks': published_tracks}
    return render(request, 'parallax/tracks.html', context)


def faq(request):
    return render(request, 'parallax/faq.html')


def team_login(request):
    if request.user.is_authenticated:
        try:
            participant = request.user.participant
            if participant.team:
                return redirect('participant_dashboard')
            if not participant.is_profile_complete:
                return redirect('profile_complete')
            return redirect('register_team')
        except Participant.DoesNotExist:
            return redirect('profile_complete')

    return render(request, 'parallax/team_login.html')


def registration_index(request):
    return render(request, 'parallax/registration/index.html')


def registration_leader(request):
    return render(request, 'parallax/registration/leader.html')


def registration_member(request):
    return render(request, 'parallax/registration/member.html')


def registration_payment(request):
    return render(request, 'parallax/registration/payment.html')


def registration_proof(request):
    return render(request, 'parallax/registration/proof_upload.html')


def registration_review(request):
    return render(request, 'parallax/registration/review.html')


@login_required(login_url='team_login')
def profile_complete(request):
    try:
        participant = request.user.participant
    except Participant.DoesNotExist:
        participant = Participant.objects.create(
            user=request.user,
            full_name=request.user.get_full_name() or request.user.username,
            email=request.user.email,
            is_profile_complete=False,
        )

    if request.method == 'POST':
        phone = request.POST.get('phone_number', '')
        college = request.POST.get('college_name', '')
        reg_num = request.POST.get('reg_number', '')

        if phone and college and reg_num:
            participant.phone_number = phone
            participant.college_name = college
            participant.reg_number = reg_num
            participant.is_profile_complete = True
            participant.save()
            return redirect('register_team')

    context = {'participant': participant}
    return render(request, 'parallax/profile_complete.html', context)


@login_required(login_url='team_login')
def register_team(request):
    try:
        participant = request.user.participant
    except Participant.DoesNotExist:
        return redirect('profile_complete')

    if not participant.is_profile_complete:
        return redirect('profile_complete')

    if request.method == 'POST':
        team_name = request.POST.get('team_name', '')
        track_id = request.POST.get('track', '')
        invoice_num = request.POST.get('invoice_number', '')

        if team_name and track_id:
            track = get_object_or_404(Track, id=track_id)
            team = Team.objects.create(
                team_name=team_name,
                leader=participant,
                track=track,
                invoice_number=invoice_num,
                status='PENDING',
            )
            participant.team = team
            participant.is_team_leader = True
            participant.save()
            return redirect('participant_dashboard')

    published_tracks = Track.objects.filter(is_published=True)
    context = {
        'participant': participant,
        'tracks': published_tracks,
    }
    return render(request, 'parallax/register_team.html', context)


@login_required(login_url='team_login')
def participant_dashboard(request):
    try:
        participant = request.user.participant
    except Participant.DoesNotExist:
        return redirect('profile_complete')

    team = participant.team
    marks = Marks.objects.filter(team=team) if team else []
    announcements = Announcement.objects.all().order_by('-is_pinned', '-created_at')

    context = {
        'participant': participant,
        'team': team,
        'marks': marks,
        'announcements': announcements,
    }
    return render(request, 'parallax/dashboard.html', context)


@login_required(login_url='team_login')
def admin_panel(request):
    if not request.user.is_staff:
        return redirect('home')

    pending_teams = Team.objects.filter(status='PENDING').count()
    approved_teams = Team.objects.filter(status='APPROVED').count()

    context = {
        'pending_teams': pending_teams,
        'approved_teams': approved_teams,
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
        elif action == 'reject':
            team.status = 'REJECTED'

        team.save()
        return redirect('admin_teams')

    teams = Team.objects.all().order_by('-created_at')
    context = {'teams': teams}
    return render(request, 'parallax/admin/teams.html', context)


@login_required(login_url='team_login')
def admin_marks(request):
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        pass

    reviews = Review.objects.all()
    context = {'reviews': reviews}
    return render(request, 'parallax/admin/marks.html', context)


@login_required(login_url='team_login')
def admin_announcements(request):
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        pass

    announcements = Announcement.objects.all().order_by('-created_at')
    context = {'announcements': announcements}
    return render(request, 'parallax/admin/announcements.html', context)
