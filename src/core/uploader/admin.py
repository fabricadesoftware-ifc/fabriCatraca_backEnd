from django.contrib import admin
from .models import Archive

@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "arquivo", "criado_em")
    search_fields = ("titulo",)
    readonly_fields = ("criado_em",)
