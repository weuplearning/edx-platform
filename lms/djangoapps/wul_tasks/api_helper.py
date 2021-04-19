"""
Helper lib for wul_tasks API.

Includes methods to check args for rescoring task, encoding student input,
and task submission logic, including handling the Celery backend.
"""


import hashlib
import json
import logging

from celery.result import AsyncResult
from celery.states import FAILURE, READY_STATES, REVOKED, SUCCESS
from django.utils.translation import ugettext as _
from opaque_keys.edx.keys import UsageKey
import six
from six import text_type

from lms.djangoapps.courseware.courses import get_problems_in_section
from lms.djangoapps.courseware.module_render import get_xqueue_callback_url_prefix
from lms.djangoapps.wul_tasks.models import PROGRESS, WulTask
from common.djangoapps.util.db import outer_atomic
from xmodule.modulestore.django import modulestore

log = logging.getLogger(__name__)


class AlreadyRunningError(Exception):
    """Exception indicating that a background task is already running"""

    message = _('Requested task is already running')

    def __init__(self, message=None):

        if not message:
            message = self.message
        super(AlreadyRunningError, self).__init__(message)


class QueueConnectionError(Exception):
    """
    Exception indicating that celery task was not created successfully.
    """
    message = _('Error occured. Please try again later.')

    def __init__(self, message=None):
        if not message:
            message = self.message
        super(QueueConnectionError, self).__init__(message)


def _task_is_running(course_id, task_type, task_key):
    """Checks if a particular task is already running"""
    running_tasks = WulTask.objects.filter(
        course_id=course_id, task_type=task_type, task_key=task_key
    )
    # exclude states that are "ready" (i.e. not "running", e.g. failure, success, revoked):
    for state in READY_STATES:
        running_tasks = running_tasks.exclude(task_state=state)
    return len(running_tasks) > 0


def _reserve_task(course_id, task_type, task_key, task_input, requester):
    """
    Creates a database entry to indicate that a task is in progress.

    Throws AlreadyRunningError if the task is already in progress.
    Includes the creation of an arbitrary value for task_id, to be
    submitted with the task call to celery.

    Note that there is a chance of a race condition here, when two users
    try to run the same task at almost exactly the same time.  One user
    could be after the check and before the create when the second user
    gets to the check.  At that point, both users are able to run their
    tasks simultaneously.  This is deemed a small enough risk to not
    put in further safeguards.
    """

    if _task_is_running(course_id, task_type, task_key):
        log.warning(u"Duplicate task found for task_type %s and task_key %s", task_type, task_key)
        error_message = generate_already_running_error_message(task_type)
        raise AlreadyRunningError(error_message)

    try:
        most_recent_id = WulTask.objects.latest('id').id
    except WulTask.DoesNotExist:
        most_recent_id = "None found"
    finally:
        log.warning(
            u"No duplicate tasks found: task_type %s, task_key %s, and most recent task_id = %s",
            task_type,
            task_key,
            most_recent_id
        )

    # Create log entry now, so that future requests will know it's running.
    return WulTask.create(course_id, task_type, task_key, task_input, requester)


def generate_already_running_error_message(task_type):
    """
    Returns already running error message for given task type.
    """

    message = ''
    report_types = {
        'grade_problems': _('problem grade'),
        'problem_responses_csv': _('problem responses'),
        'profile_info_csv': _('enrolled learner profile'),
        'may_enroll_info_csv': _('enrollment'),
        'detailed_enrollment_report': _('detailed enrollment'),
        'course_survey_report': _('survey'),
        'proctored_exam_results_report': _('proctored exam results'),
        'export_ora2_data': _('ORA data'),
        'grade_course': _('grade'),

    }

    if report_types.get(task_type):

        message = _(
            u"The {report_type} report is being created. "
            "To view the status of the report, see Pending Tasks below. "
            "You will be able to download the report when it is complete."
        ).format(report_type=report_types.get(task_type))

    return message


