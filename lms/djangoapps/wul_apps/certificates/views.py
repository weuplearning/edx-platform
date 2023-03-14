'''
/edx/app/edxapp/edx-platform/lms/djangoapps/wul_apps/certificates
'''
# -*- coding: utf-8 -*-
from lms.djangoapps.wul_apps.certificates.certificate import certificate
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpRequest
from django.contrib.auth.decorators import login_required
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from django.views.decorators.http import require_POST,require_GET,require_http_methods
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from student.models import User
from student.models import UserProfile
import json
import logging
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.rl_config import defaultPageSize
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from PyPDF2 import PdfFileWriter, PdfFileReader
from datetime import date

from lms.djangoapps.wul_apps.models import WulCourseEnrollment

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

    # Setup SIZE, IMAGE, FONT and COLOR
    page_width = certificate_config['certificate_width']
    page_height = certificate_config['certificate_height']

    try:
        multi_certificate = certificate_config['multi_certificate']
    except:
        multi_certificate = None
        
    if multi_certificate is not None:
        image_url = certificate_config['certificate_url'][request.GET.get("certificate")]
    else:
        image_url = certificate_config['certificate_url']

    try:
        font_name = certificate_config['font_name']
        font_url = certificate_config['font_url']
    except:
        font_name = 'OpenSans'
        font_url = "/edx/var/edxapp/staticfiles/fonts/OpenSans/OpenSans-Regular-webfont.ttf"
    #import custom font
    pdfmetrics.registerFont(TTFont(font_name,font_url))
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="certificat.pdf"'

    # Create the PDF object, using the response object as its "file."
    p = canvas.Canvas(response)
    # Change the page size
    p.setPageSize((page_width,page_height))
    # Draw the image at x, y. I positioned the x,y to be where i like here
    p.drawImage(image_url, 0, 0, width=page_width,height=page_height)
    # Draw things on the PDF. Here's where the PDF generation happens.



    # USER NAME
    name_position_x = certificate_config['name_position_x']
    font_size = certificate_config['font_size']
    p.setFont(font_name, font_size)
    try:
        font_color = certificate_config['font_color']
    except:
        font_color = [0, 0, 0]

    p.setFillColorRGB(font_color[0]/255, font_color[1]/255, font_color[2]/255)



    user_name = (request.user.first_name).capitalize() + " " + (request.user.last_name).upper()
    if user_name == " ":
        user_name = json.loads(request.user.profile.custom_field).get('first_name').capitalize() + " " + json.loads(request.user.profile.custom_field).get('last_name').upper()
        if user_name == " ":
                user_name = request.user.profile.name
                if user_name == "":
                    user_name = 'Missing information'

    try:
        name_position_y = certificate_config['name_position_y']
    except:
        name_position_y = False
    
    if name_position_y :
        p.drawString(name_position_y, name_position_x, user_name)
    else:
        # Center the text horizontally

        text_width = stringWidth(user_name, font_name, font_size)
        centered_text = (page_width - text_width) / 2.0
        p.drawString(centered_text, name_position_x, user_name)



    # CERTIFICATE DATE
    try:
        certificate_date = certificate_config['date']
    except:
        certificate_date = False
    try:
        date_lang = certificate_config['date_lang'].lower()
    except:
        date_lang = 'fr'

    if certificate_date :
        today = date.today()
        string_date_en = today.strftime('%d %B %Y')

        english_months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        french_months = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        for index, e in enumerate(english_months):
            if string_date_en.find(e) != -1 :
                string_date_fr = string_date_en.replace(e, french_months[index])

        # Switch to multilingue
        try:
            if date_lang == 'en' :
                certificate_date += string_date_en
            else:
                certificate_date += string_date_fr
        except:
            pass
        # COLOR
        
        try:
            font_color_2 = certificate_config['font_color_2']
        except:
            font_color_2 = [0, 0, 0]
        p.setFillColorRGB(font_color_2[0]/255, font_color_2[1]/255, font_color_2[2]/255) 



        # Write date at x and y with font_size_2
        date_position_x = certificate_config['date_position_x']
        try:
            date_position_y = certificate_config['date_position_y']
        except:
            date_position_y = False
        font_size_2 = certificate_config['font_size_2']

        p.setFont(font_name, font_size_2)
        if date_position_y:
            p.drawString(date_position_y, date_position_x , str(certificate_date))
        else:
            text_width_date = stringWidth(certificate_date, font_name, font_size_2)
            centered_date = (page_width - text_width_date) / 2.0
            p.drawString(centered_date, date_position_x , str(certificate_date))




    # COURSE DURATION

    try:
        course_duration = certificate_config['course_duration']
    except:
        course_duration = False
    
    if course_duration :

        enrollment = WulCourseEnrollment.get_enrollment(course_id, request.user)

        timeInSecond = enrollment.global_time_tracking

        def getTimeSpent():
            hours = timeInSecond // 3600
            seconds = timeInSecond % 3600
            minutes = seconds // 60

            timeSpent = "Temps passé sur le cours : "+str(hours)+"h "+str(minutes)+"min"

            return timeSpent

        try:
            course_duration_position_x = certificate_config['course_duration_position_x']
        except:
            course_duration_position_x = False

        try:
            course_duration_position_y = certificate_config['course_duration_position_y']
        except:
            course_duration_position_y = False

        if course_duration_position_x or course_duration_position_y:
            p.drawString(course_duration_position_x,course_duration_position_y,getTimeSpent())





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
