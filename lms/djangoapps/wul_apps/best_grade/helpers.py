'''
/edx/app/edxapp/edx-platform/lms/djangoapps/wul_apps/best_grade/
'''

from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from lms.djangoapps.wul_apps.models import WulCourseEnrollment
import datetime

import logging
log = logging.getLogger()

def check_best_grade(user, course, force_best_grade=None):


    grade_info = CourseGradeFactory().read(user, course)
    grade_info.percent_tma = grade_info.percent
    grade_info.passed_tma = grade_info.passed

    if configuration_helpers.get_value('tma_best_grade_mode') or force_best_grade:
        course_enrollment = WulCourseEnrollment.get_enrollment(str(course.id), user)

        # limite établie dans le studio
        grader = course._grading_policy.get('GRADE_CUTOFFS').get('Pass')

        if course_enrollment.best_grade and course_enrollment.best_grade > grade_info.percent :
            grade_info.percent_tma = course_enrollment.best_grade
            grade_info.passed_tma = course_enrollment.best_grade >= grader

        if grade_info.percent>0 and grade_info.percent > course_enrollment.best_grade:
            course_enrollment.best_grade = grade_info.percent
            course_enrollment.best_grade_date = datetime.datetime.now()
            course_enrollment.save()
    return grade_info 


