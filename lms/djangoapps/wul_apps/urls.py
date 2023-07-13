
"""
WUL APPS endpoints urls.

/edx/app/edxapp/edx-platform/lms/djangoapps/wul_apps
"""

from django.conf.urls import url, include
from django.conf import settings
from lms.djangoapps.wul_apps.dashboard.views import *
from lms.djangoapps.wul_apps.custom_fields_editor.views import CustomFieldView, CustomFieldEditor
from lms.djangoapps.wul_apps.statistics.views import add_time_tracking, get_user_global_time
from lms.djangoapps.wul_apps.ensure_form.views import ensure_form
from lms.djangoapps.wul_apps.stat_dashboard.views import tma_create_user_from_csv, calculate_grades_xls
from lms.djangoapps.wul_apps.user_dashboard.views import render_views, render_course_outline, course_registration

from lms.djangoapps.wul_apps.certificates.views import generate_pdf, ensure

# BVT specific file
from lms.djangoapps.wul_apps.converter_xlsx_to_targz.bvt.views import convert_to_tarfile_bvt 
from lms.djangoapps.wul_apps.custom_grade_report.bvt.views import run_script_from_back 

# Read Google Drive API
from lms.djangoapps.wul_apps.google_drive.views import read_google_drive_file

import logging
log = logging.getLogger()


# WUL DASHBOARD ENDPOINTS
urlpatterns = (
    url(r'^dashboard/get_course_enrollments/(?P<course_id>[^/]*)$', get_course_enrollments, name='get_course_enrollments'),
    url(r'^dashboard/get_course_enrollments_count/', get_course_enrollments_count, name='get_course_enrollments_count'),
    url(r'^dashboard/get_platform_courses/', get_platform_courses, name='get_platform_courses'),
    url(r'^dashboard/view_enrollments/', view_enrollments, name='view_enrollments'),
    url(r'^dashboard/home/', wul_dashboard_view, name='wul_dashboard_view'),
    url(r'^dashboard/get_student_profile/(?P<user_email>[\w.%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4})$', get_student_profile, name='get_student_profile'),
    url(r'^dashboard/get_password_link/', get_password_link, name='get_password_link'),
    url(r'^dashboard/unlock_account/', unlock_account, name='unlock_account'),
    url(r'^dashboard/get_register_fields/', get_register_fields, name='get_register_fields'),
    url(r'^dashboard/generate_student_time_sheet/(?P<course_id>[^/]*)/(?P<user_email>[^/]*)$', generate_student_time_sheet, name='generate_student_time_sheet'),
    url(r'^dashboard/(?P<course_id>[^/]*)/wul_dashboard_upload_csv', tma_create_user_from_csv, name='tma_create_user_from_csv'),
    # url(r'^courses/{}/stat_dashboard/xls_grade_reports/$'.format(settings.COURSE_ID_PATTERN), calculate_grades_xls,name='calculate_grades_xls'),
    
)

# CUSTOM FIELDS ENDPOINTS
urlpatterns += (
    url(r'^custom_field_view/', CustomFieldView.as_view(), name='custom_field_view'),
    url(r'^custom_field_editor/', CustomFieldEditor.as_view(), name='custom_field_editor'),
)

# ENSURE FORM
urlpatterns += (
    url(r'^ensure_profile_form/(?P<user_id>[^/]*)$', ensure_form, name='ensure_form'),
)

# TIME_TRACKING ENDPOINTS
urlpatterns += (
    url(r'^statistics/{}/add_time_tracking$'.format(settings.COURSE_ID_PATTERN), add_time_tracking ,name='add_time_tracking'),
    url(r'^statistics/{}/get_global_time_tracking$'.format(settings.COURSE_ID_PATTERN), get_user_global_time ,name='get_global_time'),
)

#GRADE REPORT
urlpatterns += (
    url(r'^dashboard/(?P<course_id>[^/]*)/stat_dashboard/xls_grade_reports/$', calculate_grades_xls,name='calculate_grades_xls'),
)

#Interface Statistiques
urlpatterns +=(
    url(r'^{}/wul_stats/time_tracker$'.format(settings.COURSE_ID_PATTERN), add_time_tracking ,name='add_time_tracking'),
    # url(r'^{}/wul_stats/get_global_time$'.format(settings.COURSE_ID_PATTERN), 'tma_apps.tma_statistics.views.get_user_global_time' ,name='get_global_time'),
    # url(r'^{}/wul_stats/course_state$'.format(settings.COURSE_ID_PATTERN), 'tma_apps.tma_statistics.views.update_user_course_state' ,name='update_user_course_state'),
)

#Certificates
urlpatterns += (
    url(r'^{}/certificate/ensure$'.format(settings.COURSE_ID_PATTERN), ensure, name="ensure"),
    url(r'^{}/certificate/generate_pdf$'.format(settings.COURSE_ID_PATTERN), generate_pdf, name="generate_pdf"),
)

# BVT specific
# Edx Converter + custom_grade_report
urlpatterns += (
    url(r'^dashboard/BVT/converter_xlsx_to_targz', convert_to_tarfile_bvt,name='convert_to_tarfile_bvt'),
    url(r'^dashboard/bvt/converter_xlsx_to_targz', convert_to_tarfile_bvt,name='convert_to_tarfile_bvt'),
    url(r'^dashboard/BVT/run_script_from_back/', run_script_from_back, name='run_script_from_back'),
    url(r'^dashboard/bvt/run_script_from_back/', run_script_from_back, name='run_script_from_back')

)

# user_dashboard v2.0
urlpatterns += (
    url(r'^event$', render_views, name="render_views"),
    url(r'^coaching$', render_views, name="render_views"),
    url(r'^{}/course_outline$'.format(settings.COURSE_ID_PATTERN), render_course_outline, name="render_course_outline"),
    url(r'^{}/course_registration$'.format(settings.COURSE_ID_PATTERN), course_registration, name="course_registration"),
)

# Google Drive API
urlpatterns += (
    url(r'^read_google_drive_file$', read_google_drive_file, name="read_google_drive_file"),
)
