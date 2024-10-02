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

from datetime import date

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

@login_required
@require_GET
def generate_pdf(request,course_id):

    #import value for the certificate
    certificate_config = configuration_helpers.get_value('CERTIFICATE_LAYOUT')[course_id]
    base_url = configuration_helpers.get_value('LMS_ROOT_URL')

    # Setup SIZE, IMAGE, FONT and COLOR
    page_width = certificate_config['certificate_width']
    page_height = certificate_config['certificate_height']

    try:
        multi_certificate = certificate_config['multi_certificate']
    except:
        multi_certificate = False

    if multi_certificate :
        image_url = certificate_config['certificate_url'][request.GET.get("certificate")]
    else:
        image_url = certificate_config['certificate_url']

    try:
        font_name = certificate_config['font_name']
        font_url = certificate_config['font_url']
    except:
        font_name = 'OpenSans'
        font_url = "/edx/var/edxapp/staticfiles/fonts/OpenSans/OpenSans-Regular-webfont.ttf"

    pdfmetrics.registerFont(TTFont(font_name, font_url))

    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="certificat.pdf"'

    p = canvas.Canvas(response)
    p.setPageSize((page_width, page_height))
    p.drawImage(image_url, 0, 0, width=page_width, height=page_height)



    # USERNAME
    font_size = certificate_config['font_size']
    p.setFont(font_name, font_size)

    try:
        font_color = certificate_config['font_color']
    except:
        font_color = [0, 0, 0]
    p.setFillColorRGB(font_color[0]/255, font_color[1]/255, font_color[2]/255)

    username = request.user.profile.name
    if username == "":
        username = (request.user.first_name).capitalize() + " " + (request.user.last_name).upper()
        if username == " ":
            try:
                username = json.loads(request.user.profile.custom_field).get('first_name').capitalize() + " " + json.loads(request.user.profile.custom_field).get('last_name').upper()
            except:
                username = 'Missing information'

    name_position_y = certificate_config['name_position_y']
    try:
        name_position_x = certificate_config['name_position_x']
    except:
        name_position_x = False

    if name_position_x :
        p.drawString(name_position_x, name_position_y, username)
    else:
        text_width = stringWidth(username, font_name, font_size)
        centered_text = (page_width - text_width) / 2.0
        p.drawString(centered_text, name_position_y, username)



    # GRADE
    try:
        certificate_grade = certificate_config['grade']
    except:
        certificate_grade = False

    if certificate_grade :

        result = ensure(request, course_id)


        # Accessing JSON data from JsonResponse
        if isinstance(result, JsonResponse):
            # Decode byte content to string and load it as a Python dict
            content = result.content.decode('utf-8')
            data = json.loads(content)
        else:
            log.error("Result is not a JsonResponse object")

        log.info('°°°°°°°°Jsonresponseattribute you can only storefunction')


        text_grade = certificate_grade['syntax_grade']
        text_grade += str(data.get("grade"))

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
    try:
        certificate_date = certificate_config['date']
    except:
        certificate_date = False

    if certificate_date:
        try:
            date_lang = certificate_date['date_lang'].lower()
        except:
            date_lang = 'fr'

        today = date.today()
        string_date_en = today.strftime('%d %B %Y')

        english_months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        french_months = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        portuguese_months = ['de Janeiro de', 'de Fevereiro de', 'de Março de', 'de Abril de', 'de Maio de', 'de Junho de', 'de Julho de', 'de Agosto de', 'de Setembro de', 'de Outubro de', 'de Novembro de', 'de Dezembro de']

        string_date_fr = string_date_en
        string_date_pt = string_date_en

        # Replace English months with French months
        for index, e in enumerate(english_months):
            if string_date_en.find(e) != -1:
                string_date_fr = string_date_en.replace(e, french_months[index])
                string_date_pt = string_date_en.replace(e, portuguese_months[index])

        text_date = certificate_date['syntax_date']

        if str(date_lang) == 'en':
            text_date += string_date_en
        elif str(date_lang) == 'fr':
            text_date += string_date_fr
        elif str(date_lang) == 'pt':
            text_date += string_date_pt
        else:
            text_date += string_date_fr         


        try:
            font_color_date = certificate_date['font_color']
        except:
            font_color_date = [0, 0, 0]
        p.setFillColorRGB(font_color_date[0]/255, font_color_date[1]/255, font_color_date[2]/255) 

        font_size = certificate_date['font_size']
        p.setFont(font_name, font_size)

        date_position_y = certificate_date['position_y']
        try:
            date_position_x = certificate_date['position_x']
        except:
            date_position_x = False

        if date_position_x:
            p.drawString(date_position_x, date_position_y, str(text_date))
        else:
            text_width_date = stringWidth(str(text_date), font_name, font_size)
            centered_date = (page_width - text_width_date) / 2.0
            p.drawString(centered_date, date_position_y, str(text_date))



    # COURSE DURATION
    try:
        course_duration = certificate_config['course_duration']
    except:
        course_duration = False

    if course_duration :
        try :
            enrollment = WulCourseEnrollment.get_enrollment(course_id, request.user)
            timeInSecond = enrollment.global_time_tracking
            syntax_duration = course_duration['syntax_duration']

            def getTimeSpent(syntax):
                hours = timeInSecond // 3600
                seconds = timeInSecond % 3600
                minutes = seconds // 60

                timeSpent = str(syntax) + str(hours) + "h " + str(minutes) + "min"
                return timeSpent

            p.drawString(course_duration['position_x'], course_duration['position_y'], getTimeSpent(syntax_duration))
        except :
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

    # CUSTOM FIELD
    try:
        custom_field_value_2 = certificate_config['custom_field_value_2']
    except:
        custom_field_value_2 = False

    if custom_field_value_2 : 
        try :
            cf = json.loads(request.user.profile.custom_field)
            value = "Matricule : "
            value += cf.get(custom_field_value_2['name'])

            font_size_cf = custom_field_value_2['font_size']
            p.setFont(font_name, font_size_cf)

            font_color = custom_field_value_2['font_color']
            p.setFillColorRGB(font_color[0]/255, font_color[1]/255, font_color[2]/255) 

            p.drawString(custom_field_value_2['position_x'], custom_field_value_2['position_y'], value)
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
