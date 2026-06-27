from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
import json, random

from .models import (
    User, Post, Reaction, Comment,
    Group, GroupMessage, Conversation,
    Message, StayTuned, Event, AnaConversation
)


def global_context(request, active_tab=''):
    """
    Retourne un dictionnaire de données communes
    à toutes les pages (onglet actif, nb notifications...)
    """
    return {
        'active': active_tab,
        'notif_count': 0,  
        'now': timezone.now(),
    }


#  AUTH

def login_view(request):
    """Page de connexion"""
    if request.user.is_authenticated:
        return redirect('accueil')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('accueil')
        else:
            messages.error(request, 'Identifiants incorrects.')

    return render(request, 'auth/login.html', global_context(request))


def logout_view(request):
    """Déconnexion"""
    logout(request)
    return redirect('login')


def register(request):
    """Page d'inscription"""
    if request.method == 'POST':
        username   = request.POST.get('username')
        matricule  = request.POST.get('matricule')
        first_name = request.POST.get('first_name')
        last_name  = request.POST.get('last_name')
        email      = request.POST.get('email')
        password1  = request.POST.get('password1')
        password2  = request.POST.get('password2')
        role       = request.POST.get('role', 'etudiant')

        # Vérifications basiques
        if password1 != password2:
            messages.error(request, 'Les mots de passe ne correspondent pas.')
            return render(request, 'auth/register.html', global_context(request))

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Ce nom d\'utilisateur est déjà pris.')
            return render(request, 'auth/register.html', global_context(request))

        if matricule and User.objects.filter(matricule=matricule).exists():
            messages.error(request, 'Ce matricule est déjà enregistré.')
            return render(request, 'auth/register.html', global_context(request))

        # Création du compte
        user = User.objects.create_user(
            username=username,
            password=password1,
            email=email,
            first_name=first_name,
            last_name=last_name,
            matricule=matricule,
            role=role,
        )
        login(request, user)
        messages.success(request, f'Bienvenue {first_name} ! Ton compte a été créé.')
        return redirect('accueil')

    return render(request, 'auth/register.html', global_context(request))



#  ACCUEIL

@login_required
def accueil(request):
    """
    Fil de publications.
    @login_required = redirige vers /login/ si pas connecté
    """
    posts = Post.objects.select_related('auteur').prefetch_related('reactions', 'comments')
    reactions_list = [
        ("👍", "like"),
        ("❤️", "coeur"),
        ("😆", "rire"),
        ("😮", "choc"),
        ("👏", "bravo")
    ]

    # Pour chaque post, on calcule les réactions de l'utilisateur connecté
    for post in posts:
        post.user_reaction = post.reactions.filter(auteur=request.user).first()
        post.likes   = post.reactions.filter(type_reaction='like').count()
        post.coeurs  = post.reactions.filter(type_reaction='coeur').count()
        post.rires   = post.reactions.filter(type_reaction='rire').count()
        post.chocs   = post.reactions.filter(type_reaction='choc').count()
        post.bravos  = post.reactions.filter(type_reaction='bravo').count()
        post.total_reactions = post.likes + post.coeurs + post.rires + post.chocs + post.bravos
        post.nb_comments = post.comments.count()
    ctx = global_context(request, 'accueil')
    ctx['posts'] = posts
    return render(request, 'core/accueil.html', ctx)


@login_required
def post_create(request):
    """Créer une publication"""
    if not request.user.can_post:
        messages.error(request, 'Vous n\'avez pas les droits pour publier.')
        return redirect('accueil')

    if request.method == 'POST':
        contenu    = request.POST.get('contenu', '')
        type_media = request.POST.get('type_media', 'texte')
        legende    = request.POST.get('legende', '')
        media      = request.FILES.get('media')

        Post.objects.create(
            auteur=request.user,
            contenu=contenu,
            type_media=type_media,
            media=media,
            legende=legende,
        )
        messages.success(request, 'Publication créée !')
        return redirect('accueil')

    ctx = global_context(request, 'accueil')
    return render(request, 'core/post_create.html', ctx)


@login_required
def post_delete(request, pk):
    """Supprimer une publication"""
    post = get_object_or_404(Post, pk=pk)
    if request.user.privilege == 'superadmin' or request.user == post.auteur:
        post.delete()
        messages.success(request, 'Publication supprimée.')
    return redirect('accueil')


