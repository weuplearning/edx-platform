# -*- coding: utf-8 -*-
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import ensure_csrf_cookie
from edxmako.shortcuts import render_to_response
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from opaque_keys.edx.keys import CourseKey
from courseware.courses import get_course_by_id, get_courses
from django.core.exceptions import ObjectDoesNotExist
#updated arbo
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from student.models import CourseEnrollment, UserProfile, LoginFailures
from lms.djangoapps.wul_apps.wul_support_functions import is_course_opened, is_enrollment_opened, wul_verify_access
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from lms.djangoapps.wul_apps.models import WulCourseEnrollment
from lms.djangoapps.wul_apps.wul_methods import WulUserActions
from openedx.core.djangoapps.course_groups.cohorts import get_cohort_by_id, get_cohort_id, get_cohort_names, is_course_cohorted
from lms.djangoapps.wul_apps.ensure_form.utils import ensure_form_factory
from django.utils.translation import ugettext as _
import json
import logging
import os

from collections import OrderedDict

# Related to time sheet pdf generation
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.rl_config import defaultPageSize
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import datetime

log = logging.getLogger()

@require_http_methods(['GET'])
def get_platform_courses(request):
    org_courses = {}
    org = configuration_helpers.get_value('course_org_filter')[0]
    courses_overviews = CourseOverview.objects.filter(org=org).values('id', 'start', 'end', 'enrollment_start', 'enrollment_end', 'display_name', 'course_image_url')

    for course_overview in courses_overviews:
        course_id = course_overview['id']
        course_key = SlashSeparatedCourseKey.from_string(str(course_id))
        course_cohorted = is_course_cohorted(course_key)

        cohorts = {}
        if course_cohorted:
            course = get_course_by_id(course_key)
            cohorts = get_cohort_names(course)

        org_courses[str(course_id)] = {
            'start': course_overview['start'],
            'end': course_overview['end'],
            'enrollment_start': course_overview['enrollment_start'],
            'enrollment_end': course_overview['enrollment_end'],
            'display_name': course_overview['display_name'],
            'cohorts': cohorts,
            'image_url': course_overview['course_image_url'],
        }

    org_courses_sorted_by_name = OrderedDict(sorted(org_courses.items(), key = lambda x: x[1]['display_name'])) 

    response = {
        'org_courses': org_courses_sorted_by_name
    }

    return JsonResponse(response)

@require_http_methods(["GET"])
def get_course_enrollments_count(request):
    count = 0
    org = configuration_helpers.get_value('course_org_filter')[0]
    courses = CourseOverview.objects.filter(org=org)

    for course in courses:
        count += CourseEnrollment.objects.filter(course_id=course.id).count()

    response = {
        'count': count
    }
    return JsonResponse(response)

@require_http_methods(["GET"])
def get_course_enrollments(request, course_id):
    user_enrollments_profiles = {}
    org_courses = {}

    course_key = SlashSeparatedCourseKey.from_string(str(course_id))
    course_overview = CourseOverview.objects.get(id=course_key).__dict__
    course_cohorted = is_course_cohorted(course_key)
    cohorts = {}

    if course_cohorted:
        course = get_course_by_id(course_key)
        cohorts = get_cohort_names(course)

    # CREATE USER ENROLLMENTS AND PROFILE DETAILS DICT
    course_enrollments = CourseEnrollment.objects.filter(course_id=course_overview['id']).values('user__first_name', 'user__email', 'user__is_active', 'user__last_name', 'user__username', 'user__id', 'created', 'is_active')
    for enrollment in course_enrollments:
        user_id = enrollment['user__id']
        username = enrollment['user__username']
        last_name = enrollment['user__last_name']
        first_name = enrollment['user__first_name']
        is_active = enrollment['user__is_active']
        email = enrollment['user__email']
        if user_id not in user_enrollments_profiles.keys():
            user_enrollments_profiles[user_id] = {
                'username': username,
                'id': user_id,
                'last_name': last_name,
                'first_name': first_name,
                'is_active': is_active,
                'email': email
            }
            user_enrollments_profiles[user_id]['enrollments'] = {}
        # ADD ENROLLMENTS TO USER ENROLLMENTS LIST
        if user_enrollments_profiles[user_id] and course_id not in user_enrollments_profiles[user_id]['enrollments'].keys():
            user_enrollments_profiles[user_id]['enrollments'][course_id] = {
                'id': course_id,
                'start_date': course_overview['start'],
                'end_date': course_overview['end'],
                'enrollment_date': enrollment['created'],
                'is_active': enrollment['is_active'],
                'name': course_overview['display_name'],
                'cohort': {}
            }
            # GET USER COHORT, IN CASE THERE IS
            if course_cohorted:
                try:
                    user = User.objects.get(id=user_id)
                    cohort_id = get_cohort_id(user, course_key)
                    if cohort_id:
                        cohort_name = cohorts[cohort_id]
                        user_enrollments_profiles[user_id]['enrollments'][course_id]['cohort'] = {
                            'name':cohort_name,
                            'id':cohort_id
                        }
                except ObjectDoesNotExist:
                    pass
    response = {
        'user_enrollments_profiles': user_enrollments_profiles,
    }
    return JsonResponse(response)

