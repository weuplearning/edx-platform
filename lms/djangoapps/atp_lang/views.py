import logging
import urllib

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.urls import reverse
from django.db import transaction
from django.conf import settings
from django.shortcuts import redirect
from student.models import UserProfile
from django.http import HttpResponseRedirect
from openedx.core.djangoapps.user_api.preferences.api import update_user_preferences
def change_lang(request,langue):
    username = request.user.username
    """
    lang_update = UserProfile.objects.get(user_id = user_id)
    lang_update.language = langue
    lang_update.save()
    """
    data = {"pref-lang":langue}
    update_user_preferences(request.user, data, user=username)
    response = HttpResponseRedirect("/")
    return response