def _get_xmodule_instance_args(request, task_id):
    """
    Calculate parameters needed for instantiating xmodule instances.

    The `request_info` will be passed to a tracking log function, to provide information
    about the source of the task request.   The `xqueue_callback_url_prefix` is used to
    permit old-style xqueue callbacks directly to the appropriate module in the LMS.
    The `task_id` is also passed to the tracking log function.
    """
    request_info = {'username': request.user.username,
                    'user_id': request.user.id,
                    'ip': request.META['REMOTE_ADDR'],
                    'agent': request.META.get('HTTP_USER_AGENT', '').encode().decode('latin1'),
                    'host': request.META['SERVER_NAME'],
                    }
    xmodule_instance_args = {'xqueue_callback_url_prefix': get_xqueue_callback_url_prefix(request),
                             'request_info': request_info,
                             'task_id': task_id,
                             }
    return xmodule_instance_args


def _supports_rescore(descriptor):
    """
    Helper method to determine whether a given item supports rescoring.
    In order to accommodate both XModules and XBlocks, we have to check
    the descriptor itself then fall back on its module class.
    """
    return hasattr(descriptor, 'rescore') or (
        hasattr(descriptor, 'module_class') and hasattr(descriptor.module_class, 'rescore')
    )


def _update_wul_task(wul_tasks, task_result):
    """
    Updates and possibly saves a WulTask entry based on a task Result.

    Used when updated status is requested.

    The `wul_tasks` that is passed in is updated in-place, but
    is usually not saved.  In general, tasks that have finished (either with
    success or failure) should have their entries updated by the task itself,
    so are not updated here.  Tasks that are still running are not updated
    and saved while they run.  The one exception to the no-save rule are tasks that
    are in a "revoked" state.  This may mean that the task never had the
    opportunity to update the WulTask entry.

    Tasks that are in progress and have subtasks doing the processing do not look
    to the task's AsyncResult object.  When subtasks are running, the
    WulTask object itself is updated with the subtasks' progress,
    not any AsyncResult object.  In this case, the WulTask is
    not updated at all.

    Calculates json to store in "task_output" field of the `wul_tasks`,
    as well as updating the task_state.

    For a successful task, the json contains the output of the task result.
    For a failed task, the json contains "exception", "message", and "traceback"
    keys.   A revoked task just has a "message" stating it was revoked.
    """
    # Pull values out of the result object as close to each other as possible.
    # If we wait and check the values later, the values for the state and result
    # are more likely to have changed.  Pull the state out first, and
    # then code assuming that the result may not exactly match the state.
    task_id = task_result.task_id
    result_state = task_result.state
    returned_result = task_result.result
    result_traceback = task_result.traceback

    # Assume we don't always save the WulTask entry if we don't have to,
    # but that in most cases we will update the WulTask in-place with its
    # current progress.
    entry_needs_updating = True
    entry_needs_saving = False
    task_output = None

    if wul_tasks.task_state == PROGRESS and len(wul_tasks.subtasks) > 0:
        # This happens when running subtasks:  the result object is marked with SUCCESS,
        # meaning that the subtasks have successfully been defined.  However, the WulTask
        # will be marked as in PROGRESS, until the last subtask completes and marks it as SUCCESS.
        # We want to ignore the parent SUCCESS if subtasks are still running, and just trust the
        # contents of the WulTask.
        entry_needs_updating = False
    elif result_state in [PROGRESS, SUCCESS]:
        # construct a status message directly from the task result's result:
        # it needs to go back with the entry passed in.
        log.info(u"background task (%s), state %s:  result: %s", task_id, result_state, returned_result)
        task_output = WulTask.create_output_for_success(returned_result)
    elif result_state == FAILURE:
        # on failure, the result's result contains the exception that caused the failure
        exception = returned_result
        traceback = result_traceback if result_traceback is not None else ''
        log.warning(u"background task (%s) failed: %s %s", task_id, returned_result, traceback)
        task_output = WulTask.create_output_for_failure(exception, result_traceback)
    elif result_state == REVOKED:
        # on revocation, the result's result doesn't contain anything
        # but we cannot rely on the worker thread to set this status,
        # so we set it here.
        entry_needs_saving = True
        log.warning(u"background task (%s) revoked.", task_id)
        task_output = WulTask.create_output_for_revoked()

    # save progress and state into the entry, even if it's not being saved:
    # when celery is run in "ALWAYS_EAGER" mode, progress needs to go back
    # with the entry passed in.
    if entry_needs_updating:
        wul_tasks.task_state = result_state
        if task_output is not None:
            wul_tasks.task_output = task_output

        if entry_needs_saving:
            wul_tasks.save()


