import logging
import json


from django.db import IntegrityError, transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST,require_GET,require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control

from opaque_keys.edx.locations import SlashSeparatedCourseKey
from opaque_keys.edx.locator import CourseLocator

from atp_task.course_grade import course_grade

from django.views.decorators.cache import cache_control
from django.db import IntegrityError, transaction
from lms.djangoapps.instructor_task.api_helper import AlreadyRunningError
from django.utils.translation import ugettext as _

from lms.djangoapps.atp_task.api import submit_calculate_grades_xls

from util.json_request import JsonResponse

from atp_task.course_grade import course_grade

log = logging.getLogger(__name__)

#TASK EXEMPLE
@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
#@require_level('staff')
def calculate_grades_xls(request,course_id):

    course_key = CourseLocator.from_string(course_id)
    try:
        submit_calculate_grades_xls(request, course_key, course_id)
        success_status = _("The grade report is being created."
                           " To view the status of the report, see Pending Tasks below.")
        return JsonResponse({"status": success_status})
    except AlreadyRunningError:
        already_running_status = _("The grade report is currently being created."
                                   " To view the status of the report, see Pending Tasks below."
                                   " You will be able to download the report when it is complete.")
        return JsonResponse({"status": already_running_status})

def get_xls(request,course_id):

	context = course_grade(course_id).get_xls()

	return JsonResponse(context)


def download_xls(request,course_id,filename):

	return course_grade(course_id).download_xls(filename)
