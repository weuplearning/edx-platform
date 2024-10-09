# -*- coding: utf-8 -*-

"/edx/app/edxapp/edx-platform/lms/djangoapps/wul_apps/custom_fields_editor/views.py"
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

class CustomFieldViewUmn(APIView):
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



def find_best_referent(custom_fields):
    file_path = '/edx/app/edxapp/edx-platform/lms/djangoapps/wul_apps/custom_fields_editor_umn/umn_formations.json'
    with open(file_path, 'r',encoding='utf-8') as file:
        data = json.load(file)
    school = custom_fields.get('school','')
    formation = custom_fields.get('formation','')
    class_name = custom_fields.get('class','')
    year = custom_fields.get('year','')
    diplomalvl = custom_fields.get('diplomalvl','')
    try:
        if school in data:
            for program in data[school]:
                if (program['title'] == formation and
                    program['class'] == class_name and
                    program['year'] == year and
                    program['diplomalvl'] == diplomalvl):
                    return program['referents']
    except:
        return "INVALID_REFERENT"
    return "UNKNOWN_REFERENT"

def fill_regular_users(custom_fields):
    # used to avoid filling custom fields with bad data from login form
    custom_fields['school'] = ''
    custom_fields['diplomalvl'] = '' 
    custom_fields['formation'] = ''
    custom_fields['class'] = ''
    custom_fields['year'] = ''
    custom_fields['referent'] = 'N/A'
    return custom_fields

def reset_custom_fields(custom_fields):
    custom_fields.pop('schoolregion',None)
    custom_fields.pop('school',None)
    custom_fields.pop('status',None) 
    custom_fields.pop('diplomalvl',None) 
    custom_fields.pop('formation',None)
    custom_fields.pop('class',None)
    custom_fields.pop('year',None)
    custom_fields.pop('referent',None)
    return custom_fields

class CustomFieldEditorUmn(APIView):
    def get(self, request):

        if not wul_verify_access(request.user).has_dashboard_access():
            return HttpResponseForbidden

        try:
            user_id = request.user_id
        except:
            user_id = request.user.id

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

        if not (wul_verify_access(request.user).has_dashboard_access() or request.data['authorized']):
            return HttpResponseForbidden

        try:
            user_id = request.data['user_id_for_api']
        except:
            user_id = request.user.id

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

                if key != 'user_id_for_api' or key != 'authorized':
                    if key == "virtual_class_1" or key == "virtual_class_2":
                        custom_fields[key] = json.loads(request.data[key]) 
                    else:
                        custom_fields[key] = request.data[key]

                    if key == "first_name":
                        user.first_name = custom_fields["first_name"]

                    if key == "last_name":
                        user.first_name = custom_fields["last_name"]
            user_status = custom_fields.get('status','')
            if(user_status == 'learner' or user_status == 'teacher'):
                custom_fields["referent"] = find_best_referent(custom_fields)
            else:
                custom_fields = fill_regular_users(custom_fields)
            if(user_status == 'reset'):
                custom_fields = reset_custom_fields(custom_fields)

            custom_fields["last_update_maker"] = request.user.email
            custom_fields["last_update_date"] = int(round(time.time() * 1000))
            # used a version marker : 1 - 09/10/2024
            custom_fields["update_marker"] = 1

            user_profile.custom_field = json.dumps(custom_fields)
            user.save()
            user_profile.save()
 
        except:
            context['status'] = False
            context['message'] = '[WUL] Custom_field update for User {} failed'.format(user_id)
            return JsonResponse(context, status=500)

        log.info('[WUL] User {} new value(s) for custom fields : {}'.format(user_id,pformat(request.data)))

        return JsonResponse(context, status=200)