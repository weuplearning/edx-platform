"""
Views related to operations on course objects
"""
from __future__ import absolute_import

import copy
import json
import logging
import random
import re
import string
from collections import defaultdict
import datetime

import django.utils
import six
from ccx_keys.locator import CCXLocator
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods
from milestones import api as milestones_api
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import BlockUsageLocator
from six import text_type
from six.moves import filter

from contentstore.course_group_config import (
    COHORT_SCHEME,
    ENROLLMENT_SCHEME,
    RANDOM_SCHEME,
    GroupConfiguration,
    GroupConfigurationsValidationError
)
from contentstore.course_info_model import delete_course_update, get_course_updates, update_course_updates
from contentstore.courseware_index import CoursewareSearchIndexer, SearchIndexingError
from contentstore.tasks import rerun_course as rerun_course_task
from contentstore.utils import (
    add_instructor,
    get_lms_link_for_item,
    initialize_permissions,
    remove_all_instructors,
    reverse_course_url,
    reverse_library_url,
    reverse_url,
    reverse_usage_url
)
from contentstore.views.entrance_exam import create_entrance_exam, delete_entrance_exam, update_entrance_exam
from course_action_state.managers import CourseActionStateItemNotFoundError
from course_action_state.models import CourseRerunState, CourseRerunUIStateManager
from course_creators.views import add_user_with_status_unrequested, get_course_creator_status
from course_modes.models import CourseMode
from edxmako.shortcuts import render_to_response
from models.settings.course_grading import CourseGradingModel
from models.settings.course_metadata import CourseMetadata
from models.settings.encoder import CourseSettingsEncoder
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.credit.api import get_credit_requirements, is_credit_course
from openedx.core.djangoapps.credit.tasks import update_credit_course_requirements
from openedx.core.djangoapps.models.course_details import CourseDetails
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.core.djangoapps.waffle_utils import WaffleSwitchNamespace
from openedx.core.djangolib.js_utils import dump_js_escaped_json
from openedx.core.lib.course_tabs import CourseTabPluginManager
from openedx.core.lib.courses import course_image_url
from openedx.features.content_type_gating.models import ContentTypeGatingConfig
from openedx.features.content_type_gating.partitions import CONTENT_TYPE_GATING_SCHEME
from openedx.features.course_experience.waffle import ENABLE_COURSE_ABOUT_SIDEBAR_HTML
from openedx.features.course_experience.waffle import waffle as course_experience_waffle
from student import auth
from student.auth import has_course_author_access, has_studio_read_access, has_studio_write_access
from student.roles import CourseCreatorRole, CourseInstructorRole, CourseStaffRole, GlobalStaff, UserBasedRole
from student.models import UserPreprofile,CourseEnrollment,User, CourseEnrollmentAllowed
from util.course import get_link_for_about_page
from util.date_utils import get_default_time_display
from util.json_request import JsonResponse, JsonResponseBadRequest, expect_json
from util.milestones_helpers import (
    is_entrance_exams_enabled,
    is_prerequisite_courses_enabled,
    is_valid_course_key,
    remove_prerequisite_course,
    set_prerequisite_courses
)
from util.organizations_helpers import add_organization_course, get_organization_by_short_name, organizations_enabled
from util.string_utils import _has_non_ascii_characters
from xblock_django.api import deprecated_xblocks
from xmodule.contentstore.content import StaticContent
from xmodule.course_module import DEFAULT_START_DATE, CourseFields
from xmodule.error_module import ErrorDescriptor
from xmodule.modulestore import EdxJSONEncoder
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import DuplicateCourseError, ItemNotFoundError
from xmodule.partitions.partitions import UserPartition
from xmodule.tabs import CourseTab, CourseTabList, InvalidTabsException

from .component import ADVANCED_COMPONENT_TYPES
from .item import create_xblock_info
from .library import LIBRARIES_ENABLED, get_library_creator_status

#TMA Custom Import - Importing SiteConfiguration instead of MS config
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
from lms.djangoapps.courseware.courses import get_course_by_id

log = logging.getLogger(__name__)

__all__ = ['course_info_handler', 'course_handler', 'course_listing',
           'course_info_update_handler', 'course_search_index_handler',
           'course_rerun_handler',
            'invite_handler',
            'email_dashboard_handler',
           'settings_handler',
           'grading_handler',
           'advanced_settings_handler',
           'course_notifications_handler',
           'textbooks_list_handler', 'textbooks_detail_handler',
           'group_configurations_list_handler', 'group_configurations_detail_handler']

WAFFLE_NAMESPACE = 'studio_home'


class AccessListFallback(Exception):
    """
    An exception that is raised whenever we need to `fall back` to fetching *all* courses
    available to a user, rather than using a shorter method (i.e. fetching by group)
    """
    pass


def get_course_and_check_access(course_key, user, depth=0):
    """
    Internal method used to calculate and return the locator and course module
    for the view functions in this file.
    """
    if not has_studio_read_access(user, course_key):
        raise PermissionDenied()
    course_module = modulestore().get_course(course_key, depth=depth)
    return course_module


def reindex_course_and_check_access(course_key, user):
    """
    Internal method used to restart indexing on a course.
    """
    if not has_course_author_access(user, course_key):
        raise PermissionDenied()
    return CoursewareSearchIndexer.do_course_reindex(modulestore(), course_key)


@login_required
def course_notifications_handler(request, course_key_string=None, action_state_id=None):
    """
    Handle incoming requests for notifications in a RESTful way.

    course_key_string and action_state_id must both be set; else a HttpBadResponseRequest is returned.

    For each of these operations, the requesting user must have access to the course;
    else a PermissionDenied error is returned.

    GET
        json: return json representing information about the notification (action, state, etc)
    DELETE
        json: return json repressing success or failure of dismissal/deletion of the notification
    PUT
        Raises a NotImplementedError.
    POST
        Raises a NotImplementedError.
    """
    # ensure that we have a course and an action state
    if not course_key_string or not action_state_id:
        return HttpResponseBadRequest()

    response_format = request.GET.get('format') or request.POST.get('format') or 'html'

    course_key = CourseKey.from_string(course_key_string)

    if response_format == 'json' or 'application/json' in request.META.get('HTTP_ACCEPT', 'application/json'):
        if not has_studio_write_access(request.user, course_key):
            raise PermissionDenied()
        if request.method == 'GET':
            return _course_notifications_json_get(action_state_id)
        elif request.method == 'DELETE':
            # we assume any delete requests dismiss actions from the UI
            return _dismiss_notification(request, action_state_id)
        elif request.method == 'PUT':
            raise NotImplementedError()
        elif request.method == 'POST':
            raise NotImplementedError()
        else:
            return HttpResponseBadRequest()
    else:
        return HttpResponseNotFound()


def _course_notifications_json_get(course_action_state_id):
    """
    Return the action and the action state for the given id
    """
    try:
        action_state = CourseRerunState.objects.find_first(id=course_action_state_id)
    except CourseActionStateItemNotFoundError:
        return HttpResponseBadRequest()

    action_state_info = {
        'action': action_state.action,
        'state': action_state.state,
        'should_display': action_state.should_display
    }
    return JsonResponse(action_state_info)


def _dismiss_notification(request, course_action_state_id):  # pylint: disable=unused-argument
    """
    Update the display of the course notification
    """
    try:
        action_state = CourseRerunState.objects.find_first(id=course_action_state_id)

    except CourseActionStateItemNotFoundError:
        # Can't dismiss a notification that doesn't exist in the first place
        return HttpResponseBadRequest()

    if action_state.state == CourseRerunUIStateManager.State.FAILED:
        # We remove all permissions for this course key at this time, since
        # no further access is required to a course that failed to be created.
        remove_all_instructors(action_state.course_key)

    # The CourseRerunState is no longer needed by the UI; delete
    action_state.delete()

    return JsonResponse({'success': True})


@login_required
def course_handler(request, course_key_string=None):
    """
    The restful handler for course specific requests.
    It provides the course tree with the necessary information for identifying and labeling the parts. The root
    will typically be a 'course' object but may not be especially as we support modules.

    GET
        html: return course listing page if not given a course id
        html: return html page overview for the given course if given a course id
        json: return json representing the course branch's index entry as well as dag w/ all of the children
        replaced w/ json docs where each doc has {'_id': , 'display_name': , 'children': }
    POST
        json: create a course, return resulting json
        descriptor (same as in GET course/...). Leaving off /branch/draft would imply create the course w/ default
        branches. Cannot change the structure contents ('_id', 'display_name', 'children') but can change the
        index entry.
    PUT
        json: update this course (index entry not xblock) such as repointing head, changing display name, org,
        course, run. Return same json as above.
    DELETE
        json: delete this branch from this course (leaving off /branch/draft would imply delete the course)
    """
    try:
        response_format = request.GET.get('format') or request.POST.get('format') or 'html'
        if response_format == 'json' or 'application/json' in request.META.get('HTTP_ACCEPT', 'application/json'):
            if request.method == 'GET':
                course_key = CourseKey.from_string(course_key_string)
                with modulestore().bulk_operations(course_key):
                    course_module = get_course_and_check_access(course_key, request.user, depth=None)
                    return JsonResponse(_course_outline_json(request, course_module))
            elif request.method == 'POST':  # not sure if this is only post. If one will have ids, it goes after access
                return _create_or_rerun_course(request)
            elif not has_studio_write_access(request.user, CourseKey.from_string(course_key_string)):
                raise PermissionDenied()
            elif request.method == 'PUT':
                raise NotImplementedError()
            elif request.method == 'DELETE':
                raise NotImplementedError()
            else:
                return HttpResponseBadRequest()
        elif request.method == 'GET':  # assume html
            if course_key_string is None:
                return redirect(reverse('home'))
            else:
                return course_index(request, CourseKey.from_string(course_key_string))
        else:
            return HttpResponseNotFound()
    except InvalidKeyError:
        raise Http404


@login_required
@ensure_csrf_cookie
@require_http_methods(["GET"])
def course_rerun_handler(request, course_key_string):
    """
    The restful handler for course reruns.
    GET
        html: return html page with form to rerun a course for the given course id
    """
    # Only global staff (PMs) are able to rerun courses during the soft launch
    if not GlobalStaff().has_user(request.user):
        raise PermissionDenied()
    course_key = CourseKey.from_string(course_key_string)
    with modulestore().bulk_operations(course_key):
        course_module = get_course_and_check_access(course_key, request.user, depth=3)
        if request.method == 'GET':
            return render_to_response('course-create-rerun.html', {
                'source_course_key': course_key,
                'display_name': course_module.display_name,
                'user': request.user,
                'course_creator_status': _get_course_creator_status(request.user),
                'allow_unicode_course_id': settings.FEATURES.get('ALLOW_UNICODE_COURSE_ID', False)
            })


