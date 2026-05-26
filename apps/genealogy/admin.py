from django.contrib import admin
from .models import Family, Relationship, PersonFamilyMembership


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display  = ['name', 'clan', 'founding_person', 'established_date']
    list_filter   = ['clan']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Relationship)
class RelationshipAdmin(admin.ModelAdmin):
    list_display  = ['from_person', 'relation_type', 'to_person', 'is_biological']
    list_filter   = ['relation_type', 'is_biological']
    search_fields = ['from_person__full_name', 'to_person__full_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PersonFamilyMembership)
class PersonFamilyMembershipAdmin(admin.ModelAdmin):
    list_display  = ['person', 'family', 'role_in_family']
    list_filter   = ['role_in_family', 'family']
    readonly_fields = ['created_at', 'updated_at']