"""
Student API Views
"""

from .serializers import StudentSerializer
from django.http import Http404, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication


from openedx.core.lib.api.view_utils import view_auth_classes, DeveloperErrorViewMixin
from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, TokenHasScope, OAuth2Authentication

#@view_auth_classes(is_authenticated=True)
class StudentInfo(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]

    def get(self, request, email, format=None):
        serializer = StudentSerializer(email, context={'request': request})
        return Response(serializer.data)