@require_http_methods(["GET"])
def view_enrollments(request):
    user_enrollments_profiles = {}
    org_courses = {}
    org = configuration_helpers.get_value('course_org_filter')[0]
    courses_overviews = CourseOverview.objects.filter(org=org)

    for course_overview in courses_overviews:
        overview_dict = course_overview.__dict__
        course_key = overview_dict['id']
        course_id = str(course_key)
        course_cohorted = is_course_cohorted(course_key)
        image_urls = course_overview.image_urls

        cohorts = {}
        if course_cohorted:
            course = get_course_by_id(overview_dict['id'])
            cohorts = get_cohort_names(course)

        org_courses[course_id] = {
            'start': overview_dict['start'],
            'end': overview_dict['end'],
            'enrollment_start': overview_dict['enrollment_start'],
            'enrollment_end': overview_dict['enrollment_end'],
            'display_name': overview_dict['display_name'],
            'cohorts': cohorts,
            'image_url': image_urls['small'],
        }

        # CREATE USER ENROLLMENTS AND PROFILE DETAILS DICT
        course_enrollments = CourseEnrollment.objects.filter(course_id=overview_dict['id']).values('user__first_name', 'user__email', 'user__is_active', 'user__last_name', 'user__username', 'user__id', 'created', 'is_active')
        for enrollment in course_enrollments:

            user_id = enrollment['user__id']
            username = enrollment['user__username']
            last_name = enrollment['user__last_name']
            first_name = enrollment['user__first_name']
            is_active = enrollment['user__is_active']
            email = enrollment['user__email']

            if user_id not in user_enrollments_profiles.keys():
                user_enrollments_profiles[user_id] = {
                    'username': username,
                    'id': user_id,
                    'last_name': last_name,
                    'first_name': first_name,
                    'is_active': is_active,
                    'email': email
                }

                user_enrollments_profiles[user_id]['enrollments'] = {}

            # ADD ENROLLMENTS TO USER ENROLLMENTS LIST
            if user_enrollments_profiles[user_id] and course_id not in user_enrollments_profiles[user_id]['enrollments'].keys():
                user_enrollments_profiles[user_id]['enrollments'][course_id] = {
                    'id': course_id,
                    'start_date': overview_dict['start'],
                    'end_date': overview_dict['end'],
                    'enrollment_date': enrollment['created'],
                    'is_active': enrollment['is_active'],
                    'name': overview_dict['display_name'],
                    'cohort': {}
                }

                # GET USER COHORT, IN CASE THERE IS
                if course_cohorted:
                    try:
                        user = User.objects.get(id=user_id)
                        cohort_id = get_cohort_id(user, course_key)
                        if cohort_id:
                            cohort_name = org_courses[course_id]['cohorts'][cohort_id]
                            user_enrollments_profiles[user_id]['enrollments'][course_id]['cohort'] = {
                                'name':cohort_name,
                                'id':cohort_id
                            }
                    except ObjectDoesNotExist:
                        pass


    response = {
        'user_enrollments_profiles': user_enrollments_profiles,
        'org_courses': org_courses
    }

    return JsonResponse(response)

