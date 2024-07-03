import random
import re
import time
import string
import hashlib
import base64
import json
from django.contrib.auth.models import User, AnonymousUser
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
from student.models import UserProfile, CourseEnrollment
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers


import logging
log = logging.getLogger()


class wul_verify_access():
    def __init__(self, user):
        self.user = user
        self.email = user.email
        self.username = user.username
        self.org = configuration_helpers.get_value('course_org_filter')[0]

    def is_wul_team(self):
        if self.user.is_staff and self.email.find('themoocagency.com') > -1 and self.user.is_active:
            return True
        elif self.user.is_staff and self.email.find('weuplearning.com') > -1 and self.user.is_active:
            return True
        else:
            return False

    def is_page_allowed(self):
        allowed_users = configuration_helpers.get_value('WUL_PAGES_ACCESS')

        if allowed_users is not None:
            if self.email in allowed_users:
                return True
                
        return False


    def is_dashboard_allowed(self):
        allowed_users = configuration_helpers.get_value('WUL_DASHBOARD_ACCESS')

        if allowed_users is not None:
            if self.email.lower() in allowed_users:
                return True

        return False

    def has_dashboard_access(self):
        if self.is_wul_team() or self.is_dashboard_allowed():
            return True
        else:
            return False


class wul_randomization():
    def __init__(self, course_key):
        self.course_key = course_key
        self.course_randomized_info = self.get_course_randomized_info()

    def clean_dict_keys(self, dict_to_clean):
        dict_to_clean = dict(dict_to_clean)
        for key in dict_to_clean.keys():
            new_key = key.lower().replace(' ', '')
            dict_to_clean[new_key] = dict_to_clean.pop(key)
        return dict_to_clean

    def get_course_randomized_info(self):
        organization = self.course_key.org
        microsite_info = {}
        try:
            microsite_info = SiteConfiguration.objects.get(
                key=organization).values.get('WUL_SKILL_RANDOMIZED')
        except:
            pass
        if microsite_info:
            return microsite_info.get(str(self.course_key))
        else:
            return {}

    def get_randomization_mode(self):
        if self.course_randomized_info:
            if self.course_randomized_info.get('skill-dispatch'):
                mode = 'skill-dispatch'
            else:
                mode = 'skill'
        else:
            mode = 'random'
        return mode

    def get_skill_dispatch(self):
        skill_dispatch = {}
        if self.course_randomized_info:
            skill_dispatch = self.course_randomized_info.get('skill-dispatch')
            if skill_dispatch:
                skill_dispatch = self.clean_dict_keys(skill_dispatch)
        return skill_dispatch


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def is_valid_email(email):
    match = re.match(
        '^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email)
    if match == None:
        valid = False
    else:
        valid = True
    return valid


def data_check(post_parameters, api_client_data):
    valid_data = True
    required_parameters = api_client_data['register_call_parameters']
    missing_fields = []
    invalid_fields = []

    for parameter in required_parameters:
        if required_parameters[parameter].get('required') and not parameter in post_parameters.keys():
            missing_fields.append(parameter)
            valid_data = False
        elif 'email_check' in required_parameters[parameter] and required_parameters[parameter]['email_check'] == True and not is_valid_email(post_parameters[parameter]):
            invalid_fields.append(parameter)
            valid_data = False

    if not missing_fields:
        if not is_valid_client(post_parameters, api_client_data):
            invalid_fields.append('signature is not valid')
            valid_data = False
        if not is_valid_courseid(post_parameters['course_id'], api_client_data):
            invalid_fields.append('course_id is not valid')
            valid_data = False

    if valid_data:
        return valid_data
    else:
        response = {
            'invalid_fields': invalid_fields,
            'missing_fields': missing_fields
        }
    return response


def is_valid_client(parameters, api_client_data):
    valid_client = True
    signature = parameters['signature']
    API_KEY = api_client_data['api_key']
    decoded_signature_base = parameters['email']+parameters['first_name'] + \
        parameters['last_name']+parameters['referrer']+API_KEY

    if hashlib.sha512(decoded_signature_base).hexdigest() != signature:
        valid_client = False
    return valid_client


def is_valid_courseid(course_id, api_client_data):
    valid_course_id = False
    try:
        course_key = SlashSeparatedCourseKey.from_string(course_id)
    except:
        valid_course_id = False
        return valid_course_id
    if(api_client_data['org_rights'] == 'all') and CourseOverview.objects.filter(id=course_key).exists():
        valid_course_id = True
    elif CourseOverview.objects.filter(id=course_key, org__in=api_client_data['org_rights']).exists():
        valid_course_id = True
    return valid_course_id


def generate_username(last_name, client_name):
    clean_prefix = last_name.replace(" ", "_").replace("-", "_")+"_"
    username = client_name + clean_prefix + id_generator()
    while User.objects.filter(username=username).exists():
        username = client_name + clean_prefix + id_generator()
    return username


def get_password(first_name, password_base):
    clean_name = first_name.replace(' ', '')
    password = base64.b64encode(clean_name+password_base)
    return password


def register_from_courseid(user, student_mail, course_id):
    course_id = SlashSeparatedCourseKey.from_string(course_id)
    if not CourseEnrollment.is_enrolled(user, course_id):
        enrollment_obj = CourseEnrollment.enroll_by_email(
            student_mail, course_id)
    else:
        enrollment_obj = "Already registered to class {}".format(course_id)
    return enrollment_obj


def is_enrollment_opened(course):
    enrollment_open = True
    _current = time.time()
    if course.enrollment_start and int(course.enrollment_start.strftime("%s")) > _current:
        enrollment_open = False
    elif course.enrollment_end and int(course.enrollment_end.strftime("%s")) < _current:
        enrollment_open = False
    return enrollment_open


def is_course_opened(course):
    _current = time.time()
    course_opened = True
    if course.start and (_current < int(course.start.strftime("%s"))):
        course_opened = False
    elif course.end and (_current > int(course.end.strftime("%s"))):
        course_opened = False
    return course_opened