@login_required
@ensure_csrf_cookie
@require_GET
def course_search_index_handler(request, course_key_string):
    """
    The restful handler for course indexing.
    GET
        html: return status of indexing task
        json: return status of indexing task
    """
    # Only global staff (PMs) are able to index courses
    if not GlobalStaff().has_user(request.user):
        raise PermissionDenied()
    course_key = CourseKey.from_string(course_key_string)
    content_type = request.META.get('CONTENT_TYPE', None)
    if content_type is None:
        content_type = "application/json; charset=utf-8"
    with modulestore().bulk_operations(course_key):
        try:
            reindex_course_and_check_access(course_key, request.user)
        except SearchIndexingError as search_err:
            return HttpResponse(dump_js_escaped_json({
                "user_message": search_err.error_list
            }), content_type=content_type, status=500)
        return HttpResponse(dump_js_escaped_json({
            "user_message": _("Course has been successfully reindexed.")
        }), content_type=content_type, status=200)


def _course_outline_json(request, course_module):
    """
    Returns a JSON representation of the course module and recursively all of its children.
    """
    is_concise = request.GET.get('format') == 'concise'
    include_children_predicate = lambda xblock: not xblock.category == 'vertical'
    if is_concise:
        include_children_predicate = lambda xblock: xblock.has_children
    return create_xblock_info(
        course_module,
        include_child_info=True,
        course_outline=False if is_concise else True,
        include_children_predicate=include_children_predicate,
        is_concise=is_concise,
        user=request.user
    )


def get_in_process_course_actions(request):
    """
     Get all in-process course actions
    """
    return [
        course for course in
        CourseRerunState.objects.find_all(
            exclude_args={'state': CourseRerunUIStateManager.State.SUCCEEDED},
            should_display=True,
        )
        if has_studio_read_access(request.user, course.course_key)
    ]


def _accessible_courses_summary_iter(request, org=None):
    """
    List all courses available to the logged in user by iterating through all the courses

    Arguments:
        request: the request object
        org (string): if not None, this value will limit the courses returned. An empty
            string will result in no courses, and otherwise only courses with the
            specified org will be returned. The default value is None.
    """
    def course_filter(course_summary):
        """
        Filter out unusable and inaccessible courses
        """
        # pylint: disable=fixme
        # TODO remove this condition when templates purged from db
        if course_summary.location.course == 'templates':
            return False

        return has_studio_read_access(request.user, course_summary.id)
    if org is not None:
        courses_summary = [] if org == '' else CourseOverview.get_all_courses(orgs=[org])
    else:
        courses_summary = modulestore().get_course_summaries()
    courses_summary = six.moves.filter(course_filter, courses_summary)
    in_process_course_actions = get_in_process_course_actions(request)
    return courses_summary, in_process_course_actions


def _accessible_courses_iter(request):
    """
    List all courses available to the logged in user by iterating through all the courses.
    """
    def course_filter(course):
        """
        Filter out unusable and inaccessible courses
        """
        if isinstance(course, ErrorDescriptor):
            return False

        # Custom Courses for edX (CCX) is an edX feature for re-using course content.
        # CCXs cannot be edited in Studio (aka cms) and should not be shown in this dashboard.
        if isinstance(course.id, CCXLocator):
            return False

        # pylint: disable=fixme
        # TODO remove this condition when templates purged from db
        if course.location.course == 'templates':
            return False

        return has_studio_read_access(request.user, course.id)

    courses = six.moves.filter(course_filter, modulestore().get_courses())

    in_process_course_actions = get_in_process_course_actions(request)
    return courses, in_process_course_actions


def _accessible_courses_iter_for_tests(request):
    """
    List all courses available to the logged in user by iterating through all the courses.
    CourseSummary objects are used for listing purposes.
    This method is only used by tests.
    """
    def course_filter(course):
        """
        Filter out unusable and inaccessible courses
        """

        # Custom Courses for edX (CCX) is an edX feature for re-using course content.
        # CCXs cannot be edited in Studio (aka cms) and should not be shown in this dashboard.
        if isinstance(course.id, CCXLocator):
            return False

        # pylint: disable=fixme
        # TODO remove this condition when templates purged from db
        if course.location.course == 'templates':
            return False

        return has_studio_read_access(request.user, course.id)

    courses = six.moves.filter(course_filter, modulestore().get_course_summaries())

    in_process_course_actions = get_in_process_course_actions(request)
    return courses, in_process_course_actions


def _accessible_courses_list_from_groups(request):
    """
    List all courses available to the logged in user by reversing access group names
    """
    def filter_ccx(course_access):
        """ CCXs cannot be edited in Studio and should not be shown in this dashboard """
        return not isinstance(course_access.course_id, CCXLocator)

    instructor_courses = UserBasedRole(request.user, CourseInstructorRole.ROLE).courses_with_role()
    staff_courses = UserBasedRole(request.user, CourseStaffRole.ROLE).courses_with_role()
    all_courses = list(filter(filter_ccx, instructor_courses | staff_courses))
    courses_list = []
    course_keys = {}

    for course_access in all_courses:
        if course_access.course_id is None:
            raise AccessListFallback
        course_keys[course_access.course_id] = course_access.course_id

    course_keys = list(course_keys.values())

    if course_keys:
        courses_list = modulestore().get_course_summaries(course_keys=course_keys)

    return courses_list, []


def _accessible_libraries_iter(user, org=None):
    """
    List all libraries available to the logged in user by iterating through all libraries.

    org (string): if not None, this value will limit the libraries returned. An empty
        string will result in no libraries, and otherwise only libraries with the
        specified org will be returned. The default value is None.
    """
    if org is not None:
        libraries = [] if org == '' else modulestore().get_libraries(org=org)
    else:
        libraries = modulestore().get_library_summaries()
    # No need to worry about ErrorDescriptors - split's get_libraries() never returns them.
    return (lib for lib in libraries if has_studio_read_access(user, lib.location.library_key))


@login_required
@ensure_csrf_cookie
def course_listing(request):
    """
    List all courses and libraries available to the logged in user
    """

    optimization_enabled = GlobalStaff().has_user(request.user) and \
        WaffleSwitchNamespace(name=WAFFLE_NAMESPACE).is_enabled(u'enable_global_staff_optimization')

    org = request.GET.get('org', '') if optimization_enabled else None
    courses_iter, in_process_course_actions = get_courses_accessible_to_user(request, org)
    user = request.user
    libraries = _accessible_libraries_iter(request.user, org) if LIBRARIES_ENABLED else []

    def format_in_process_course_view(uca):
        """
        Return a dict of the data which the view requires for each unsucceeded course
        """
        return {
            u'display_name': uca.display_name,
            u'course_key': six.text_type(uca.course_key),
            u'org': uca.course_key.org,
            u'number': uca.course_key.course,
            u'run': uca.course_key.run,
            u'is_failed': True if uca.state == CourseRerunUIStateManager.State.FAILED else False,
            u'is_in_progress': True if uca.state == CourseRerunUIStateManager.State.IN_PROGRESS else False,
            u'dismiss_link': reverse_course_url(
                u'course_notifications_handler',
                uca.course_key,
                kwargs={
                    u'action_state_id': uca.id,
                },
            ) if uca.state == CourseRerunUIStateManager.State.FAILED else u''
        }

    def format_library_for_view(library):
        """
        Return a dict of the data which the view requires for each library
        """

        return {
            u'display_name': library.display_name,
            u'library_key': six.text_type(library.location.library_key),
            u'url': reverse_library_url(u'library_handler', six.text_type(library.location.library_key)),
            u'org': library.display_org_with_default,
            u'number': library.display_number_with_default,
            u'can_edit': has_studio_write_access(request.user, library.location.library_key),
        }

    microsite = SiteConfiguration.objects.all()

    #update template tma atp
    user_email = request.user.email
    current_date = int(datetime.datetime.now().strftime("%s"))
    course_scheduled = [[],[],[],[],[]]
    course_in_progress = [[],[],[],[],[]]
    course_completed = [[],[],[],[],[]]
    amundi_template = [[],[],[],[],[]]
    check_admin_microsite = False
    _active_camp = False

    split_archived = settings.FEATURES.get(u'ENABLE_SEPARATE_ARCHIVED_COURSES', False)
    active_courses, archived_courses = _process_courses_list(courses_iter, in_process_course_actions, split_archived)
    in_process_course_actions = [format_in_process_course_view(uca) for uca in in_process_course_actions]
    log.info(active_courses)
    for course_info in sorted(active_courses, key=lambda s: s['display_name'].lower() if s['display_name'] is not None else ''):
      q={}
      q['course_key_id'] = CourseKey.from_string(course_info['course_key'])
      is_true = False
      q['staf_users'] = CourseStaffRole(q['course_key_id']).users_with_role()
      for n in q['staf_users']:
        if n.email == user_email or request.user.is_staff:
           is_true = True
      q['course_info'] = course_info
      q['is_true'] = is_true
      q['courses_overviews'] = CourseOverview.get_from_id(q['course_key_id'])
      q['courses_stats'] = CourseOverview.get_from_id(q['course_key_id'])
      log.info(q['courses_stats'])
      q['categories'] = q['courses_stats'].categ
      q['course_img'] = q['courses_overviews'].image_urls
      q['course_start'] = q['courses_overviews'].start.strftime('%Y-%m-%d')
      q['course_end'] = ''
      if q['courses_overviews'].end:
        q['course_end'] = q['courses_overviews'].end.strftime('%Y-%m-%d')
        q['course_end_compare'] = int(q['courses_overviews'].end.strftime("%s"))
      else:
        q['course_end_compare'] = current_date
      q['course_start_compare'] = int(q['courses_overviews'].start.strftime("%s"))
      q['duration'] = q['courses_overviews'].effort

      #indice
      sorted_indices = {
        "fundamentals":0,
        "fundamental":0,
        "oursolutions":1,
        "regulatory":2,
        "salesapproach":3,
        "none":4
      }
      if q['categories'] is not None and  q['categories'] in sorted_indices:
          cur_indice = sorted_indices[q['categories'].lower().replace(' ','')]
      else:
          cur_indice = 4

      #sort by arrays
      log.info(course_info)
      if (not 'AMUNDI-GENERIC-TEMPLATE' in course_info['display_name']) and (current_date < q['course_start_compare']) and is_true and (not q['course_key_id'] in course_scheduled):
           course_scheduled[cur_indice].append(q)
           _active_camp = True
      elif (not 'AMUNDI-GENERIC-TEMPLATE' in course_info['display_name']) and (current_date > q['course_start_compare'] and current_date <= q['course_end_compare']) and is_true and (not q['course_key_id'] in course_in_progress):
           course_in_progress[cur_indice].append(q)
           _active_camp = True
      elif (not 'AMUNDI-GENERIC-TEMPLATE' in course_info['display_name']) and (current_date > q['course_end_compare']) and is_true and (not q['course_key_id'] in course_completed):
           course_completed[cur_indice].append(q)
           _active_camp = True
      elif ('AMUNDI-GENERIC-TEMPLATE' in course_info['display_name']) and (not q['course_key_id'] in amundi_template):
           amundi_template[cur_indice].append(q)

    return render_to_response(u'index.html', {

        u'courses': active_courses,
        u'archived_courses': archived_courses,
        u'in_process_course_actions': in_process_course_actions,
        u'libraries_enabled': LIBRARIES_ENABLED,
        u'libraries': [format_library_for_view(lib) for lib in libraries],
        u'show_new_library_button': get_library_creator_status(user),
        u'user': user,
        u'request_course_creator_url': reverse('request_course_creator'),
        u'course_creator_status': _get_course_creator_status(user),
        u'rerun_creator_status': GlobalStaff().has_user(user),
        u'allow_unicode_course_id': settings.FEATURES.get(u'ALLOW_UNICODE_COURSE_ID', False),
        u'allow_course_reruns': settings.FEATURES.get(u'ALLOW_COURSE_RERUNS', True),
        u'optimization_enabled': optimization_enabled,
        u'course_scheduled':course_scheduled,
        u'course_in_progress':course_in_progress,
        u'course_completed':course_completed,
        u'amundi_template':amundi_template,
        u'active_campaign':_active_camp,
        u'language_options_dict':get_list_lang()
    })


