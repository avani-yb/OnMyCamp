from django.db import models
from django.contrib.auth.models import AbstractUser

# ── UTILISATEUR PERSONNALISÉ ──
# On étend le modèle User par défaut de Django
# pour ajouter nos champs spécifiques à OnMyCamp
class User(AbstractUser):
    ROLE_CHOICES = [
        ('etudiant', 'Étudiant'),
        ('enseignant', 'Enseignant'),
        ('rr', 'Représentant Résident'),
        ('daac', 'DAAC'),
        ('tuteur', 'Tuteur'),
    ]
    PRIVILEGE_CHOICES = [
        ('aucun', 'Aucun'),
        ('delegue', 'Délégué'),
        ('chef_classe', 'Chef de classe'),
        ('extended', 'Extended'),
        ('exclusif', 'Exclusif'),
        ('admin', 'Admin'),
        ('superadmin', 'Super Admin'),
    ]

    matricule   = models.CharField(max_length=20, unique=True, blank=True, null=True)
    role        = models.CharField(max_length=20, choices=ROLE_CHOICES, default='etudiant')
    privilege   = models.CharField(max_length=20, choices=PRIVILEGE_CHOICES, default='aucun')
    bio         = models.TextField(blank=True)
    avatar      = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_active_campus = models.BooleanField(default=True)

    # Propriété calculée : peut-il publier dans l'Accueil ?
    @property
    def can_post(self):
        return self.privilege in ['extended', 'exclusif', 'admin', 'superadmin'] \
               or self.role in ['rr', 'daac']

    # Peut-il créer un groupe Team ?
    @property
    def can_create_group(self):
        return self.privilege in ['delegue', 'chef_classe', 'exclusif', 'extended', 'admin', 'superadmin']

    def __str__(self):
        return f"{self.get_full_name()} ({self.matricule})"


# ── PUBLICATION (ACCUEIL) ──
# Une publication dans le fil d'actualité
class Post(models.Model):
    TYPE_CHOICES = [
        ('texte', 'Texte'),
        ('image', 'Image'),
        ('video', 'Vidéo'),
    ]
    auteur      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    contenu     = models.TextField(blank=True)
    type_media  = models.CharField(max_length=10, choices=TYPE_CHOICES, default='texte')
    media       = models.ImageField(upload_to='posts/', blank=True, null=True)
    legende     = models.TextField(blank=True)
    is_pinned   = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_pinned', '-date_creation']  # épinglés en premier

    def __str__(self):
        return f"Post de {self.auteur} — {self.date_creation:%d/%m/%Y}"


# ── RÉACTION ──
# Un utilisateur peut réagir à un post (👍❤️😂😮👏)
class Reaction(models.Model):
    TYPES = [
        ('like', '👍'), ('coeur', '❤️'), ('rire', '😂'),
        ('choc', '😮'), ('bravo', '👏'),
    ]
    post    = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    auteur  = models.ForeignKey(User, on_delete=models.CASCADE)
    type_reaction = models.CharField(max_length=10, choices=TYPES)

    class Meta:
        unique_together = ('post', 'auteur')  # un seul vote par personne par post

    def __str__(self):
        return f"{self.auteur} → {self.type_reaction} sur Post#{self.post.id}"


# ── COMMENTAIRE ──
class Comment(models.Model):
    post    = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    auteur  = models.ForeignKey(User, on_delete=models.CASCADE)
    contenu = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Commentaire de {self.auteur} sur Post#{self.post.id}"


# ── GROUPE (TEAM) ──
class Group(models.Model):
    nom         = models.CharField(max_length=100)
    admin       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='groupes_admins')
    membres     = models.ManyToManyField(User, related_name='groupes', blank=True)
    description = models.TextField(blank=True)
    emoji       = models.CharField(max_length=5, default='👥')
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom


# ── MESSAGE DE GROUPE ──
class GroupMessage(models.Model):
    groupe  = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages')
    auteur  = models.ForeignKey(User, on_delete=models.CASCADE)
    contenu = models.TextField(blank=True)
    fichier = models.FileField(upload_to='group_files/', blank=True, null=True)
    date    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"[{self.groupe}] {self.auteur}: {self.contenu[:40]}"


# ── CONVERSATION PRIVÉE (INBOX) ──
class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        noms = " & ".join([u.username for u in self.participants.all()])
        return f"Conv: {noms}"


# ── MESSAGE PRIVÉ ──
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    auteur  = models.ForeignKey(User, on_delete=models.CASCADE)
    contenu = models.TextField(blank=True)
    fichier = models.FileField(upload_to='inbox_files/', blank=True, null=True)
    lu      = models.BooleanField(default=False)
    date    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']


# ── STAY TUNED (liens de conférences) ──
class StayTuned(models.Model):
    auteur      = models.ForeignKey(User, on_delete=models.CASCADE)
    titre       = models.CharField(max_length=200)
    url         = models.URLField()
    plateforme  = models.CharField(max_length=50, default='Zoom')
    description = models.TextField(blank=True)
    is_live     = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_live', '-date_creation']

    def __str__(self):
        return self.titre


# ── ÉVÉNEMENT (AGENDA) ──
class Event(models.Model):
    TYPE_CHOICES = [
        ('examen', 'Examen'),
        ('conference', 'Conférence'),
        ('ferie', 'Férié'),
        ('autre', 'Autre'),
    ]
    auteur      = models.ForeignKey(User, on_delete=models.CASCADE)
    titre       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date_event  = models.DateField()
    heure_debut = models.TimeField(blank=True, null=True)
    heure_fin   = models.TimeField(blank=True, null=True)
    type_event  = models.CharField(max_length=20, choices=TYPE_CHOICES, default='autre')
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date_event']

    def __str__(self):
        return f"{self.titre} — {self.date_event}"


# ── CONVERSATION ANA IA ──
# Stocke l'historique des échanges avec Ana
class AnaConversation(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ana_conversations')
    question    = models.TextField()
    reponse     = models.TextField()
    date        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"Ana [{self.user}] — {self.date:%d/%m %H:%M}"


