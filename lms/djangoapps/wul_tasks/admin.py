from django.contrib import admin
from lms.djangoapps.wul_tasks.models import WulTask

class WulTaskAdmin(admin.ModelAdmin):
    list_display = ('task_type', 'requester', 'course_id','created','task_state')
admin.site.register(WulTask, WulTaskAdmin)