def _get_rerun_link_for_item(course_key):
    """ Returns the rerun link for the given course key. """
    return reverse_course_url('course_rerun_handler', course_key)


def _deprecated_blocks_info(course_module, deprecated_block_types):
    """
    Returns deprecation information about `deprecated_block_types`

    Arguments:
        course_module (CourseDescriptor): course object
        deprecated_block_types (list): list of deprecated blocks types

    Returns:
        Dict with following keys:
        deprecated_enabled_block_types (list): list containing all deprecated blocks types enabled on this course
        blocks (list): List of `deprecated_enabled_block_types` instances and their parent's url
        advance_settings_url (str): URL to advance settings page
    """
    data = {
        'deprecated_enabled_block_types': [
            block_type for block_type in course_module.advanced_modules if block_type in deprecated_block_types
        ],
        'blocks': [],
        'advance_settings_url': reverse_course_url('advanced_settings_handler', course_module.id)
    }

    deprecated_blocks = modulestore().get_items(
        course_module.id,
        qualifiers={
            'category': re.compile('^' + '$|^'.join(deprecated_block_types) + '$')
        }
    )

    for block in deprecated_blocks:
        data['blocks'].append([
            reverse_usage_url('container_handler', block.parent),
            block.display_name
        ])

    return data


@login_required
@ensure_csrf_cookie
def course_index(request, course_key):
    """
    Display an editable course overview.

    org, course, name: Attributes of the Location for the item to edit
    """
    # A depth of None implies the whole course. The course outline needs this in order to compute has_changes.
    # A unit may not have a draft version, but one of its components could, and hence the unit itself has changes.
    with modulestore().bulk_operations(course_key):
        course_module = get_course_and_check_access(course_key, request.user, depth=None)
        if not course_module:
            raise Http404
        lms_link = get_lms_link_for_item(course_module.location)
        reindex_link = None
        if settings.FEATURES.get('ENABLE_COURSEWARE_INDEX', False):
            if GlobalStaff().has_user(request.user):
                reindex_link = "/course/{course_id}/search_reindex".format(course_id=six.text_type(course_key))
        sections = course_module.get_children()
        course_structure = _course_outline_json(request, course_module)
        locator_to_show = request.GET.get('show', None)

        course_release_date = (
            get_default_time_display(course_module.start)
            if course_module.start != DEFAULT_START_DATE
            else _("Set Date")
        )

        settings_url = reverse_course_url('settings_handler', course_key)

        try:
            current_action = CourseRerunState.objects.find_first(course_key=course_key, should_display=True)
        except (ItemNotFoundError, CourseActionStateItemNotFoundError):
            current_action = None

        deprecated_block_names = [block.name for block in deprecated_xblocks()]
        deprecated_blocks_info = _deprecated_blocks_info(course_module, deprecated_block_names)

        frontend_app_publisher_url = configuration_helpers.get_value_for_org(
            course_module.location.org,
            'FRONTEND_APP_PUBLISHER_URL',
            settings.FEATURES.get('FRONTEND_APP_PUBLISHER_URL', False)
        )

        return render_to_response('course_outline.html', {
            'language_code': request.LANGUAGE_CODE,
            'context_course': course_module,
            'lms_link': lms_link,
            'sections': sections,
            'course_structure': course_structure,
            'initial_state': course_outline_initial_state(locator_to_show, course_structure) if locator_to_show else None,
            'rerun_notification_id': current_action.id if current_action else None,
            'course_release_date': course_release_date,
            'settings_url': settings_url,
            'reindex_link': reindex_link,
            'deprecated_blocks_info': deprecated_blocks_info,
            'notification_dismiss_url': reverse_course_url(
                'course_notifications_handler',
                current_action.course_key,
                kwargs={
                    'action_state_id': current_action.id,
                },
            ) if current_action else None,
            'frontend_app_publisher_url': frontend_app_publisher_url,
        })


def get_courses_accessible_to_user(request, org=None):
    """
    Try to get all courses by first reversing django groups and fallback to old method if it fails
    Note: overhead of pymongo reads will increase if getting courses from django groups fails

    Arguments:
        request: the request object
        org (string): for global staff users ONLY, this value will be used to limit
            the courses returned. A value of None will have no effect (all courses
            returned), an empty string will result in no courses, and otherwise only courses with the
            specified org will be returned. The default value is None.
    """
    if GlobalStaff().has_user(request.user):
        # user has global access so no need to get courses from django groups
        courses, in_process_course_actions = _accessible_courses_summary_iter(request, org)
    else:
        try:
            courses, in_process_course_actions = _accessible_courses_list_from_groups(request)
        except AccessListFallback:
            # user have some old groups or there was some error getting courses from django groups
            # so fallback to iterating through all courses
            courses, in_process_course_actions = _accessible_courses_summary_iter(request)
    return courses, in_process_course_actions


def _process_courses_list(courses_iter, in_process_course_actions, split_archived=False):
    """
    Iterates over the list of courses to be displayed to the user, and:

    * Removes any in-process courses from the courses list. "In-process" refers to courses
      that are in the process of being generated for re-run.
    * If split_archived=True, removes any archived courses and returns them in a separate list.
      Archived courses have has_ended() == True.
    * Formats the returned courses (in both lists) to prepare them for rendering to the view.
    """
    def format_course_for_view(course):
        """
        Return a dict of the data which the view requires for each course
        """
        return {
            'display_name': course.display_name,
            'course_key': six.text_type(course.location.course_key),
            'url': reverse_course_url('course_handler', course.id),
            'lms_link': get_lms_link_for_item(course.location),
            'rerun_link': _get_rerun_link_for_item(course.id),
            'org': course.display_org_with_default,
            'number': course.display_number_with_default,
            'run': course.location.run
        }

    in_process_action_course_keys = {uca.course_key for uca in in_process_course_actions}
    active_courses = []
    archived_courses = []

    for course in courses_iter:
        if isinstance(course, ErrorDescriptor) or (course.id in in_process_action_course_keys):
            continue

        formatted_course = format_course_for_view(course)
        if split_archived and course.has_ended():
            archived_courses.append(formatted_course)
        else:
            active_courses.append(formatted_course)

    return active_courses, archived_courses


def course_outline_initial_state(locator_to_show, course_structure):
    """
    Returns the desired initial state for the course outline view. If the 'show' request parameter
    was provided, then the view's initial state will be to have the desired item fully expanded
    and to scroll to see the new item.
    """
    def find_xblock_info(xblock_info, locator):
        """
        Finds the xblock info for the specified locator.
        """
        if xblock_info['id'] == locator:
            return xblock_info
        children = xblock_info['child_info']['children'] if xblock_info.get('child_info', None) else None
        if children:
            for child_xblock_info in children:
                result = find_xblock_info(child_xblock_info, locator)
                if result:
                    return result
        return None

    def collect_all_locators(locators, xblock_info):
        """
        Collect all the locators for an xblock and its children.
        """
        locators.append(xblock_info['id'])
        children = xblock_info['child_info']['children'] if xblock_info.get('child_info', None) else None
        if children:
            for child_xblock_info in children:
                collect_all_locators(locators, child_xblock_info)

    selected_xblock_info = find_xblock_info(course_structure, locator_to_show)
    if not selected_xblock_info:
        return None
    expanded_locators = []
    collect_all_locators(expanded_locators, selected_xblock_info)
    return {
        'locator_to_show': locator_to_show,
        'expanded_locators': expanded_locators
    }


@expect_json
def _create_or_rerun_course(request):
    """
    To be called by requests that create a new destination course (i.e., create_new_course and rerun_course)
    Returns the destination course_key and overriding fields for the new course.
    Raises DuplicateCourseError and InvalidKeyError
    """
    if not auth.user_has_role(request.user, CourseCreatorRole()):
        raise PermissionDenied()

    try:
        org = request.json.get('org')
        course = request.json.get('number', request.json.get('course'))
        display_name = request.json.get('display_name')
        # force the start date for reruns and allow us to override start via the client
        start = request.json.get('start', CourseFields.start.default)
        run = request.json.get('run')

        # allow/disable unicode characters in course_id according to settings
        if not settings.FEATURES.get('ALLOW_UNICODE_COURSE_ID'):
            if _has_non_ascii_characters(org) or _has_non_ascii_characters(course) or _has_non_ascii_characters(run):
                return JsonResponse(
                    {'error': _('Special characters not allowed in organization, course number, and course run.')},
                    status=400
                )

        fields = {'start': start}
        if display_name is not None:
            fields['display_name'] = display_name

        # Set a unique wiki_slug for newly created courses. To maintain active wiki_slugs for
        # existing xml courses this cannot be changed in CourseDescriptor.
        # # TODO get rid of defining wiki slug in this org/course/run specific way and reconcile
        # w/ xmodule.course_module.CourseDescriptor.__init__
        wiki_slug = u"{0}.{1}.{2}".format(org, course, run)
        definition_data = {'wiki_slug': wiki_slug}
        fields.update(definition_data)

        source_course_key = request.json.get('source_course_key')
        if source_course_key:
            source_course_key = CourseKey.from_string(source_course_key)
            destination_course_key = rerun_course(request.user, source_course_key, org, course, run, fields)
            return JsonResponse({
                'url': reverse_url('course_handler'),
                'destination_course_key': six.text_type(destination_course_key)
            })
        else:
            try:
                new_course = create_new_course(request.user, org, course, run, fields)
                return JsonResponse({
                    'url': reverse_course_url('course_handler', new_course.id),
                    'course_key': six.text_type(new_course.id),
                })
            except ValidationError as ex:
                return JsonResponse({'error': text_type(ex)}, status=400)
    except DuplicateCourseError:
        return JsonResponse({
            'ErrMsg': _(
                'There is already a course defined with the same '
                'organization and course number. Please '
                'change either organization or course number to be unique.'
            ),
            'OrgErrMsg': _(
                'Please change either the organization or '
                'course number so that it is unique.'),
            'CourseErrMsg': _(
                'Please change either the organization or '
                'course number so that it is unique.'),
        })
    except InvalidKeyError as error:
        return JsonResponse({
            "ErrMsg": _(u"Unable to create course '{name}'.\n\n{err}").format(name=display_name, err=text_type(error))}
        )


