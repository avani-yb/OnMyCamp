from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Post, Reaction, Comment,
    Group, GroupMessage, Conversation,
    Message, StayTuned, Event, AnaConversation
)

# On enregistre chaque modèle pour qu'il apparaisse dans l'admin Django
# UserAdmin est spécial — il gère l'affichage des mots de passe correctement

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Colonnes affichées dans la liste des utilisateurs
    list_display = ['username', 'matricule', 'role', 'privilege', 'is_active_campus']
    list_filter  = ['role', 'privilege']
    # Ajouter nos champs personnalisés dans le formulaire d'édition
    fieldsets = UserAdmin.fieldsets + (
        ('OnMyCamp', {'fields': ('matricule', 'role', 'privilege', 'bio', 'avatar', 'is_active_campus')}),
    )

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['auteur', 'type_media', 'is_pinned', 'date_creation']
    list_filter  = ['type_media', 'is_pinned']

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['nom', 'admin', 'date_creation']

@admin.register(StayTuned)
class StayTunedAdmin(admin.ModelAdmin):
    list_display = ['titre', 'plateforme', 'is_live', 'auteur', 'date_creation']

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['titre', 'type_event', 'date_event', 'auteur']
    list_filter  = ['type_event']

# Les autres modèles enregistrés simplement
admin.site.register(Reaction)
admin.site.register(Comment)
admin.site.register(GroupMessage)
admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(AnaConversation)