@login_required
def post_react(request, pk):
    """Toggle réaction sur un post — retourne JSON si appel AJAX"""
    post = get_object_or_404(Post, pk=pk)
    type_reaction = request.POST.get('type_reaction', 'like')

    reaction, created = Reaction.objects.get_or_create(
        post=post, auteur=request.user,
        defaults={'type_reaction': type_reaction}
    )
    if not created:
        if reaction.type_reaction == type_reaction:
            reaction.delete()
            user_reaction = None
        else:
            reaction.type_reaction = type_reaction
            reaction.save()
            user_reaction = type_reaction
    else:
        user_reaction = type_reaction

    # Si appel AJAX (fetch) → retourner JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'likes':  post.reactions.filter(type_reaction='like').count(),
            'coeurs': post.reactions.filter(type_reaction='coeur').count(),
            'rires':  post.reactions.filter(type_reaction='rire').count(),
            'chocs':  post.reactions.filter(type_reaction='choc').count(),
            'bravos': post.reactions.filter(type_reaction='bravo').count(),
            'user_reaction': user_reaction,
        })

    return redirect('accueil')
# ══════════════════════════════════════════
#  TEAM
# ══════════════════════════════════════════
@login_required
def team(request):
    """Liste des groupes de l'utilisateur"""
    groupes = request.user.groupes.all().prefetch_related('messages')

    for g in groupes:
        g.last_msg = g.messages.last()
        g.unread   = 0  # compteur simplifié pour l'instant

    ctx = global_context(request, 'team')
    ctx['groups'] = groupes
    return render(request, 'core/team.html', ctx)


@login_required
def group_create(request):
    """Créer un groupe"""
    if not request.user.can_create_group:
        messages.error(request, 'Droits insuffisants.')
        return redirect('team')

    if request.method == 'POST':
        nom         = request.POST.get('nom')
        description = request.POST.get('description', '')
        emoji       = request.POST.get('emoji', '👥')

        group = Group.objects.create(
            nom=nom, admin=request.user,
            description=description, emoji=emoji
        )
        group.membres.add(request.user)
        messages.success(request, f'Groupe "{nom}" créé !')
        return redirect('group_detail', pk=group.pk)

    ctx = global_context(request, 'team')
    return render(request, 'core/group_create.html', ctx)


@login_required
def group_detail(request, pk):
    group = get_object_or_404(Group, pk=pk)

    if request.user not in group.membres.all():
        messages.error(request, 'Vous n\'êtes pas membre de ce groupe.')
        return redirect('team')

    if request.method == 'POST':
        contenu = request.POST.get('contenu', '')
        fichier = request.FILES.get('fichier')
        if contenu or fichier:
            GroupMessage.objects.create(
                groupe=group, auteur=request.user,
                contenu=contenu, fichier=fichier
            )
        return redirect('group_detail', pk=pk)

    messages_list = group.messages.select_related('auteur').all()

    # Utilisateurs qu'on peut encore ajouter (pas déjà membres)
    users_to_add = User.objects.exclude(
        pk__in=group.membres.values_list('pk', flat=True)
    ).order_by('first_name')

    ctx = global_context(request, 'team')
    ctx.update({
        'group': group,
        'messages_list': messages_list,
        'users_to_add': users_to_add,
    })
    return render(request, 'core/group_detail.html', ctx)

# ══════════════════════════════════════════
#  STAY TUNED
# ══════════════════════════════════════════
@login_required
def staytuned(request):
    """Liste des liens de conférences"""
    liens = StayTuned.objects.select_related('auteur').all()
    ctx = global_context(request, 'staytuned')
    ctx['liens'] = liens
    return render(request, 'core/staytuned.html', ctx)


@login_required
def staytuned_create(request):
    """Ajouter un lien de conférence"""
    if request.method == 'POST':
        StayTuned.objects.create(
            auteur=request.user,
            titre=request.POST.get('titre'),
            url=request.POST.get('url'),
            plateforme=request.POST.get('plateforme', 'Zoom'),
            description=request.POST.get('description', ''),
            is_live=request.POST.get('is_live') == 'on',
        )
        messages.success(request, 'Lien ajouté !')
        return redirect('staytuned')

    ctx = global_context(request, 'staytuned')
    return render(request, 'core/staytuned_create.html', ctx)


# ══════════════════════════════════════════
#  INBOX
# ══════════════════════════════════════════
@login_required
def inbox(request):
    """Liste des conversations privées"""
    convs = request.user.conversations.prefetch_related('participants', 'messages').all()

    conv_list = []
    for conv in convs:
        interlocuteur = conv.participants.exclude(pk=request.user.pk).first()
        last_msg = conv.messages.last()
        conv_list.append({
            'conv': conv,
            'interlocuteur': interlocuteur,
            'last_msg': last_msg,
            'unread': conv.messages.filter(lu=False).exclude(auteur=request.user).count(),
        })

    ctx = global_context(request, 'inbox')
    ctx['conv_list'] = conv_list
    return render(request, 'core/inbox.html', ctx)