def create_new_course(user, org, number, run, fields):
    """
    Create a new course run.

    Raises:
        DuplicateCourseError: Course run already exists.
    """
    org_data = get_organization_by_short_name(org)
    if not org_data and organizations_enabled():
        raise ValidationError(_('You must link this course to an organization in order to continue. Organization '
                                'you selected does not exist in the system, you will need to add it to the system'))
    store_for_new_course = modulestore().default_modulestore.get_modulestore_type()
    new_course = create_new_course_in_store(store_for_new_course, user, org, number, run, fields)
    add_organization_course(org_data, new_course.id)
    return new_course


def create_new_course_in_store(store, user, org, number, run, fields):
    """
    Create course in store w/ handling instructor enrollment, permissions, and defaulting the wiki slug.
    Separated out b/c command line course creation uses this as well as the web interface.
    """

    # Set default language from settings and enable web certs
    fields.update({
        'language': getattr(settings, 'DEFAULT_COURSE_LANGUAGE', 'en'),
        'cert_html_view_enabled': True,
    })

    with modulestore().default_store(store):
        # Creating the course raises DuplicateCourseError if an existing course with this org/name is found
        new_course = modulestore().create_course(
            org,
            number,
            run,
            user.id,
            fields=fields,
        )

    # Make sure user has instructor and staff access to the new course
    add_instructor(new_course.id, user, user)

    # Initialize permissions for user in the new course
    initialize_permissions(new_course.id, user)
    log.info(new_course.language)
    return new_course


def rerun_course(user, source_course_key, org, number, run, fields, background=True):
    """
    Rerun an existing course.
    """
    # verify user has access to the original course
    if not has_studio_write_access(user, source_course_key):
        raise PermissionDenied()

    # create destination course key
    store = modulestore()
    with store.default_store('split'):
        destination_course_key = store.make_course_key(org, number, run)

    # verify org course and run don't already exist
    if store.has_course(destination_course_key, ignore_case=True):
        raise DuplicateCourseError(source_course_key, destination_course_key)

    # Make sure user has instructor and staff access to the destination course
    # so the user can see the updated status for that course
    add_instructor(destination_course_key, user, user)

    # Mark the action as initiated
    CourseRerunState.objects.initiated(source_course_key, destination_course_key, user, fields['display_name'])

    # Clear the fields that must be reset for the rerun
    fields['advertised_start'] = None
    fields['enrollment_start'] = None
    fields['enrollment_end'] = None
    fields['video_upload_pipeline'] = {}

    json_fields = json.dumps(fields, cls=EdxJSONEncoder)
    args = [six.text_type(source_course_key), six.text_type(destination_course_key), user.id, json_fields]

    if background:
        rerun_course_task.delay(*args)
    else:
        rerun_course_task(*args)

    return destination_course_key


@login_required
@ensure_csrf_cookie
@require_http_methods(["GET"])
def course_info_handler(request, course_key_string):
    """
    GET
        html: return html for editing the course info handouts and updates.
    """
    try:
        course_key = CourseKey.from_string(course_key_string)
    except InvalidKeyError:
        raise Http404

    with modulestore().bulk_operations(course_key):
        course_module = get_course_and_check_access(course_key, request.user)
        if not course_module:
            raise Http404
        if 'text/html' in request.META.get('HTTP_ACCEPT', 'text/html'):
            return render_to_response(
                'course_info.html',
                {
                    'context_course': course_module,
                    'updates_url': reverse_course_url('course_info_update_handler', course_key),
                    'handouts_locator': course_key.make_usage_key('course_info', 'handouts'),
                    'base_asset_url': StaticContent.get_base_url_path_for_course_assets(course_module.id),
                }
            )
        else:
            return HttpResponseBadRequest("Only supports html requests")


@login_required
@ensure_csrf_cookie
@require_http_methods(("GET", "POST", "PUT", "DELETE"))
@expect_json
def course_info_update_handler(request, course_key_string, provided_id=None):
    """
    restful CRUD operations on course_info updates.
    provided_id should be none if it's new (create) and index otherwise.
    GET
        json: return the course info update models
    POST
        json: create an update
    PUT or DELETE
        json: change an existing update
    """
    if 'application/json' not in request.META.get('HTTP_ACCEPT', 'application/json'):
        return HttpResponseBadRequest("Only supports json requests")

    course_key = CourseKey.from_string(course_key_string)
    usage_key = course_key.make_usage_key('course_info', 'updates')
    if provided_id == '':
        provided_id = None

    # check that logged in user has permissions to this item (GET shouldn't require this level?)
    if not has_studio_write_access(request.user, usage_key.course_key):
        raise PermissionDenied()

    if request.method == 'GET':
        course_updates = get_course_updates(usage_key, provided_id, request.user.id)
        if isinstance(course_updates, dict) and course_updates.get('error'):
            return JsonResponse(course_updates, course_updates.get('status', 400))
        else:
            return JsonResponse(course_updates)
    elif request.method == 'DELETE':
        try:
            return JsonResponse(delete_course_update(usage_key, request.json, provided_id, request.user))
        except:
            return HttpResponseBadRequest(
                "Failed to delete",
                content_type="text/plain"
            )
    # can be either and sometimes django is rewriting one to the other:
    elif request.method in ('POST', 'PUT'):
        try:
            return JsonResponse(update_course_updates(usage_key, request.json, provided_id, request.user))
        except:
            return HttpResponseBadRequest(
                "Failed to save",
                content_type="text/plain"
            )


@login_required
@ensure_csrf_cookie
@require_http_methods(("GET", "PUT", "POST"))
@expect_json
def settings_handler(request, course_key_string):
    """
    Course settings for dates and about pages
    GET
        html: get the page
        json: get the CourseDetails model
    PUT
        json: update the Course and About xblocks through the CourseDetails model
    """
    course_key = CourseKey.from_string(course_key_string)
    credit_eligibility_enabled = settings.FEATURES.get('ENABLE_CREDIT_ELIGIBILITY', False)
    with modulestore().bulk_operations(course_key):
        course_module = get_course_and_check_access(course_key, request.user)
        if 'text/html' in request.META.get('HTTP_ACCEPT', '') and request.method == 'GET':
            upload_asset_url = reverse_course_url('assets_handler', course_key)

            # see if the ORG of this course can be attributed to a defined configuration . In that case, the
            # course about page should be editable in Studio
            publisher_enabled = configuration_helpers.get_value_for_org(
                course_module.location.org,
                'ENABLE_PUBLISHER',
                settings.FEATURES.get('ENABLE_PUBLISHER', False)
            )
            marketing_enabled = configuration_helpers.get_value_for_org(
                course_module.location.org,
                'ENABLE_MKTG_SITE',
                settings.FEATURES.get('ENABLE_MKTG_SITE', False)
            )
            enable_extended_course_details = configuration_helpers.get_value_for_org(
                course_module.location.org,
                'ENABLE_EXTENDED_COURSE_DETAILS',
                settings.FEATURES.get('ENABLE_EXTENDED_COURSE_DETAILS', False)
            )

            about_page_editable = not publisher_enabled
            enrollment_end_editable = GlobalStaff().has_user(request.user) or not publisher_enabled
            short_description_editable = configuration_helpers.get_value_for_org(
                course_module.location.org,
                'EDITABLE_SHORT_DESCRIPTION',
                settings.FEATURES.get('EDITABLE_SHORT_DESCRIPTION', True)
            )
            sidebar_html_enabled = course_experience_waffle().is_enabled(ENABLE_COURSE_ABOUT_SIDEBAR_HTML)
            # self_paced_enabled = SelfPacedConfiguration.current().enabled

            verified_mode = CourseMode.verified_mode_for_course(course_key, include_expired=True)
            upgrade_deadline = (verified_mode and verified_mode.expiration_datetime and
                                verified_mode.expiration_datetime.isoformat())

            settings_context = {
                'context_course': course_module,
                'course_locator': course_key,
                'lms_link_for_about_page': get_link_for_about_page(course_module),
                'course_image_url': course_image_url(course_module, 'course_image'),
                'banner_image_url': course_image_url(course_module, 'banner_image'),
                'video_thumbnail_image_url': course_image_url(course_module, 'video_thumbnail_image'),
                'details_url': reverse_course_url('settings_handler', course_key),
                'about_page_editable': about_page_editable,
                'marketing_enabled': marketing_enabled,
                'short_description_editable': short_description_editable,
                'sidebar_html_enabled': sidebar_html_enabled,
                'upload_asset_url': upload_asset_url,
                'course_handler_url': reverse_course_url('course_handler', course_key),
                'language_options': settings.ALL_LANGUAGES,
                'credit_eligibility_enabled': credit_eligibility_enabled,
                'is_credit_course': False,
                'show_min_grade_warning': False,
                'enrollment_end_editable': enrollment_end_editable,
                'is_prerequisite_courses_enabled': is_prerequisite_courses_enabled(),
                'is_entrance_exams_enabled': is_entrance_exams_enabled(),
                'enable_extended_course_details': enable_extended_course_details,
                'upgrade_deadline': upgrade_deadline,
            }
            if is_prerequisite_courses_enabled():
                courses, in_process_course_actions = get_courses_accessible_to_user(request)
                # exclude current course from the list of available courses
                courses = (course for course in courses if course.id != course_key)
                if courses:
                    courses, __ = _process_courses_list(courses, in_process_course_actions)
                settings_context.update({'possible_pre_requisite_courses': list(courses)})

            if credit_eligibility_enabled:
                if is_credit_course(course_key):
                    # get and all credit eligibility requirements
                    credit_requirements = get_credit_requirements(course_key)
                    # pair together requirements with same 'namespace' values
                    paired_requirements = {}
                    for requirement in credit_requirements:
                        namespace = requirement.pop("namespace")
                        paired_requirements.setdefault(namespace, []).append(requirement)

                    # if 'minimum_grade_credit' of a course is not set or 0 then
                    # show warning message to course author.
                    show_min_grade_warning = False if course_module.minimum_grade_credit > 0 else True
                    settings_context.update(
                        {
                            'is_credit_course': True,
                            'credit_requirements': paired_requirements,
                            'show_min_grade_warning': show_min_grade_warning,
                        }
                    )

            return render_to_response('settings.html', settings_context)
        elif 'application/json' in request.META.get('HTTP_ACCEPT', ''):
            if request.method == 'GET':
                course_details = CourseDetails.fetch(course_key)
                return JsonResponse(
                    course_details,
                    # encoder serializes dates, old locations, and instances
                    encoder=CourseSettingsEncoder
                )
            # For every other possible method type submitted by the caller...
            else:
                # if pre-requisite course feature is enabled set pre-requisite course
                if is_prerequisite_courses_enabled():
                    prerequisite_course_keys = request.json.get('pre_requisite_courses', [])
                    if prerequisite_course_keys:
                        if not all(is_valid_course_key(course_key) for course_key in prerequisite_course_keys):
                            return JsonResponseBadRequest({"error": _("Invalid prerequisite course key")})
                        set_prerequisite_courses(course_key, prerequisite_course_keys)
                    else:
                        # None is chosen, so remove the course prerequisites
                        course_milestones = milestones_api.get_course_milestones(course_key=course_key, relationship="requires")
                        for milestone in course_milestones:
                            remove_prerequisite_course(course_key, milestone)

                # If the entrance exams feature has been enabled, we'll need to check for some
                # feature-specific settings and handle them accordingly
                # We have to be careful that we're only executing the following logic if we actually
                # need to create or delete an entrance exam from the specified course
                if is_entrance_exams_enabled():
                    course_entrance_exam_present = course_module.entrance_exam_enabled
                    entrance_exam_enabled = request.json.get('entrance_exam_enabled', '') == 'true'
                    ee_min_score_pct = request.json.get('entrance_exam_minimum_score_pct', None)
                    # If the entrance exam box on the settings screen has been checked...
                    if entrance_exam_enabled:
                        # Load the default minimum score threshold from settings, then try to override it
                        entrance_exam_minimum_score_pct = float(settings.ENTRANCE_EXAM_MIN_SCORE_PCT)
                        if ee_min_score_pct:
                            entrance_exam_minimum_score_pct = float(ee_min_score_pct)
                        if entrance_exam_minimum_score_pct.is_integer():
                            entrance_exam_minimum_score_pct = entrance_exam_minimum_score_pct / 100
                        # If there's already an entrance exam defined, we'll update the existing one
                        if course_entrance_exam_present:
                            exam_data = {
                                'entrance_exam_minimum_score_pct': entrance_exam_minimum_score_pct
                            }
                            update_entrance_exam(request, course_key, exam_data)
                        # If there's no entrance exam defined, we'll create a new one
                        else:
                            create_entrance_exam(request, course_key, entrance_exam_minimum_score_pct)

                    # If the entrance exam box on the settings screen has been unchecked,
                    # and the course has an entrance exam attached...
                    elif not entrance_exam_enabled and course_entrance_exam_present:
                        delete_entrance_exam(request, course_key)

                # Perform the normal update workflow for the CourseDetails model
                return JsonResponse(
                    CourseDetails.update_from_json(course_key, request.json, request.user),
                    encoder=CourseSettingsEncoder
                )