def _update_wul_task_state(wul_tasks, task_state, message=None):
    """
    Update state and output of WulTask object.
    """
    wul_tasks.task_state = task_state
    if message:
        wul_tasks.task_output = message

    wul_tasks.save()


def _handle_wul_task_failure(wul_tasks, error):
    """
    Do required operations if task creation was not complete.
    """
    log.info(u"instructor task (%s) failed, result: %s", wul_tasks.task_id, text_type(error))
    _update_wul_task_state(wul_tasks, FAILURE, text_type(error))

    raise QueueConnectionError()


def _get_async_result(task_id):
    """
    Use this minor indirection to facilitate mocking the AsyncResult in tests.
    """
    return AsyncResult(task_id)


def get_updated_wul_task(task_id):
    """
    Returns WulTask object corresponding to a given `task_id`.

    If the WulTask thinks the task is still running, then
    the task's result is checked to return an updated state and output.
    """
    # First check if the task_id is known
    try:
        wul_tasks = WulTask.objects.get(task_id=task_id)
    except WulTask.DoesNotExist:
        log.warning(u"query for WulTask status failed: task_id=(%s) not found", task_id)
        return None

    # if the task is not already known to be done, then we need to query
    # the underlying task's result object:
    if wul_tasks.task_state not in READY_STATES:
        result = _get_async_result(task_id)
        _update_wul_task(wul_tasks, result)

    return wul_tasks


def get_status_from_wul_task(wul_tasks):
    """
    Get the status for a given WulTask entry.

    Returns a dict, with the following keys:
      'task_id': id assigned by LMS and used by celery.
      'task_state': state of task as stored in celery's result store.
      'in_progress': boolean indicating if task is still running.
      'task_progress': dict containing progress information.  This includes:
          'attempted': number of attempts made
          'succeeded': number of attempts that "succeeded"
          'total': number of possible subtasks to attempt
          'action_name': user-visible verb to use in status messages.  Should be past-tense.
          'duration_ms': how long the task has (or had) been running.
          'exception': name of exception class raised in failed tasks.
          'message': returned for failed and revoked tasks.
          'traceback': optional, returned if task failed and produced a traceback.

     """
    status = {}

    if wul_tasks is not None:
        # status basic information matching what's stored in WulTask:
        status['task_id'] = wul_tasks.task_id
        status['task_state'] = wul_tasks.task_state
        status['in_progress'] = wul_tasks.task_state not in READY_STATES
        if wul_tasks.task_output is not None:
            status['task_progress'] = json.loads(wul_tasks.task_output)

    return status


def check_arguments_for_rescoring(usage_key):
    """
    Do simple checks on the descriptor to confirm that it supports rescoring.

    Confirms first that the usage_key is defined (since that's currently typed
    in).  An ItemNotFoundException is raised if the corresponding module
    descriptor doesn't exist.  NotImplementedError is raised if the
    corresponding module doesn't support rescoring calls.

    Note: the string returned here is surfaced as the error
    message on the instructor dashboard when a rescore is
    submitted for a non-rescorable block.
    """
    descriptor = modulestore().get_item(usage_key)
    if not _supports_rescore(descriptor):
        msg = _("This component cannot be rescored.")
        raise NotImplementedError(msg)


