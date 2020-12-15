"""
Webservice Student API URLs
"""
from django.conf import settings
from django.conf.urls import url, include
from rest_framework.urlpatterns import format_suffix_patterns
from .views import StudentInfo


urlpatterns = [
        url(r'^v1/student_info/(?P<email>[^/]*)$', StudentInfo.as_view(), name="student-info"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
