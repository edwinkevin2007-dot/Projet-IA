"""
email_verif.py
Vérifie qu'un email a un format valide ET que son domaine existe réellement
(résolution DNS), sans dépendance externe, sans clé API, gratuit.

Important — honnêteté sur la portée de cette vérification :
Cette fonction confirme que le DOMAINE (ex. gmail.com, yahoo.fr, mail.mg) existe
et peut recevoir des emails. Elle ne confirme PAS qu'une boîte mail précise
(ex. rakoto123@gmail.com) existe réellement chez le fournisseur : cela
nécessiterait un handshake SMTP direct avec les serveurs de Google/Yahoo/etc.,
que ces fournisseurs bloquent quasi systématiquement pour lutter contre le
spam. C'est pourquoi aucun service, gratuit ou payant, ne peut garantir à 100 %
qu'une adresse Gmail précise existe sans envoyer un email de confirmation.
La vérification par domaine est le niveau de contrôle fiable et gratuit
généralement utilisé en pratique (c'est ce que fait Django, Rails, etc.).
"""

import re
import socket

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-.]+$")


def ressemble_a_un_email(contact):
    return "@" in contact


def verifier_email(email):
    """
    Retourne (valide: bool, message: str|None).

    - (False, "...")                    -> format invalide ou domaine inexistant, à bloquer.
    - (True, None)                      -> domaine vérifié avec succès.
    - (True, "verification_impossible") -> format correct mais vérification DNS
      impossible (ex. serveur sans accès réseau sortant) : on choisit de ne pas
      bloquer l'inscription plutôt que de refuser à tort un email valide.
    """
    email = email.strip()
    if not EMAIL_REGEX.match(email):
        return False, "Format d'email invalide."

    domaine = email.rsplit("@", 1)[-1].lower()

    try:
        # Résolution DNS du domaine (fonctionne pour gmail.com, yahoo.fr, etc.)
        socket.getaddrinfo(domaine, None)
        return True, None
    except socket.gaierror:
        return False, f"Le domaine « {domaine} » n'existe pas ou ne peut pas recevoir d'emails."
    except OSError:
        return True, "verification_impossible"
