from django.contrib import admin
from core.models import Participant, Team, Track, Prize, Review, Marks, Announcement


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    # Admin interface for Participant records
    # Mohan uses this to audit incomplete profiles and send reminders
    
    list_display = ['full_name', 'email', 'college_name', 'is_profile_complete', 'team', 'created_at']
    list_filter = ['is_profile_complete', 'created_at']
    search_fields = ['full_name', 'email', 'reg_number']
    readonly_fields = ['user', 'created_at']
    
    fieldsets = (
        ('User Link', {
            'fields': ('user', 'created_at')
        }),
        ('Profile Info', {
            'fields': ('full_name', 'email', 'phone_number', 'college_name', 'reg_number')
        }),
        ('Team & Status', {
            'fields': ('team', 'is_team_leader', 'is_profile_complete')
        }),
    )


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    # Admin interface for Team records
    # Mohan approves/rejects teams, views invoice numbers, manages team details
    
    list_display = ['team_name', 'leader', 'track', 'status', 'invoice_number', 'created_at']
    list_filter = ['status', 'track', 'created_at']
    search_fields = ['team_name', 'leader__full_name', 'invoice_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Team Details', {
            'fields': ('team_name', 'leader', 'track')
        }),
        ('Payment & Verification', {
            'fields': ('invoice_number', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_teams', 'reject_teams']
    
    def approve_teams(self, request, queryset):
        # Bulk action to approve multiple teams
        # TODO: Kirthik adds email trigger here — sends "approved" email to leader
        updated = queryset.update(status='APPROVED')
        self.message_user(request, f'{updated} teams approved.')
    approve_teams.short_description = 'Approve selected teams'
    
    def reject_teams(self, request, queryset):
        # Bulk action to reject teams
        updated = queryset.update(status='REJECTED')
        self.message_user(request, f'{updated} teams rejected.')
    reject_teams.short_description = 'Reject selected teams'


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    # Admin interface for Tracks
    # Mohan publishes/unpublishes tracks on hackathon day
    
    list_display = ['name', 'is_published', 'created_at']
    list_filter = ['is_published', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Track Info', {
            'fields': ('name', 'description', 'problem_statements')
        }),
        ('Publication Status', {
            'fields': ('is_published',),
            'description': 'Toggle to show/hide on frontend'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    # Admin interface for Prize pool per track
    # Mohan updates prize details once sponsorships confirm
    
    list_display = ['track', 'first_place', 'second_place', 'third_place', 'updated_at']
    search_fields = ['track__name']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('Track Link', {
            'fields': ('track',)
        }),
        ('Prize Amounts', {
            'fields': ('first_place', 'second_place', 'third_place')
        }),
        ('Timestamps', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    # Admin interface for Review rounds
    # Mohan creates Review records for each evaluation checkpoint
    
    list_display = ['name', 'scheduled_at', 'max_marks']
    list_filter = ['scheduled_at']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Review Details', {
            'fields': ('name', 'description', 'scheduled_at', 'max_marks')
        }),
    )


@admin.register(Marks)
class MarksAdmin(admin.ModelAdmin):
    # Admin interface for Marks entry
    # Mohan enters scores per team per review, then publishes
    
    list_display = ['team', 'review', 'score', 'graded_by', 'updated_at']
    list_filter = ['review', 'updated_at']
    search_fields = ['team__team_name', 'review__name']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('Grading', {
            'fields': ('team', 'review', 'score', 'remarks')
        }),
        ('Admin Info', {
            'fields': ('graded_by', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    # Admin interface for Announcements
    # Mohan creates pinned announcements and optionally emails them
    
    list_display = ['title', 'is_pinned', 'send_email', 'created_by', 'created_at']
    list_filter = ['is_pinned', 'send_email', 'created_at']
    search_fields = ['title', 'body']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Announcement Content', {
            'fields': ('title', 'body')
        }),
        ('Distribution', {
            'fields': ('is_pinned', 'send_email'),
            'description': 'Pinned shows first on homepage. Send email triggers participant notification.'
        }),
        ('Admin Info', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        # Auto-set created_by to current user if not already set
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)