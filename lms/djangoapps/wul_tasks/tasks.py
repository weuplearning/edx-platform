# -*- coding: utf-8 -*-
import sys
import importlib
importlib.reload(sys)

import logging
from functools import partial

from django.conf import settings
from django.utils.translation import ugettext_noop

from celery import task

from lms.djangoapps.wul_tasks.tasks_helper import (
    run_main_task,
    BaseInstructorTask,
    upload_grades_xls,
    users_generation,
    # sbo_xls_generation,
    # helper_generate_users_from_csv,
    # helper_add_extra_time
)


log = logging.getLogger(__name__)
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

@task(base=BaseInstructorTask, routing_key=settings.GRADES_DOWNLOAD_ROUTING_KEY)
def generate_users(entry_id, xmodule_instance_args):



    """
    Grade a course and push the results to an S3 bucket for download.
    """
    # Translators: This is a past-tense verb that is inserted into task progress messages as {action}.
    action_name = ugettext_noop('graded')
    TASK_LOG.info(
        u"Task: %s, statdashboardTask ID: %s, Task type: %s, Preparing for task execution",
        xmodule_instance_args.get('task_id'), entry_id, action_name
    )

    task_fn = partial(users_generation, xmodule_instance_args)

    return run_main_task(entry_id, task_fn, action_name)

# @task(base=BaseInstructorTask, routing_key=settings.GRADES_DOWNLOAD_ROUTING_KEY)
# def sbo_user(entry_id, xmodule_instance_args):

#     # Translators: This is a past-tense verb that is inserted into task progress messages as {action}.
#     action_name = ugettext_noop('sbo_user')
#     TASK_LOG.info(
#         u"Task: %s, statdashboardTask ID: %s, Task type: %s, Preparing for task execution",
#         xmodule_instance_args.get('task_id'), entry_id, action_name
#     )

#     task_fn = partial(sbo_xls_generation, xmodule_instance_args)
#     return run_main_task(entry_id, task_fn, action_name)


# #DASHBOARD V2 TASKS
# @task(base=BaseInstructorTask, routing_key=settings.GRADES_DOWNLOAD_ROUTING_KEY)
# def task_generate_users_from_csv(entry_id, xmodule_instance_args):
#     # Translators: This is a past-tense verb that is inserted into task progress messages as {action}.
#     action_name = ugettext_noop('creating_csv_users')
#     TASK_LOG.info(
#         u"Task: %s, statdashboardTask ID: %s, Task type: %s, Preparing for task execution",
#         xmodule_instance_args.get('task_id'), entry_id, action_name
#     )
#     task_fn = partial(helper_generate_users_from_csv, xmodule_instance_args)
#     return run_main_task(entry_id, task_fn, action_name)


# #ADD TIME TMA DASHBOARD
# @task(base=BaseInstructorTask, routing_key=settings.GRADES_DOWNLOAD_ROUTING_KEY)
# def add_extra_time(entry_id, xmodule_instance_args):
#     # Translators: This is a past-tense verb that is inserted into task progress messages as {action}.
#     action_name = ugettext_noop('add_extra_time')
#     TASK_LOG.info(
#         u"Task: %s, statdashboardTask ID: %s, Task type: %s, Preparing for task execution",
#         xmodule_instance_args.get('task_id'), entry_id, action_name
#     )

#     task_fn = partial(helper_add_extra_time, xmodule_instance_args)
#     return run_main_task(entry_id, task_fn, action_name)