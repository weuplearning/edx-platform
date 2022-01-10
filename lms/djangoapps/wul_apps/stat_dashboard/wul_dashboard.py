# -*- coding: utf-8 -*-
'''
/edx/app/edxapp/edx-platform/lms/djangoapps/wul_apps/stat_dashboard/wul_dashboard.py
'''

import sys
import importlib
importlib.reload(sys)

import string
import random
from datetime import datetime
import os
import csv
import time
# from xlwt import *
import json
from io import BytesIO
from path import Path

from opaque_keys.edx.keys import CourseKey

from xmodule.modulestore.django import modulestore
from courseware.courses import get_course_by_id
from student.models import User,CourseEnrollment,UserProfile,LoginFailures
from course_api.blocks.api import get_blocks
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
# from lms.djangoapps.tma_grade_tracking.models import dashboardStats
from edxmako.shortcuts import render_to_response
# from .api import stat_dashboard_api

from openedx.core.lib.tempdir import mkdtemp_clean

from django.core.validators import validate_email

import logging
import json


from django.conf import settings

#enroll
from django.utils.translation import ugettext as _
from django.db import IntegrityError, transaction
from instructor.views.api import generate_random_string,create_manual_course_enrollment
from django.core.exceptions import ValidationError, PermissionDenied
from openedx.core.djangoapps.course_groups.models import CohortMembership, CourseUserGroup

from django.contrib.auth.models import User

# from shoppingcart.models import (
#     Coupon,
#     CourseRegistrationCode,
#     RegistrationCodeRedemption,
#     Invoice,
#     CourseMode,
#     CourseRegistrationCodeInvoiceItem,
# )
from student.models import (
    CourseEnrollment, unique_id_for_user, anonymous_id_for_user,
    UserProfile, Registration, EntranceExamConfiguration,
    ManualEnrollmentAudit, UNENROLLED_TO_ALLOWEDTOENROLL, ALLOWEDTOENROLL_TO_ENROLLED,
    ENROLLED_TO_ENROLLED, ENROLLED_TO_UNENROLLED, UNENROLLED_TO_ENROLLED,
    UNENROLLED_TO_UNENROLLED, ALLOWEDTOENROLL_TO_UNENROLLED, DEFAULT_TRANSITION_STATE
)
from lms.djangoapps.instructor.enrollment import (
    get_user_email_language,
    enroll_email,
    send_mail_to_student,
    get_email_params,
    send_beta_role_email,
    unenroll_email,
)
from instructor.enrollment import render_message_to_string
from django.core.mail import send_mail

#taskmodel
from lms.djangoapps.wul_tasks.models import WulTask

#USER MANAGEMENT
from django.utils.http import int_to_base36
from django.contrib.auth.tokens import default_token_generator
# from student.views import password_reset_confirm_wrapper
# from django.core.urlresolvers import reverse

#EMAIL MANAGEMENT
import smtplib
# from email.MIMEMultipart import MIMEMultipart
# from email.MIMEText import MIMEText
# from email.MIMEBase import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from courseware.courses import get_course_by_id

#Course timer
from lms.djangoapps.wul_apps.models import WulCourseOverview
from django.core import serializers

from openedx.core.djangoapps.course_groups.cohorts import is_course_cohorted
# from lms.djangoapps.tma_apps.tma_statistics.time_tracker import time_tracker_manager

# from social.apps.django_app.default.models import UserSocialAuth
from social_django.models import UserSocialAuth


log = logging.getLogger(__name__)


