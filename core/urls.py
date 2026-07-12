from django.urls import path

from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('tracks/', views.tracks, name='tracks'),
    path('faq/', views.faq, name='faq'),
    path('accounts/login/', views.team_login, name='team_login'),
    path('profile/complete/', views.profile_complete, name='profile_complete'),
    path('register/', views.register_team, name='register_team'),
    path('dashboard/', views.participant_dashboard, name='participant_dashboard'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/teams/', views.admin_teams, name='admin_teams'),
    path('admin-panel/marks/', views.admin_marks, name='admin_marks'),
    path('admin-panel/announcements/', views.admin_announcements, name='admin_announcements'),
    path('registration/', views.registration_index, name='registration_index'),
    path('registration/leader/', views.registration_leader, name='registration_leader'),
    path('registration/member/', views.registration_member, name='registration_member'),
    path('registration/payment/', views.registration_payment, name='registration_payment'),
    path('registration/proof-upload/', views.registration_proof, name='registration_proof'),
    path('registration/review/', views.registration_review, name='registration_review'),
]