@login_required
def wul_dashboard_view(request):
    if not wul_verify_access(request.user).has_dashboard_access():
        return HttpResponseForbidden
    context = {}

    microsite = configuration_helpers.get_value('domain_prefix')
    translations = json.load(open("/edx/var/edxapp/media/wul_apps/dashboard/trads/dashboard_trads.json"))
    endpoints = json.load(open("/edx/var/edxapp/media/wul_apps/dashboard/endpoints/wul_endpoints.json"))
    user_language = request.LANGUAGE_CODE if request.LANGUAGE_CODE in translations.keys() else 'en'

    primary_color = configuration_helpers.get_value('primary_color', '#333333')
    secondary_color = "#388E3C"
    error_color = "#f44336"
    dashboard_config = configuration_helpers.get_value('WUL_DASHBOARD_CONFIG')

    colors = {
        'primary_color': primary_color,
        'secondary_color': secondary_color,
        'error': error_color,
    }

    context['colors'] = colors
    context['translations'] = translations[user_language]
    context['dashboard_config'] = dashboard_config
    context['user_email'] = str(request.user.email)
    context['endpoints'] = endpoints
    return render_to_response('wul_apps/dashboard.html', {"props": context})

@login_required
def get_student_profile(request, user_email):
    log.info('test')
    if not wul_verify_access(request.user).has_dashboard_access():
        return HttpResponseForbidden
    context={}

    if User.objects.filter(email=user_email).exists():
        user = User.objects.get(email=user_email)
        userprofile = UserProfile.objects.get(user=user)
        username = user.username

        try :
            custom_field = json.loads(user.profile.custom_field)
            first_name = custom_field['first_name']
            last_name = custom_field['last_name']
        except :
            last_name = 'Undefined'
            first_name = 'Undefined'

        #Get certificate form extra)
        form_factory = ensure_form_factory()

        # db = 'ensure_form'
        # collection = 'certificate_form'
        # form_factory.connect(db=db,collection=collection)
        # form_factory.get_user_form_extra(user)
        # log.info(form_factory.get_user_form_extra(user))
        # form_factory.get_user_certificate_form_extra(user)
        # certificate_form_extra = form_factory.user_certificate_form_extra
        certificate_form_extra = {}

        #Get courses enrollments
        microsite_courses = get_courses(user=user, org=configuration_helpers.get_value('course_org_filter')[0])
        custom_field_editor_unlocked = configuration_helpers.get_value('WUL_ENABLE_CUSTOM_FIELD_EDITOR', False)
        field_configs = configuration_helpers.get_value('FORM_EXTRA',{})
        certificate_configs = configuration_helpers.get_value('CERTIFICATE_FORM_EXTRA',{})

        user_ms_course_list = {}
        
        for course in microsite_courses :
            course_key = SlashSeparatedCourseKey.from_string(str(course.id))
            _course=get_course_by_id(course_key)
            enrollment=CourseEnrollment.objects.filter(user=user, course_id=_course.id)

            if enrollment.exists() and CourseEnrollment.objects.filter(user=user,course_id=_course.id, is_active=1).exists():
                # create method has been deprecated
                #grade = CourseGradeFactory().read(user, _course) # grade desactivation : takes too long to get this stuff
                grade = CourseGradeFactory().read(user, _course) # grade desactivation : takes too long to get this stuff
                passed = grade.passed
                enrolled_to_enrollment = True
                enrollment_grades='/courses/'+str(_course.id)+'/progress/'+str(user.id)
                start_date=True
            else:
                enrolled_to_enrollment = False
                enrollment_grades = 'n/a'
                start_date = False
                passed = False

            user_ms_course_list[str(course.id)]={
                'id': str(course.id),
                'start_date': start_date,
                'course_name': _course.display_name_with_default,
                'course_grades': enrollment_grades,
                'opened_enrollments': is_enrollment_opened(course),
                'opened_course': is_course_opened(course),
                'on_invitation': _course.invitation_only,
                'passed': passed, 
                'enrolled_to_enrollment': enrolled_to_enrollment,
            }

            # Get the time tracking for the course
            try:
                wul_course_enrollment = WulCourseEnrollment.objects.get(course_enrollment_edx__user=user, course_enrollment_edx__course_id=course_key)
                global_time_tracking = wul_course_enrollment.global_time_tracking
                user_ms_course_list[str(course.id)]['time_tracking'] = global_time_tracking
            except:
                pass

        #User dates
        if user.last_login is not None:
            last_login=user.last_login.strftime("%d-%b-%Y %H:%M:%S")
        else :
            last_login=_('User has not logged in yet')

        sorted_user_ms_course_list = OrderedDict(sorted(user_ms_course_list.items(), key = lambda x: x[1]['course_name'])) 

        log.info(custom_field)

        context={
            'email':str(user_email),
            'id':str(user.id),
            'inscription':user.date_joined.strftime("%d-%b-%Y %H:%M:%S"),
            'last_login':last_login,
            'first_name':first_name,
            'last_name':last_name,
            'username':username,
            'org':configuration_helpers.get_value('SITE_NAME'),
            'enrollments': sorted_user_ms_course_list,
            'custom_field':custom_field,
            'certificate_form_extra': certificate_form_extra,
            'active':user.is_active,
            'is_locked':LoginFailures.is_user_locked_out(user),
            'field_configs':field_configs,
            'certificate_configs':certificate_configs,
            'custom_field_editor_unlocked':custom_field_editor_unlocked,
        }

    else :
        return JsonResponse(context, status=500)

    return JsonResponse(context, status=200)

