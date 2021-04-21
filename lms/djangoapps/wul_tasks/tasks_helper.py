# -*- coding: utf-8 -*-
import sys
import importlib
importlib.reload(sys)

import json
import logging
# from StringIO import StringIO
from collections import OrderedDict
from datetime import datetime
from itertools import chain
from time import time

import re
import unicodecsv
from celery import Task, current_task
from celery.states import SUCCESS, FAILURE
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import DefaultStorage
from django.db import reset_queries
from django.db.models import Q
from django.utils.translation import ugettext as _
from eventtracking import tracker

from pytz import UTC
from track import contexts

from courseware.courses import get_course_by_id, get_problems_in_section

from lms.djangoapps.wul_tasks.models import WulTask, PROGRESS

from util.db import outer_atomic

#GEOFFREY
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from lms.djangoapps.wul_apps.stat_dashboard.wul_dashboard import wul_dashboard
from lms.djangoapps.wul_apps.stat_dashboard.grade_reports import grade_reports
# from tma_apps.fraissinet.fraissinet import fraissinet

# #DASHBOARD V2
# from tma_apps.wul_dashboard.dashboard_tasks import create_and_register_multi_users

log = logging.getLogger(__name__)

TASK_LOG = logging.getLogger('edx.celery.task')

REPORT_REQUESTED_EVENT_NAME = u'tma.stat_dashboard.report.requested'

class TaskProgress(object):
    """
    Encapsulates the current task's progress by keeping track of
    'attempted', 'succeeded', 'skipped', 'failed', 'total',
    'action_name', and 'duration_ms' values.
    """
    def __init__(self, action_name):
        self.action_name = action_name
        self.complementary = None

    def update_task_state(self, extra_meta=None):
        """
        Update the current celery task's state to the progress state
        specified by the current object.  Returns the progress
        dictionary for use by `run_main_task` and
        `BaseInstructorTask.on_success`.

        Arguments:
            extra_meta (dict): Extra metadata to pass to `update_state`

        Returns:
            dict: The current task's progress dict
        """
        progress_dict = {
            'action_name': self.action_name,
            'complementary': self.complementary
        }
        if extra_meta is not None:
            progress_dict.update(extra_meta)
        _get_current_task().update_state(state=PROGRESS, meta=progress_dict)
        return progress_dict

class BaseInstructorTask(Task):
    """
    Base task class for use with InstructorTask models.

    Permits updating information about task in corresponding InstructorTask for monitoring purposes.

    Assumes that the entry_id of the InstructorTask model is the first argument to the task.

    The `entry_id` is the primary key for the InstructorTask entry representing the task.  This class
    updates the entry on success and failure of the task it wraps.  It is setting the entry's value
    for task_state based on what Celery would set it to once the task returns to Celery:
    FAILURE if an exception is encountered, and SUCCESS if it returns normally.
    Other arguments are pass-throughs to perform_module_state_update, and documented there.
    """
    abstract = True

    def on_success(self, task_progress, task_id, args, kwargs):
        """
        Update InstructorTask object corresponding to this task with info about success.

        Updates task_output and task_state.  But it shouldn't actually do anything
        if the task is only creating subtasks to actually do the work.

        Assumes `task_progress` is a dict containing the task's result, with the following keys:

          'attempted': number of attempts made
          'succeeded': number of attempts that "succeeded"
          'skipped': number of attempts that "skipped"
          'failed': number of attempts that "failed"
          'total': number of possible subtasks to attempt
          'action_name': user-visible verb to use in status messages.  Should be past-tense.
              Pass-through of input `action_name`.
          'duration_ms': how long the task has (or had) been running.

        This is JSON-serialized and stored in the task_output column of the InstructorTask entry.

        """
        TASK_LOG.debug('Task %s: success returned with progress: %s', task_id, task_progress)
        # We should be able to find the InstructorTask object to update
        # based on the task_id here, without having to dig into the
        # original args to the task.  On the other hand, the entry_id
        # is the first value passed to all such args, so we'll use that.
        # And we assume that it exists, else we would already have had a failure.
        entry_id = args[0]
        entry = WulTask.objects.get(pk=entry_id)
        # Check to see if any subtasks had been defined as part of this task.
        # If not, then we know that we're done.  (If so, let the subtasks
        # handle updating task_state themselves.)
        if len(entry.subtasks) == 0:
            entry.task_output = WulTask.create_output_for_success(task_progress)
            entry.task_state = SUCCESS
            entry.save_now()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Update InstructorTask object corresponding to this task with info about failure.

        Fetches and updates exception and traceback information on failure.

        If an exception is raised internal to the task, it is caught by celery and provided here.
        The information is recorded in the InstructorTask object as a JSON-serialized dict
        stored in the task_output column.  It contains the following keys:

               'exception':  type of exception object
               'message': error message from exception object
               'traceback': traceback information (truncated if necessary)

        Note that there is no way to record progress made within the task (e.g. attempted,
        succeeded, etc.) when such failures occur.
        """
        TASK_LOG.debug(u'Task %s: failure returned', task_id)
        entry_id = args[0]
        try:
            entry = WulTask.objects.get(pk=entry_id)
        except WulTask.DoesNotExist:
            # if the InstructorTask object does not exist, then there's no point
            # trying to update it.
            TASK_LOG.error(u"Task (%s) has no InstructorTask object for id %s", task_id, entry_id)
        else:
            TASK_LOG.warning(u"Task (%s) failed", task_id, exc_info=True)
            entry.task_output = WulTask.create_output_for_failure(einfo.exception, einfo.traceback)
            entry.task_state = FAILURE
            entry.save_now()

# class UpdateProblemModuleStateError(Exception):
#     """
#     Error signaling a fatal condition while updating problem modules.