@login_required
def conversation_new(request):
    """Démarrer une nouvelle conversation"""
    if request.method == 'POST':
        dest_pk = request.POST.get('destinataire')
        dest = get_object_or_404(User, pk=dest_pk)

        # Bloquer étudiant → enseignant/RR/DAAC
        roles_interdits = ['enseignant', 'rr', 'daac']
        if request.user.role == 'etudiant' and dest.role in roles_interdits:
            messages.error(request, f'Vous ne pouvez pas écrire directement à {dest.get_full_name()}.')
            return redirect('inbox')

        # Cherche conversation existante
        conv = Conversation.objects.filter(
            participants=request.user
        ).filter(participants=dest).first()

        if not conv:
            conv = Conversation.objects.create()
            conv.participants.add(request.user, dest)

        return redirect('conversation_detail', pk=conv.pk)

    users = User.objects.exclude(pk=request.user.pk)
    ctx = global_context(request, 'inbox')
    ctx['users'] = users
    return render(request, 'core/conversation_new.html', ctx)


@login_required
def conversation_detail(request, pk):
    """Page de conversation privée"""
    conv = get_object_or_404(Conversation, pk=pk)

    if request.user not in conv.participants.all():
        return redirect('inbox')

    if request.method == 'POST':
        contenu = request.POST.get('contenu', '')
        fichier = request.FILES.get('fichier')
        if contenu or fichier:
            Message.objects.create(
                conversation=conv,
                auteur=request.user,
                contenu=contenu,
                fichier=fichier,
            )
        return redirect('conversation_detail', pk=pk)

    # Marquer les messages comme lus
    conv.messages.filter(lu=False).exclude(auteur=request.user).update(lu=True)

    interlocuteur = conv.participants.exclude(pk=request.user.pk).first()
    msgs = conv.messages.select_related('auteur').all()

    ctx = global_context(request, 'inbox')
    ctx.update({'conv': conv, 'interlocuteur': interlocuteur, 'msgs': msgs})
    return render(request, 'core/conversation_detail.html', ctx)



#  AGENDA

@login_required
def agenda(request):
    """Calendrier des événements"""
    events = Event.objects.select_related('auteur').all()
    ctx = global_context(request, 'agenda')
    ctx['events'] = events
    return render(request, 'core/agenda.html', ctx)


@login_required
def event_create(request):
    """Créer un événement"""
    if request.method == 'POST':
        Event.objects.create(
            auteur=request.user,
            titre=request.POST.get('titre'),
            description=request.POST.get('description', ''),
            date_event=request.POST.get('date_event'),
            heure_debut=request.POST.get('heure_debut') or None,
            heure_fin=request.POST.get('heure_fin') or None,
            type_event=request.POST.get('type_event', 'autre'),
        )
        messages.success(request, 'Événement ajouté !')
        return redirect('agenda')

    ctx = global_context(request, 'agenda')
    return render(request, 'core/event_create.html', ctx)


# ══════════════════════════════════════════
#  ANA IA
# ══════════════════════════════════════════
@login_required
def ana(request):
    """Page Ana IA"""
    historique = AnaConversation.objects.filter(user=request.user).order_by('date')[:20]
    ctx = global_context(request, 'ana')
    ctx['historique'] = historique
    return render(request, 'core/ana.html', ctx)


