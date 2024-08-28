# -*- coding: utf-8 -*-
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse

from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers


from edxmako.shortcuts import render_to_response
import requests
import json


import logging
log = logging.getLogger()


@login_required
def share_linkedin(request):

    auth_code = request.GET.get('code', None)
    badge = request.GET.get('section', None)

    access_token = get_access_token(auth_code, badge)
    profile_info = get_user_profile(access_token)
    upload_badge_link_data = get_upload_link_linkedin(access_token, profile_info.get('sub'))
    upload_badge(upload_badge_link_data, badge)


    badge_data = {
        "author": "urn:li:person:"+profile_info.get('sub') ,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": "I just earned a badge for completing section 1 from course afbrazil-test!"
                },
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "description": {
                            "text": "badge section 1 cours afbrazil-test"
                        },
                        "media": upload_badge_link_data["value"]["asset"],
                        "title": {
                            "text": "Premier pas"
                        }
                    }
                ]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    share_badge_on_linkedin(access_token, badge_data)
    # return ok



def get_access_token(auth_code, badge):
    url = "https://www.linkedin.com/oauth/v2/accessToken"
    linkedIn_id = configuration_helpers.get_value('linkedIn_id', None)
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': 'https://af-brazil.weup.in/wul_apps/social_network/share_linkedin?section='+ badge, 
        'client_id': linkedIn_id["client_id"],
        'client_secret': linkedIn_id["client_secret"] 
    }
    headers = {
        'X-Restli-Protocol-Version' : '2.0.0'
    }

    response = requests.post(url, data=data, headers=headers)

    if response.status_code == 200:
        # Success, return the access token
        return response.json()['access_token']
    else:
        log.error(f"Failed to get access token: {response.status_code}, {response.text}")
        return None



def get_user_profile(access_token):
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version' : '2.0.0'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        log.error(f"Failed to get user profile: {response.status_code}, {response.text}")
        return {}




def get_upload_link_linkedin(access_token,user_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version' : '2.0.0'
    }
    body_upload = {
        "registerUploadRequest": {
            "recipes": [
                "urn:li:digitalmediaRecipe:feedshare-image"
            ],
            "owner": "urn:li:person:"+user_id,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }

    response = requests.post('https://api.linkedin.com/v2/assets?action=registerUpload', json=body_upload, headers=headers)

    if response.status_code == 201:
        log.info('Badge shared successfully.')
    else:
        log.error(f"Failed to share badge: {response.status_code}, {response.text}")

    return  response.json()



def upload_badge( upload_badge_link_data, badge):
    headers = {
        'Authorization': 'Bearer redacted',
        'media-type-family': 'STILLIMAGE'
    }
    # log.info(upload_badge_link_data)
    # log.info(upload_badge_link_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"])
    url = upload_badge_link_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    file_path= '/edx/var/edxapp/media/microsites/af-brazil/badge/'+badge+'.png'

    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, headers=headers, files=files)


    if response.status_code == 201:
        log.info('Badge shared successfully.')
    else:
        log.error(f"Failed to share badge: {response.status_code}, {response.text}")

    return  response

    
def share_badge_on_linkedin(access_token, badge_data):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version' : '2.0.0'
    }

    response = requests.post('https://api.linkedin.com/v2/ugcPosts', json=badge_data, headers=headers)

    if response.status_code == 201:
        log.info('Badge shared successfully.')
    else:
        log.error(f"Failed to share badge: {response.status_code}, {response.text}")

    return response.json()




















@login_required
def share_facebook(request):

    # Semble trop chronophage a mettre en palce pour le moment 


    # https://developers.facebook.com/apps/1003168664888737/settings/basic/

    
    log.info('in share_facebook method')
    log.info(request)

    badge = request.GET.get('section', None)

    log.info("badge")
    log.info(badge)