#     Used when the current module cannot be processed and no more
#     modules should be attempted.
#     """
#     pass

def _get_current_task():
    """
    Stub to make it easier to test without actually running Celery.

    This is a wrapper around celery.current_task, which provides access
    to the top of the stack of Celery's tasks.  When running tests, however,
    it doesn't seem to work to mock current_task directly, so this wrapper
    is used to provide a hook to mock in tests, while providing the real
    `current_task` in production.
    """
    return current_task

def run_main_task(entry_id, task_fcn, action_name):
    """
    Applies the `task_fcn` to the arguments defined in `entry_id` InstructorTask.

    Arguments passed to `task_fcn` are:

     `entry_id` : the primary key for the InstructorTask entry representing the task.
     `course_id` : the id for the course.
     `task_input` : dict containing task-specific arguments, JSON-decoded from InstructorTask's task_input.
     `action_name` : past-tense verb to use for constructing status messages.

    If no exceptions are raised, the `task_fcn` should return a dict containing
    the task's result with the following keys:

          'attempted': number of attempts made
          'succeeded': number of attempts that "succeeded"
          'skipped': number of attempts that "skipped"
          'failed': number of attempts that "failed"
          'total': number of possible subtasks to attempt
          'action_name': user-visible verb to use in status messages.
              Should be past-tense.  Pass-through of input `action_name`.
          'duration_ms': how long the task has (or had) been running.

    """

    # Get the InstructorTask to be updated. If this fails then let the exception return to Celery.
    # There's no point in catching it here.
    with outer_atomic():
        entry = WulTask.objects.get(pk=entry_id)
        entry.task_state = PROGRESS
        entry.save_now()

    # Get inputs to use in this task from the entry
    task_id = entry.task_id
    course_id = entry.course_id
    task_input = json.loads(entry.task_input)
    microsite = entry.microsite_input

    # Construct log message
    fmt = u'Task: {task_id}, WulTask ID: {entry_id}, Course: {course_id}, Input: {task_input}'
    task_info_string = fmt.format(task_id=task_id, entry_id=entry_id, course_id=course_id, task_input=task_input)
    TASK_LOG.info(u'%s, Starting update (nothing %s yet)', task_info_string, action_name)

    # Check that the task_id submitted in the InstructorTask matches the current task
    # that is running.



    request_task_id = _get_current_task().request.id
    if task_id != request_task_id:
        fmt = u'{task_info}, Requested task did not match actual task "{actual_id}"'
        message = fmt.format(task_info=task_info_string, actual_id=request_task_id)
        TASK_LOG.error(message)
        raise ValueError(message)

    # Now do the work
    # with dog_stats_api.timer('instructor_tasks.time.overall', tags=[u'action:{name}'.format(name=action_name)]):
    task_progress = task_fcn(entry_id, course_id, task_input, action_name,microsite)

    # Release any queries that the connection has been hanging onto
    reset_queries()

    # Log and exit, returning task_progress info as task result
    return task_progress

def upload_grades_xls(_xmodule_instance_args, _entry_id, course_id, _task_input, action_name,microsite):
    course_key = course_id
    course_id = str(course_id)
    grade_path = grade_reports(_task_input,course_id=course_id,microsite=microsite).task_generate_xls()

    task_progress = TaskProgress('grade_generation')
    task_progress.complementary = grade_path

    return task_progress.update_task_state()
    #tracker.emit(REPORT_REQUESTED_EVENT_NAME, {"report_type": grade_path, })

def users_generation(_xmodule_instance_args, _entry_id, course_id, _task_input, action_name, microsite):
    course_key = course_id
    course_id = str(course_id)
    generation_path =  wul_dashboard(course_id=course_id,course_key=course_key,request=_task_input).task_generate_user()

    task_progress = TaskProgress('user_generation')
    task_progress.complementary = generation_path

    return task_progress.update_task_state()


    #tracker.emit(REPORT_REQUESTED_EVENT_NAME, {"report_type": generation_path, })

# #SBO TASK
# def sbo_xls_generation(_xmodule_instance_args, _entry_id, course_id, _task_input, action_name,microsite):
#     course_key = course_id
#     course_id = str(course_id)
#     user_id = _task_input.get('requester_id')
#     user_email = _task_input.get('requester_email')
#     custom_field = _task_input.get('custom_field')
#     generation_path =  fraissinet(course_id=course_id,course_key=course_key).generate_xls(user_id,user_email,custom_field)

#     task_progress = TaskProgress('sbo_user_xls')
#     task_progress.complementary = generation_path

#     return task_progress.update_task_state()
#     #tracker.emit(REPORT_REQUESTED_EVENT_NAME, {"report_type": generation_path, })


# #DASHBOARD V2 TASKS
# def helper_generate_users_from_csv(_xmodule_instance_args, _entry_id, course_key, task_input, action_name, microsite):
#     task_function = create_and_register_multi_users(course_key, task_input=task_input)
#     task_progress = TaskProgress('user_generation')
#     task_progress.complementary = task_function
#     return task_progress.update_task_state()

# #TMA DASHBOARD ADD TIME
# def helper_add_extra_time(_xmodule_instance_args, _entry_id, course_id, _task_input, action_name,microsite):
#     course_key = course_id
#     course_id = str(course_id)
#     add_time_task =  wul_dashboard(course_id=course_id,course_key=course_key,request=_task_input).task_add_time()
#     task_progress = TaskProgress('add_extra_time')
#     task_progress.complementary = add_time_task
#     return task_progress.update_task_state()
