import logging
import urllib

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.urls import reverse
from django.db import transaction
from django.conf import settings
from django.shortcuts import redirect

from xmodule.modulestore.django import modulestore
from courseware.courses import get_course_by_id
from courseware.access import has_access
from courseware.access_response import StartDateError
from util.date_utils import strftime_localized
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from util.views import ensure_valid_course_key
from edxmako.shortcuts import render_to_response
from student.models import CourseEnrollment

from atp_module.ressource import render_accordion, get_final_score
from course_progress.helpers import get_overall_progress

log = logging.getLogger("edx.courseware")

@transaction.non_atomic_requests
#@ensure_csrf_cookie
@ensure_valid_course_key
@login_required
def course_welcome(request, course_id):
    """
    Display the course's welcome.html, or 404 if there is no such course.

    Assumes the course_id is in a valid format.
    """
    course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
    with modulestore().bulk_operations(course_key):
        course = get_course_by_id(course_key, depth=2)
        access_response = has_access(request.user, 'load', course, course_key)

        is_enrolled = CourseEnrollment.is_enrolled(request.user, course_key)
        if not is_enrolled:
            return redirect(reverse('about_course', args=[unicode(course_key)]))

        if not access_response:

            # The user doesn't have access to the course. If they're
            # denied permission due to the course not being live yet,
            # redirect to the dashboard page.
            if isinstance(access_response, StartDateError):
                start_date = strftime_localized(course.start, 'SHORT_DATE')
                params = urllib.urlencode({'notlive': start_date})
                return redirect('{0}?{1}'.format(reverse('dashboard'), params))
            # Otherwise, give a 404 to avoid leaking info about access
            # control.
            raise Http404("Course not found.")


    context = {
        'request': request,
        'course_id': course_key.to_deprecated_string(),
        'course': course
    }

    # Get the final score for the student
    score = get_final_score(request, course)
    # Set badge if the score is greater or equal to 60%
    # update context
    context.update({
        'score': score,
        'overall_progress': get_overall_progress(request.user.id, course_key),
        'accordion': render_accordion(request, course)
    })
    # set template to purple
    return context
