import os

from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from django.http import HttpResponse
from datetime import datetime
import json
import hashlib
import hmac

import logging
log = logging.getLogger()


SECRET_KEY = 'wAl%Nx<6Rq/$f6-!7jQFB4mO)P'

def data_check(signature, data):
    """
    Validates the provided signature using HMAC and a shared secret key.
    """

    # Generate HMAC signature based on the data and the SECRET_KEY
    expected_signature = hmac.new(
        SECRET_KEY.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()

    # log.info("expected_signature")
    # log.info(expected_signature)
    # log.info("signature")
    # log.info(signature)

    return hmac.compare_digest(expected_signature, signature)



@csrf_exempt
@require_http_methods(["POST"])
def csvDataWeup(request, course_id):
    """
    Will respond :
        https://af-brazil.weup.in/wul_apps/csv_data_weup/course-v1:af-brasil+PP+TB
    """

    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)
    signature = body_data.get('signature')

    if not signature or not data_check(signature, course_id):
        return HttpResponse('Unauthorized', status=403)


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


