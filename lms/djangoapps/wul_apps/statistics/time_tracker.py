import json
from lms.djangoapps.wul_apps.models import WulCourseEnrollment
import datetime

import logging
log = logging.getLogger()

class time_tracker_manager():
    def __init__(self, user, course_id):
        self.user=user
        self.course_id=course_id
        self.wul_course_enrollment = WulCourseEnrollment.get_enrollment(user=user, course_id=course_id)

    def add_course_time(self, time, section, sub_section):
        detailed_time = {}
        daily_time = {}

        if self.wul_course_enrollment.detailed_time_tracking :
            detailed_time = json.loads(self.wul_course_enrollment.detailed_time_tracking)

        if self.wul_course_enrollment.daily_time_tracking :
            daily_time = json.loads(self.wul_course_enrollment.daily_time_tracking)
            today = datetime.datetime.now().strftime("%d-%m-%Y")

            if today in daily_time.keys():
                daily_time[today] += int(time)
            else:
                daily_time[today] = int(time)

        section_time = int(detailed_time.get(section,0))+ int(time)
        detailed_time[section]=section_time

        sub_section_time = int(detailed_time.get(sub_section,0))+ int(time)
        detailed_time[sub_section]=sub_section_time

        feedback = WulCourseEnrollment.update_timer(self.course_id, self.user, int(time), json.dumps(detailed_time), json.dumps(daily_time))
        return feedback

    def mark_course_status(self, course_state):
        if course_state=="started":
            self.wul_course_enrollment.has_started_course=True
        elif course_state=="finished":
            self.wul_course_enrollment.has_finished_course=True
            if not self.wul_course_enrollment.finished_course_date:
                self.wul_course_enrollment.finished_course_date=datetime.datetime.now()
        try :
            self.wul_course_enrollment.save()
            feedback='success'
        except:
            feedback='error'
        return feedback

    def get_user_state(self):
        if self.wul_course_enrollment.has_finished_course:
            user_status="finished"
        elif self.wul_course_enrollment.has_started_course:
            user_status="ongoing"
        else :
            user_status="not_started"
        return user_status

    def get_global_time(self):
        return self.wul_course_enrollment.global_time_tracking
