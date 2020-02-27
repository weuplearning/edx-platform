from .completion import Completion
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import JsonResponse
import logging

log = logging.getLogger()


@login_required
@require_GET
def get_course_completion(request,course_id):
    return JsonResponse(Completion(request).get_course_completion(course_id))

@login_required
@require_GET
def get_unit_completion(request, *args, **kwargs):
    course_id = kwargs.get('course_id')
    unit_id = kwargs.get('usage_key_string')
    return JsonResponse(Completion(request).get_unit_completion(course_id, unit_id))