# -*- coding: utf-8 -*-
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
import json
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build


import logging
log = logging.getLogger()


@require_http_methods(["POST"])
def read_google_drive_file(request):

    credentials_path = '/edx/var/edxapp/media/wul_apps/google_api/credentials.json'
    # Le fichier credentials.json a été récupéré via : https://console.cloud.google.com/iam-admin/serviceaccounts?hl=fr&project=weup-project-28062023

    testData = json.loads(request.body)
    file_id = testData['id']

    # Charger les informations d'identification du fichier de clé
    credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=['https://www.googleapis.com/auth/drive'])

    # Créer un client Drive à l'aide des informations d'identification
    drive_service = build('drive', 'v3', credentials=credentials)
    request = drive_service.files().get_media(fileId=file_id)
    response = request.execute()

    # Préparer les données pour renvoyer au format JSON 
    file_content = response.decode('utf-8')
    file_content_json = json.loads(file_content)

    return JsonResponse(file_content_json)
