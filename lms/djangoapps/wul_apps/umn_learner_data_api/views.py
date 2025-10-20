'''
lms/djangoapps/wul_apps/umn_secured_data_access/views.py
'''

import os
from io import BytesIO
import json
import time

from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from django.http import JsonResponse
from lms.djangoapps.instructor_task.api_helper import AlreadyRunningError
# from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from django.utils.translation import ugettext as _



from opaque_keys.edx.locator import CourseLocator
from common.djangoapps.student.models import CourseEnrollment
from courseware.courses import get_course_by_id
from lms.djangoapps.grades.context import grading_context_for_course
from lms.djangoapps.courseware.user_state_client import DjangoXBlockUserStateClient

from openpyxl import Workbook

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import logging
log = logging.getLogger()



# views.py
import base64
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View




from lms.djangoapps.wul_apps.umn_learner_data_api.api_config import credentials 

# example :
# credentials = {
#     "user": "password"
# }

AUTHORIZED_USERS = credentials

@method_decorator(csrf_exempt, name="dispatch")
class PowerBIAuthView(View):
    """Testing Auth access."""
    def get(self, request):
        auth_header = request.headers.get("Authorization")
        log.info('testing auth')
        if not auth_header or not auth_header.startswith("Basic "):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        try:
            # Decode the credentials
            b64_credentials = auth_header.split(" ")[1]
            decoded = base64.b64decode(b64_credentials).decode("utf-8")
            username, password = decoded.split(":", 1)
        except Exception:
            return JsonResponse({"error": "Invalid credentials format"}, status=400)

        # Validate user
        if AUTHORIZED_USERS.get(username) != password:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        
        with open("/edx/app/edxapp/edx-platform/lms/djangoapps/wul_apps/umn_learner_data_api/data.json", "r") as datafile:
            UMN_DATA = json.load(datafile)

        return JsonResponse(UMN_DATA, safe=False)


