import six
import logging
from six.moves import urllib
from opaque_keys.edx.keys import CourseKey
from django.template.context_processors import csrf
from openedx.core.djangoapps.crawlers.models import CrawlersConfig
from openedx.features.course_experience.utils import get_course_outline_block_tree
from ..model_data import FieldDataCache
from ..module_render import toc_for_course
from common.djangoapps.edxmako.shortcuts import  render_to_string
from ..courses import get_course_with_access

TEMPLATE_IMPORTS = {'urllib': urllib}
CONTENT_DEPTH = 2
log = logging.getLogger("edx.courseware.views.index")


# def render_accordion(request, course, table_of_contents):
def render_accordion(request, course_id, chapter_module, section_module):
    """
    Returns the HTML that renders the navigation for the given course.
    Expects the table_of_contents to have data on each chapter and section,
    including which ones are active.
    """

    course_key = CourseKey.from_string(course_id)

    course = get_course_with_access(
        request.user, 'load', course_key,
        depth=CONTENT_DEPTH,
        check_if_enrolled=True,
        check_if_authenticated=True
    )

    field_data_cache = FieldDataCache.cache_for_descriptor_descendents(
        course_key,
        request.user,
        course,
        depth=CONTENT_DEPTH,
        read_only=CrawlersConfig.is_crawler(request),
    )

    table_of_contents = toc_for_course(
        request.user,
        request,
        course,
        chapter_module,
        section_module,
        field_data_cache,
    )

    course_key = str(six.text_type(course.id))
    # To get the completion into the accordion menu
    course_details = get_course_outline_block_tree(request, course_key , request.user)
    course_sections = course_details.get('children')

    sections_completed = []
    subsections_completed = []
    for section in course_sections:
        if section.get('complete'):
            sections_completed.append(section['block_id'])
        for subsection in section.get('children', []):
            if subsection.get('complete'):
                subsections_completed.append(subsection['block_id'])

    context = dict(
        [
            ('completed_sections', sections_completed),
            ('completed_subsections', subsections_completed),
            ('toc', table_of_contents["chapters"]),
            ('course_id', six.text_type(course.id)),
            ('csrf', csrf(request)['csrf_token']),
            ('due_date_display_format', course.due_date_display_format),
        ] + list(TEMPLATE_IMPORTS.items())
    )   

    return render_to_string('courseware/accordion.html', context)
