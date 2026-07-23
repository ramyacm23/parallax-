import random
from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Participant(models.Model):
    APPROVAL_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='participant')
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True)
    college_name = models.CharField(max_length=200, blank=True)
    reg_number = models.CharField(max_length=30, blank=True, null=True)
    is_profile_complete = models.BooleanField(default=False)
    team = models.ForeignKey('Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    is_team_leader = models.BooleanField(default=False)
    payment_proof = models.FileField(upload_to='payment-proofs/', blank=True, null=True)
    approval_status = models.CharField(max_length=10, choices=APPROVAL_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class Track(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    problem_statements = models.TextField(blank=True)
    problem_statements_set_one = models.TextField(blank=True)
    problem_statements_set_two = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    is_problem_live = models.BooleanField(
        default=False,
        help_text='Make this track problem statement visible to participants.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Prize(models.Model):
    track = models.OneToOneField(Track, on_delete=models.CASCADE, related_name='prize')
    first_place = models.CharField(max_length=200, default='Pending sponsorship confirmation')
    second_place = models.CharField(max_length=200, default='Pending sponsorship confirmation')
    third_place = models.CharField(max_length=200, default='Pending sponsorship confirmation')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.track.name} - Prizes"


class Team(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    team_name = models.CharField(max_length=100, unique=True)
    team_code = models.CharField(max_length=8, unique=True, blank=True, editable=False)
    leader = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name='led_team', null=True, blank=True
    )
    track = models.ForeignKey(Track, on_delete=models.SET_NULL, null=True, blank=True, related_name='teams')
    problem_statement = models.ForeignKey(
        'ProblemStatement', on_delete=models.SET_NULL, null=True, blank=True, related_name='booked_teams'
    )
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    payment_confirmed = models.BooleanField(default=False)
    payment_confirmed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.team_name

    @property
    def member_count(self):
        return self.members.count()

    @classmethod
    def generate_unique_team_code(cls):
        while True:
            generated_code = f"TEAM{random.randint(1000, 9999)}"
            if not cls.objects.filter(team_code=generated_code).exists():
                return generated_code

    def save(self, *args, **kwargs):
        if not self.team_code:
            self.team_code = self.generate_unique_team_code()

        if self.payment_confirmed and not self.payment_confirmed_at:
            self.payment_confirmed_at = timezone.now()
        elif not self.payment_confirmed:
            self.payment_confirmed_at = None

        super().save(*args, **kwargs)


class EventConfiguration(models.Model):
    event_start_date = models.DateField(default=date(2026, 8, 18))
    set_one_released = models.BooleanField(default=False)
    set_two_released = models.BooleanField(default=False)
    set_one_released_at = models.DateTimeField(null=True, blank=True)
    set_two_released_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Event Configuration'
        verbose_name_plural = 'Event Configuration'

    def __str__(self):
        return f"Parallax configuration for {self.event_start_date.isoformat()}"

    @classmethod
    def get_solo(cls):
        configuration, _ = cls.objects.get_or_create(pk=1)
        return configuration

    @property
    def set_one_release_date(self):
        return self.event_start_date - timedelta(days=4)

    @property
    def set_two_release_date(self):
        return self.event_start_date - timedelta(days=2)

    def can_release_set_one(self, today=None):
        comparison_date = today or timezone.localdate()
        return comparison_date >= self.set_one_release_date

    def can_release_set_two(self, today=None):
        comparison_date = today or timezone.localdate()
        return comparison_date >= self.set_two_release_date

    def update_problem_set_release(self, set_number, release, current_time=None):
        timestamp = current_time or timezone.now()
        comparison_date = timestamp.date()

        if set_number == 1:
            if release and not self.can_release_set_one(today=comparison_date):
                raise ValueError('Problem Statement Set 1 can only be released four days before the event.')

            self.set_one_released = release
            self.set_one_released_at = timestamp if release else None
            return

        if set_number == 2:
            if release and not self.set_one_released:
                raise ValueError('Problem Statement Set 1 must be released before Set 2.')

            if release and not self.can_release_set_two(today=comparison_date):
                raise ValueError('Problem Statement Set 2 can only be released two days before the event.')

            self.set_two_released = release
            self.set_two_released_at = timestamp if release else None
            return

        raise ValueError('Unsupported problem statement set.')


class Review(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    scheduled_at = models.DateTimeField()
    max_marks = models.PositiveIntegerField(default=100)

    def __str__(self):
        return self.name


class Marks(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='marks')
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='marks')
    score = models.DecimalField(max_digits=6, decimal_places=2)
    remarks = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_marks'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('team', 'review')

    def __str__(self):
        return f"{self.team.team_name} - {self.review.name}: {self.score}"


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_pinned = models.BooleanField(default=False)
    send_email = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='announcements'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title


class LeaderRegistration(models.Model):
    """Standalone team-leader registration form and payment funnel.

    Powers the OC dashboard counters (registered / paid / pay-later). The real
    confirmation emails are owned by Akash; the send_* helpers are placeholders.
    """

    PAYMENT_PENDING = 'PENDING'
    PAYMENT_PAY_LATER = 'PAY_LATER'
    PAYMENT_PAID = 'PAID'
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, 'Not started'),
        (PAYMENT_PAY_LATER, 'Pay later'),
        (PAYMENT_PAID, 'Paid'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='leader_registration',
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    college = models.CharField(max_length=200)
    department = models.CharField(max_length=150)
    reg_number = models.CharField('Registration number', max_length=50)
    graduation_year = models.PositiveIntegerField()
    team_name = models.CharField(max_length=150)
    team_members = models.TextField(
        help_text='Names of the team members, one per line or comma-separated.',
    )
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_PENDING)
    registration_email_sent = models.BooleanField(default=False)
    payment_email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def has_paid(self):
        return self.payment_status == self.PAYMENT_PAID


class ProblemStatement(models.Model):
    """A bookable problem statement with a fixed first-come-first-served slot pool.

    Slot capacity is entered manually by the OC in the admin dashboard.
    """

    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='problem_statement_slots')
    code = models.CharField(max_length=20, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    slot_capacity = models.PositiveIntegerField(
        default=0, help_text='Total teams allowed to book this problem statement.'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['track__name', 'code', 'title']

    def __str__(self):
        return f"{self.title} ({self.track.name})"

    @property
    def slots_filled(self):
        return self.booked_teams.count()

    @property
    def slots_available(self):
        return max(self.slot_capacity - self.slots_filled, 0)

    @property
    def is_full(self):
        return self.slot_capacity > 0 and self.slots_filled >= self.slot_capacity
