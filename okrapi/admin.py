from django.contrib import admin
from .models import Department, BusinessUnit, User, OKR, Task, OkrUserMapping, Log, TaskChallenges, BusinessUnitOKRMapping

# Register your models here.
admin.site.register(Department)
admin.site.register(BusinessUnit)
admin.site.register(User)
admin.site.register(OKR)
admin.site.register(Task)
admin.site.register(OkrUserMapping)
admin.site.register(Log)
admin.site.register(BusinessUnitOKRMapping)
admin.site.register(TaskChallenges)
