#geoffrey
from courseware.courses import get_course_by_id
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from django.conf import settings
import json
from django.http import JsonResponse
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST,require_GET
from django.views.decorators.csrf import ensure_csrf_cookie
from xmodule.modulestore.django import modulestore

#TMA GRADE TRACKING LIB
from lms.djangoapps.tma_grade_tracking.models import dashboardStats
import logging
log = logging.getLogger()

@ensure_csrf_cookie
@require_GET
@login_required
def ensure_certif(request,course_id):
    log.info('ensure certidddddddddddddddd')
    user_id = request.user.id
    username = request.user.username
    course_key = SlashSeparatedCourseKey.from_string(course_id)
    course_tma = get_course_by_id(course_key)
    log.info(course_tma)
    is_graded = True
    grade_cutoffs = modulestore().get_course(course_key, depth=0).grade_cutoffs['Pass'] * 100
    grading_note =  CourseGradeFactory().read(request.user, course_tma)

    #TMA GRADE TRACKING UPDATE
    mongo_persist = dashboardStats()
    collection = mongo_persist.connect()
    add_user = {}
    add_user['user_id'] = request.user.id
    add_user['username'] = request.user.username
    add_user['passed'] = grading_note.passed
    add_user['percent'] = grading_note.percent
    add_user['summary'] = grading_note.summary
    mongo_persist.add_user_grade_info(collection,str(course_id),add_user)
    # END TMA GRADE TRACKING UPDATE


    passed = grading_note.passed
    percent = float(int(grading_note.percent * 1000)/10)
    context = {
        'passed':passed,
        'percent':percent,
        'is_graded':is_graded,
        'grade_cutoffs':grade_cutoffs,
    }

    return JsonResponse(context)
