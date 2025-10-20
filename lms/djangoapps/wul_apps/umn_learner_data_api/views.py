'''
/lms/djangoapps/wul_apps/umn_learner_data_api/views.py
'''

import json
import base64
import logging
log = logging.getLogger()

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from lms.djangoapps.wul_apps.umn_learner_data_api.api_config import credentials 

# example :
# credentials = {
#     "user": "password"
# }

AUTHORIZED_USERS = credentials

@method_decorator(csrf_exempt, name="dispatch")
class PowerBIAuthView(View):
    """Testing Auth access."""
    def get(self, request):
        auth_header = request.headers.get("Authorization")
        log.info('testing auth')
        if not auth_header or not auth_header.startswith("Basic "):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        try:
            # Decode the credentials
            b64_credentials = auth_header.split(" ")[1]
            decoded = base64.b64decode(b64_credentials).decode("utf-8")
            username, password = decoded.split(":", 1)
        except Exception:
            return JsonResponse({"error": "Invalid credentials format"}, status=400)

        # Validate user
        if AUTHORIZED_USERS.get(username) != password:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        
        with open("/edx/app/edxapp/edx-platform/lms/djangoapps/wul_apps/umn_learner_data_api/data.json", "r") as datafile:
            UMN_DATA = json.load(datafile)

        return JsonResponse(UMN_DATA, safe=False)


