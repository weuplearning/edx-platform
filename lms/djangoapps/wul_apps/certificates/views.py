'''
/edx/app/edxapp/edx-platform/lms/djangoapps/wul_apps/certificates
'''
# -*- coding: utf-8 -*-
from lms.djangoapps.wul_apps.certificates.certificate import certificate
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpRequest
from django.contrib.auth.decorators import login_required
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from student.models import User, UserProfile
import json

from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.rl_config import defaultPageSize
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

from datetime import date, datetime

from lms.djangoapps.wul_apps.models import WulCourseEnrollment
import requests

import logging
log = logging.getLogger(__name__)


@login_required
@require_GET
def ensure(request,course_id):
    course_key = SlashSeparatedCourseKey.from_string(course_id)
    return certificate(course_key,request.user).ensure_certificate()

@login_required
@require_GET
def ensure_csv(request,course_id):
    course_key = SlashSeparatedCourseKey.from_string(course_id)
    return certificate(course_key,request.user).grade_csv_and_user()

@login_required
@require_GET
def render(request,course_id):
    course_key = SlashSeparatedCourseKey.from_string(course_id)
    return certificate(course_key,request.user).view(request)

@login_required
@require_GET
def ensure_partial(request,course_id):
    course_key = SlashSeparatedCourseKey.from_string(course_id)
    return certificate(course_key,request.user).ensure_partial_certificate()

@login_required
@require_GET
def render_partial(request,course_id):
    course_key = SlashSeparatedCourseKey.from_string(course_id)
    return certificate(course_key,request.user).view_partial_certificate(request)


def safe_get(config, key, default=None):
    try:
        return config[key]
    except (KeyError, TypeError):
        return default


def draw_text(p, text, font_name, font_size, color, x, y, page_width):
    p.setFont(font_name, font_size)
    p.setFillColorRGB(color[0]/255, color[1]/255, color[2]/255)
    if x:
        p.drawString(x, y, text)
    else:
        text_width = stringWidth(text, font_name, font_size)
        centered_x = (page_width - text_width) / 2.0
        p.drawString(centered_x, y, text)


def get_username(user):
    name = user.profile.name
    if name:
        return name
    full_name = f"{user.first_name.capitalize()} {user.last_name.upper()}"
    if full_name.strip():
        return full_name
    try:
        cf = json.loads(user.profile.custom_field)
        return f"{cf.get('first_name', '').capitalize()} {cf.get('last_name', '').upper()}"
    except:
        return "Missing information"


def translate_date(today, lang):
    string_date = today.strftime('%d %B %Y')
    months = {
        'en': [],
        'fr': ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'],
        'pt': ['de Janeiro de', 'de Fevereiro de', 'de Março de', 'de Abril de', 'de Maio de', 'de Junho de', 'de Julho de', 'de Agosto de', 'de Setembro de', 'de Outubro de', 'de Novembro de', 'de Dezembro de'],
    }
    english_months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    for i, month in enumerate(english_months):
        if month in string_date:
            if lang in months and months[lang]:
                return string_date.replace(month, months[lang][i])
    return string_date


def check_user_success_date(user, course_id):
    """ Check if the user success date already exists, if not create it """

    today_str = date.today().isoformat() 
    try:
        user_profile = UserProfile.objects.get(user=user)
        user_custom_fields = json.loads(user_profile.custom_field)
    except:
        return today_str

    field_name = 'success_date_' + course_id
    if field_name in user_custom_fields and user_custom_fields[field_name] != '':
        context = {'is_recorded': True, 'success_date': user_custom_fields[field_name]}
    else:
        # The first time, add the success date to the custom field
        user_custom_fields[field_name] = today_str
        user_profile.custom_field = json.dumps(user_custom_fields)
        user_profile.save()
        context = {'is_recorded': False, 'success_date': today_str}

    return context['success_date']


