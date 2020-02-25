import json
import logging
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

from atp_task.models import tmaTask, PROGRESS

from util.db import outer_atomic

#GEOFFREY
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

from atp_task.course_grade import course_grade

log = logging.getLogger(__name__)

TASK_LOG = logging.getLogger('edx.celery.task')

REPORT_REQUESTED_EVENT_NAME = u'tma.stat_dashboard.report.requested'

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
        entry = tmaTask.objects.get(pk=entry_id)
        # Check to see if any subtasks had been defined as part of this task.
        # If not, then we know that we're done.  (If so, let the subtasks
        # handle updating task_state themselves.)
        if len(entry.subtasks) == 0:
            entry.task_output = tmaTask.create_output_for_success(task_progress)
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
            entry = tmaTask.objects.get(pk=entry_id)
        except tmaTask.DoesNotExist:
            # if the InstructorTask object does not exist, then there's no point
            # trying to update it.
            TASK_LOG.error(u"Task (%s) has no InstructorTask object for id %s", task_id, entry_id)
        else:
            TASK_LOG.warning(u"Task (%s) failed", task_id, exc_info=True)
            entry.task_output = tmaTask.create_output_for_failure(einfo.exception, einfo.traceback)
            entry.task_state = FAILURE
            entry.save_now()

class UpdateProblemModuleStateError(Exception):
    """
    Error signaling a fatal condition while updating problem modules.

    Used when the current module cannot be processed and no more
    modules should be attempted.
    """
    pass

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
        entry = tmaTask.objects.get(pk=entry_id)
        entry.task_state = PROGRESS
        entry.save_now()

    # Get inputs to use in this task from the entry
    task_id = entry.task_id
    course_id = entry.course_id
    task_input = json.loads(entry.task_input)

    # Construct log message
    fmt = u'Task: {task_id}, tmaTask ID: {entry_id}, Course: {course_id}, Input: {task_input}'
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
    task_progress = task_fcn(entry_id, course_id, task_input, action_name)

    # Release any queries that the connection has been hanging onto
    reset_queries()

    # Log and exit, returning task_progress info as task result
    TASK_LOG.info(u'%s, Task type: %s, Finishing task: %s', task_info_string, action_name, task_progress)
    return task_progress

def upload_grades_xls(_xmodule_instance_args, _entry_id, course_id, _task_input, action_name):
    course_id = str(course_id)
    email = _task_input.get('email')
    log.warning("email1 : "+str(email))
    log.warning("email2 : "+str(email))
    log.warning("email3 : "+str(email))
    log.warning("email4 : "+str(email))
    grade_path = course_grade(course_id).export(email)
    tracker.emit(REPORT_REQUESTED_EVENT_NAME, {"report_type": grade_path, })