@login_required
@ensure_csrf_cookie
@require_http_methods(("GET", "POST", "PUT", "DELETE"))
@expect_json
def grading_handler(request, course_key_string, grader_index=None):
    """
    Course Grading policy configuration
    GET
        html: get the page
        json no grader_index: get the CourseGrading model (graceperiod, cutoffs, and graders)
        json w/ grader_index: get the specific grader
    PUT
        json no grader_index: update the Course through the CourseGrading model
        json w/ grader_index: create or update the specific grader (create if index out of range)
    """
    course_key = CourseKey.from_string(course_key_string)
    with modulestore().bulk_operations(course_key):
        course_module = get_course_and_check_access(course_key, request.user)

        if 'text/html' in request.META.get('HTTP_ACCEPT', '') and request.method == 'GET':
            course_details = CourseGradingModel.fetch(course_key)

            return render_to_response('settings_graders.html', {
                'context_course': course_module,
                'course_locator': course_key,
                'course_details': course_details,
                'grading_url': reverse_course_url('grading_handler', course_key),
                'is_credit_course': is_credit_course(course_key),
            })
        elif 'application/json' in request.META.get('HTTP_ACCEPT', ''):
            if request.method == 'GET':
                if grader_index is None:
                    return JsonResponse(
                        CourseGradingModel.fetch(course_key),
                        # encoder serializes dates, old locations, and instances
                        encoder=CourseSettingsEncoder
                    )
                else:
                    return JsonResponse(CourseGradingModel.fetch_grader(course_key, grader_index))
            elif request.method in ('POST', 'PUT'):  # post or put, doesn't matter.
                # update credit course requirements if 'minimum_grade_credit'
                # field value is changed
                if 'minimum_grade_credit' in request.json:
                    update_credit_course_requirements.delay(six.text_type(course_key))

                # None implies update the whole model (cutoffs, graceperiod, and graders) not a specific grader
                if grader_index is None:
                    return JsonResponse(
                        CourseGradingModel.update_from_json(course_key, request.json, request.user),
                        encoder=CourseSettingsEncoder
                    )
                else:
                    return JsonResponse(
                        CourseGradingModel.update_grader_from_json(course_key, request.json, request.user)
                    )
            elif request.method == "DELETE" and grader_index is not None:
                CourseGradingModel.delete_grader(course_key, grader_index, request.user)
                return JsonResponse()


def _refresh_course_tabs(request, course_module):
    """
    Automatically adds/removes tabs if changes to the course require them.

    Raises:
        InvalidTabsException: raised if there's a problem with the new version of the tabs.
    """

    def update_tab(tabs, tab_type, tab_enabled):
        """
        Adds or removes a course tab based upon whether it is enabled.
        """
        tab_panel = {
            "type": tab_type.type,
        }
        has_tab = tab_panel in tabs
        if tab_enabled and not has_tab:
            tabs.append(CourseTab.from_json(tab_panel))
        elif not tab_enabled and has_tab:
            tabs.remove(tab_panel)

    course_tabs = copy.copy(course_module.tabs)

    # Additionally update any tabs that are provided by non-dynamic course views
    for tab_type in CourseTabPluginManager.get_tab_types():
        if not tab_type.is_dynamic and tab_type.is_default:
            tab_enabled = tab_type.is_enabled(course_module, user=request.user)
            update_tab(course_tabs, tab_type, tab_enabled)

    CourseTabList.validate_tabs(course_tabs)

    # Save the tabs into the course if they have been changed
    if course_tabs != course_module.tabs:
        course_module.tabs = course_tabs


@login_required
@ensure_csrf_cookie
@require_http_methods(("GET", "POST", "PUT"))
@expect_json
def advanced_settings_handler(request, course_key_string):
    """
    Course settings configuration
    GET
        html: get the page
        json: get the model
    PUT, POST
        json: update the Course's settings. The payload is a json rep of the
            metadata dicts.
    """
    course_key = CourseKey.from_string(course_key_string)
    with modulestore().bulk_operations(course_key):
        course_module = get_course_and_check_access(course_key, request.user)
        if 'text/html' in request.META.get('HTTP_ACCEPT', '') and request.method == 'GET':
            publisher_enabled = configuration_helpers.get_value_for_org(
                course_module.location.org,
                'ENABLE_PUBLISHER',
                settings.FEATURES.get('ENABLE_PUBLISHER', False)
            )

            return render_to_response('settings_advanced.html', {
                'context_course': course_module,
                'advanced_dict': CourseMetadata.fetch(course_module),
                'advanced_settings_url': reverse_course_url('advanced_settings_handler', course_key),
                'publisher_enabled': publisher_enabled,

            })
        elif 'application/json' in request.META.get('HTTP_ACCEPT', ''):
            if request.method == 'GET':
                return JsonResponse(CourseMetadata.fetch(course_module))
            else:
                try:
                    # validate data formats and update the course module.
                    # Note: don't update mongo yet, but wait until after any tabs are changed
                    is_valid, errors, updated_data = CourseMetadata.validate_and_update_from_json(
                        course_module,
                        request.json,
                        user=request.user,
                    )

                    if is_valid:
                        try:
                            # update the course tabs if required by any setting changes
                            _refresh_course_tabs(request, course_module)
                        except InvalidTabsException as err:
                            log.exception(text_type(err))
                            response_message = [
                                {
                                    'message': _('An error occurred while trying to save your tabs'),
                                    'model': {'display_name': _('Tabs Exception')}
                                }
                            ]
                            return JsonResponseBadRequest(response_message)

                        # now update mongo
                        modulestore().update_item(course_module, request.user.id)

                        return JsonResponse(updated_data)
                    else:
                        return JsonResponseBadRequest(errors)

                # Handle all errors that validation doesn't catch
                except (TypeError, ValueError, InvalidTabsException) as err:
                    return HttpResponseBadRequest(
                        django.utils.html.escape(text_type(err)),
                        content_type="text/plain"
                    )


class TextbookValidationError(Exception):
    "An error thrown when a textbook input is invalid"
    pass


def validate_textbooks_json(text):
    """
    Validate the given text as representing a single PDF textbook
    """
    if isinstance(text, (bytes, bytearray)):  # data appears as bytes
        text = text.decode('utf-8')
    try:
        textbooks = json.loads(text)
    except ValueError:
        raise TextbookValidationError("invalid JSON")
    if not isinstance(textbooks, (list, tuple)):
        raise TextbookValidationError("must be JSON list")
    for textbook in textbooks:
        validate_textbook_json(textbook)
    # check specified IDs for uniqueness
    all_ids = [textbook["id"] for textbook in textbooks if "id" in textbook]
    unique_ids = set(all_ids)
    if len(all_ids) > len(unique_ids):
        raise TextbookValidationError("IDs must be unique")
    return textbooks


def validate_textbook_json(textbook):
    """
    Validate the given text as representing a list of PDF textbooks
    """
    if isinstance(textbook, (bytes, bytearray)):  # data appears as bytes
        textbook = textbook.decode('utf-8')
    if isinstance(textbook, six.string_types):
        try:
            textbook = json.loads(textbook)
        except ValueError:
            raise TextbookValidationError("invalid JSON")
    if not isinstance(textbook, dict):
        raise TextbookValidationError("must be JSON object")
    if not textbook.get("tab_title"):
        raise TextbookValidationError("must have tab_title")
    tid = six.text_type(textbook.get("id", ""))
    if tid and not tid[0].isdigit():
        raise TextbookValidationError("textbook ID must start with a digit")
    return textbook


def assign_textbook_id(textbook, used_ids=()):
    """
    Return an ID that can be assigned to a textbook
    and doesn't match the used_ids
    """
    tid = BlockUsageLocator.clean(textbook["tab_title"])
    if not tid[0].isdigit():
        # stick a random digit in front
        tid = random.choice(string.digits) + tid
    while tid in used_ids:
        # add a random ASCII character to the end
        tid = tid + random.choice(string.ascii_lowercase)
    return tid


