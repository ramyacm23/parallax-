from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from core.models import Marks, Participant, Review, Team, Track

TRACKS = [
    ('Aviation & Space Tech', 'Build intelligent systems for aerospace, autonomous flight and satellite technologies.', 'fa-rocket'),
    ('Internet Of Things', 'Create real-time hardware-software systems for devices, automation and edge computing.', 'fa-microchip'),
    ('Healthcare & Assistive Tech', 'Design technologies that improve access, rehabilitation and quality of life.', 'fa-heart-pulse'),
    ('Artificial Intelligence And Machine Learning', 'Engineer resilient cities through smart energy, mobility and monitoring.', 'fa-leaf'),
    ('Communication & Networks', 'Develop secure networks and intelligent connected infrastructure.', 'fa-satellite-dish'),
]

def public_tracks():
    saved = list(Track.objects.filter(is_published=True))
    return saved or [{'name': n, 'description': d, 'icon': i, 'is_problem_live': False} for n, d, i in TRACKS]

def home(request):
    reviews = Review.objects.all().order_by('scheduled_at')
    context = {'reviews': reviews, 'tracks': public_tracks()}
    return render(request, 'parallax/home.html', context)

def about(request):
    return render(request, 'parallax/about.html', {'values': [
        {'letter':'01','title':'Curiosity over certainty','description':'Ask the questions that move a problem forward.'},
        {'letter':'02','title':'Build with intent','description':'Make useful ideas tangible, testable and humane.'},
        {'letter':'03','title':'Different views, stronger work','description':'The best solutions are rarely built from one perspective.'},
        {'letter':'04','title':'Leave a trace','description':'Create work that matters after the final demo ends.'},
    ], 'team': []})

def tracks(request):
    published_tracks = public_tracks()
    context = {'tracks': published_tracks}
    return render(request, 'parallax/tracks.html', context)

def information(request, page):
    pages = {
        'schedule': ('Review Schedule', 'Every checkpoint is designed to turn momentum into measurable progress.'),
        'prizes': ('Prizes & Recognition', 'The prize pool and sponsor awards will be announced here.'),
        'guidelines': ('Guidelines', 'Build boldly. Work fairly. Leave every space better than you found it.'),
        'theme': ('Theme', 'Same problem. Different view. Better answer.'),
        'contact': ('Contact the OC', 'Have a question? The organising committee is here to help.'),
    }
    return render(request, 'parallax/information.html', {'page': page, 'heading': pages[page][0], 'tagline': pages[page][1], 'reviews': Review.objects.all().order_by('scheduled_at'), 'tracks': public_tracks()})

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
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '')
        email = request.POST.get('email', '')
        phone_number = request.POST.get('phone_number', '')
        college = request.POST.get('college', '')
        department = request.POST.get('department', '')
        year = request.POST.get('year', '')
        team_name = request.POST.get('team_name', '')
        team_size = request.POST.get('team_size', '')
        preferred_track = request.POST.get('preferred_track', '')
        team_description = request.POST.get('team_description', '')
        domains = request.POST.getlist('domains')
        terms_agreed = request.POST.get('terms_agreed', '')
        
        if not (full_name and email and phone_number and college and department and year and team_name and team_size and preferred_track and terms_agreed):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'parallax/registration/leader.html')
        
        request.session['registration_data'] = {
            'full_name': full_name,
            'email': email,
            'phone_number': phone_number,
            'college': college,
            'department': department,
            'year': year,
            'team_name': team_name,
            'team_size': team_size,
            'preferred_track': preferred_track,
            'team_description': team_description,
            'domains': domains,
        }
        request.session.modified = True
        
        return redirect('registration_payment')
    
    return render(request, 'parallax/registration/leader.html')

def registration_payment(request):
    registration_data = request.session.get('registration_data')
    if not registration_data:
        return redirect('registration_leader')
    
    context = {'registration_data': registration_data}
    return render(request, 'parallax/registration/payment.html', context)

def registration_member(request):
    return render(request, 'parallax/registration/member.html')

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
            track = Track.objects.get(id=track_id)
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
            messages.success(request, f'Team created. Your team code is {team.team_code}.')
            return redirect('participant_dashboard')
    published_tracks = Track.objects.filter(is_published=True)
    context = {'participant': participant, 'tracks': published_tracks}
    return render(request, 'parallax/register_team.html', context)

@login_required(login_url='team_login')
def participant_dashboard(request):
    try:
        participant = request.user.participant
    except Participant.DoesNotExist:
        return redirect('profile_complete')
    team = participant.team
    marks = Marks.objects.filter(team=team) if team else []
    context = {'participant': participant, 'team': team, 'marks': marks}
    return render(request, 'parallax/dashboard.html', context)

@login_required(login_url='team_login')
def admin_panel(request):
    if not request.user.is_staff:
        return redirect('home')
    pending_teams = Team.objects.filter(status='PENDING').count()
    approved_teams = Team.objects.filter(status='APPROVED').count()
    context = {'pending_teams': pending_teams, 'approved_teams': approved_teams}
    return render(request, 'parallax/admin/dashboard.html', context)

@login_required(login_url='team_login')
def admin_teams(request):
    if not request.user.is_staff:
        return redirect('home')
    if request.method == 'POST':
        team_id = request.POST.get('team_id')
        action = request.POST.get('action')
        team = Team.objects.get(id=team_id)
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
    reviews = Review.objects.all()
    context = {'reviews': reviews}
    return render(request, 'parallax/admin/marks.html', context)

@login_required(login_url='team_login')
def admin_tracks(request):
    if not request.user.is_staff:
        return redirect('home')
    if request.method == 'POST':
        track = Track.objects.get(id=request.POST.get('track_id'))
        field = request.POST.get('field')
        if field in ('is_published', 'is_problem_live'):
            setattr(track, field, not getattr(track, field))
            track.save(update_fields=[field, 'updated_at'])
    return render(request, 'parallax/admin/tracks.html', {'tracks': Track.objects.all().order_by('name')})