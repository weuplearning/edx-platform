# -*- coding: utf-8 -*-

import os

from django.http import JsonResponse, HttpResponseForbidden
from rest_framework.views import APIView
from django.utils.dateparse import parse_date
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.http import HttpResponse
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from lms.djangoapps.wul_apps.wul_support_functions import wul_verify_access

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory

from datetime import datetime
import json

import logging
log = logging.getLogger()


# @method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(login_required, name='dispatch')
class DashboardDataView(APIView):



    # utiliser le get pour les données globale, calculées dans un script à part pour limiter le temps de chargement sur les grosses plateformes
    def get(self, request):

        log.info(request)
        log.info(request.user)

        if not wul_verify_access(request.user).has_dashboard_access() or not configuration_helpers.get_value('WUL_DASHBOARD_CONFIG'):
            return HttpResponseForbidden


        org = configuration_helpers.get_value('course_org_filter')[0]
        json_dir_path = '/edx/var/edxapp/data_visualisation/'+ org 
        json_file_path = os.path.join(json_dir_path, 'datavis_report.json')




        if os.path.exists(json_file_path):
            with open(json_file_path, 'rb') as file:
                response = HttpResponse(file.read(), content_type='json')
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(json_file_path)}"'

                return response
        else:
            return HttpResponse('JSON file not found', status=404)




    def post(self, request, format='json'):

        log.info("POST")
        log.info(request)
        log.info(request.user)

        if not wul_verify_access(request.user).has_dashboard_access() or not configuration_helpers.get_value('WUL_DASHBOARD_CONFIG'):
            return HttpResponseForbidden


        try:
            data = request.data

            log.info('data')
            log.info(data)
            log.info(type(data))

            start_date = parse_date(data.get("start"))
            end_date = parse_date(data.get("end")) or datetime.today().date()

        except (TypeError, ValueError, json.JSONDecodeError):
            log.info("POST error")
            log.info(request)
            return JsonResponse({"error": "Invalid date format"}, status=400)


        log.info(f"Start: {start_date}, End: {end_date}")


        # à mettre dans un try ? 
            # except servir un message d'erreur
        org = configuration_helpers.get_value('course_org_filter')[0]
        log.info("org")
        log.info(org)


        courses = CourseOverview.objects.filter(org=org)
        log.info('courses')
        log.info(courses)

        data = {}

        for course in courses:

            stats = {
                "countEnrollment" : 0,
                "countFinishedEnrollment": 0, 
                "averageProgression": {},
                "averageTimeTracking": {}
            }

            enrollments = CourseEnrollment.objects.filter(course_id=course.id)
            stats["countEnrollment"] = enrollments.count()
            log.info("course")
            log.info(course)


            completed_count = sum(1 for e in enrollments if CourseGradeFactory().read(e.user, course).passed)

            stats["countFinishedEnrollment"] = completed_count
            stats["averageProgression"] = self.get_course_completion_rate(course, enrollments)

            data[str(course.id)] = stats



        return JsonResponse(data)




    def get_course_completion_rate(self, course, enrollments):
        completed_count = 0

        for e in enrollments :
            grade = CourseGradeFactory().read(e.user, course).percent
            completed_count += grade

        return (completed_count / enrollments.count() * 100) if enrollments.count() > 0 else 0



    # def get_quiz_success_rate(self, course=None):
    #     return 70



def get_dashboard_data(request):
    """
    Access site config and more if necessary
    """

    log.info(request)
    log.info(request.user)

    if not wul_verify_access(request.user).has_dashboard_access() or not configuration_helpers.get_value('WUL_DASHBOARD_CONFIG'):
        return HttpResponseForbidden

    csrf_token = get_token(request)
    log.info(csrf_token)
    email = request.user.email

    data = {
        "platform_name": configuration_helpers.get_value("platform_name", default="Open edX"),
        "dashboard_config": configuration_helpers.get_value("WUL_DASHBOARD_CONFIG", default={}),
        "lms_base": configuration_helpers.get_value("LMS_BASE", default="lms.example.com"),
        "expiration_date": configuration_helpers.get_value("EXPIRATION_DATE", default="01-01-2030"),
        "form": configuration_helpers.get_value("FORM_EXTRA", default="[]"),
        "csrf_token": csrf_token,
        "user_email": email
        # ajoute d'autres valeurs utiles ici
    }

    log.info("data")
    log.info(data)


    return JsonResponse(data)






