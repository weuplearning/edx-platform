from __future__ import unicode_literals
from django.db import models
from opaque_keys.edx.django.models import UsageKeyField
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment
from opaque_keys.edx.keys import CourseKey
import datetime

import logging
logger = logging.getLogger()


class WulCourseOverview(models.Model):
    course_id_edx = UsageKeyField(blank=False, max_length=255, db_index=True)
    course_timer_active = models.BooleanField(default=False)
    course_timer_type = models.CharField(default='no_timer', max_length=255)
    course_timer_days_value = models.IntegerField(null=True,blank=True)
    course_timer_date_value = models.DateField(null=True,blank=True)
    course_certificat_mode = models.CharField(default='default_mode', max_length=255)
    course_certificat_detail = models.TextField(blank=True)

    @classmethod
    def get_overview(cls, course_id):
        wul_course_overview, created = cls.objects.get_or_create(course_id_edx = CourseKey.from_string(course_id))
        return wul_course_overview

    @classmethod
    def set_timer_status(cls, course_id, status):
        wul_course_overview = cls.get_overview(course_id)
        if wul_course_overview is not None :
            if status == "activate":
                wul_course_overview.course_timer_active = True
            if status == "deactivate":
                wul_course_overview.course_timer_active = False
            return 'success'
        else:
            return'error'

    @classmethod
    def add_course_timer(cls, course_id, timer_type, timer_value):
        wul_course_overview = cls.get_overview(course_id)
        if wul_course_overview is not None :
            wul_course_overview.course_timer_active = True
            wul_course_overview.course_timer_type = timer_type
            if timer_type == 'date_timer':
                wul_course_overview.course_timer_date_value = datetime.datetime.strptime(timer_value,"%d-%m-%Y").date()
                wul_course_overview.course_timer_days_value = None
            else :
                wul_course_overview.course_timer_days_value = int(timer_value)
                wul_course_overview.course_timer_date_value = None
            wul_course_overview.save()
            return 'success'
        else :
            return 'error'

    @classmethod
    def delete_course_timer(cls, course_id):
        wul_course_overview = cls.get_overview(course_id)
        if wul_course_overview is not None:
            wul_course_overview.course_timer_active = False
            wul_course_overview.course_timer_type = 'no_timer'
            wul_course_overview.course_timer_date_value = None
            wul_course_overview.course_timer_days_value = None
            wul_course_overview.save()
            return 'success'
        else :
            return 'error'


    @classmethod
    def get_certificat_mode (cls, course_id):
        wul_course_overview = cls.get_overview(course_id)
        if wul_course_overview is not None :
            course_certificat_mode = wul_course_overview.course_certificat_mode
            return course_certificat_mode
        else :
            return 'error'

    @classmethod
    def add_certificat_mode (cls, course_id, certificat_mode, certificat_detail):
        wul_course_overview = cls.get_overview(course_id)
        if wul_course_overview is not None:
            wul_course_overview.course_certificat_mode = certificat_mode
            wul_course_overview.course_certificat_detail = certificat_detail
            wul_course_overview.save()
            return 'success'
        else :
            return 'error'

    @classmethod
    def reset_certificat_mode (cls, course_id, certificat_mode, certificat_detail):
        wul_course_overview = cls.get_overview(course_id)
        if wul_course_overview is not None :
            wul_course_overview.course_certificat_mode = 'default_mode'
            wul_course_overview.course_certificat_detail = None
            wul_course_overview.save()
            return 'success'
        else :
            return 'error'


class WulCourseEnrollment(models.Model):
    course_enrollment_edx = models.ForeignKey(
        CourseEnrollment,
        on_delete=models.CASCADE,
        unique=True
    )
    global_time_tracking = models.IntegerField(default=0)
    detailed_time_tracking = models.TextField(blank=True, default="{}")
    daily_time_tracking = models.TextField(blank=True, default="{}")
    has_started_course = models.BooleanField(default=False)
    has_finished_course = models.BooleanField(default=False)
    finished_course_date = models.DateTimeField(null=True, blank=True)
    is_hidden = models.BooleanField(default=False)
    best_grade = models.FloatField(default=0,db_index=True)
    best_grade_date = models.DateTimeField(blank=True,null=True)
    extra_data = models.TextField(blank=True, default="{}")


    @classmethod
    def get_enrollment(cls, course_id, user):
        try:
            course_enrollment = CourseEnrollment.objects.get(course_id=CourseKey.from_string(course_id), user=user)
            wul_course_enrollment, created = WulCourseEnrollment.objects.get_or_create(course_enrollment_edx = course_enrollment)

        except CourseEnrollment.DoesNotExist:
            wul_course_enrollment = None
            pass

        return wul_course_enrollment


    @classmethod
    def update_timer(cls, course_id, user, global_time, detailed_time, daily_time):
        wul_course_enrollment = cls.get_enrollment(course_id, user)

        if wul_course_enrollment:

            if not wul_course_enrollment.has_started_course:
                wul_course_enrollment.has_started_course = True

            wul_course_enrollment.global_time_tracking += global_time
            wul_course_enrollment.detailed_time_tracking = detailed_time
            wul_course_enrollment.daily_time_tracking = daily_time
            wul_course_enrollment.save()
            return 'success'

        else:
            return 'error'
