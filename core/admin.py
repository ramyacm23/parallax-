from django.contrib import admin

from .models import Announcement, EventConfiguration, Marks, Participant, Prize, Review, Team, Track


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'college_name', 'team', 'is_team_leader', 'is_profile_complete')
    search_fields = ('full_name', 'email', 'college_name', 'reg_number')
    list_filter = ('is_team_leader', 'is_profile_complete', 'college_name')


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_published', 'is_problem_live', 'updated_at')
    search_fields = ('name',)
    list_filter = ('is_published', 'is_problem_live')


@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ('track', 'first_place', 'second_place', 'third_place', 'updated_at')


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('team_name', 'team_code', 'track', 'payment_confirmed', 'status', 'created_at')
    search_fields = ('team_name', 'team_code', 'invoice_number')
    list_filter = ('payment_confirmed', 'status', 'track')


@admin.register(EventConfiguration)
class EventConfigurationAdmin(admin.ModelAdmin):
    list_display = ('event_start_date', 'set_one_released', 'set_two_released', 'updated_at')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'scheduled_at', 'max_marks')


@admin.register(Marks)
class MarksAdmin(admin.ModelAdmin):
    list_display = ('team', 'review', 'score', 'graded_by', 'updated_at')
    list_filter = ('review',)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_pinned', 'send_email', 'created_by', 'created_at')
    list_filter = ('is_pinned', 'send_email')
    search_fields = ('title', 'body')
