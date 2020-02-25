from celery.states import READY_STATES

from atp_task.models import tmaTask
from atp_task.tasks import (
    calculate_grades_xls
)

from atp_task.api_helper import (
    submit_task
)

import logging
log = logging.getLogger(__name__)

#generation grades reports
def submit_calculate_grades_xls(request, course_key, course_id):
    """
    AlreadyRunningError is raised if the course's grades are already being updated.
    """
    task_type = 'grade_course'
    task_class = calculate_grades_xls
    log.warning("send grade reports current email : "+str(request.user.email))
    task_input = {
        "course_id":course_id,
        "email":request.user.email
    }
    task_key = ""

    return submit_task(request, task_type, task_class, course_key, task_input, task_key)

