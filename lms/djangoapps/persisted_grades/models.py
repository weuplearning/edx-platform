from django.db import models

from opaque_keys.edx.django.models import CourseKeyField
from lms.djangoapps.courseware.fields import UnsignedBigIntAutoField
from django.utils import timezone

from logging import getLogger
log = getLogger(__name__)

class PersistedGrades(models.Model):
    class Meta:
        app_label = "persisted_grades"
        unique_together = ('course_id', 'user_id',)

    id = UnsignedBigIntAutoField(primary_key=True)
    course_id = CourseKeyField(max_length=255, db_index=True, blank=True)
    user_id = models.IntegerField(blank=False,default=0, db_index=True)
    percent = models.FloatField(default=0)
    passed = models.BooleanField(default=False)
    quiz_completed = models.BooleanField(default=False)
    first_access = models.DateTimeField(null=True,blank=True)
    first_success = models.DateTimeField(null=True,blank=True)

    def set_first_access_date_if_needed(self):
        if not self.first_access:
           self.first_access = timezone.now()
           self.save()

    def set_first_success_date_if_needed(self):
        if not self.first_success and self.passed and self.quiz_completed:
            self.first_success = timezone.now()
            self.save()

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

    #persisted_grade.set_first_success_date_if_needed()

    return persisted_grade

def get_persisted_course_grades_for_course(course_id):
    return PersistedGrades.objects.filter(course_id = course_id)

def get_persisted_course_grades_for_user(user_id):
   return PersistedGrades.objects.filter(user_id = user_id)

def set_quiz_completion(course_id, user_id):
    persisted_grade = None
    if PersistedGrades.objects.filter(course_id = course_id, user_id = user_id).exists():
        persisted_grade = PersistedGrades.objects.get(course_id = course_id, user_id = user_id)
        if not persisted_grade.quiz_completed:
            persisted_grade.quiz_completed = True
            persisted_grade.save()
        #persisted_grade.set_first_success_date_if_needed()
    return persisted_grade
