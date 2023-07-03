"""
TMA DASHBOARD API endpoint urls.
"""

from django.conf.urls import url

from lms.djangoapps.instructor.views import api, gradebook_api
from django.conf import settings
from tma_stat_dashboard.views import tma_dashboard_views,tma_overall_users_views,tma_per_question_views,tma_create_user_from_csv,tma_ensure_email_username,task_user_grade_list,tma_users_registered,tma_password_link,tma_unlock_account,tma_activate_account, tma_timer_cohortes,tma_timer_user,tma_timer_course,tma_timer_activation,tma_schedulded_gr, tma_add_time, is_task_running

urlpatterns = (
    url(r'^dashboard$', tma_dashboard_views, name="tma_dashboard"),
    url(r'^overall_users_stats$', tma_overall_users_views, name="tma_overall_users_stats"),
    url(r'^per_question$', tma_per_question_views, name="tma_specific_users_stats"),
    url(r'^tma_dashboard_upload_csv$', tma_create_user_from_csv, name="tma_create_user_from_csv"),
    url(r'^ensure_user_exist$', tma_ensure_email_username, name="tma_ensure_email_username"),
    url(r'^task_user_grade_list$', task_user_grade_list, name="task_user_grade_list"),

    #Actions participants inscrits
    url(r'^tma_users_registered$', tma_users_registered, name="tma_users_registered"),
    url(r'^tma_password_link$', tma_password_link, name="tma_password_link"),
    url(r'^tma_unlock_failure$', tma_unlock_account, name="tma_unlock_failure"),
    url(r'^tma_activate_account$', tma_activate_account, name="tma_activate_account"),

    #Cutoff
    url(r'^tma_timer_activation$', tma_timer_activation, name="tma_timer_activation"),
    url(r'^tma_timer_course$', tma_timer_course, name="tma_timer_course"),
    url(r'^tma_timer_user$', tma_timer_user, name="tma_timer_user"),
    url(r'^tma_timer_cohortes$', tma_timer_cohortes, name="tma_timer_cohortes"),

    #Grades reports
    url(r'^tma_schedulded_gr$', tma_schedulded_gr, name="tma_schedulded_gr"),

    #Add Time
    url(r'^tma_add_time$', tma_add_time, name="tma_add_time"),

    #Check Task
    url(r'^is_task_running$', is_task_running, name="is_task_running"),
 )
