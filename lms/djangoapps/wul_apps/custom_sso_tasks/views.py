# -*- coding: utf-8 -*-

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST,require_GET,require_http_methods
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from edxmako.shortcuts import render_to_response
from student.models import CourseEnrollment



import logging
log = logging.getLogger(__name__)


@login_required
def sso_registration_views(request, course_id):
    """
    Can be used after SSO login.
    As it is not possible to register and enroll in the same time,
    we are using a temporary views to do the enrollment.

    If the user is already enroll redirect to the corresponding course
    Else display the template to process to the enrollment 

    request contain logged user info
    course_id is accessed through the URL (params)
    """

    user = request.user
    enrollment_list_for_a_given_user = CourseEnrollment.objects.filter(user=user)

    for enrollment in enrollment_list_for_a_given_user:

        if course_id == str(enrollment.course_id):

            url_value = '/courses/'+course_id+'/course/'
            return HttpResponseRedirect(url_value)

    context = {'course_id': course_id}

    return render_to_response('wul_apps/sso_registration.html', {"props": context})