@require_http_methods(("GET", "POST", "PUT"))
@login_required
@ensure_csrf_cookie
def textbooks_list_handler(request, course_key_string):
    """
    A RESTful handler for textbook collections.

    GET
        html: return textbook list page (Backbone application)
        json: return JSON representation of all textbooks in this course
    POST
        json: create a new textbook for this course
    PUT
        json: overwrite all textbooks in the course with the given list
    """
    course_key = CourseKey.from_string(course_key_string)
    store = modulestore()
    with store.bulk_operations(course_key):
        course = get_course_and_check_access(course_key, request.user)

        if "application/json" not in request.META.get('HTTP_ACCEPT', 'text/html'):
            # return HTML page
            upload_asset_url = reverse_course_url('assets_handler', course_key)
            textbook_url = reverse_course_url('textbooks_list_handler', course_key)
            return render_to_response('textbooks.html', {
                'context_course': course,
                'textbooks': course.pdf_textbooks,
                'upload_asset_url': upload_asset_url,
                'textbook_url': textbook_url,
            })

        # from here on down, we know the client has requested JSON
        if request.method == 'GET':
            return JsonResponse(course.pdf_textbooks)
        elif request.method == 'PUT':
            try:
                textbooks = validate_textbooks_json(request.body)
            except TextbookValidationError as err:
                return JsonResponse({"error": text_type(err)}, status=400)

            tids = set(t["id"] for t in textbooks if "id" in t)
            for textbook in textbooks:
                if "id" not in textbook:
                    tid = assign_textbook_id(textbook, tids)
                    textbook["id"] = tid
                    tids.add(tid)

            if not any(tab['type'] == 'pdf_textbooks' for tab in course.tabs):
                course.tabs.append(CourseTab.load('pdf_textbooks'))
            course.pdf_textbooks = textbooks
            store.update_item(course, request.user.id)
            return JsonResponse(course.pdf_textbooks)
        elif request.method == 'POST':
            # create a new textbook for the course
            try:
                textbook = validate_textbook_json(request.body)
            except TextbookValidationError as err:
                return JsonResponse({"error": text_type(err)}, status=400)
            if not textbook.get("id"):
                tids = set(t["id"] for t in course.pdf_textbooks if "id" in t)
                textbook["id"] = assign_textbook_id(textbook, tids)
            existing = course.pdf_textbooks
            existing.append(textbook)
            course.pdf_textbooks = existing
            if not any(tab['type'] == 'pdf_textbooks' for tab in course.tabs):
                course.tabs.append(CourseTab.load('pdf_textbooks'))
            store.update_item(course, request.user.id)
            resp = JsonResponse(textbook, status=201)
            resp["Location"] = reverse_course_url(
                'textbooks_detail_handler',
                course.id,
                kwargs={'textbook_id': textbook["id"]}
            )
            return resp


@login_required
@ensure_csrf_cookie
@require_http_methods(("GET", "POST", "PUT", "DELETE"))
def textbooks_detail_handler(request, course_key_string, textbook_id):
    """
    JSON API endpoint for manipulating a textbook via its internal ID.
    Used by the Backbone application.

    GET
        json: return JSON representation of textbook
    POST or PUT
        json: update textbook based on provided information
    DELETE
        json: remove textbook
    """
    course_key = CourseKey.from_string(course_key_string)
    store = modulestore()
    with store.bulk_operations(course_key):
        course_module = get_course_and_check_access(course_key, request.user)
        matching_id = [tb for tb in course_module.pdf_textbooks
                       if six.text_type(tb.get("id")) == six.text_type(textbook_id)]
        if matching_id:
            textbook = matching_id[0]
        else:
            textbook = None

        if request.method == 'GET':
            if not textbook:
                return JsonResponse(status=404)
            return JsonResponse(textbook)
        elif request.method in ('POST', 'PUT'):  # can be either and sometimes django is rewriting one to the other
            try:
                new_textbook = validate_textbook_json(request.body)
            except TextbookValidationError as err:
                return JsonResponse({"error": text_type(err)}, status=400)
            new_textbook["id"] = textbook_id
            if textbook:
                i = course_module.pdf_textbooks.index(textbook)
                new_textbooks = course_module.pdf_textbooks[0:i]
                new_textbooks.append(new_textbook)
                new_textbooks.extend(course_module.pdf_textbooks[i + 1:])
                course_module.pdf_textbooks = new_textbooks
            else:
                course_module.pdf_textbooks.append(new_textbook)
            store.update_item(course_module, request.user.id)
            return JsonResponse(new_textbook, status=201)
        elif request.method == 'DELETE':
            if not textbook:
                return JsonResponse(status=404)
            i = course_module.pdf_textbooks.index(textbook)
            remaining_textbooks = course_module.pdf_textbooks[0:i]
            remaining_textbooks.extend(course_module.pdf_textbooks[i + 1:])
            course_module.pdf_textbooks = remaining_textbooks
            store.update_item(course_module, request.user.id)
            return JsonResponse()


def remove_content_or_experiment_group(request, store, course, configuration, group_configuration_id, group_id=None):
    """
    Remove content group or experiment group configuration only if it's not in use.
    """
    configuration_index = course.user_partitions.index(configuration)
    if configuration.scheme.name == RANDOM_SCHEME:
        usages = GroupConfiguration.get_content_experiment_usage_info(store, course)
        used = int(group_configuration_id) in usages

        if used:
            return JsonResponse(
                {"error": _("This group configuration is in use and cannot be deleted.")},
                status=400
            )
        course.user_partitions.pop(configuration_index)
    elif configuration.scheme.name == COHORT_SCHEME:
        if not group_id:
            return JsonResponse(status=404)

        group_id = int(group_id)
        usages = GroupConfiguration.get_partitions_usage_info(store, course)
        used = group_id in usages[configuration.id]

        if used:
            return JsonResponse(
                {"error": _("This content group is in use and cannot be deleted.")},
                status=400
            )

        matching_groups = [group for group in configuration.groups if group.id == group_id]
        if matching_groups:
            group_index = configuration.groups.index(matching_groups[0])
            configuration.groups.pop(group_index)
        else:
            return JsonResponse(status=404)

        course.user_partitions[configuration_index] = configuration

    store.update_item(course, request.user.id)
    return JsonResponse(status=204)


@require_http_methods(("GET", "POST"))
@login_required
@ensure_csrf_cookie
def group_configurations_list_handler(request, course_key_string):
    """
    A RESTful handler for Group Configurations

    GET
        html: return Group Configurations list page (Backbone application)
    POST
        json: create new group configuration
    """
    course_key = CourseKey.from_string(course_key_string)
    store = modulestore()
    with store.bulk_operations(course_key):
        course = get_course_and_check_access(course_key, request.user)

        if 'text/html' in request.META.get('HTTP_ACCEPT', 'text/html'):
            group_configuration_url = reverse_course_url('group_configurations_list_handler', course_key)
            course_outline_url = reverse_course_url('course_handler', course_key)
            should_show_experiment_groups = are_content_experiments_enabled(course)
            if should_show_experiment_groups:
                experiment_group_configurations = GroupConfiguration.get_split_test_partitions_with_usage(store, course)
            else:
                experiment_group_configurations = None

            all_partitions = GroupConfiguration.get_all_user_partition_details(store, course)
            should_show_enrollment_track = False
            has_content_groups = False
            displayable_partitions = []
            for partition in all_partitions:
                partition['read_only'] = getattr(UserPartition.get_scheme(partition['scheme']), 'read_only', False)

                if partition['scheme'] == COHORT_SCHEME:
                    has_content_groups = True
                    displayable_partitions.append(partition)
                elif partition['scheme'] == CONTENT_TYPE_GATING_SCHEME:
                    # Add it to the front of the list if it should be shown.
                    if ContentTypeGatingConfig.current(course_key=course_key).studio_override_enabled:
                        displayable_partitions.append(partition)
                elif partition['scheme'] == ENROLLMENT_SCHEME:
                    should_show_enrollment_track = len(partition['groups']) > 1

                    # Add it to the front of the list if it should be shown.
                    if should_show_enrollment_track:
                        displayable_partitions.insert(0, partition)
                elif partition['scheme'] != RANDOM_SCHEME:
                    # Experiment group configurations are handled explicitly above. We don't
                    # want to display their groups twice.
                    displayable_partitions.append(partition)

            # Set the sort-order. Higher numbers sort earlier
            scheme_priority = defaultdict(lambda: -1, {
                ENROLLMENT_SCHEME: 1,
                CONTENT_TYPE_GATING_SCHEME: 0
            })
            displayable_partitions.sort(key=lambda p: scheme_priority[p['scheme']], reverse=True)
            # Add empty content group if there is no COHORT User Partition in the list.
            # This will add ability to add new groups in the view.
            if not has_content_groups:
                displayable_partitions.append(GroupConfiguration.get_or_create_content_group(store, course))

            return render_to_response('group_configurations.html', {
                'context_course': course,
                'group_configuration_url': group_configuration_url,
                'course_outline_url': course_outline_url,
                'experiment_group_configurations': experiment_group_configurations,
                'should_show_experiment_groups': should_show_experiment_groups,
                'all_group_configurations': displayable_partitions,
                'should_show_enrollment_track': should_show_enrollment_track
            })
        elif "application/json" in request.META.get('HTTP_ACCEPT'):
            if request.method == 'POST':
                # create a new group configuration for the course
                try:
                    new_configuration = GroupConfiguration(request.body, course).get_user_partition()
                except GroupConfigurationsValidationError as err:
                    return JsonResponse({"error": text_type(err)}, status=400)

                course.user_partitions.append(new_configuration)
                response = JsonResponse(new_configuration.to_json(), status=201)

                response["Location"] = reverse_course_url(
                    'group_configurations_detail_handler',
                    course.id,
                    kwargs={'group_configuration_id': new_configuration.id}
                )
                store.update_item(course, request.user.id)
                return response
        else:
            return HttpResponse(status=406)


@login_required
@ensure_csrf_cookie
@require_http_methods(("POST", "PUT", "DELETE"))
def group_configurations_detail_handler(request, course_key_string, group_configuration_id, group_id=None):
    """
    JSON API endpoint for manipulating a group configuration via its internal ID.
    Used by the Backbone application.

    POST or PUT
        json: update group configuration based on provided information
    """
    course_key = CourseKey.from_string(course_key_string)
    store = modulestore()
    with store.bulk_operations(course_key):
        course = get_course_and_check_access(course_key, request.user)
        matching_id = [p for p in course.user_partitions
                       if six.text_type(p.id) == six.text_type(group_configuration_id)]
        if matching_id:
            configuration = matching_id[0]
        else:
            configuration = None

        if request.method in ('POST', 'PUT'):  # can be either and sometimes django is rewriting one to the other
            try:
                new_configuration = GroupConfiguration(request.body, course, group_configuration_id).get_user_partition()
            except GroupConfigurationsValidationError as err:
                return JsonResponse({"error": text_type(err)}, status=400)

            if configuration:
                index = course.user_partitions.index(configuration)
                course.user_partitions[index] = new_configuration
            else:
                course.user_partitions.append(new_configuration)
            store.update_item(course, request.user.id)
            configuration = GroupConfiguration.update_usage_info(store, course, new_configuration)
            return JsonResponse(configuration, status=201)

        elif request.method == "DELETE":
            if not configuration:
                return JsonResponse(status=404)

            return remove_content_or_experiment_group(
                request=request,
                store=store,
                course=course,
                configuration=configuration,
                group_configuration_id=group_configuration_id,
                group_id=group_id
            )


