import logging
from functools import partial

from django.conf import settings
from django.utils.translation import ugettext_noop

from celery import task

from atp_task.tasks_helper import (
    run_main_task,
    BaseInstructorTask,
    upload_grades_xls
)

TASK_LOG = logging.getLogger('edx.celery.task')

@task(base=BaseInstructorTask, routing_key=settings.GRADES_DOWNLOAD_ROUTING_KEY)
def calculate_grades_xls(entry_id, xmodule_instance_args):
    """
    Grade a course and push the results to an S3 bucket for download.
    """
    # Translators: This is a past-tense verb that is inserted into task progress messages as {action}.
    action_name = ugettext_noop('graded')
    TASK_LOG.info(
        u"Task: %s, statdashboardTask ID: %s, Task type: %s, Preparing for task execution",
        xmodule_instance_args.get('task_id'), entry_id, action_name
    )

    task_fn = partial(upload_grades_xls, xmodule_instance_args)
    return run_main_task(entry_id, task_fn, action_name)
