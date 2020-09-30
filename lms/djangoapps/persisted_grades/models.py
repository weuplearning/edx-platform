from django.db import models

from opaque_keys.edx.django.models import CourseKeyField
from lms.djangoapps.courseware.fields import UnsignedBigIntAutoField

from logging import getLogger
log = getLogger(__name__)

class PersistedGrades(models.Model):
    class Meta:
        app_label = "persisted_grades"
        unique_together = ('course_id', 'user_id',)

    id = UnsignedBigIntAutoField(primary_key=True)
    course_id = CourseKeyField(max_length=255, db_index=True, blank=True)
    user_id = models.IntegerField(blank=False,default=0)
    percent = models.FloatField(default=0)
    passed = models.BooleanField(default=False)
    quiz_completed = models.BooleanField(default=False)

def get_persisted_course_grade(course_id, user_id):
    persisted_course_grade = None
    if PersistedGrades.objects.filter(course_id = course_id, user_id = user_id).exists():
        persisted_course_grade = PersistedGrades.objects.get(course_id = course_id, user_id = user_id)
    return persisted_course_grade

def store_persisted_course_grade(course_id, user_id, grade, passed):
    #optim hypothesis, most of the time the course grade does not already exist
    persisted_grade = None
    if not PersistedGrades.objects.filter(course_id = course_id, user_id = user_id).exists():
        persisted_grade = PersistedGrades.objects.create(course_id = course_id, user_id = user_id, percent = grade, passed = passed)
    else:
        persisted_grade = PersistedGrades.objects.get(course_id = course_id, user_id = user_id)
        persisted_grade.percent = grade
        persisted_grade.passed = passed
        persisted_grade.save()
        pass
    return persisted_grade

def get_persisted_course_grades_for_course(course_id):
    return PersistedGrades.objects.filter(course_id = course_id)

def get_persisted_course_grades_for_user(user_id):
   return PersistedGrades.objects.filter(user_id = user_id)

def set_quiz_completion(course_id, user_id):
    persisted_grade = None
    if PersistedGrades.objects.filter(course_id = course_id, user_id = user_id).exists():
        persisted_grade = PersistedGrades.objects.get(course_id = course_id, user_id = user_id)
        persisted_grade.quiz_completed = True
        persisted_grade.save()
    return persisted_grade
