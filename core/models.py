import random
import string
from django.conf import settings
from django.db import models
class Participant(models.Model):
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
    approval_status = models.CharField(max_length=10, choices=[('PENDING','Pending'),('APPROVED','Approved')], default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.full_name} ({self.email})"
class Track(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    problem_statements = models.TextField() 
    is_published = models.BooleanField(default=False)  
    is_problem_live = models.BooleanField(default=False, help_text='Make this track’s problem statements visible to participants.')
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
        return f"{self.track.name} — Prizes"
class Team(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
    ]
    team_name = models.CharField(max_length=100, unique=True)
    team_code = models.CharField(max_length=10, unique=True, blank=True)
    leader = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name='led_team', null=True, blank=True
    )
    track = models.ForeignKey(Track, on_delete=models.SET_NULL, null=True, blank=True, related_name='teams')
    invoice_number = models.CharField(max_length=100, blank=True, null=True)  # From Event Hub or student submission
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.team_name
    def save(self, *args, **kwargs):
        if not self.team_code:
            while True:
                code = 'PX-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                if not Team.objects.filter(team_code=code).exists():
                    self.team_code = code
                    break
        super().save(*args, **kwargs)
    @property
    def member_count(self):
        return self.members.count()
class Review(models.Model):
    # Evaluation round (e.g., Review 1, Review 2, Finals).
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    scheduled_at = models.DateTimeField()
    max_marks = models.PositiveIntegerField(default=100)
    def __str__(self):
        return self.name
class Marks(models.Model):
    # Grades awarded to a team for a specific review.
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