@login_required
def get_password_link(request):
    user_email = request.body
    password_link= WulUserActions(user_email).generate_password_link()
    response ={'link':str(password_link)}
    return JsonResponse(response)

@login_required
def unlock_account(request):
    user_email = request.body
    if WulUserActions(user_email).unlock_user_account() :
        response={'success': 'User login failure was reset'}
    else :
        response={'error':'LoginFailure object doesn\'t exists'}
    return JsonResponse(response)

@require_http_methods(["GET"])
@login_required
def get_register_fields(request):
    register_fields = [
        {
            "name":"email",
            "required":True,
            "label":"Email"
        }
    ]

    microsite_register_fields = configuration_helpers.get_value("FORM_EXTRA")

    if microsite_register_fields is not None:
        for field in microsite_register_fields:
            register_fields.append(field)

    response = {'register_fields': register_fields}

    return JsonResponse(response)

@require_http_methods(["GET"])
@login_required
def generate_student_time_sheet(request, course_id, user_email):
    course_key = SlashSeparatedCourseKey.from_string(str(course_id))
    course = get_course_by_id(course_key)
    user = User.objects.get(email=user_email)
    custom_field = json.loads(UserProfile.objects.get(user=user).custom_field)
    wul_course_enrollment = WulCourseEnrollment.objects.get(course_enrollment_edx__user=user, course_enrollment_edx__course_id=course_key)
    global_time_tracking = wul_course_enrollment.global_time_tracking

    page_width = 600
    page_height = 1200
    line_height = 20
    font_size = 12
    # font_name = 'OpenSans'
    # font_url = '/edx/var/edxapp/media/fonts/OpenSans-Regular.ttf'
    image_up_left_url = '/edx/var/edxapp/media/microsite/e-formation-artisanat/fiche_suivi/cma_logo.png'
    image_down_middle_url = '/edx/var/edxapp/media/microsite/e-formation-artisanat/fiche_suivi/parcours_logo.jpg'


    font_variants = ("OpenSans-Regular","OpenSans-Bold")
    folder = '/edx/var/edxapp/media/fonts/'
    for variant in font_variants:
        pdfmetrics.registerFont(TTFont(variant, os.path.join(folder, variant+'.ttf')))

    # pdfmetrics.registerFont(TTFont(font_name,font_url))

    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="fiche-de-présence.pdf"'

    p = canvas.Canvas(response)
    p.setPageSize((page_width,page_height))
    # p.setFont(font_name, font_size)
    p.drawImage(image_up_left_url, 40, 1060, width=100,height=100, mask='auto')


    x = 430
    y = 1150
    p.setFont("OpenSans-Bold", font_size)
    p.drawString(x, y, 'Fiche de suivi')
    y -= line_height 
    x -= 34
    p.setFont("OpenSans-Regular", font_size)
    p.drawString(x, y, 'Editée le: {}'.format(datetime.datetime.today().strftime('%d/%m/%Y')))
    y -= line_height * 7
    x = 50

    p.setFont("OpenSans-Bold", font_size)
    p.drawString(x, y, 'Formation :')
    y -= line_height 
    p.setFont("OpenSans-Regular", font_size)
    p.drawString(x, y, course.display_name_with_default)
    y -= line_height
    p.setFont("OpenSans-Bold", font_size) 
    p.drawString(x, y, 'Nom, Prénom du stagiaire :')
    y -= line_height
    p.setFont("OpenSans-Regular", font_size)
    p.drawString(x, y, custom_field['first_name'] + ","  + custom_field['last_name'])
    y -= line_height
    p.setFont("OpenSans-Bold", font_size)
    p.drawString(x, y, 'Temps total passé :')
    y -= line_height
    p.setFont("OpenSans-Regular", font_size)
    p.drawString(x, y, str(datetime.timedelta(seconds=global_time_tracking)))
    y -= line_height * 3


    try:
        # DETAILED TIME TRACKING DISPLAY
        detailed_time_tracking = json.loads(wul_course_enrollment.detailed_time_tracking)
        chapters = course.get_children()
        modules_total_time = sum(detailed_time_tracking[chapter.url_name] for chapter in chapters if chapter.url_name in detailed_time_tracking.keys())


        time_delta = global_time_tracking - modules_total_time
        delta_module_split = time_delta / len(chapters)
        log.info(delta_module_split)
        p.setFont("OpenSans-Bold", font_size)
        p.drawString(x, y, 'Détail par module:')
        y -= line_height
        
        for chapter in chapters:
            p.setFont("OpenSans-Bold", 10)
            if chapter.url_name in detailed_time_tracking.keys():
                p.drawString(x, y, chapter.display_name_with_default_escaped)
                y -= line_height
                p.setFont("OpenSans-Regular", 10)
                p.drawString(x, y, str(datetime.timedelta(seconds=(detailed_time_tracking[chapter.url_name]) + delta_module_split)))
            else:
                p.drawString(x, y, chapter.display_name_with_default_escaped)
                y -= line_height 
                p.setFont("OpenSans-Regular", 10)
                p.drawString(x, y, str(datetime.timedelta(seconds=delta_module_split)))
            y -= line_height * 1.2
        y -= line_height * 2
    except:
        pass

    try:
        # DAILY TIME TRACKING DISPLAY
        daily_time_tracking = json.loads(wul_course_enrollment.daily_time_tracking)
        if daily_time_tracking.items():
            p.setFont("OpenSans-Bold", font_size)
            p.drawString(x, y, 'Détail par jour:')
            y -= line_height
            sorted_dates = daily_time_tracking.items()
            sorted_dates.sort(key=lambda date: datetime.datetime.strptime(date[0], "%d-%m-%Y"))
            daily_total_time = sum(date[1] for date in sorted_dates)

            if global_time_tracking > daily_total_time:
                p.setFont("OpenSans-Regular", 10)
                time_delta = global_time_tracking - daily_total_time
                p.drawString(x, y, 'Avant le {}: {}'.format(sorted_dates[0][0].replace('-', '/'), str(datetime.timedelta(seconds=time_delta))))
                y -= line_height

            for date in sorted_dates:
                p.drawString(x, y, '{} : {}'.format(date[0].replace('-', '/'), str(datetime.timedelta(seconds=date[1]))))
                y -= line_height

    except:
        pass

    y_display_image = y - 100

    p.drawImage(image_down_middle_url, 200, y_display_image, width=200,height=100)
    p.showPage()
    p.save()
    return response

#breakline  si nom de cours trop long
#change page quand arrive à la fin   if y < image_size => nouvelle page + image

# def tma_create_user_from_csv(request, course_id):
#     log.info("*****************TEST***************")