from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from core.models import Participant, Team, Track, Review, Marks, Announcement

# ===== PUBLIC PAGES =====

def home(request):
    # Homepage: pinned announcements, upcoming reviews, countdown
    announcements = Announcement.objects.filter(is_pinned=True).order_by('-created_at')
    reviews = Review.objects.all().order_by('scheduled_at')
    context = {
        'announcements': announcements,
        'reviews': reviews,
    }
    return render(request, 'parallax/home.html', context)


def about(request):
    # About Us: VIT → SENSE → Hackathon → Faculty (hardcoded for now)
    return render(request, 'parallax/about.html')


def tracks(request):
    # Tracks & Prizes: only published tracks visible
    tracks = Track.objects.filter(is_published=True)
    context = {'tracks': tracks}
    return render(request, 'parallax/tracks.html', context)


def faq(request):
    # FAQ: static content
    return render(request, 'parallax/faq.html')


# ===== AUTH & PROFILE =====

@login_required(login_url='team_login')
def profile_complete(request):
    # Mandatory profile completion after OAuth login
    # Redirects here if Participant.is_profile_complete == False
    try:
        participant = request.user.participant
    except Participant.DoesNotExist:
        # If OAuth user doesn't have a Participant record yet, create one
        participant = Participant.objects.create(
            user=request.user,
            full_name=request.user.get_full_name() or request.user.username,
            email=request.user.email,
            is_profile_complete=False
        )
    
    if request.method == 'POST':
        # TODO: Ramya will build this form. For now, placeholder.
        # Expected POST fields: phone_number, college_name, reg_number
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


def team_login(request):
    # Simple redirect: if user is authenticated and has a team, show dashboard
    if request.user.is_authenticated:
        try:
            participant = request.user.participant
            if participant.team:
                return redirect('participant_dashboard')
            elif not participant.is_profile_complete:
                return redirect('profile_complete')
            else:
                return redirect('register_team')
        except Participant.DoesNotExist:
            return redirect('profile_complete')
    
    # For unauthenticated users, Django's allauth handles Google OAuth redirect
    return render(request, 'parallax/team_login.html')


# ===== TEAM REGISTRATION =====

@login_required(login_url='team_login')
def register_team(request):
    # Team creation page — only accessible if profile_complete == True
    try:
        participant = request.user.participant
    except Participant.DoesNotExist:
        return redirect('profile_complete')
    
    if not participant.is_profile_complete:
        return redirect('profile_complete')
    
    if request.method == 'POST':
        # TODO: Ramya will build this form. For now, placeholder.
        # Expected POST fields: team_name, track, invoice_number
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
                status='PENDING'
            )
            participant.team = team
            participant.is_team_leader = True
            participant.save()
            
            # TODO: Send welcome email here (Kirthik handles email)
            return redirect('participant_dashboard')
    
    published_tracks = Track.objects.filter(is_published=True)
    context = {
        'participant': participant,
        'tracks': published_tracks,
    }
    return render(request, 'parallax/register_team.html', context)


# ===== PARTICIPANT DASHBOARD =====

@login_required(login_url='team_login')
def participant_dashboard(request):
    # Logged-in user's dashboard: team details, marks, announcements
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


# ===== ADMIN PANEL =====

@login_required(login_url='team_login')
def admin_panel(request):
    # Admin dashboard overview (restrict to staff/superuser later)
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
    # Team management: approve/reject
    if not request.user.is_staff:
        return redirect('home')
    
    if request.method == 'POST':
        # TODO: Mohan will handle team approval logic
        # Expected POST: team_id, action (approve/reject)
        team_id = request.POST.get('team_id')
        action = request.POST.get('action')
        
        team = get_object_or_404(Team, id=team_id)
        if action == 'approve':
            team.status = 'APPROVED'
            # TODO: Send approval email (Kirthik handles)
        elif action == 'reject':
            team.status = 'REJECTED'
        
        team.save()
        return redirect('admin_teams')
    
    teams = Team.objects.all().order_by('-created_at')
    context = {'teams': teams}
    return render(request, 'parallax/admin/teams.html', context)


@login_required(login_url='team_login')
def admin_marks(request):
    # Mark entry & publication
    if not request.user.is_staff:
        return redirect('home')
    
    if request.method == 'POST':
        # TODO: Mohan will handle marks entry & publish logic
        # Expected POST: team_id, review_id, score, remarks
        pass
    
    reviews = Review.objects.all()
    context = {'reviews': reviews}
    return render(request, 'parallax/admin/marks.html', context)


@login_required(login_url='team_login')
def admin_announcements(request):
    # Announcement CRUD
    if not request.user.is_staff:
        return redirect('home')
    
    if request.method == 'POST':
        # TODO: Mohan will handle announcement create/edit/delete
        pass
    
    announcements = Announcement.objects.all().order_by('-created_at')
    context = {'announcements': announcements}
    return render(request, 'parallax/admin/announcements.html', context)