from django.urls import path
from . import views
urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('tracks/', views.tracks, name='tracks'),
    path('accounts/login/', views.team_login, name='team_login'),
    path('profile/complete/', views.profile_complete, name='profile_complete'),
    path('register/', views.register_team, name='register_team'),
    path('dashboard/', views.participant_dashboard, name='participant_dashboard'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/teams/', views.admin_teams, name='admin_teams'),
    path('admin-panel/marks/', views.admin_marks, name='admin_marks'),
    path('admin-panel/announcements/', views.admin_announcements, name='admin_announcements'),
    path('admin-panel/tracks/', views.admin_tracks, name='admin_tracks'),
    path('registration/', views.registration_index, name='registration_index'),
    path('registration/team/', views.registration_leader, name='registration_leader'),
    path('registration/member/', views.registration_member, name='registration_member'),
    path('registration/payment/', views.registration_payment, name='registration_payment'),
    path('registration/event-hub/', views.registration_event_hub, name='registration_event_hub'),
    path('<str:page>/', views.information, name='information'),
]