@login_required
def ana_message(request):
    """
    Reçoit un message de l'utilisateur et retourne
    une réponse simulée d'Ana (version démo).
    En production : remplacer par l'appel au modèle Mistral.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        question = data.get('message', '')

        # Réponses simulées selon les mots-clés
        reponse = generer_reponse_ana(question)

        # Sauvegarder l'échange en base
        AnaConversation.objects.create(
            user=request.user,
            question=question,
            reponse=reponse,
        )
        return JsonResponse({'response': reponse})

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


def generer_reponse_ana(question):
    """
    Réponses simulées pour la démo.
    Sera remplacé par le vrai modèle Mistral fine-tuné.
    """
    q = question.lower()
    if any(w in q for w in ['django', 'python', 'views', 'models']):
        return "Django est un framework Python qui suit le pattern MVT (Model-View-Template). Les modèles définissent tes données, les vues traitent la logique, et les templates affichent le HTML. C'est exactement ce qu'on utilise dans OnMyCamp ! 🐍"
    elif any(w in q for w in ['flutter', 'dart', 'mobile']):
        return "Flutter est le framework Google pour créer des apps Android et iOS avec une seule base de code en Dart. Il compile en code natif, ce qui donne d'excellentes performances. C'est ce qu'on utilisera pour l'app mobile OnMyCamp ! 📱"
    elif any(w in q for w in ['ia', 'intelligence', 'machine learning', 'ml', 'deep']):
        return "Le Machine Learning, c'est apprendre des patterns dans les données. Le Deep Learning est un sous-ensemble qui utilise des réseaux de neurones profonds. Je suis moi-même basée sur Mistral 7B, un modèle fine-tuné sur les données Tech et du campus IAI ! 🤖"
    elif any(w in q for w in ['iai', 'examen', 'campus', 'cours', 'soutenance']):
        return "Pour les informations sur le campus IAI Cameroun : les examens S1 2024-2025 débutent le 15 janvier. Pour les questions administratives, consulte le bureau de la scolarité ou ton représentant résident. 🏫"
    elif any(w in q for w in ['bonjour', 'salut', 'hello', 'hi', 'bonsoir']):
        return "Bonjour ! Je suis Ana, ton assistante IA spécialisée en Tech et dans la vie du campus IAI. Comment puis-je t'aider aujourd'hui ? 😊"
    elif any(w in q for w in ['merci', 'thanks', 'thank you']):
        return "Avec plaisir ! N'hésite pas si tu as d'autres questions. Je suis là pour t'aider. 💪"
    else:
        reponses_defaut = [
            "C'est une excellente question ! Dans ma version complète (avec Mistral fine-tuné), je pourrai te répondre précisément sur ce sujet. Pour l'instant, consulte la documentation officielle ou pose la question à ton prof. 📚",
            "Je note cette question pour améliorer mon entraînement ! En attendant, Stack Overflow et la documentation Django sont tes meilleurs amis. 🔍",
            "Bonne question ! Reviens me voir quand mon modèle sera complètement fine-tuné — je serai bien plus précise. Tu peux aussi chercher sur docs.djangoproject.com. 🐍",
        ]
        return random.choice(reponses_defaut)



#  PROFIL & UTILITAIRES
@login_required
def post_comment(request, pk):
    """Ajouter un commentaire sur un post"""
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        contenu = request.POST.get('contenu', '').strip()
        if contenu:
            Comment.objects.create(
                post=post,
                auteur=request.user,
                contenu=contenu,
            )
    return redirect('accueil')


@login_required
def group_add_member(request, pk):
    """Ajouter un membre dans un groupe — réservé à l'admin du groupe"""
    group = get_object_or_404(Group, pk=pk)

    # Seul l'admin du groupe peut ajouter des membres
    if request.user != group.admin:
        messages.error(request, 'Seul l\'admin du groupe peut ajouter des membres.')
        return redirect('group_detail', pk=pk)

    if request.method == 'POST':
        user_pk = request.POST.get('user_pk')
        user = get_object_or_404(User, pk=user_pk)
        group.membres.add(user)
        messages.success(request, f'{user.get_full_name()} ajouté au groupe !')

    return redirect('group_detail', pk=pk)


@login_required
def group_remove_member(request, pk, user_pk):
    """Retirer un membre du groupe — réservé à l'admin du groupe"""
    group = get_object_or_404(Group, pk=pk)

    if request.user != group.admin:
        messages.error(request, 'Seul l\'admin du groupe peut retirer des membres.')
        return redirect('group_detail', pk=pk)

    user = get_object_or_404(User, pk=user_pk)

    # On ne peut pas retirer l'admin lui-même
    if user == group.admin:
        messages.error(request, 'L\'admin ne peut pas être retiré du groupe.')
        return redirect('group_detail', pk=pk)

    group.membres.remove(user)
    messages.success(request, f'{user.get_full_name()} retiré du groupe.')
    return redirect('group_detail', pk=pk)
@login_required
def post_reaction_summary(request, pk):
    """Retourne le résumé des réactions d'un post en JSON"""
    post = get_object_or_404(Post, pk=pk)
    user_reaction = post.reactions.filter(auteur=request.user).first()
    data = {
        'like':  post.reactions.filter(type_reaction='like').count(),
        'coeur': post.reactions.filter(type_reaction='coeur').count(),
        'rire':  post.reactions.filter(type_reaction='rire').count(),
        'choc':  post.reactions.filter(type_reaction='choc').count(),
        'bravo': post.reactions.filter(type_reaction='bravo').count(),
        'user_reaction': user_reaction.type_reaction if user_reaction else None,
    }
    return JsonResponse(data)
@login_required
def profil(request, pk):
    """Page profil d'un utilisateur"""
    user_profil = get_object_or_404(User, pk=pk)
    ctx = global_context(request)
    ctx['user_profil'] = user_profil
    return render(request, 'core/profil.html', ctx)


@login_required
def recherche(request):
    """Recherche d'utilisateurs et de contenus"""
    query = request.GET.get('q', '')
    results_users = []
    results_posts = []

    if query:
        results_users = User.objects.filter(
            username__icontains=query
        ) | User.objects.filter(first_name__icontains=query)

        results_posts = Post.objects.filter(contenu__icontains=query)

    ctx = global_context(request)
    ctx.update({'query': query, 'results_users': results_users, 'results_posts': results_posts})
    return render(request, 'core/recherche.html', ctx)


@login_required
def notifications(request):
    """Page notifications (simplifiée pour la démo)"""
    ctx = global_context(request)
    return render(request, 'core/notifications.html', ctx)