def are_content_experiments_enabled(course):
    """
    Returns True if content experiments have been enabled for the course.
    """
    return (
        'split_test' in ADVANCED_COMPONENT_TYPES and
        'split_test' in course.advanced_modules
    )


def _get_course_creator_status(user):
    """
    Helper method for returning the course creator status for a particular user,
    taking into account the values of DISABLE_COURSE_CREATION and ENABLE_CREATOR_GROUP.

    If the user passed in has not previously visited the index page, it will be
    added with status 'unrequested' if the course creator group is in use.
    """

    if user.is_staff:
        course_creator_status = 'granted'
    elif settings.FEATURES.get('DISABLE_COURSE_CREATION', False):
        course_creator_status = 'disallowed_for_this_site'
    elif settings.FEATURES.get('ENABLE_CREATOR_GROUP', False):
        course_creator_status = get_course_creator_status(user)
        if course_creator_status is None:
            # User not grandfathered in as an existing user, has not previously visited the dashboard page.
            # Add the user to the course creator admin table with status 'unrequested'.
            add_user_with_status_unrequested(user)
            course_creator_status = get_course_creator_status(user)
    else:
        course_creator_status = 'granted'

    return course_creator_status

def get_list_lang():
    language_options_tulp=settings.ALL_LANGUAGES
    language_options_dict={}
    for lang, label in language_options_tulp:
        language_options_dict[lang]=label
    return language_options_dict



#GEOFFREY
def get_course_langue(lang_code):
    language_options_dict=get_list_lang()
    course_language=language_options_dict[lang_code]
    return course_language


@login_required
@ensure_csrf_cookie
@require_http_methods(("GET", "PUT", "POST"))
@expect_json
def invite_handler(request, course_key_string):
    course_key = CourseKey.from_string(course_key_string)
    course = get_course_by_id(course_key)
    course_details = CourseDetails.fetch(course_key)
    overview = CourseOverview.get_from_id(course_key)
    module_store = modulestore().get_course(course_key, depth=0)

    #  GET = RENDER INVITE PAGE
    if request.method == "GET":
        context = {
            'course':course,
            'overview':overview,
            'details':course_details,
            'module_store':module_store,
            'course_key':course_key_string,
            'language_course':get_course_langue(course.language)
        }
        #retour = {'course-key_string':context}
        return render_to_response('invite_course.html', context)

    # POST = SEND INVITATIONS
    if request.method == 'POST':
        reload(sys)
        sys.setdefaultencoding('utf8')

        files = ''
        request_type = request.POST.get('request_type')
        csv_file = request.FILES.get('file')
        regex_email = r'[\w\.-]+@[\w\.-]+(\.[\w]+)+'
        notify_participants = json.loads(request.POST.get('notify_participants'),'true')

        log.info("invite_handler: start")
        log.info("notify participants: "+pformat(notify_participants))

        # IF NEED ONLY TO PRE REGISTER USERS FROM AN ADRESS MAIL
        if request_type == 'register_only' and csv_file :
            atp_students_list = {}
            sem_mails = []
            students_treated=[]
            student_errors=[]

            #Select email language
            if course.language in language_setup :
                obj = language_setup[course.language]['obj'].format(course.display_name)
                platform_lang = language_setup[course.language]['platform_lang']
            else :
                obj = language_setup['en']['obj'].format(course.display_name)
                platform_lang = language_setup['en']['platform_lang']

            #Prepare course details
            org = course.org
            course_key = CourseKey.from_string(course_key_string)
            course = get_course_by_id(course_key)
            course_details = CourseDetails.fetch(course_key)
            overview = CourseOverview.get_from_id(course_key)
            module_store = modulestore().get_course(course_key, depth=0)

            #Read CSV file
            try:
                #log.info("invite_handler: finding out encoding...")
                csv_file_for_detection = copy.deepcopy(csv_file)
                source_encoding = chardet.detect(csv_file_for_detection.read())['encoding'].lower()
                log.info("invite_handler: encoding is "+pformat(source_encoding))
                decoded_csv_file = io.StringIO(unicode(csv_file.read(),source_encoding).decode('utf-8'))
                #log.info("invite_handler: csv decoded")
                csv_dict= csv.DictReader(decoded_csv_file)
                #log.info("invite_handler: csv is in dict now : "+pformat(csv_dict))
            except:
                csv_dict={}

            log.info("invite_handler: csv is in dict now : "+pformat(csv_dict))

            for atp_student in csv_dict:
                #force lower case on emails
                log.info("invite_handler: inside")
                atp_student['email'] = atp_student['email'].lower()
                log.info(atp_student['last_name'].encode('utf-8'))
                log.info("invite_handler: "+pformat(atp_student))
                log.info("invite_handler: treating student {}".format(atp_student['email']))
                atp_student = {key.lower(): value for key, value in atp_student.items()}
                atp_students_list[atp_student['email']] = atp_student

                #Decide between SEM or ATP mail
                if re.search(regex_email,atp_student['email']) :
                    log.info("invite_handler: email is valid")
                    if User.objects.filter(email=atp_student['email']).exists() and notify_participants:
                        send_values = [
                                {
                                 "first_name":atp_student['first_name'],
                                 "last_name":atp_student['last_name'],
                                 "email":atp_student['email']
                                }
                        ]
                        try :
                            send_enroll_mail(obj,course,overview,course_details,send_values,module_store)
                            students_treated.append(atp_student['email'])
                            log.info("invite_handler: user exists mail metier sent")
                        except :
                            student_errors.append(atp_student['email'])
                            log.info("invite_handler: user exists error mail metier")
                    else :
                        log.info("USER OBJECT DOESNT EXIST")
                        if UserPreprofile.objects.filter(email=atp_student['email']).exists() :
                            log.info('USER PREPROFILE EXIST')
                            last_invite = UserPreprofile.objects.get(email=atp_student['email']).last_invite
                            if last_invite and last_invite !='' and localtime(now())-datetime.timedelta(hours=24) >= last_invite:
                                sem_mails.append(atp_student['email'])
                                log.info("invite_handler: preprofile exist last invite sup than 24h")
                        else :
                            log.info('USER PREPROFILE DOESNT')
                            sem_mails.append(atp_student['email'])
                            log.info("invite_handler: preprofile doesnt exist")

                    #Register to course
                    enroll_email(course_key, atp_student['email'], auto_enroll=True, email_students=False, email_params=None, language=course.language)
                    log.info("invite_handler: user enrolled to course")

            #Treat SEM invite
            if sem_mails :
                log.info("invite_handler: session manager starts with candidates {}".format(sem_mails))
                session_manager_results = session_manager_handler(sem_mails,org,course)
                for sem_register in session_manager_results :
                    try :
                        atp_student_infos = atp_students_list[sem_register['email']]
                        if not UserPreprofile.objects.filter(email=sem_register['email']).exists():
                            student_preprofile=UserPreprofile(
                                email=atp_student_infos['email'],
                                first_name=atp_student_infos['first_name'],
                                last_name=atp_student_infos['last_name'],
                                language=platform_lang,
                                level_1=atp_student_infos['level_1'],
                                level_2=atp_student_infos['level_2'],
                                level_3=atp_student_infos['level_3'],
                                level_4=atp_student_infos['level_4'],
                                uuid=sem_register['uuid'],
                                last_invite=localtime(now()).date()
                                )
                            student_preprofile.save()
                            log.info("invite_handler: user preprofile doesnt exist being created")
                        else :
                            student_preprofile= UserPreprofile.objects.get(email=sem_register['email'])
                            student_preprofile.last_invite = localtime(now()).date()
                            student_preprofile.save()
                            log.info("invite_handler: user preprofile already exists date being updated to {}".format(localtime(now()).date()))

                        students_treated.append(sem_register['email'])
                    except:
                        student_errors.append(sem_register['email'])


            retour={
                'errors':student_errors,
                'success':students_treated
            }
            response = {'response':request_type,'message':retour}

        #Not the right request type
        else :
            response = {'error':'no request_type'}

    return JsonResponse(response)


@login_required
@ensure_csrf_cookie
@require_http_methods(("GET", "PUT", "POST"))
@expect_json
def invitelist_handler(request, course_key_string):
    # GET COURSE_KEY
    course_key = CourseKey.from_string(course_key_string)
    # GET COURSE_PARAM
    course = get_course_by_id(course_key)
    #course details
    course_details = CourseDetails.fetch(course_key)
    #GET COURSE OVERVIEW
    overview = CourseOverview.get_from_id(course_key)
    #GET MODULE STORE
    module_store = modulestore().get_course(course_key, depth=0)


    #Get user registration ALLOWED
    course_enr_allowed = CourseEnrollmentAllowed.objects.all().filter(course_id=course_key)
    course_enr=CourseEnrollment.objects.all().filter(course_id=course_key)
    student_list=[]

    #search for student invited but not connected yet
    for student in course_enr_allowed:
        student_details={}
        try:
            student_preprofile=UserPreprofile.objects.filter(email=student.email).first()
            student_details['uuid']=student_preprofile.uuid
        except:
            student_details['uuid']=""
        student_details['email']=student.email
        if student_details['uuid']=='':
            student_details['invited']=False
        else :
            student_details['invited']=True
        student_list.append(student_details)

    #search for student who already have an account => registered directly to course
    for student_enr in course_enr:
        student_enr_details={}
        student_enr_mail = student_enr.user.email
        try:
            student_enr_preprofile=UserPreprofile.objects.filter(email=student_enr_mail).first()
            student_enr_details['uuid']=student_enr_preprofile.uuid
        except:
            student_enr_details['uuid']=""
        if student_enr_details['uuid']=='':
            student_enr_details['invited']=False
        else :
            student_enr_details['invited']=True
        student_enr_details['email']=student_enr_mail
        student_list.append(student_enr_details)


    if request.method == "GET":
        # CREATE A CONTEXT
        context = {
            'course':course,
            'overview':overview,
            'details':course_details,
            'module_store':module_store,
            'course_key':course_key_string,
            'student_list': student_list,
            'language_course':get_course_langue(course.language)
        }
        # CREATE THE RETURN
        retour = {'course-key_string':context}
        #  RETURN VALUE AND RENDER INVITE PAGE
        return render_to_response('invite_studentlist.html', context)