def check_arguments_for_overriding(usage_key, score):
    """
    Do simple checks on the descriptor to confirm that it supports overriding
    the problem score and the score passed in is not greater than the value of
    the problem or less than 0.
    """
    descriptor = modulestore().get_item(usage_key)
    score = float(score)

    # some weirdness around initializing the descriptor requires this
    if not hasattr(descriptor.__class__, 'set_score'):
        msg = _("This component does not support score override.")
        raise NotImplementedError(msg)

    if score < 0 or score > descriptor.max_score():
        msg = _("Scores must be between 0 and the value of the problem.")
        raise ValueError(msg)


def check_entrance_exam_problems_for_rescoring(exam_key):  # pylint: disable=invalid-name
    """
    Grabs all problem descriptors in exam and checks each descriptor to
    confirm that it supports re-scoring.

    An ItemNotFoundException is raised if the corresponding module
    descriptor doesn't exist for exam_key. NotImplementedError is raised if
    any of the problem in entrance exam doesn't support re-scoring calls.
    """
    problems = list(get_problems_in_section(exam_key).values())
    if any(not _supports_rescore(problem) for problem in problems):
        msg = _("Not all problems in entrance exam support re-scoring.")
        raise NotImplementedError(msg)


def encode_problem_and_student_input(usage_key, student=None):
    """
    Encode optional usage_key and optional student into task_key and task_input values.

    Args:
        usage_key (Location): The usage_key identifying the problem.
        student (User): the student affected
    """

    assert isinstance(usage_key, UsageKey)
    if student is not None:
        task_input = {'problem_url': text_type(usage_key), 'student': student.username}
        task_key_stub = "{student}_{problem}".format(student=student.id, problem=text_type(usage_key))
    else:
        task_input = {'problem_url': text_type(usage_key)}
        task_key_stub = "_{problem}".format(problem=text_type(usage_key))

    # create the key value by using MD5 hash:
    task_key = hashlib.md5(six.b(task_key_stub)).hexdigest()

    return task_input, task_key


def encode_entrance_exam_and_student_input(usage_key, student=None):
    """
    Encode usage_key and optional student into task_key and task_input values.

    Args:
        usage_key (Location): The usage_key identifying the entrance exam.
        student (User): the student affected
    """
    assert isinstance(usage_key, UsageKey)
    if student is not None:
        task_input = {'entrance_exam_url': text_type(usage_key), 'student': student.username}
        task_key_stub = "{student}_{entranceexam}".format(student=student.id, entranceexam=text_type(usage_key))
    else:
        task_input = {'entrance_exam_url': text_type(usage_key)}
        task_key_stub = "_{entranceexam}".format(entranceexam=text_type(usage_key))

    # create the key value by using MD5 hash:
    task_key = hashlib.md5(task_key_stub.encode('utf-8')).hexdigest()

    return task_input, task_key


def submit_task(request, task_type, task_class, course_key, task_input, task_key, microsite):
    """
    Helper method to submit a task.

    Reserves the requested task, based on the `course_key`, `task_type`, and `task_key`,
    checking to see if the task is already running.  The `task_input` is also passed so that
    it can be stored in the resulting WulTask entry.  Arguments are extracted from
    the `request` provided by the originating server request.  Then the task is submitted to run
    asynchronously, using the specified `task_class` and using the task_id constructed for it.

    Cannot be inside an atomic block.

    `AlreadyRunningError` is raised if the task is already running.
    """
    with outer_atomic():
        # check to see if task is already running, and reserve it otherwise:
        wul_tasks = _reserve_task(course_key, task_type, task_key, task_input, request.user)

    # make sure all data has been committed before handing off task to celery.

    task_id = wul_tasks.task_id
    task_args = [wul_tasks.id, _get_xmodule_instance_args(request, task_id)]
    try:
        task_class.apply_async(task_args, task_id=task_id)

    except Exception as error:
        _handle_wul_task_failure(wul_tasks, error)
    return wul_tasks
