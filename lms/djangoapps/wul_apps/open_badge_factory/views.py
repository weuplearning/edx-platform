# -*- coding: utf-8 -*-
import sys
#reload(sys)
#sys.setdefaultencoding('utf8')

import requests
import json

from util.json_request import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseServerError
from django.http import HttpResponseForbidden
from django.core.mail import EmailMessage
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

import logging
log = logging.getLogger()


@login_required
@require_http_methods(['POST'])
def issue_badge(request):

    open_badge_factory = configuration_helpers.get_value('open_badge_factory', None)
    if open_badge_factory:
        client_id = open_badge_factory.get('client_id')
        client_secret = open_badge_factory.get('client_secret')
    else:
        client_id = None
        client_secret = None

    if client_id is not None and client_secret is not None:
        # Get access_token
        url = 'https://openbadgefactory.com/v1/client/oauth2/token'
        form = {'grant_type': 'client_credentials', 'client_id': client_id, 'client_secret': client_secret}
        resp = requests.post(url, data=form)
        access_token = resp.json()['access_token']
        badge_id = request.POST['badge_id']

        # Update user's badge status
        url = 'https://openbadgefactory.com/v1/badge/{}/{}'.format(client_id, badge_id)
        form = json.dumps({'recipient': [request.user.email]})
        headers = {
            'content-type': 'application/json',
            'Authorization': 'Bearer ' + access_token,
        }
        resp = requests.post(url, data=form, headers=headers)
        return JsonResponse({'status':resp.status_code})
    else:
        log.info('issue_badge in ELSE loop')
        return JsonResponse({'status':500, 'message' : '[WUL] [ERROR] missing open_badge_factory object/proporties in microsite configurations, please check this in Django admin'})