@login_required
@require_GET
def generate_pdf(request,course_id):

    #import value for the certificate
    certificate_config = configuration_helpers.get_value('CERTIFICATE_LAYOUT')[course_id]
    base_url = configuration_helpers.get_value('LMS_ROOT_URL')

    # Setup SIZE, IMAGE, FONT and COLOR
    page_width = certificate_config['certificate_width']
    page_height = certificate_config['certificate_height']
    image_url = certificate_config['certificate_url']

    multi_certificate = safe_get(certificate_config, 'multi_certificate', False)
    if multi_certificate :
        image_url = certificate_config['certificate_url'][request.GET.get("certificate")]

    font_name = safe_get(certificate_config, 'font_name', 'OpenSans')
    font_url = safe_get(certificate_config, 'font_url', "/edx/var/edxapp/staticfiles/fonts/OpenSans/OpenSans-Regular-webfont.ttf")
    pdfmetrics.registerFont(TTFont(font_name, font_url))

    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="certificat.pdf"'

    p = canvas.Canvas(response)
    p.setPageSize((page_width, page_height))
    p.drawImage(image_url, 0, 0, width=page_width, height=page_height)



    # USERNAME
    username = get_username(request.user)
    font_size = certificate_config['font_size']
    font_color = safe_get(certificate_config, 'font_color', [0, 0, 0])
    draw_text(p, username, font_name, font_size, font_color, safe_get(certificate_config, 'name_position_x'), certificate_config['name_position_y'], page_width)




    # GRADE
    try:
        certificate_grade = certificate_config['grade']
    except:
        certificate_grade = False

    if certificate_grade :
        result = ensure_csv(request, course_id)

        # Accessing JSON data from JsonResponse
        if isinstance(result, JsonResponse):
            # Decode byte content to string and load it as a Python dict
            content = result.content.decode('utf-8')
            data = json.loads(content)
        else:
            log.error("Result is not a JsonResponse object")

        try :
            text_grade = certificate_grade['syntax_grade']
        except:
            text_grade = str(round(data.get("grade"),2)) + '%'

        try :
            text_grade = text_grade.replace('{note}',str(round(data.get('global_grade')*100, 2)))
        except :
            text_grade = text_grade.replace('{note}',str(round(data.get("grade")*100, 2)))


        log.info("text_grade")
        log.info(text_grade)
        try:
            font_color_grade = certificate_grade['font_color']
        except:
            font_color_grade = [0, 0, 0]
        p.setFillColorRGB(font_color_grade[0]/255, font_color_grade[1]/255, font_color_grade[2]/255) 

        font_size = certificate_grade['font_size']
        p.setFont(font_name, font_size)

        grade_position_y = certificate_grade['position_y']
        try:
            grade_position_x = certificate_grade['position_x']
        except:
            grade_position_x = False

        if grade_position_x:
            p.drawString(grade_position_x, grade_position_y, str(text_grade))
        else:
            text_width_grade = stringWidth(str(text_grade), font_name, font_size)
            centered_grade = (page_width - text_width_grade) / 2.0
            p.drawString(centered_grade, grade_position_y, str(text_grade))




    # CERTIFICATE DATE
    certificate_date = safe_get(certificate_config, 'date')
    if certificate_date:
        date_lang = safe_get(certificate_date, 'date_lang', 'fr').lower()

        date_value = check_user_success_date(request.user, course_id)
        formatted_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        string_date = translate_date(formatted_date, date_lang)

        text_date = certificate_date['syntax_date'] + string_date
        draw_text(p, text_date, font_name, certificate_date['font_size'], safe_get(certificate_date, 'font_color', [0, 0, 0]), safe_get(certificate_date, 'position_x'), certificate_date['position_y'], page_width)




    # COURSE DURATION
    course_duration = safe_get(certificate_config, 'course_duration')
    if course_duration :
        try:
            enrollment = WulCourseEnrollment.get_enrollment(course_id, request.user)
            hours = enrollment.global_time_tracking // 3600
            minutes = (enrollment.global_time_tracking % 3600) // 60
            text_duration = f"{course_duration['syntax_duration']}{hours}h {minutes}min"
            p.drawString(course_duration['position_x'], course_duration['position_y'], text_duration)
        except:
            log.info('error with course duration for certificate')



    # CUSTOM FIELD
    try:
        custom_field_value = certificate_config['custom_field_value']
    except:
        custom_field_value = False

    if custom_field_value : 
        try :
            cf = json.loads(request.user.profile.custom_field)
            value = cf.get(custom_field_value['name'])

            font_size_cf = custom_field_value['font_size']
            p.setFont(font_name, font_size_cf)

            font_color = custom_field_value['font_color']
            p.setFillColorRGB(font_color[0]/255, font_color[1]/255, font_color[2]/255) 

            p.drawString(custom_field_value['position_x'], custom_field_value['position_y'], value)
        except:
            log.info('error with custom fields for certificate')



    # Close the PDF object cleanly, and we're done.
    p.showPage()
    p.save()

    return response


@login_required
@require_GET
def check_name(request):
    # NOT YET ACTIVATE FOR KOA
    # NOT YET ACTIVATE FOR KOA
    # PROBABLY NOT NEEDED ANYMORE
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        user_custom_fields = json.loads(user_profile.custom_field)
    except:
        user_custom_fields = {}

    if 'last_name' in user_custom_fields and 'first_name' in user_custom_fields and user_custom_fields['last_name'] !='' and user_custom_fields['first_name'] !='':
        context = {'is_recorded': True}
    else:
        context = {'is_recorded': False}

    return JsonResponse(context)


@login_required
@require_POST
def record_name(request):
    first_name=request.POST.get('first_name')
    last_name=request.POST.get('last_name')
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        try:
            user_custom_fields = json.loads(user_profile.custom_field)
        except:
            user_custom_fields={}
        user_custom_fields['last_name']=last_name
        user_custom_fields['first_name']=first_name
        user_profile.custom_field=json.dumps(user_custom_fields)
        user_profile.save()
        context = {'name_recorded': True}
    except:
        context = {'name_recorded': False}
    return JsonResponse(context)
