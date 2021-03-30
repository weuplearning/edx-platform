
"""
WUL APPS endpoint urls.
"""

from django.conf.urls import url, include
from django.conf import settings
from lms.djangoapps.wul_apps.dashboard.views import *
from lms.djangoapps.wul_apps.custom_fields_editor.views import *
from lms.djangoapps.wul_apps.statistics.views import *
from lms.djangoapps.wul_apps.ensure_form.views import *


# WUL DASHBOARD ENDPOINTS
urlpatterns = (
    url(r'^dashboard/get_course_enrollments/(?P<course_id>[^/]*)$', get_course_enrollments, name='get_course_enrollments'),
    url(r'^dashboard/get_course_enrollments_count/', get_course_enrollments_count, name='get_course_enrollments_count'),
    url(r'^dashboard/get_platform_courses/', get_platform_courses, name='get_platform_courses'),
    url(r'^dashboard/view_enrollments/', view_enrollments, name='view_enrollments'),
    url(r'^dashboard/', wul_dashboard_view, name='wul_dashboard_view'),
    url(r'^dashboard/get_student_profile/(?P<user_email>[^/]*)$', get_student_profile, name='get_student_profile'),
    url(r'^dashboard/get_password_link/', get_password_link, name='get_password_link'),
    url(r'^dashboard/unlock_account/', unlock_account, name='unlock_account'),
    url(r'^dashboard/get_register_fields/', get_register_fields, name='get_register_fields'),
    url(r'^dashboard/generate_student_time_sheet/(?P<course_id>[^/]*)/(?P<user_email>[^/]*)$', generate_student_time_sheet, name='generate_student_time_sheet'),
)

# CUSTOM FIELDS ENDPOINTS
urlpatterns += (
    url(r'^custom_field_view/', CustomFieldView.as_view(), name='custom_field_view'),
    url(r'^custom_field_editor/', CustomFieldEditor.as_view(), name='custom_field_editor'),
)

# ENSURE FORM
urlpatterns += (
    url(r'^wul_apps/ensure_profile_form/(?P<user_id>[^/]*)$', ensure_form, name='ensure_form'),
)

# TIME_TRACKING ENDPOINTS
urlpatterns += (
    url(r'^statistics/{}/add_time_tracking$'.format(settings.COURSE_ID_PATTERN), add_time_tracking ,name='add_time_tracking'),
    url(r'^statistics/{}/get_global_time_tracking$'.format(settings.COURSE_ID_PATTERN), get_user_global_time ,name='get_global_time'),
)