from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.http import JsonResponse

from edxmako.shortcuts import render_to_response
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from xmodule.modulestore.django import modulestore

from course_progress.models import StudentCourseProgress
from course_progress.helpers import get_overall_progress

import logging
from pprint import pformat
log = logging.getLogger()
