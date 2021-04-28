# -*- coding: utf-8 -*-
import sys
import importlib
importlib.reload(sys)
# from celery.states import READY_STATES
# from tasks.models import tmaTask

from lms.djangoapps.wul_tasks.tasks import (
    calculate_grades_xls,
    generate_users,
    # sbo_user,
    # add_extra_time
)

from lms.djangoapps.wul_tasks.api_helper import (
    submit_task
)
from lms.djangoapps.wul_tasks.wul_dashboard import wul_dashboard
import json
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

import logging
log = logging.getLogger(__name__)

#generation grades reports
def submit_calculate_grades_xls(request, course_key):

    """
    AlreadyRunningError is raised if the course's grades are already being updated.
    """
    task_type = 'grade_course'
    task_class = calculate_grades_xls
    site_name = configuration_helpers.get_value('SITE_NAME')

    _microsite = configuration_helpers.get_value('domain_prefix')
    register_form = configuration_helpers.get_value('FORM_EXTRA')
    if register_form is None:
        register_form = []
    certificate_form = configuration_helpers.get_value('CERTIFICATE_FORM_EXTRA')
    if certificate_form is None:
        certificate_form = []
    if _microsite is None:
        _microsite = '_';
    _form = json.loads(request.body).get('fields')
    scope = json.loads(request.body).get('scope')
    users_admin = []
    certificate_advanced_config = {}
    include_days_left_in_report = False
    
    try :
        users_admin = configuration_helpers.get_value("TMA_DASHBOARD_ACCESS").get("all")
    except:
        pass

    try :
        include_days_left_in_report = configuration_helpers.get_value("TMA_DASHBOARD_REPORTS_INCLUDE_DAYS_LEFT_FOR_COURSE_ACCESS")
    except:
        pass

    try :
        certificate_advanced_config = configuration_helpers.get_value("CERTIFICATE_ADVANCED_CONFIGURATION")
    except:
        pass

    receivers = json.loads(request.body).get('receivers')
    task_input = {
        "site_name": site_name,
        "microsite":_microsite,
        "form":_form,
        "register_form":register_form,
        "certificate_form":certificate_form,
        "send_to":receivers,
        "scope":scope,
        "users_admin": users_admin,
        "include_days_left_in_report": include_days_left_in_report,
        "certificate_advanced_config": certificate_advanced_config
    }
    task_key = ""

    return submit_task(request, task_type, task_class, course_key, task_input, task_key, _microsite)

#generations utilisateurs
def submit_generate_users(request, course_key):
    """
    AlreadyRunningError is raised if the course's grades are already being updated.
    """
    task_type = 'user_generation'
    task_class = generate_users
    #recuperation des donnees de la plateforme
    microsite = configuration_helpers.get_value('domain_prefix')
    register_form = configuration_helpers.get_value('FORM_EXTRA')
    site_name = configuration_helpers.get_value('SITE_NAME')
    log.info("********************************SUBMITGENERATEUSER***********************")
    log.info(microsite)
    log.info(register_form)
    log.info(site_name)
    
    if register_form is None:
        register_form = []
    #recuperations des donnees du call issues du csv genere
    _fields = wul_dashboard(course_key=course_key).required_register_fields()
    #parse from json request csv rows
    rows = json.loads(request.POST['rows'])
    #get current header
    #check if each rows as valid keys
    #list of valid rows
    valid_rows = []
    #list of invalid rows
    invalid_rows = []
    #check each rows
    for row in rows:
        _ensure = True
        for field in _fields:

            name = field.get('name')
            required = field.get('required')

            if required and (not name in row.keys()):
                _ensure = False

        if _ensure:
            valid_rows.append(row)
        else:
            invalid_rows.append(row)

    task_input = {
        "requester_id":request.user.id,
        "valid_rows":valid_rows,
        "invalid_rows":invalid_rows,
        "microsite":microsite,
        "site_name":site_name,
        "register_form":register_form,
    }

    task_key = ""

    # return submit_task(request, task_type, task_class, course_key, task_input, task_key, microsite)
    return submit_task(request, task_type, task_class, course_key, task_input, task_key, microsite)


# def submit_sbo_user_xls(request,course_key):

#     task_type = 'sbo_xls_user'

#     task_class = sbo_user

#     microsite = configuration_helpers.get_value('domain_prefix')

#     task_input = {
#         "requester_id":request.user.id,
#         "requester_email":request.user.email,
#         "custom_field":json.loads(request.user.profile.custom_field),
#         "microsite":microsite,
#     }

#     task_key = ""

#     return submit_task(request, task_type, task_class, course_key, task_input, task_key, microsite)


# #ADD TIME TMA DASHBOARD
# def submit_add_extra_time(request,course_key):
#     task_type = 'add_extra_time'
#     task_class = add_extra_time
#     microsite = configuration_helpers.get_value('domain_prefix')

#     task_input = {
#         "requester_id":request.user.id,
#         "requester_email":request.user.email,
#         "participants_list":json.loads(request.body).get('participants_list',[]),
#         "time_to_add":json.loads(request.body).get('time_to_add',0),
#         "microsite":microsite,
#     }
#     task_key = "tma_extra_time"
#     return submit_task(request, task_type, task_class, course_key, task_input, task_key, microsite)
