# -*- coding: utf-8 -*-

import json
import logging
from pprint import pformat
from random import randint
from rest_framework.views import APIView
from rest_framework import status
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment
from student.models import User, UserProfile
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse,Http404,HttpResponseForbidden,HttpResponse
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from lms.djangoapps.wul_apps.wul_support_functions import wul_verify_access
from lms.djangoapps.wul_apps.ensure_form.utils import ensure_form_factory
import datetime, time

log = logging.getLogger()

class CustomFieldView(APIView):
    def get(self, request):
        user_id = str(request.user.id)

        context = {
            "status":True,
            "message":'[WUL] custom_field for User {} successfully read'.format(user_id)
        }

        user_email = request.user.email

        user = User.objects.get(email=user_email)

        form_factory = ensure_form_factory()
        db = 'ensure_form'
        collection = 'certificate_form'
        form_factory.connect(db=db,collection=collection)
        form_factory.get_user_form_extra(user)
        form_factory.get_user_certificate_form_extra(user)
        certificate_form_extra = form_factory.user_certificate_form_extra

        try :
            cas_pratique_grade = int(certificate_form_extra["cas_pratique_grade"])
        except:
            pass

        try:
            user_profile = UserProfile.objects.get(user_id=user_id)
            custom_field = json.loads(user_profile.custom_field)
            try :
                custom_field["cas_pratique_grade"] = cas_pratique_grade
            except:
                pass

        except:
            context['status'] = False
            context['message'] = '[WUL] Custom_field failed for User {} to be read'.format(user_id)
            return JsonResponse(context, status=500)

        return JsonResponse(custom_field, status=200)
    
    def post(self, request, format='json'):
        user_id = str(request.user.id)

        log.info('[WUL] User {} POST new values for his custom fields'.format(user_id))

        context = {
            "status":True,
            "message":'[WUL] custom_field for User {} successfully updated'.format(user_id)
        }

        try: 
            custom_fields = json.loads(request.user.profile.custom_field)
            # As request.data is a querydict with multiplevalues for keys we update manually
            for key in request.data.keys():
                custom_fields[key] = request.data[key]
            request.user.profile.custom_field = json.dumps(custom_fields)
            request.user.profile.save()
        except:
            context['status'] = False
            context['message'] = '[WUL] Custom_field update for User {} failed'.format(user_id)
            return JsonResponse(context, status=500)

        log.info('[WUL] User {} new value(s) for custom fields : {}'.format(user_id,pformat(request.data)))

        return JsonResponse(context, status=200)



class CustomFieldEditor(APIView):
    def get(self, request):

        if not wul_verify_access(request.user).has_dashboard_access(course_id=None):
            return HttpResponseForbidden
        user_id = request.user_id
        context = {
            "status":True,
            "message":'[WUL] custom_field for User {} successfully read'.format(user_id)
        }

        try:
            user_profile = UserProfile.objects.get(user_id=user_id)
            custom_field = json.loads(user_profile.custom_field)
        except:
            context['status'] = False
            context['message'] = '[WUL] Custom_field failed for User {} to be read'.format(user_id)
            return JsonResponse(context, status=500)

        return JsonResponse(custom_field, status=200)
    
    def post(self, request, format='json'):

        if not wul_verify_access(request.user).has_dashboard_access():
            return HttpResponseForbidden
        # if not wul_verify_access(request.user).has_dashboard_access(course_id=None):
        #     return HttpResponseForbidden
        user_id = request.data['user_id_for_api']

        user = User.objects.get(id=user_id)
        user_profile = UserProfile.objects.get(user_id=user_id)

        log.info('[WUL] User {} POST new values for his custom fields'.format(user_id))

        context = {
            "status":True,
            "message":'[WUL] custom_field for User {} successfully updated'.format(user_id)
        }

        try: 
            custom_fields = json.loads(user_profile.custom_field)
            # As request.data is a querydict with multiplevalues for keys we update manually
            for key in request.data.keys():
                # if key != 'user_id_for_api':
                #     custom_fields[key] = request.data[key]
                #     log.info(request.data[key])
                #     log.info(type(request.data[key]))

                if key != 'user_id_for_api':
                    if key == "virtual_class_1" or key == "virtual_class_2":
                        custom_fields[key] =json.loads(request.data[key]) 
                    else:
                        custom_fields[key] = request.data[key]

            custom_fields["last_update_maker"] = request.user.email
            custom_fields["last_update_date"] = int(round(time.time() * 1000))
            user_profile.custom_field = json.dumps(custom_fields)
            user.first_name = custom_fields["first_name"]
            user.last_name = custom_fields["last_name"]
            user.save()

            user_profile.save()
        except:
            context['status'] = False
            context['message'] = '[WUL] Custom_field update for User {} failed'.format(user_id)
            return JsonResponse(context, status=500)

        log.info('[WUL] User {} new value(s) for custom fields : {}'.format(user_id,pformat(request.data)))

        return JsonResponse(context, status=200)