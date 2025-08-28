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


def draw_multiline_text_centered(canvas, text, font_name, font_size, font_color, x, y, line_spacing=1.2):
    lines = text.split('\n')
    line_height = font_size * line_spacing
    start_y = y

    canvas.setFont(font_name, font_size)
    canvas.setFillColorRGB(font_color[0]/255, font_color[1]/255, font_color[2]/255)

    for i, line in enumerate(lines):
        text_width = stringWidth(line, font_name, font_size)
        line_x = x - text_width / 2  # centré horizontalement autour de x
        line_y = start_y - i * line_height
        canvas.drawString(line_x, line_y, line)


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
        user_custom_fields[field_name] = today_str
        user_profile.custom_field = json.dumps(user_custom_fields)
        user_profile.save()
        context = {'is_recorded': False, 'success_date': today_str}

    return context['success_date']


def generate_certificate_pdf(user, course_id, certificate_type=None):

    certificate_config = configuration_helpers.get_value('CERTIFICATE_LAYOUT')[course_id]

    page_width = certificate_config['certificate_width']
    page_height = certificate_config['certificate_height']
    image_url = certificate_config['certificate_url']

    multi_certificate = safe_get(certificate_config, 'multi_certificate', False)
    if multi_certificate and certificate_type:
        image_url = image_url[certificate_type]

    font_name = safe_get(certificate_config, 'font_name', 'OpenSans')
    font_url = safe_get(certificate_config, 'font_url', "/edx/var/edxapp/staticfiles/fonts/OpenSans/OpenSans-Regular-webfont.ttf")
    pdfmetrics.registerFont(TTFont(font_name, font_url))

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="certificat.pdf"'

    p = canvas.Canvas(response)
    p.setPageSize((page_width, page_height))
    p.drawImage(image_url, 0, 0, width=page_width, height=page_height)

    # USERNAME
    username = get_username(user)
    font_size = certificate_config['font_size']
    font_color = safe_get(certificate_config, 'font_color', [0, 0, 0])
    draw_text(p, username, font_name, font_size, font_color,
              safe_get(certificate_config, 'name_position_x'),
              certificate_config['name_position_y'], page_width)

    # GRADE
    certificate_grade = safe_get(certificate_config, 'grade')
    detailed_grade = safe_get(certificate_config, 'detailed_grade')

    if certificate_grade:
        result = certificate(SlashSeparatedCourseKey.from_string(course_id), user).ensure_certificate()
        if isinstance(result, JsonResponse):
            data = json.loads(result.content.decode('utf-8'))

            text_grade = safe_get(certificate_grade, 'syntax_grade')
            grade_g = f"{data.get('grade') * 100:.0f}%"
            text_grade += grade_g

            draw_text(p, text_grade, font_name,
                      certificate_grade['font_size'],
                      safe_get(certificate_grade, 'font_color', [0, 0, 0]),
                      safe_get(certificate_grade, 'position_x'),
                      certificate_grade['position_y'], page_width)

            if detailed_grade:
                text_grade_detailed = safe_get(detailed_grade, 'syntax_detailed_grade')
                detailed_grade_data = data.get("grade_summary").get("section_breakdown")
                for section in detailed_grade_data:
                    text_grade_detailed += section['detail'] + '\n'

                draw_multiline_text_centered(
                    canvas=p,
                    text=text_grade_detailed,
                    font_name=font_name,
                    y=safe_get(detailed_grade, 'position_y', 0),
                    x=safe_get(detailed_grade, 'position_x', 0),
                    font_size=safe_get(detailed_grade, 'font_size'),
                    font_color=safe_get(detailed_grade, 'font_color', [255, 255, 255]),
                    line_spacing=1.2
                )

    # DATE
    certificate_date = safe_get(certificate_config, 'date')
    if certificate_date:
        date_lang = safe_get(certificate_date, 'date_lang', 'fr').lower()
        date_value = check_user_success_date(user, course_id)
        formatted_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        string_date = translate_date(formatted_date, date_lang)

        text_date = certificate_date['syntax_date'] + string_date
        draw_text(p, text_date, font_name,
                  certificate_date['font_size'],
                  safe_get(certificate_date, 'font_color', [0, 0, 0]),
                  safe_get(certificate_date, 'position_x'),
                  certificate_date['position_y'], page_width)

    # COURSE DURATION
    course_duration = safe_get(certificate_config, 'course_duration')
    if course_duration:
        try:
            enrollment = WulCourseEnrollment.get_enrollment(course_id, user)
            hours = enrollment.global_time_tracking // 3600
            minutes = (enrollment.global_time_tracking % 3600) // 60
            text_duration = f"{course_duration['syntax_duration']}{hours}h {minutes}min"
            p.drawString(course_duration['position_x'], course_duration['position_y'], text_duration)
        except:
            log.info('error with course duration for certificate')

    # CUSTOM FIELDS
    for field_key in ['custom_field_value', 'custom_field_value_2']:
        cf_data = safe_get(certificate_config, field_key)
        if cf_data:
            try:
                cf = json.loads(user.profile.custom_field)
                value = cf.get(cf_data['name'], '')
                if field_key == 'custom_field_value_2':
                    value = f"Matricule : {value}"
                draw_text(p, value, font_name,
                          cf_data['font_size'], cf_data['font_color'],
                          cf_data['position_x'], cf_data['position_y'],
                          page_width)
            except:
                log.info(f'error with {field_key} for certificate')

    p.showPage()
    p.save()
    return response


@login_required
@require_GET
def generate_pdf(request, course_id):
    certificate_type = request.GET.get("certificate")
    return generate_certificate_pdf(request.user, course_id, certificate_type)


@login_required
@require_POST
def generate_pdf_for_user(request):
    """ Admin function to generate certificate for a given user (used in dashboard_datavis) """

    user_id = json.loads(request.body).get('userId')
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    certificate_type = json.loads(request.body).get('certificate_type', None)
    return generate_certificate_pdf(user, json.loads(request.body).get('courseId') , certificate_type)


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
