"""
Course progress helpers
"""
import json
from collections import OrderedDict

from django.db import connection
from xmodule.modulestore.django import modulestore
from course_api.blocks.api import get_blocks

from opaque_keys.edx.locations import BlockUsageLocator
from django.contrib.auth.models import User
from completion.api.v1.views import SubsectionCompletionView
import logging

log = logging.getLogger()
# Valid components for tracking

def get_overall_progress(username,request, course_key, subsection_id):
    """
    Get the course completion percent
    for the given student Id in given course.
    """
    log.info(request.user.username)
    overall_progress = 0
    completiontest = SubsectionCompletionView().get(request,request.user.username,course_key,subsection_id)
    log.info(completionresult)
    completionresult = completiontest.get_completion()
    return completionresult
