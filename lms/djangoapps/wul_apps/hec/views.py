# -*- coding: utf-8 -*-
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
import json
import logging
log = logging.getLogger()




@require_http_methods(["POST"])
def hec_pe_check_email(request):
    
    input_data = json.loads(request.body)
    try:
        input_email = input_data['email']
        input_email = input_email.lower()

    except KeyError:
        response = {'isValid' : False,'msg' : 'KeyError on POST data'}
        return JsonResponse(response, safe=False)
    
    # json file provided / modified via github
    filename = 'email_template.json'
    path = '/edx/var/edxapp/media/hec-pole-emploi/client_hec-pole-emploi/hec-pole-emploi_allowed-emails/' + filename
    email_json = json.load(open(path))
    emails = email_json.get('email_list_hec_pole_emploi',None)
    if(emails == None):
        response = {'isValid' : False,'msg' : 'KeyError in json object'}
        return JsonResponse(response, safe=False)
        
    
    response_ok = {'isValid' : True,'msg' : 'valid'}
    response_notfound = {'isValid' : False,'msg' : 'access denied', 'data': emails,'input' : input_data}
    
    for email in emails:
        if(email.lower()==input_email):
            return JsonResponse(response_ok, safe=False)
    
    return JsonResponse(response_notfound, safe=False)
