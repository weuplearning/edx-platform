# pylint: disable=unused-import
"""
Python APIs exposed by the bulk_email app to other in-process apps.
"""

# Public Bulk Email Functions


import logging

from bulk_email.models_api import (
    is_bulk_email_enabled_for_course,
    is_bulk_email_feature_enabled,
    is_user_opted_out_for_course
)

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from lms.djangoapps.discussion.notification_prefs.views import UsernameCipher, UsernameDecryptionException

User = get_user_model()
log = logging.getLogger(__name__)


def get_emails_enabled(user, course_id):
    """
    Get whether or not emails are enabled in the context of a course.

    Arguments:
        user: the user object for which we want to check whether emails are enabled
        course_id (string): the course id of the course

    Returns:
        (bool): True if emails are enabled for the course associated with course_id for the user;
        False otherwise
    """
    if is_bulk_email_feature_enabled(course_id=course_id):
        return not is_user_opted_out_for_course(user=user, course_id=course_id)
    return None


def get_unsubscribed_link(email, course_id):
    """

    :param email: user email
    :param course_id:
    :return: AES encrypted token based on the email and course_id
    """
    text_to_encrypt = u'{email} {course_id}'.format(email=email, course_id=course_id)
    token = UsernameCipher.encrypt(text_to_encrypt)
    optout_url = reverse('bulk_email_opt_out', kwargs={'token': token})
    url = '{base_url}/{optout_url}'.format(base_url=settings.LMS_ROOT_URL, optout_url=optout_url)
    return url
