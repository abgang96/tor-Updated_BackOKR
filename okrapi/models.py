from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class BusinessUnit(models.Model):
    business_unit_id = models.AutoField(primary_key=True)
    business_unit_name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.business_unit_name

class BusinessUnitOKRMapping(models.Model):
    okr = models.ForeignKey('OKR', related_name='business_unit_mappings', on_delete=models.CASCADE)
    business_unit = models.ForeignKey(BusinessUnit, related_name='okr_mappings', on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('okr', 'business_unit')
    
    def __str__(self):
        return f"{self.okr} - {self.business_unit}"

class User(models.Model):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True, default='default_user')
    employee_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=50)
    level = models.IntegerField()
    manager = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='subordinates')
    hierarchy_path = models.CharField(max_length=255)
    org_unit = models.CharField(max_length=100)
    status = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            # Generate username from email if not provided
            if not self.username:
                self.username = self.email.split('@')[0]
            
            if self.manager:
                # Get manager's hierarchy path and append new user's ID
                manager = User.objects.get(user_id=self.manager.user_id)
                # Save first to get the user_id
                super().save(*args, **kwargs)
                self.hierarchy_path = f"{manager.hierarchy_path}/{self.user_id}"
                # Save again with updated hierarchy_path
                super().save(update_fields=['hierarchy_path'])
            else:
                # If no manager, save first to get user_id
                super().save(*args, **kwargs)
                self.hierarchy_path = f"/{self.user_id}"
                # Save again with updated hierarchy_path
                super().save(update_fields=['hierarchy_path'])
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.employee_id})"

class OKR(models.Model):
    okr_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    assumptions = models.TextField(blank=True, null=True)
    parent_okr = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='child_okrs')
    assigned_users = models.ManyToManyField(User, through='OkrUserMapping', related_name='assigned_okrs_many')
    business_units = models.ManyToManyField(
        BusinessUnit, 
        through='BusinessUnitOKRMapping',
        related_name='okrs'
    )
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='department_okrs')
    start_date = models.DateField()
    due_date = models.DateField()
    status = models.BooleanField(default=True)  # True for Active, False for Inactive
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2)
    isMeasurable = models.BooleanField(default=False)  # Added isMeasurable field

    def __str__(self):
        return self.name

class Task(models.Model):
    # Task status choices as integer enum
    STATUS_COMPLETED = 0
    STATUS_IN_PROGRESS = 1
    STATUS_HOLD = 2
    STATUS_DELAYED = 3
    STATUS_YET_TO_START = 4
    
    STATUS_CHOICES = [
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_HOLD, 'Hold'),
        (STATUS_DELAYED, 'Delayed'),
        (STATUS_YET_TO_START, 'Yet to Start'),
    ]
    
    task_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    due_date = models.DateField()
    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_YET_TO_START)
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_tasks')
    linked_to_okr = models.ForeignKey(OKR, on_delete=models.CASCADE, related_name='tasks')
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.title} ({self.task_id})"

# New model for OKR to User mapping
class OkrUserMapping(models.Model):
    okr = models.ForeignKey(OKR, on_delete=models.CASCADE, related_name='user_mappings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='okr_mappings')
    is_primary = models.BooleanField(default=False)  # Indicates if this is the primary assignee
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('okr', 'user')  # Prevent duplicate mappings
        verbose_name = "OKR User Assignment"
        verbose_name_plural = "OKR User Assignments"

    def __str__(self):
        return f"{self.okr.name} - {self.user.name}"


class Log(models.Model):
    log_id = models.AutoField(primary_key=True)
    date = models.DateField()
    okr = models.ForeignKey(OKR, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logs')
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=50)
    confidence_level = models.IntegerField()
    comment = models.TextField()
    is_auto_generated = models.BooleanField(default=False)
    source = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Log {self.log_id} for OKR {self.okr.okr_id}"


class TaskChallenges(models.Model):
    # Status enum choices
    STATUS_YET_TO_START = 0
    STATUS_ACTIVE = 1
    STATUS_DISCARDED = 2
    STATUS_RESOLVED = 3
    
    STATUS_CHOICES = [
        (STATUS_YET_TO_START, 'Yet to Start'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_DISCARDED, 'Discarded'),
        (STATUS_RESOLVED, 'Resolved'),
    ]
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='challenges')
    challenge_name = models.CharField(max_length=200, default='', blank=True)  # New field for challenge name
    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_YET_TO_START)
    due_date = models.DateField()
    remarks = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        challenge_name = self.challenge_name if self.challenge_name else f"Challenge for Task {self.task.title}"
        return f"{challenge_name} - {self.get_status_display()}"

    class Meta:
        verbose_name = "Task Challenge"
        verbose_name_plural = "Task Challenges"