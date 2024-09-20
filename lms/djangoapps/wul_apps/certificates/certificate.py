from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.conf import settings
from pprint import pformat
import json
import hashlib
import csv

from xmodule.mongo_utils import connect_to_mongodb

from edxmako.shortcuts import render_to_response
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
# from lms.djangoapps.grades.new.course_grade import CourseGradeFactory
from courseware.courses import get_course_by_id
from lms.djangoapps.wul_apps.best_grade.helpers import check_best_grade

import logging
log = logging.getLogger(__name__)

class certificate():

    def __init__(self,course_key,user):
        self.course_key = course_key
        self.user = user
        self.course = None
        self.courseGrade = None
        self.metadata = None

    def get_course(self):
        if self.course_key is not None:
            self.course = get_course_by_id(self.course_key)

    def get_course_grade(self):
        if self.course is not None and self.user is not None:
            self.courseGrade = check_best_grade(self.user, self.course, force_best_grade=True)

    # def get_metadata(self):
    #     if self.course is not None:
    #         self.metadata = self.course.course_extra['certificate']
    
    def _connect_to_forum_mongo_db(self):
        """
        Create & open the connection, authenticate, and provide pointers to the collection
        """
        db_settings = settings.DOC_STORE_CONFIG
        database = connect_to_mongodb(
        host=db_settings["host"],
        port=db_settings["port"],
        db="cs_comments_service_development",
        user=None,
        password=None,
        connectTimeoutMS=db_settings["connectTimeoutMS"],
        socketTimeoutMS=db_settings["socketTimeoutMS"]
        )
        return database

    def get_nb_of_forum_posts(self,user_id,course_id):
        database = self._connect_to_forum_mongo_db()
        collection = database["contents"]
        number_of_posts = collection.find({"_type": "Comment","author_id": str(user_id),"course_id" : course_id}).count()
        number_of_posts += collection.find({"_type": "CommentThread","author_id": str(user_id),"course_id" : course_id}).count()
        database.connection.close()
        return number_of_posts

    def check_certificate(self):

        self.get_course()
        self.get_course_grade()
        # self.get_metadata()

        passed = False
        forum_posts_validated = False
        total = 0
        add = 0
        finished = 0
        values = []
        from_vue = []
        grade = self.courseGrade.percent_tma
        _is_certified = False
        course_grade = CourseGradeFactory().read(self.user, self.course)
        grade_summary = course_grade.summary

        # if not self.metadata.get('custom_cutoff'):
        passed = self.courseGrade.passed_tma
        _is_certified = True


        # THE CODE BELOW SEEMS TO BE BYPASSED BY THE ABOVE ONE IN THE PREVIOUSLY ESTABLISHED CONDITION IT SHOULD WORK FINE LIKE THIS 
        # CA - 09/03/2022

        # else:
        #     user_breakdown = self.courseGrade.grade_value['grade_breakdown']
        #     log.info(user_breakdown)

        #     for row in self.metadata.get('sub_sections'):
        #         _type = row.get('type')
        #         required = row.get('required')
        #         if required:

        #             total = total + 1
        #             coef = row.get('coef')
        #             value = float((float(row.get('real')) / 100) * coef)
        #             values.append(value)
        #             log.info('certificate values required {}'.format(value))

        #             for n in user_breakdown.keys():
        #                 if n == _type:
        #                     add = add + 1
        #                     from_vue.append(user_breakdown.get(n).get('percent'))
        #                     if user_breakdown.get(n).get('percent') > value:
        #                         finished = finished + 1

        #     if add == total:
        #         _is_certified = True
        #         if finished == total and self.courseGrade.passed:
        #             passed = True


        # UPDATE PARTIAL CODE IF NEEDED
        # UPDATE PARTIAL CODE IF NEEDED
        # partial = True
        partial = False
        # for grade_category_result in self.courseGrade.grade_value['grade_breakdown'].keys():
        #     # If any grade is zero then it means there is a course category that was not tried or outrageously failed
        #     # But a grade can be zero if its weight is zero
        #     if self.courseGrade.grade_value['grade_breakdown'].get(grade_category_result).get('percent') == 0 and not ("of a possible 0.00%" in self.courseGrade.grade_value['grade_breakdown'].get(grade_category_result).get('detail')):
        #         log.info('inside grade_category loop')
        #         log.info(self.courseGrade.grade_value['grade_breakdown'].get(grade_category_result).get('detail'))
        #         partial = False
        #         break
        # UPDATE PARTIAL CODE IF NEEDED
        # UPDATE PARTIAL CODE IF NEEDED

        # If posts_threshold_configs is enabled we check if the user has posts enough message in a specific course's forum

        posts_threshold_configs = configuration_helpers.get_value('WUL_COURSE_CERTIFICATE_FORUM_POSTS_THRESHOLD', False)
        if posts_threshold_configs:
            course_id=str(self.course.id)
            nb_of_forum_posts = self.get_nb_of_forum_posts(self.user.id,course_id)
            
            if course_id in posts_threshold_configs:
                if nb_of_forum_posts >= posts_threshold_configs[course_id] :
                    forum_posts_validated = True
            elif "all" in posts_threshold_configs:
                if nb_of_forum_posts >= posts_threshold_configs['all'] :
                    forum_posts_validated = True

        context = {
            "partial":partial,
            "passed":passed,
            "finished":finished,
            "regular":_is_certified,
            "add":add,
            "total":total,
            "grade":grade,
            "values":values,
            "from_vue":from_vue,
            "forum_posts_validated":forum_posts_validated,
            "grade_summary":grade_summary
        }

        return context

    def view(self,request,partial=False):
        grades = self.check_certificate()
        try:
            first_name = json.loads(request.user.profile.custom_field).get('first_name')
            course_id=str(self.course.id)
        except:
            first_name = ""

        try:
            last_name = json.loads(request.user.profile.custom_field).get('last_name')
        except:
            last_name = ""

        name = last_name+" "+first_name
        context = {
            "course_id":course_id,
            "request":request,
            "grades":grades,
            "course_name":self.course.display_name_with_default,
            "signature":self.metadata.get('signature'),
            "pdf":self.metadata.get('pdf'),
            "bg":self.metadata.get('bg'),
            "first_name":first_name,
            "last_name":last_name,
            "hash":hashlib.sha256(name.strip()+"AyuNUNag62wFrApuqErafE"+str(grades.get('grade')*100)).hexdigest()[0:9]
        }
        if partial:
            return render_to_response('tma_apps/certificate_partial.html',context)
        else:
            return render_to_response('tma_apps/certificate.html',context)

    def ensure_certificate(self):
        context = self.check_certificate()
        return JsonResponse(context)

    def ensure_partial_certificate(self):
        context = self.check_certificate()
        return JsonResponse(context)

    def view_partial_certificate(self,request):
        return self.view(request,partial=True)

    def grade_csv_and_user(self):

        context = self.check_certificate()

        course_id = str(self.course.id)

        csv_file_path = '/edx/var/edxapp/media/microsites/af-brazil/data/' + str(course_id) +'.csv'
        csv_data = False
        csv_user_grade = []
        best_grade_for_section = []
        global_grade_sum = 0
        global_grade_count = 0

        try :
            with open(csv_file_path, newline='') as csvfile:
                csvreader = csv.reader(csvfile, delimiter=';')
                csv_data = []
                for row in csvreader:
                    csv_data.append(row)
        except :
            csv_data = False

        if csv_data :
            for user_data_csv in csv_data :
                if len(user_data_csv)>1 and self.user.email == user_data_csv[1] :

                    csv_user_grade = user_data_csv[4:-7]
                    i=0
                    for grade_section_csv in csv_user_grade : 
                        if float(grade_section_csv) < context["grade_summary"]["section_breakdown"][global_grade_count]["percent"] :
                            grade_section_csv = context["grade_summary"]["section_breakdown"][global_grade_count]["percent"]
                            # context["grade_summary"]["section_breakdown"][i] = grade_section_csv
                        global_grade_count+=1
                        
                        best_grade_for_section.append(grade_section_csv)
                        global_grade_sum += float(grade_section_csv)


                    continue
        else :
            context = self.check_certificate()
            return JsonResponse(context)


        grade_object= {"global_grade" : global_grade_sum/global_grade_count , "section_grades" : best_grade_for_section}

        return JsonResponse(grade_object , safe=False)
