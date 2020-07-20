from django.contrib import admin
from .models import MicrositeDetail

class MicrositeDetailAdmin(admin.ModelAdmin):
    list_display = ['name','logo','language_code','color_code']

admin.site.register(MicrositeDetail, MicrositeDetailAdmin)

