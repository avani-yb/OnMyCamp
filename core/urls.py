from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('',                          views.accueil,             name='accueil'),
    path('login/',                    views.login_view,          name='login'),
    path('logout/',                   views.logout_view,         name='logout'),
    path('register/',                 views.register,            name='register'),

    # Onglets
    path('team/',                     views.team,                name='team'),
    path('staytuned/',                views.staytuned,           name='staytuned'),
    path('inbox/',                    views.inbox,               name='inbox'),
    path('agenda/',                   views.agenda,              name='agenda'),
    path('ana/',                      views.ana,                 name='ana'),

    # Posts
    path('post/create/',              views.post_create,         name='post_create'),
    path('post/<int:pk>/delete/',     views.post_delete,         name='post_delete'),
    path('post/<int:pk>/react/',      views.post_react,          name='post_react'),
    path('post/<int:pk>/comment/',    views.post_comment,        name='post_comment'),
    path('post/<int:pk>/summary/', views.post_reaction_summary, name='post_reaction_summary'),

    # Groupes
    path('group/create/',             views.group_create,        name='group_create'),
    path('group/<int:pk>/',           views.group_detail,        name='group_detail'),
    path('group/<int:pk>/add/',       views.group_add_member,    name='group_add_member'),
    path('group/<int:pk>/remove/<int:user_pk>/', views.group_remove_member, name='group_remove_member'),

    # Inbox
    path('inbox/<int:pk>/',           views.conversation_detail, name='conversation_detail'),
    path('inbox/new/',                views.conversation_new,    name='conversation_new'),

    # Stay Tuned
    path('staytuned/create/',         views.staytuned_create,    name='staytuned_create'),

    # Agenda
    path('agenda/create/',            views.event_create,        name='event_create'),

    # Ana
    path('ana/message/',              views.ana_message,         name='ana_message'),

    # Profil
    path('profil/<int:pk>/',          views.profil,              name='profil'),
    path('recherche/',                views.recherche,           name='recherche'),
    path('notifications/',            views.notifications,       name='notifications'),
]