class wul_dashboard():

    def __init__(self,course_id=None,course_key=None,request=None):

        self.request = request
        self.site_name = None
        self.course_key = course_key
        self.course_id = course_id
        self.course = get_course_by_id(course_key)
        self.course_module = modulestore().get_course(course_key, depth=0)

    def required_register_fields(self):

        register_fields = [
            {
                "name":"email",
                "required":True,
                "label":"Email"
            }
        ]

        _microsite_register_fields = configuration_helpers.get_value("FORM_EXTRA")

        if _microsite_register_fields is not None:
            for row in _microsite_register_fields:

                name = row.get('name')
                required = row.get('required')
                label = row.get('label')

                register_fields.append(
                        {
                            "name":name,
                            "required":required,
                            "label":label
                        }
                    )

        return register_fields

    def required_certificates_fields(self):

        certificates_fields = [

        ]

        _microsite_certificates_fields = configuration_helpers.get_value("CERTIFICATE_FORM_EXTRA")

        if _microsite_certificates_fields is not None:
            for row in _microsite_certificates_fields:

                name = row.get('name')
                required = row.get('required')
                label=row.get('label')

                certificates_fields.append(
                        {
                            "name":name,
                            "required":required,
                            "label":label
                        }
                    )

        return certificates_fields


    #password generator

    def create_user_and_user_profile(self,email, username, password, custom_field, complete_name, first_name, last_name):
        """
        Create a new user, add a new Registration instance for letting user verify its identity and create a user profile.
        :param email: user's email address
        :param username: user's username
        :param name: user's name
        :param country: user's country
        :param password: user's password
        :return: User instance of the new user.
        """
        user = User(
            username=username,
            email=email,
            is_active=True,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        user.save()
        registration = Registration()
        registration.register(user)
        """
        reg = Registration()
        reg.register(user)
        """
        #user.save()
        profile = UserProfile(user=user)
        profile.custom_field = json.dumps(custom_field)
        profile.name=complete_name
        profile.save()

        return user

    def create_and_enroll_user(self,email, username, custom_field, password,complete_name, course_id, course_mode, enrolled_by, email_params, first_name, last_name, microsite):
        """
        Create a new user and enroll him/her to the given course, return list of errors in the following format
            Error format:
                each error is key-value pait dict with following key-value pairs.
                1. username: username of the user to enroll
                1. email: email of the user to enroll
                1. response: readable error message
        :param email: user's email address
        :param username: user's username
        :param name: user's name
        :param country: user's country
        :param password: user's password
        :param course_id: course identifier of the course in which to enroll the user.
        :param course_mode: mode for user enrollment, e.g. 'honor', 'audit' etc.
        :param enrolled_by: User who made the manual enrollment entry (usually instructor or support)
        :param email_params: information to send to the user via email
        :return: list of errors
        """
        errors = list()
        user = ''

        try:
            with transaction.atomic():
                # Create a new user
                user = self.create_user_and_user_profile(email, username, password, custom_field,complete_name, first_name, last_name)
                # Enroll user to the course and add manual enrollment audit trail
                create_manual_course_enrollment(
                    user=user,
                    course_id=self.course_key,
                    mode=course_mode,
                    enrolled_by=enrolled_by,
                    reason='Enrolling via csv upload',
                    state_transition=UNENROLLED_TO_ENROLLED,
                )

                #add custom_field
        except IntegrityError:
            errors.append({
                'username': username, 'email': email, 'response': _('Username {user} already exists.').format(user=username)
            })
        except Exception as ex:  # pylint: disable=broad-except
            log.exception(type(ex).__name__)
            errors.append({
                'username': username, 'email': email, 'response': type(ex).__name__,
            })
        else:
            try:
                desired_start_date =custom_field['desired_start_date']
                email_params.update({
                    'desired_start_date': desired_start_date
                })
            except:
                pass
            try:
                # It's a new user, an email will be sent to each newly created user.
                email_params.update({
                    'message': 'account_creation_and_enrollment',
                    'email_address': email,
                    'password': password,
                    'platform_name': self.site_name,
                    'first_name': first_name,
                    'microsite':microsite,
                    'site_name':self.site_name,
                    'full_name':first_name+" "+last_name,
                    'course_key':str(self.course_key)
                })
                #update sitename params
                self.send_mail_to_student(email, email_params)
            except Exception as ex:  # pylint: disable=broad-except
                log.exception(
                    "Exception '{exception}' raised while sending email to new user.".format(exception=type(ex).__name__)
                )
                errors.append({
                    'username': username,
                    'email': email,
                    'response':
                        _("Error '{error}' while sending email to new user (user email={email}). "
                          "Without the email student would not be able to login. "
                          "Please contact support for further information.").format(error=type(ex).__name__, email=email),
                })
            else:
                log.info(u'email sent to new created user at %s', email)

        return user

    #enroll
    def send_mail_to_student(self,student, param_dict, language=None):
        log.info("send_mail_to_students")
        """
        Construct the email using templates and then send it.
        `student` is the student's email address (a `str`),
        `param_dict` is a `dict` with keys
        [
            `site_name`: name given to edX instance (a `str`)
            `registration_url`: url for registration (a `str`)
            `display_name` : display name of a course (a `str`)
            `course_id`: id of course (a `str`)
            `auto_enroll`: user input option (a `str`)
            `course_url`: url of course (a `str`)
            `email_address`: email of student (a `str`)
            `full_name`: student full name (a `str`)
            `message`: type of email to send and template to use (a `str`)
            `is_shib_course`: (a `boolean`)
        ]
        `language` is the language used to render the email. If None the language
        of the currently-logged in user (that is, the user sending the email) will
        be used.
        Returns a boolean indicating whether the email was sent successfully.
        """

        # add some helpers and microconfig subsitutions

        if 'display_name' in param_dict:
            param_dict['course_name'] = param_dict['display_name']

        subject = None
        message = None
        plain_message = None
        html_message = None

        # see if there is an activation email template definition available as configuration,
        # if so, then render that
        message_type = param_dict['message']
        dest_path = Path(settings.COMPREHENSIVE_THEME_DIRS[0])
        
        # template_base="/edx/app/edxapp/edx-themes/"+param_dict['microsite']+"/lms/templates/instructor/edx_ace/"
        template_base= dest_path + "/" + param_dict['microsite']+"/lms/templates/instructor/edx_ace/"

        log.info(template_base)

        email_template_dict = {
            'allowed_enroll': (
                'allowed_enroll/email/subject.txt',
                'allowed_enroll/email/body.txt'
            ),
            'enrolled_enroll': (
                'enrollenrolled/email/subject.txt',
                'enrollenrolled/email/body.txt'
            ),
            'allowed_unenroll': (
                'allowed_unenroll/email/subject.txt',
                'allowed_unenroll/email/body.txt'
            ),
            'enrolled_unenroll': (
                'enrolled_unenroll/email/subject.txt',
                'enrolled_unenroll/email/body.txt'
            ),
            'add_beta_tester': (
                'add_beta_tester/email/subject.txt',
                'add_beta_tester/email/body.txt'
            ),
            'remove_beta_tester': (
                'remove_beta_tester/email/subject.txt',
                'remove_beta_tester/email/body.txt'
            ),
            'account_creation_and_enrollment': (
                'accountcreationandenrollment/email/subject.txt',
                'accountcreationandenrollment/email/body.txt'
            ),
        }

        subject_template, message_template = email_template_dict.get(message_type, (None, None))
        log.info(template_base+subject_template)
        if subject_template is not None and message_template is not None:
            subject, message = render_message_to_string(
                template_base+subject_template, template_base+message_template, param_dict, language=language
            )

        if subject and message:
            # Remove leading and trailing whitespace from body
            message = message.strip()

            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())
            from_address = configuration_helpers.get_value(
                'email_from_address',
                settings.DEFAULT_FROM_EMAIL
            )

            # set email type : plain/text or html/text
            org = self.course_id.split(":")[1].split("+")[0]
            email_type = configuration_helpers.get_value_for_org(org, 'LIST_EMAIL_IN_HTML_TYPE')
            if isinstance(email_type, list) and message_type in email_type :
                html_message=message
            else:
                plain_message=message

            send_mail(subject, message=plain_message, from_email=from_address, recipient_list=[student], fail_silently=False, html_message=html_message)

    def generate_unique_password(self,generated_passwords, password_length=12):
        """
        generate a unique password for each student.
        """

        password = generate_random_string(password_length)
        while password in generated_passwords:
            password = generate_random_string(password_length)

        generated_passwords.append(password)

        return password

    def task_generate_user(self):
        """
            Logique de traitement:
            - l'utilisateur a un compte sur la plateforme : inscription cours + email enrolled_enroll. Si déjà inscrit pas d'action. Dans tous les cas pas d'update des custom field prévu
            - l'utilisateur a un compte via SSO probablement sur la plateforme : inscription cours + email account_creation_and_enrollment + ajout custom_fields manquants
            - l'utilisateur n'a pas de compte : création compte plateforme + inscription cours + email account_creation_and_enrollment
            Les emails des templates microsite sont utilisés.
        """
        task_input = self.request
        valid_rows = task_input.get("valid_rows")
        microsite = task_input.get("microsite")

        requester_id = task_input.get("requester_id")
        _requester_user = User.objects.get(pk=requester_id)
        self.site_name = task_input.get('site_name')+' '

        log.warning(u'wul_dashboard.task_generate_user inscription users pour le microsite : '+microsite)  
        log.warning(u'wul_dashboard.task_generate_user inscription users par le username '+_requester_user.username+' email : '+_requester_user.email)

        generated_passwords = []
        _generates = []
        _failed = []
        warnings = []
        registered_users_list = []

        #Get all keys from register form
        register_keys = []
        register_form = task_input.get("register_form")
        for _key in register_form:
            register_keys.append(_key.get('name'))

        # for white labels we use 'shopping cart' which uses CourseMode.DEFAULT_SHOPPINGCART_MODE_SLUG as
        # course mode for creating course enrollments.

        # if CourseMode.is_white_label(self.course_key):
        #     course_mode = CourseMode.DEFAULT_SHOPPINGCART_MODE_SLUG
        # else:
        #     course_mode = None
        course_mode= None

        #TREATING EACH USER

        new_users = []
        already_enrolled_users = []

        for _user in valid_rows:
            #get current users values
            try:
                email = _user.get('email')
                username = email.split('@')[0].replace('-','').replace('.','').replace('_','')[0:10]+'_'+random_string(5)
                first_name=str(_user.get("first_name"))
                last_name=str(_user.get("last_name"))
                complete_name=first_name+' '+last_name

                #check valid email
                email_params = get_email_params(self.course, True, secure=True)
                new_course_url='https://'+self.site_name.replace(' ','')+'/dashboard/'+str(self.course.id)
                email_params.update({
                    'site_name': self.site_name,
                    'course_url':new_course_url,
                })
            except:
                _failed.append({
                    'email': email, 'response': _('Invalid info {email_address}.').format(email_address=email)})
            try:
                validate_email(email)
            except ValidationError:
                _failed.append({
                    'email': email, 'response': _('Invalid email {email_address}.').format(email_address=email)})

            created_user = ''
            if User.objects.filter(email=email).exists():

                # ENROLL EXISTING USER TO COURSE
                user = User.objects.get(email=email)
                # see if it is an exact match with email and username if it's not an exact match then just display a warning message, but continue onwards
                if not User.objects.filter(email=email, username=username).exists():
                    warning_message = _(
                        'An account with email {email} exists but the provided username {username} '
                        'is different. Enrolling anyway with {email}.'
                    ).format(email=email, username=username)

                    warnings.append({
                        'username': username, 'email': email, 'response': warning_message
                    })
                    log.warning(u'email %s already exist', email)
                else:
                    log.info(
                        u"user already exists with username '%s' and email '%s'",
                        username,
                        email
                    )

                # enroll a user if it is not already enrolled.
                if not CourseEnrollment.is_enrolled(user, self.course_key):

                    registered_users_list.append(email)
                    create_manual_course_enrollment(
                        user=user,
                        course_id=self.course_key,
                        mode=course_mode,
                        enrolled_by=_requester_user,
                        reason='Enrolling via csv upload',
                        state_transition=UNENROLLED_TO_ENROLLED,
                    )
                    # IF THERE IS NO SSO GO FOR STANDARD BEHAVIOUR

                    log.info('test UserSocialAuth.objects.filter(user=user).exists()  -->')
                    log.info(UserSocialAuth.objects.filter(user=user).exists())

                    if not UserSocialAuth.objects.filter(user=user).exists():
                        email_params.update({
                            'message':'enrolled_enroll',
                            'email_address':email,
                            'platform_name': self.site_name,
                            'first_name': first_name,
                            'microsite':microsite,
                            'full_name':first_name+" "+last_name,
                            'course_key':str(self.course_key)
                        })
                        already_enrolled_users.append(email)
                    else:
                    # IF THERE IS SSO THEN ACT AS IF THIS WAS A NEW USER IN TERMS OF EMAIL
                    # and change the password and update custom_fields if needed
                        password = self.generate_unique_password(generated_passwords)
                        user.set_password(password)
                        user.save()

                        profile = UserProfile.objects.get(user_id=user.id)
                        custom_field = {}
                        try:
                            custom_field = json.loads(profile.custom_field)
                        except:
                            pass

                        for key,value in _user.items():
                            #assurer que la key est presente dans la liste des key et non presente dans les custom_fields actuels
                            if (key in register_keys) and (not key in custom_field.keys()):
                                custom_field[key] = value
                        profile.custom_field = json.dumps(custom_field)
                        profile.save()

                        email_params.update({
                            'message': 'account_creation_and_enrollment',
                            'email_address': email,
                            'password': password,
                            'platform_name': self.site_name,
                            'site_name':self.site_name,
                            'first_name': first_name,
                            'microsite':microsite,
                            'full_name':first_name+" "+last_name,
                            'course_key':str(self.course_key)
                        })
                        new_users.append(email)
                    log.info("REGISTER USER TO COURSE")
                    self.send_mail_to_student(email, email_params)
                    #enroll_email(course_id=self.course_key, student_email=email, auto_enroll=True, email_students=True, email_params=email_params)

            else:
                # CREATE NEW ACCOUNT
                password = self.generate_unique_password(generated_passwords)
                #generate custom_field
                custom_field = {}
                for key,value in _user.items():
                    #assurer que la key est presente dans la liste des key et non presente dans les custom_fields actuels
                    if (key in register_keys) and (not key in custom_field.keys()):
                        custom_field[key] = value

            
                created_user = self.create_and_enroll_user(
                    email, username, custom_field, password, complete_name, self.course_id, course_mode, _requester_user, email_params, first_name, last_name, microsite
                )
                #maj de l'info
                if created_user != '':
                    _generates.append(
                        {"id":created_user.id,"email":created_user.email})
                    registered_users_list.append(created_user.email)
                else:
                    _failed.append(
                        {"email":email,"reponse":"creation failed"})
                new_users.append(email)

            # Dev Cyril Start
            # inspired from selective_register_fields feature from Ficus
            if created_user != '':
                try:
                    # register_fields = configuration_helpers.get_value('FORM_EXTRA',{})
                    if microsite == 'BVT' or microsite == 'bvt':
                        register_fields = configuration_helpers.get_value_for_org('bvt', 'FORM_EXTRA',{})
                        associated_courses = configuration_helpers.get_value_for_org('bvt', 'TMA_ASSOCIATED_COURSES',{})
                    else:
                        register_fields = configuration_helpers.get_value_for_org(microsite, 'FORM_EXTRA',{})
                        associated_courses = configuration_helpers.get_value_for_org(microsite, 'TMA_ASSOCIATED_COURSES',{})


                    custom_field = {}
                    # log.info(register_fields)
                    try:
                        custom_field = json.loads(created_user.profile.custom_field)
                        log.info(custom_field)
                    except:
                        log.info('no custom_field')
                        pass


                    user = User.objects.get(email=email)

                    if associated_courses.get('selective_register_fields') and custom_field:
                        for field_name in associated_courses.get('selective_register_fields'):
                            custom_field_value = custom_field.get(field_name)

                            for register_field in register_fields :

                                if register_field.get('name') == field_name:
                                    # courseList = []
                                    course = register_field.get('course')
                                    course_key = CourseKey.from_string(course)

                                    if custom_field_value == 'true' :
                                        # ENROLL
                                        if not CourseEnrollment.is_enrolled(user, course_key):
                                            CourseEnrollment.enroll(user, course_key)
                                            log.info('enroll '+user+' to '+str(course_key))

                                    # UNENROLL
                                    else:
                                        CourseEnrollment.unenroll(user, course_key)
                                        log.info('unenroll '+user+' to '+str(course_key))
                except:
                    pass

        # Dev Cyril End

        log.warning(u'wul_dashboard.task_generate_user fin inscription users pour le microsite : '+microsite)
        log.warning(u'wul_dashboard.task_generate_user fin inscription users par le username '+_requester_user.username+' email : '+_requester_user.email)

        #Send an email to requester with potential failures
        generated_users_list = ''
        # for user in registered_users_list :
        #     generated_users_list+="<li>{}</li>".format(user)
        status_text=''
        if not _failed :
            status_text='Tous les utilisateurs ont bien été créés et/ou inscrits au cours.'
        else :
            status_text="Une erreur s'est produite lors de l'inscription des utilisateurs suivants :<ul>"
            for user in _failed :
                status_text+="<li>"+user['email']+"</li>"
            status_text+="</ul><p>Merci de remonter le problème au service IT pour identifier l'erreur sur ces profils. Les autres profils utilisateur ont été correctement créés et/ou inscrits au cours.</p>"

        course=get_course_by_id(self.course_key)

        generated_users_list_enrolled = ""

        html = "<html><head></head><body><p>Bonjour,<br><br> L'inscription par CSV de vos utilisateurs au cours "+course.display_name_with_default+" sur le microsite "+microsite+" est maintenant terminée, voici la liste des utilisateurs inscrits:<br><ul>"+generated_users_list+"</ul><br>"+status_text+"<br><br>L'équipe WeUp Learning<br></p></body></html>"

        if len(new_users) > 0 and len(already_enrolled_users) > 0 :
            for user in new_users:
                generated_users_list+="<li>{}</li>".format(user)

            for user in already_enrolled_users:
                generated_users_list_enrolled+="<li>{}</li>".format(user)
            html = "<html><head></head><body><p>Bonjour,<br><br> L'inscription par CSV de vos utilisateurs au cours "+course.display_name_with_default+" sur le microsite "+microsite+" est maintenant terminée, voici la liste des utilisateurs inscrits:<br>- Nouveaux inscrits:<br><ul>"+generated_users_list+"</ul><br>-Déjà inscrits:<br><ul>"+generated_users_list_enrolled+"</ul><br>"+status_text+"<br><br>L'équipe WeUp Learning<br></p></body></html>"
        elif len(new_users) > 0:
            for user in new_users:
                generated_users_list+="<li>{}</li>".format(user)
            html = "<html><head></head><body><p>Bonjour,<br><br> L'inscription par CSV de vos utilisateurs au cours "+course.display_name_with_default+" sur le microsite "+microsite+" est maintenant terminée, voici la liste des utilisateurs nouvellement inscrits sur la plateforme :<br><ul>"+generated_users_list+"</ul><br>"+status_text+"<br><br>L'équipe WeUp Learning<br></p></body></html>"
        elif len(already_enrolled_users) > 0: 
            for user in already_enrolled_users:
                generated_users_list_enrolled+="<li>{}</li>".format(user)
            html = "<html><head></head><body><p>Bonjour,<br><br> L'inscription par CSV de vos utilisateurs au cours "+course.display_name_with_default+" sur le microsite "+microsite+" est maintenant terminée, voici la liste des utilisateurs déjà inscrits sur la plateforme :<br><ul>"+generated_users_list_enrolled+"</ul><br>"+status_text+"<br><br>L'équipe WeUp Learning<br></p></body></html>"

        part2 = MIMEText(html.encode('utf-8'), 'html', 'utf-8')
        fromaddr = "ne-pas-repondre@themoocagency.com"
        toaddr = _requester_user.email
        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['Subject'] = "Import utilisateurs csv"
        part = MIMEBase('application', 'octet-stream')
        server = smtplib.SMTP('mail3.themoocagency.com', 25)
        server.starttls()
        server.login('contact', 'waSwv6Eqer89')
        msg.attach(part2)
        text = msg.as_string()
        server.sendmail(fromaddr, toaddr, text)
        server.quit()

        retour = {
            "requester": _requester_user.email,
            "_generates": _generates,
            "_failed": _failed,
            "warning": warnings
        }

        return retour

    # def as_views(self):

    #     _stat_dashboard_api = _stat_dashboard_api = stat_dashboard_api(self.request,self.course_id,course_key=self.course_key)
    #     course_structure = _stat_dashboard_api.get_course_structure()

    #     #ensure user is @themoocagency.com
    #     _email = self.request.user.email
    #     if "@themoocagency.com" in _email:
    #         csv_limits = False
    #     else:
    #         csv_limits = True


    #     total_participants=CourseEnrollment.objects.enrollment_counts(self.course_key)

    #     #Course cohorted
    #     course_cohorted = is_course_cohorted(self.course_key)

    #     context = {
    #         "course_id":self.course_id,
    #         "course":self.course,
    #         "course_module":self.course_module,
    #         "course_structure":course_structure,
    #         "register_fields":self.required_register_fields(),
    #         "certificates_fields":self.required_certificates_fields(),
    #         "csv_limits":csv_limits,
    #         "total_participants":total_participants,
    #         "cohorted":course_cohorted,
    #     }

    #     return render_to_response('dashboard/home.html', context)

    def ensure_user_exists(self):

        list_users = json.loads(self.request.body)

        _username = []
        _email = []

        for u in list_users:
            _id = u.get('id')
            email = u.get('email')
            username = u.get('username')
            try:
                user = User.objects.get(email=email)
                q = {
                    "id":_id,
                    "email":email
                }
                _email.append(q)
            except:
                pass
            try:
                user = User.objects.get(username=username)
                q = {
                    "id":_id,
                    "username":username
                }
                _username.append(q)
            except:
                pass

        context = {
            "username":_username,
            "email":_email
        }

        return context

    # def user_grade_task_list(self):
    #     task_type = "user_generation"
    #     course_key = self.course_key
    #     task_list = WulTask.objects.all().filter(course_id=course_key,task_type=task_type)
    #     return_list = []
    #     for task in task_list:

    #         requester = User.objects.get(pk=task.requester_id)

    #         q = {}

    #         q['id'] = task.id

    #         q['requester'] = {
    #             "id":requester.id,
    #             "email":requester.email,
    #             "username":requester.username,
    #         }
	#         try:
    #             q['output'] = json.loads(task.task_output)
    #         except:
    #             q['output'] = {}

    #         q['date'] = task.created
    #         q['progress'] = task.task_state

    #         return_list.append(q)

    #     return return_list



    #USER MANAGEMENT ACTIONS
    # def generate_password_link(self):
    #     user_email=self.request.POST.get('user_email')
    #     user=User.objects.get(email=user_email)
    #     uid=int_to_base36(user.id)
    #     token = default_token_generator.make_token(user)

    #     final_link = reverse(password_reset_confirm_wrapper, args=(uid, token))
    #     json ={
    #     'link':str(final_link)
    #     }
    #     return json

    def tma_unlock_account(self):
        json={}
        user_email=self.request.POST.get('user_email')
        user=User.objects.get(email=user_email)
        if LoginFailures.objects.filter(user=user).exists():

            user_failure = LoginFailures.objects.get(user=user)
            user_failure.lockout_until = datetime.now()
            user_failure.failure_count=0
            user_failure.save()
            json['success']='User login failure was reset'

        else :
            json['error']='LoginFailure object doesn\'t exists'

        return json


    def tma_activate_account(self):
        user_email=self.request.POST.get('user_email')
        if User.objects.filter(email=user_email).exists():
            try :
                user=User.objects.get(email=user_email)
                user.is_active=True
                user.save()
                json ={
                'success':'account activated'
                }
            except:
                json ={
                'error':'error while activating account'
                }
        else :
            json ={
            'error':'user account does not exists'
            }

        return json



    # def task_add_time(self):
    #     task_input = self.request
    #     participant_list = task_input.get("participants_list")
    #     time_to_add = task_input.get("time_to_add")
    #     microsite = task_input.get("microsite")
    #     feedback=''
    #     invalid_mail=[]
    #     not_enrolled=[]
    #     not_registered=[]
    #     treated=[]
    #     failed=[]
    #     course = get_course_by_id(self.course_key)
    #     time_to_add_hours=time_to_add/3600
    #     time_to_add_minutes=(time_to_add-(time_to_add_hours*3600))/60

    #     if int(time_to_add) > 0 and len(participant_list)>0:
    #         for participant in participant_list :
    #             valid_email=False
    #             try:
    #                 validate_email(participant)
    #                 valid_email=True
    #             except ValidationError:
    #                 invalid_mail.append(participant)
                
    #             if valid_email :
    #                 if User.objects.filter(email=participant).exists():
    #                     user = User.objects.get(email=participant)
    #                     if CourseEnrollment.is_enrolled(user, self.course_key):
    #                         try:
    #                             time_tracker_manager(user=user, course_id=self.course_id).add_course_time(time=time_to_add, section="extra", sub_section="extra")
    #                             treated.append(participant)
    #                         except:
    #                             failed.append(participant)
    #                     else :
    #                         not_enrolled.append(participant)
    #                 else :
    #                     not_registered.append(participant)
                        
    #         if treated :
    #             feedback+=self.feedbackGenerator("Les utilisateurs suivants ont bien été traités (temps ajouté : "+str(time_to_add_hours)+"h"+str(time_to_add_minutes)+"mn) :", treated)
    #         if failed :
    #             feedback+=self.feedbackGenerator("Une erreur s'est produite lors de l'ajout de temps pour les utilisateurs suivants :", failed)
    #         if invalid_mail :
    #             feedback+=self.feedbackGenerator("Les emails suivants sont invalides :", invalid_mail)
    #         if not_enrolled :
    #             feedback+=self.feedbackGenerator("Les emails suivants ne sont pas inscrits à ce cours:", not_enrolled)
    #         if not_registered :
    #             feedback+=self.feedbackGenerator("Les emails suivants n'ont pas de cours sur notre plateforme:", not_registered)

    #     else :
    #         feedback="<p>Une erreur est survenue lors de l'ajout de temps sur votre liste d'utilisateurs :</p><ul>"
    #         if int(time_to_add)==0 or not time_to_add :
    #             feedback+="<li>Aucun temps à ajouter</li>"
    #         if len(participant_list)==0:
    #             feedback+="<li>Aucun participant dans la liste</li>"
    #         feedback+="</ul>"
        
    #     html = "<html><head></head><body><p>Bonjour,<br><br> L'ajout de temps sur votre liste d'utilisateurs pour le cours "+course.display_name_with_default+" sur le microsite "+microsite+" est maintenant terminé.<br> "+feedback+"<br><br>L'équipe WeUp Learning<br></p></body></html>"
    #     part2 = MIMEText(html.encode('utf-8'), 'html', 'utf-8')
    #     fromaddr = "ne-pas-repondre@themoocagency.com"
    #     toaddr = task_input.get('requester_email')
    #     msg = MIMEMultipart()
    #     msg['From'] = fromaddr
    #     msg['To'] = toaddr+", sysadmin@themoocagency.com"
    #     msg['Subject'] = "Ajout de Temps liste utilisateurs -"+course.display_name_with_default
    #     part = MIMEBase('application', 'octet-stream')
    #     server = smtplib.SMTP('mail3.themoocagency.com', 25)
    #     server.starttls()
    #     server.login('contact', 'waSwv6Eqer89')
    #     msg.attach(part2)
    #     text = msg.as_string()
    #     server.sendmail(fromaddr, toaddr, text)
    #     server.quit()
    #     retour = {
    #         "requester": task_input.get('requester_email'),
    #         "treated": treated,
    #         "failed": failed,
    #         "warning": invalid_mail+not_enrolled+not_registered
    #     }
    #     return retour

        


    def feedbackGenerator(self, context, emails):
        feedback= "<p>"+context+"</p><ul>"
        for email in emails :
            feedback+="<li>"+email+"</li>"
        feedback+="</ul>"
        return feedback





def random_string(length):
    pool = string.ascii_letters + string.digits
    return ''.join(random.choice(pool) for i in range(length))
