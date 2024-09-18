import os

from django.http import HttpResponse
from datetime import datetime

import logging
log = logging.getLogger()


def csvDataWeup(request, course_id):
    # will respond :
    # https://af-brazil.weup.in/wul_apps/csv_data_weup/course-v1:af-brasil+july+2024

    csv_dir_path = '/edx/var/edxapp/media/microsites/af-brazil/csv/'+ course_id
    today_date = datetime.now().strftime('%Y_%m_%d')
    csv_file_path = os.path.join(csv_dir_path, f'{today_date}_af-brasil_grade_report.csv')

    if os.path.exists(csv_file_path):
        with open(csv_file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(csv_file_path)}"'
            return response
    else:
        return HttpResponse('CSV file not found', status=404)