@login_required
@require_http_methods(("GET", "PUT", "POST"))
@expect_json
def email_dashboard_handler(request, course_key_string):
    reload(sys)
    sys.setdefaultencoding('utf8')
    list_sem=[]
    mail_send= False
    if request.method == "GET":
        #GET COURSE KEY
        course_key = CourseKey.from_string(course_key_string)
        #GET COURSE OVERVIEW
        overview = CourseOverview.get_from_id(course_key)
        #GET COURSE DETAILS
        details = CourseDetails.fetch(course_key)

        #GET COURSE LOGS
        course = get_course_by_id(course_key)
        #GET MODULE STORE
        module_store = modulestore().get_course(course_key, depth=0)
        # CREATE A CONTEXT
        context = {
            'course':course,
            'overview':overview,
            'details':details,
            'module_store':module_store,
            'course_key':course_key_string,
            'language_course':get_course_langue(course.language)
        }
        # CREATE THE RETURN
        retour = {'course-key_string':context}
        #  RETURN VALUE AND RENDER INVITE PAGE
        return render_to_response('mail_course.html', context)

    # IF POST METHOD
    if request.method == 'POST':
        # FILE VAR
        files = '';
        # GET REQUEST_TYPE
        request_type = ''
        try:
            request_type = request.POST['request_type']
            # GET COURSE_KEY
            course_key = CourseKey.from_string(course_key_string)
            # GET COURSE_PARAM
            course = get_course_by_id(course_key)
            #course details
            course_details = CourseDetails.fetch(course_key)
            #GET COURSE OVERVIEW
            overview = CourseOverview.get_from_id(course_key)
            #GET MODULE STORE
            module_store = modulestore().get_course(course_key, depth=0)

        except:
            request_type = False
        # IF NEED ONLY TO PRE REGISTER USERS FROM AN ADRESS MAIL
        if request_type == 'send_mail':
            response = ''
            list_email = []
            try:
                #GET POST PARAMS
                myself = request.POST['myself']
                staff = request.POST['staff']
                custom = request.POST['custom']
                all_users = request.POST['all']
                adress = request.POST['adress']
                obj = request.POST['object']
                body = request.POST['body']
                course_key = CourseKey.from_string(course_key_string)

                if myself == 'true':
                    q = {}
                    q['email'] = request.user.email
                    q['first_name'] = request.user.first_name
                    q['last_name'] = request.user.last_name
                    list_email.append(q)

                if staff == 'true':
                    staf_users = CourseInstructorRole(course_key).users_with_role()
                    for n in staf_users:
                        if not n.email in list_email:
                            try:
                                _staf_user = User.objects.get(email=n.email)
                                q = {}
                                q['email'] = n.email
                                q['first_name'] = _staf_user.first_name
                                q['last_name'] = _staf_user.last_name
                                list_email.append(q)
                            except:
                                pass

                if custom == 'true':
                    log.info("custom true")
                    adress = adress.split(',')
                    log.info("custom true adress {}".format(adress))
                    for n in adress:
                        email_is_in_list_email = False
                        for email_in_list_email in list_email:
                            if n in email_in_list_email.email:
                                email_is_in_list_email = True
                                break
                        if not email_is_in_list_email:
                            log.info("custom true ok n not in list_email")
                            try :
                                q = {}
                                if User.objects.filter(email=n).exists() :
                                    log.info("custom true ok first try")
                                    _user_custom = User.objects.get(email=n)
                                    log.info("custom true n {}".format(n))
                                    q['email'] = n
                                    q['first_name'] = _user_custom.first_name
                                    q['last_name'] = _user_custom.last_name
                                    list_email.append(q)
                                    log.info("custom true append ok to atp mail")
                            except:
                                pass
                            if (n not in list_sem) and (n not in list_email):
                                list_sem.append(n)
                                log.info("custom true append ok to sem mail")
                if all_users == 'true':
                    user_id = []
                    try:
                        full_list=get_full_course_users_list(course_key)
                        log.info("all users get_full_course_users_list: "+pformat(full_list))
                        for user in full_list :
                            if User.objects.filter(email=user['email']).exists() :
                                email_is_in_list_email = False
                                for email_in_list_email in list_email:
                                    if user['email'] in email_in_list_email['email']:
                                        email_is_in_list_email = True
                                        break
                                if not email_is_in_list_email:
                                    q = {}
                                    q['email'] = user['email']
                                    q['first_name'] = user['first_name']
                                    q['last_name'] = user['last_name']
                                    list_email.append(q)
                            else :
                                if (user['email'] not in list_sem):
                                    list_sem.append(user['email'])
                    except:
                        ALL = False
            except:
                list_email = False

            if list_email:
                log.info("end of email_dashboard_handler before mail_send "+pformat(len(list_email))+"users, list:"+pformat(list_email))
                mail_send = send_enroll_mail(obj,course,overview,course_details,list_email,module_store,body)

            #Send sem mails if any
            if list_sem :
                log.info("end of email_dashboard_handler before session_manager_handler"+pformat(list_sem))
                course_concerned = get_course_by_id(course_key)
                org_concerned = course_concerned.org
                session_manager_handler(list_sem,org_concerned,course_concerned,body)
                mail_send = True

            return JsonResponse({'mail_send':mail_send})
        # if not request_type in POST request body
        else:
            response = {'error':'no request_type'}
            return JsonResponse(response)



language_setup={
    "en":{
        'platform_lang' :'en',
        'sem_lang' :'en',
        'msg':'Once you’ve passed this step, you will be able to access the training module {0}.',
        'obj':'Invitation to access {0} training module',
        'title_mail' : ['Category','Duration','Mode','End date'],
        'required':'mandatory',
        'optional':'optional',
        'categories':{
            'fundamentals':'fundamentals',
            'our solutions':'our solutions',
            'sales approach' :'sales approach',
            'regulatory' : 'regulatory',
            'expert':'expert',
            'soft skills':'soft skills'
        }
    },
    "nl":{
        'platform_lang' :'nl-nl',
        'sem_lang' :'nl',
        'msg':'Na deze stap hebt u toegang tot de opleidingsmodule {0}.',
        'obj':'Uitnodiging om opleidingsmodule {0} te volgen',
        'title_mail' : [' Categorie','Duur','Wijze','Einddatum'],
        'required':'verplicht',
        'optional':'facultatief',
        'categories':{
            'fundamentals':'BASISKENNIS',
            'our solutions':'ONZE OPLOSSINGEN',
            'sales approach' :'ZAKELIJKE AANPAK',
            'regulatory' : 'REGELGEVING',
            'expert':'expert',
            'soft skills':'soft skills'
        }
    },
    'fr':{
        'platform_lang':'fr',
        'sem_lang' :'fr',
        'msg':'Une fois passée cette étape, vous pourrez accéder à votre module sur {0}.',
        'obj':'Invitation pour accéder au module {0}',
        'title_mail':['Catégorie','Durée','Mode','Date de fin'],
        'required':'obligatoire',
        'optional':'facultatif',
        'categories':{
            'fundamentals':'fondamentaux',
            'our solutions':'nos solutions',
            'sales approach' :'démarche commerciale',
            'regulatory' : 'réglementaire',
            'expert':'experts',
            'soft skills':'Démarche commerciale'
        }

    },
    'de':{
        'platform_lang':'de-de',
        'sem_lang' :'de',
        'msg':'Sobald Sie diesen Schritt bestanden haben, können Sie auf das Schulungsmodul zugreifen {0}.',
        'obj' : 'Einladung zum Schulungsmodul {0}',
        'title_mail':['Kategorie','Dauer','Modus','Enddaten'],
        'required':'verbindlich',
        'optional':'fakultativ',
        'categories':{
            'fundamentals':'grundlagen',
            'our solutions':'unsere lösungen',
            'sales approach' :'vertriebsansatz',
            'regulatory' : 'vorschriften',
            'expert':'experten',
            'soft skills':'Kommerzieller Ansatz'
        }
    },
    'it':{
        'platform_lang':'it-it',
        'sem_lang' :'it',
        'msg':'Una volta superato questo passaggio, sarai in grado di accedere al modulo di formazione {0}.',
        'obj' : ' Invito per accedere al {0} modulo di formazione	',
        'title_mail':['Categoria','Durata','Modo','Data di fine'],
        'required':'obbligatorio',
        'optional':'facoltativo',
        'categories':{
            'fundamentals':'Fondamentali',
            'our solutions':'Le noste soluzioni',
            'sales approach' :'Approcio commerciale',
            'regulatory' : 'reglomentazione',
            'expert':'esperti',
            'soft skills':'Approccio commerciale'
        }
    },
    'cs':{
        'platform_lang':'cs',
        'sem_lang' :'cz',
        'msg':'Po tomto kroku budete mít přístup k vzdělávacímu kurzu {0}.',
        'obj' : ' Pozvánka k zahájení vzdělávacího kurzu  {0}',
        'title_mail':['Kategorie','Trvání','Režim','Datum ukončení'],
        'required':'povinné',
        'required_in_text':'povinný',
        'optional':'volitelný',
        'categories':{
            'fundamentals':'OBECNÉ ZÁKLADY',
            'our solutions':'ZÁKLADNÍ ŘEŠENÍ',
            'sales approach' :'PRODEJNÍ PŘÍSTUP',
            'regulatory' : 'REGULACE',
            'expert':'DOPLŇKOVÁ ŘEŠENÍ',
            'soft skills':'PRODEJNÍ DOVEDNOSTI'
        }
    },
    'ro':{
        'platform_lang':'ro',
        'sem_lang' :'ro',
        'msg':'Dupa ce ai trecut de acest pas, vei putea accesa modulele de training {0}.',
        'obj' : 'Invitatie de a accesa modulul de training  {0}',
        'title_mail':['Categoria','Durata','Modul','Data de incheiere'],
        'required':'obligatoriu',
        'optional':'optional',
        'categories':{
            'fundamentals':'PRINCIPII FUNDAMENTALE',
            'our solutions':'SOLUTIILE NOASTRE',
            'sales approach' :'ABORDARE DE VANZARI',
            'regulatory' : 'ORGANISM DE REGLEMENTARE',
            'expert':'EXPERT',
            'soft skills':'ABILITĂȚI SOFT'
        }
    },
    "hu":{
        'platform_lang' :'hu',
        'sem_lang' :'hu',
        'msg':'Miután teljesítetted ezt a lépést, eléred a tréning modult {0}.',
        'obj':'Meghívás a {0} tréning modulra',
        'title_mail' : ['Kategória','Idõigény','Mód','Határidõ'],
        'required':'kötelezõ',
        'optional':'opcionális',
        'categories':{
            'fundamentals':'ALAPVETÕ ISMERETEK',
            'our solutions':'MEGOLDÁSAINK',
            'sales approach' :'ÉRTÉKESÍTÉSI MEGKÖZELÍTÉS',
            'regulatory' : 'SZABÁLYOZÓI',
            'expert':'expert',
            'soft skills':'soft skills'
        }
    }
}
