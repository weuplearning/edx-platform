from openedx.features.course_experience.utils import get_course_outline_block_tree
from student.views.dashboard import get_course_enrollments
from opaque_keys.edx.keys import CourseKey

from completion.api.v1.views import SubsectionCompletionView

from django.apps import apps

import logging
import pprint
log = logging.getLogger()

class Completion():
    def __init__(self,request):
        self.request = request

    def calculate_completion(self, course_id):
        total_blocks=0
        total_blockstma=0
        completed_blockstma=0
        completed_blocks=0
        completion_rate=0
        quiz_completion=0
        quiz_total_components=0
        quiz_completed_components=0
        quiz_completion_rate=0
        course_key = CourseKey.from_string(course_id)
        course_sections = get_course_outline_block_tree(self.request,course_id).get('children')
        for section in course_sections :
          total_blockstma+=1
          section_completion = SubsectionCompletionView().get(self.request,self.request.user,course_id,section.get('id')).data
          if section.get('children') is None:
            continue
          for subsection in section.get('children') :
            if subsection.get('children'):
                for unit in subsection.get('children'):
                    total_blocks+=1
                    unit_completion = SubsectionCompletionView().get(self.request,self.request.user,course_id,unit.get('id')).data
                    log.info(unit_completion)
                    if unit_completion.get('completion'):
                        completed_blocks+=1
                    if unit.get('graded') and unit.get('children'):
                        for component in unit.get('children') :
                            quiz_total_components+=1
                            if component.get('complete'):
                                quiz_completed_components+=1
                if completed_blocks == total_blocks:
                    completed_blockstma+=1

        if quiz_total_components!=0:
            quiz_completion_rate =float(quiz_completed_components)/quiz_total_components
        if total_blocks != 0:
            completion_rate = float(completed_blocks)/total_blocks
        response={
            'completion_rate':completion_rate,
            'quiz_completion_rate':quiz_completion_rate
        }
        return response

    def get_course_completion(self, course_id):
        response=self.calculate_completion(course_id)
        return response

    def get_unit_completion(self, course_id, unit_id):
        response = {}
        course_sections = get_course_outline_block_tree(self.request,course_id).get('children')

        for section in course_sections :
          for subsection in section.get('children') :
            if subsection.get('children'):
                for unit in subsection.get('children'):
                    # If current unit
                    if unit['block_id'] in unit_id:
                        response['unit_blocks'] = unit
                        response['success'] = 'ok'

        return response
