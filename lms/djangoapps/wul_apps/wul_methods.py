from random import *

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.http import int_to_base36
from student.models import LoginFailures
from openedx.core.djangoapps.user_authn.views.password_reset import PasswordResetConfirmWrapper
from datetime import datetime

import logging
log = logging.getLogger(__name__)


class WulUserActions():
    """
    edx-ficus version == TmaUserActions
    in lms.djangoapps.tma_apps.tma_methods
    """

    def __init__(self, email):
        self.email = email
        self.user = self.get_user(email)

    def get_user(self, email):
        user = None
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            pass
        return user

    # def generate_password_link(self):
    #     final_link=''
    #     if self.user:
    #         uid = int_to_base36(self.user.id)
    #         token = default_token_generator.make_token(self.user)
    #         final_link = reverse(PasswordResetConfirmWrapper, args=(uid, token))
    #     return final_link

    def unlock_user_account(self):
        if self.user and LoginFailures.objects.filter(user=self.user):
            user_failure = LoginFailures.objects.get(user=self.user)
            user_failure.lockout_until = datetime.now()
            user_failure.failure_count=0
            user_failure.save()
            return True
        else:
            return False