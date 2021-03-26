from django.contrib import admin
from lms.djangoapps.wul_apps.models import WulCourseOverview, WulCourseEnrollment

class WulCourseOverviewAdmin(admin.ModelAdmin):
    list_display = ('course_id_edx', 'course_timer_active','course_timer_type','course_timer_days_value','course_timer_date_value')

admin.site.register(WulCourseOverview, WulCourseOverviewAdmin)

class WulCourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('course_id','user_edx', 'global_time_tracking','detailed_time_tracking','has_started_course','enrollment_active','has_finished_course','finished_course_date')

    def user_edx(self, obj):
        return obj.course_enrollment_edx.user.email

    user_edx.admin_order_field = 'course_enrollment_edx'
    user_edx.short_description = 'User'

    def course_id(self, obj):
        return obj.course_enrollment_edx.course_id

    course_id.admin_order_field = 'course_enrollment_edx'
    course_id.short_description = 'Course ID'

    def enrollment_active(self, obj):
        return obj.course_enrollment_edx.is_active

    enrollment_active.admin_order_field = 'course_enrollment_edx'
    enrollment_active.short_description = 'Enrollment Active'

    readonly_fields =('course_enrollment_edx','enrollment_active')
    search_fields = ['course_enrollment_edx__user__email']

admin.site.register(WulCourseEnrollment, WulCourseEnrollmentAdmin)
