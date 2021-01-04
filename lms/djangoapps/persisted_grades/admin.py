from config_models.admin import ConfigurationModelAdmin, KeyedConfigurationModelAdmin
from django.contrib import admin

from import_export.admin import ImportExportModelAdmin

from lms.djangoapps.persisted_grades import models

class PersistedGradesAdmin(ImportExportModelAdmin):
    """Admin for PersistedGrades"""
    list_display = ['course_id','user_id','percent','passed','quiz_completed','first_access','first_success']
    search_fields = ['course_id','user_id','percent','passed','quiz_completed','first_access','first_success']

admin.site.register(models.PersistedGrades, PersistedGradesAdmin)

