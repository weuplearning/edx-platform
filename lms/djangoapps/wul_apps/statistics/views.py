import logging
log = logging.getLogger()
import json

from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST,require_GET,require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from .time_tracker import time_tracker_manager
from util.json_request import JsonResponse
from student.models import User
from edxmako.shortcuts import render_to_response
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

##### TIME TRACKING #########
@ensure_csrf_cookie
@login_required
@require_POST
def add_time_tracking(request,course_id):
    if request.POST.get('user_email'):
        user= User.objects.get(email=request.POST.get('user_email'))
    else :
        user=request.user
    response={}
    try :
        time=request.POST.get('time')
        section=request.POST.get('course_section')
        sub_section=request.POST.get('course_sub_section')
    except:
        time=''
        section=''
        sub_section=''
    if time is not None and section is not None and sub_section is not None :
        feedback = time_tracker_manager(user, course_id).add_course_time(time, section, sub_section)
        if feedback !='error':
            status = 200
            response['success']=_('Time spent registered for user')
        else :
            status = 400
            response['success']=_('Error while registering time')
    else :
        status = 400
        response['error']=_('Missing parameters')
    return JsonResponse(response, status=status)


@ensure_csrf_cookie
@login_required
@require_POST
def update_user_course_state(request,course_id):
    user=request.user
    response={}
    course_state=request.POST.get('course_user_status')
    if course_state is not None :
        feedback=time_tracker_manager(user, course_id).mark_course_status(course_state)
        if feedback !='error':
            status = 200
            response['success']=_('Time spent registered for user')
        else :
            status = 400
            response['success']=_('Error while registering time')
    else:
        status = 400
        response['error']=_('Missing parameters')
    return JsonResponse(response, status=status)

@ensure_csrf_cookie
@login_required
def get_user_global_time(request,course_id):
    global_time=''
    if request.POST.get('user_email') and User.objects.filter(email=request.POST.get('user_email')).exists():
        user= User.objects.get(email=request.POST.get('user_email'))
        try:
            global_time = time_tracker_manager(user, course_id).get_global_time()
        except:
            global_time = 0
            pass
    elif not request.POST.get('user_email') and User.objects.filter(email=request.user.email).exists():
        user= User.objects.get(email=request.user.email)
        try:
            global_time = time_tracker_manager(user, course_id).get_global_time()
        except:
            global_time = 0
            pass

    if global_time:
        if global_time:
            status=200
            response={
            "global_time":global_time
            }
        elif global_time==0:
            status=200
            response={
            "global_time":0
            }
        else :
            status=200
            response={
            "global_time":0
            }
    else :
        status=400
        response={
            "global_time":"user_not_registered"
        }
    
    return JsonResponse(response, status=status)

