from django.core.context_processors import csrf

from edxmako.shortcuts import render_to_string
from xmodule.modulestore.django import modulestore

from courseware.module_render import get_module_for_descriptor
from courseware.model_data import FieldDataCache
from courseware.views.views import get_current_child

from course_progress.models import StudentCourseProgress

def prepare_chapters_with_progress(request, course):
    '''
    Create chapters with grade details.

    Return format:
    { 'chapters': [
            {'display_name': name, 'sections': SECTIONS},
        ],
    }

    where SECTIONS is a list
    [ {'display_name': name, 'format': format, 'due': due, 'completed' : bool,
        'graded': bool}, ...]

    chapters with name 'hidden' are skipped.

    NOTE: assumes that if we got this far, user has access to course.  Returns
    [] if this is not the case.
    '''
    student = request.user

    # find the course progress
    progress = get_course_progress(student, course.id)

    # Get the field data cache
    field_data_cache = FieldDataCache.cache_for_descriptor_descendents(
        course.id, student, course, depth=2,
    )
    
    # Get the course module
    with modulestore().bulk_operations(course.id):
        course_module = get_module_for_descriptor(
            student, request, course, field_data_cache, course.id, course=course
        )
        if course_module is None:
            return []

    # get the courseware position where left off
    active_section = None
    if course.has_children_at_depth(2):
        active_chapter = get_last_accessed_chapter(course)
        active_section = get_last_accessed_section(active_chapter)

    chapters = []
    section_index = 0
    for chapter in course_module.get_display_items():
        sections = []
        for sequential in chapter.get_display_items():
            section_index += 1
            sections.append({
                'section_index': section_index,
                'display_name': sequential.display_name_with_default_escaped,
                'url_name': sequential.url_name,
                'passed': has_passed(str(sequential.location), progress),
                'paused': active_section and (sequential.url_name == active_section.url_name)
            })
        chapters.append({
            'display_name': chapter.display_name_with_default_escaped,
            'url_name': chapter.url_name,
            'sections': sections
        })

    return chapters

def render_accordion(request, course):
    """
    Returns the HTML that renders the navigation for the given course.
    Expects the table_of_contents to have data on each chapter and section,
    including which ones are completed.
    """
    context = {
        'chapters': prepare_chapters_with_progress(request, course),
        'course_id': unicode(course.id),
        'csrf': csrf(request)['csrf_token'],
    }

    return render_to_string('course_welcome/accordion.html', context)

def get_final_score(request, course):
    """
    To get the final score for the user in
    particular course.
    """
    grade_summary = {}
    student = request.user

    try:
        grade_summary = grades.grade(student, request, course)
    except:
        pass

    final_grade = grade_summary.get('percent', 0)

    return int(final_grade * 100)

def get_last_accessed_chapter(course):
    """
    It returns the last accessed chapter in
    the course.
    """
    return get_current_child(course, min_depth=1, requested_child=None)

def get_last_accessed_section(chapter):
    """
    It returns the last accessed section in
    the chapter.
    """
    return get_current_child(chapter, min_depth=None, requested_child=None)

def get_course_progress(student, course_key):
    progress = {}

    try:
        course_progress = StudentCourseProgress.objects.get(student=student.id, course_id=course_key)
        progress = course_progress.progress
    except StudentCourseProgress.DoesNotExist:
        pass

    return progress

def has_passed(module_id, course_progress):
    """
    Author: Naresh Makwana
    """
    module_progress = course_progress.get(module_id, {})

    return int(module_progress.get('progress', 0)) == 100
