'''
lms/djangoapps/wul_apps/custom_grade/bvt/views.py
'''

import os
from io import BytesIO
import json
import time

from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from django.http import JsonResponse
from lms.djangoapps.instructor_task.api_helper import AlreadyRunningError
# from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from django.utils.translation import ugettext as _



from opaque_keys.edx.locator import CourseLocator
from common.djangoapps.student.models import CourseEnrollment
from courseware.courses import get_course_by_id
from lms.djangoapps.grades.context import grading_context_for_course
from lms.djangoapps.courseware.user_state_client import DjangoXBlockUserStateClient

from openpyxl import Workbook

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import logging
log = logging.getLogger()



@require_http_methods(["POST"])
@login_required
def run_script_from_back(request):
  try:
    email = str(request.user.email)
    data = json.loads(request.body)
    log.info('------------> Begin fetching user data and answers')
    all_users_data = {}
    course_id = data['courseId']
    course_key = CourseLocator.from_string(course_id)
    course = get_course_by_id(course_key)
    course_enrollments = CourseEnrollment.objects.filter(course_id=course_key)

    for i in range(len(course_enrollments)):
      user = course_enrollments[i].user
      log.info('user')
      log.info(user)
      user_data = {}

      # Update object with user data without grades
      try:
        user_data["username"] = user.username
      except:
        try:
          user_data["username"] = json.loads(user.profile.custom_field)['username']
        except:
          user_data["username"] = 'n.a.'

      try:
        user_data["firstname"] = user.first_name.capitalize()
      except:
        try:
          user_data["firstname"] = json.loads(user.profile.custom_field)['firstname'].capitalize()
        except:
          user_data["firstname"] = 'n.a.'

      try:
        user_data["lastname"] = user.last_name.capitalize()
      except:
        try:
          user_data["lastname"] = json.loads(user.profile.custom_field)['lastname'].capitalize()
        except:
          user_data["lastname"] = 'n.a.'

      # Access Section
      scorable_block_titles = []
      grading_context = grading_context_for_course(course)
      user_state_client = DjangoXBlockUserStateClient()
      list_question = []

      for section in grading_context['all_graded_subsections_by_type']['Exam']:
          for unit in section['scored_descendants']:
              scorable_block_titles.append((unit.location))

      for block_location in scorable_block_titles:

        question = {}
        try:
          history_entries = list(user_state_client.get_history(user.username, block_location))
        except:
          history_entries = []
        question['problem'] = str(block_location)[-2:]

        try:
          for key, value in history_entries[0].state['student_answers'].items():

            if isinstance(value, list):
              question['choice'] = value
            else:
              liste = []
              liste.append(value)
              question['choice'] = liste
        except:
          question['choice'] = 'n.a.'

        try:
          question['time'] = history_entries[0].state['last_submission_time']
        except:
          question['time'] = 'n.a.'

        try:
          question['score'] = history_entries[0].state['score']['raw_earned']
        except:
          question['score'] = 'n.a.'

        list_question.append(question)

      data = { "general": user_data, 'list_question' : list_question }
      all_users_data[str(user.id)]= data

    log.info('------------> Finish fetching user data and answers')

    log.info('------------> Begin Calculate grades and write xlsx report')
    # Grades need to be recalculate :
    # We need to generate un json when the course is converted. 
    # Then we can fetch it using the course name (value given when creating the tar.gz) 

    course_names = []
    course_names_html = []
    
    course = get_course_by_id(CourseLocator.from_string(course_id)) 
    course_names.append(course.display_name_with_default)
    course_names_html.append("<li>"+ str(course.display_name_with_default)+"</li>")
    # course_names_html.append("<li>"+ str(course.display_name_with_default.encode('ascii', errors='xmlcharrefreplace'))+"</li>")


    json_file_name = 'list_corrected_answer_' + str(course_names[0]).replace(' ', '_') +'.json'
    # UPDATE answer_list
    with open('/edx/var/edxapp/media/microsites/bvt/answers_lists_files/'+json_file_name) as json_file:
      answer_list = json.load(json_file)


    def updateGrade(problemNum, choices, answer_list):
      answered_true = 0

      if choices == 'n.a.' :
        grade = 0
        return grade

      translated_list = []
      for choice in choices:
        index = choice.split('_')[1]
        translated_list.append(index)

      for choice in translated_list :
        problemRef = 'problem'+ problemNum

        if choice in answer_list[problemRef]:
          answered_true += 1
        else:
          grade = 0
          return grade

      if answered_true == len(answer_list[problemRef]):
        grade = 1
      else:
        grade = 0.5

      return grade


    # WRITE XLS
    timestr = time.strftime("%Y_%m_%d")
    wb = Workbook()
    # wb = Workbook(encoding='utf-8')
    sheet = wb.active
    sheet.title= 'Rapport'
    filename = '/home/edxtma/csv/{}_BVT_grade_report.xls'.format(timestr)
    headers = ['ID', 'Prénom', 'Nom']
    first = True

    j=2
    for i, header in enumerate(headers):
      sheet.cell(1, i+1, header)

    for key, user in all_users_data.items():
      i = 3 
      sheet.cell(j, 1, user['general']['username'])
      sheet.cell(j, 2, user['general']['firstname'])
      sheet.cell(j, 3, user['general']['lastname'])

      correctedExamGrade = 0
      for question in user['list_question']:
        correctedGrade = 0

        if first:  
          sheet.cell(1, i+1, question['problem'])
          sheet.cell(1, i+2, 'Score')
          sheet.cell(1, i+3, 'Réponses choisies')
        sheet.cell(j, i+1, question['time'])

        correctedGrade = updateGrade(question['problem'], question['choice'], answer_list)
        choices = ''
        for choice in question['choice'] :
          choices += str(choice) + ' '

        sheet.cell(j, i+2, correctedGrade)
        sheet.cell(j, i+3, choices)

        correctedExamGrade += correctedGrade
        i += 3
      sheet.cell(j, i+1, correctedExamGrade)
      first = False
      j += 1

    sheet.cell(1, i+1, 'Note finale')

    # SEND MAILS
    output = BytesIO()
    wb.save(output)
    _files_values = output.getvalue()
    course_names_html = ''.join(course_names_html)

    html = "<html><head></head><body><p>Bonjour,<br/><br/>Vous trouverez en pièce jointe le rapport de note : "+ course_names_html +"<br/><br/></p></body></html>"


    part2 = MIMEText(html.encode('utf-8'), 'html', 'utf-8')
    fromaddr = "ne-pas-repondre@themoocagency.com"
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = email
    msg['Subject'] = "BVT_grade_report"
    attachment = _files_values
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= %s" % os.path.basename(filename))
    msg.attach(part)
    server = smtplib.SMTP('mail3.themoocagency.com', 25)
    server.starttls()
    server.login('contact', 'waSwv6Eqer89')
    msg.attach(part2)
    text = msg.as_string()
    server.sendmail(fromaddr, email, text)
    server.quit()
    log.info('Email sent to '+str(email))


    log.info('------------> Finish calculate grades and write xlsx report')


    success_status = _("The grade report is being created."
                        " To view the status of the report, see Pending Tasks below.")
    return JsonResponse({"status": success_status,"user_email":email})
  except :
    already_running_status = _("La création d'utilisateurs est en cours, veuillez attendre quelle se finisse")
    return JsonResponse({"status": already_running_status})

