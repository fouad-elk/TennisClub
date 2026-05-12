/* ============================================================
   TENNIS CLUB — INTERACTIONS JS
   Modale, animations, SweetAlert2
   ============================================================ */

// --- Ouverture / fermeture des modales ---
// Demande au serveur si le créneau est encore libre avant d'ouvrir la modale
function ouvrirModal(id, num, h, surface) {
    var dateJour = document.getElementById('modalResa').dataset.date;

    // Appel asynchrone vers l'API pour vérifier la dispo en temps réel
    fetch('/api/disponibilite/?terrain=' + id + '&date=' + dateJour + '&heure=' + h)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.disponible) {
                // Créneau pris entre temps, on prévient l'utilisateur
                Swal.fire({
                    icon: 'warning',
                    title: 'Créneau déjà pris',
                    text: "Ce créneau vient d'être réservé. Choisis un autre horaire.",
                    confirmButtonColor: '#C1440E',
                    background: '#FDF6F0'
                });
                return;
            }
            // Créneau libre, on remplit et ouvre la modale normalement
            document.getElementById('modalResa').style.display = 'block';
            document.getElementById('labelDetails').innerHTML =
                "<b>Court " + num + "</b> &bull; " + h + "h00<br><small>" + surface + "</small>";
            document.getElementById('id_terrain').value = id;
            document.getElementById('id_heure_debut').value = h;
            document.getElementById('id_date').value = dateJour;
        })
        .catch(function() {
            // Si l'API ne répond pas, on ouvre quand même la modale (fallback)
            document.getElementById('modalResa').style.display = 'block';
            document.getElementById('labelDetails').innerHTML =
                "<b>Court " + num + "</b> &bull; " + h + "h00<br><small>" + surface + "</small>";
            document.getElementById('id_terrain').value = id;
            document.getElementById('id_heure_debut').value = h;
            document.getElementById('id_date').value = dateJour;
        });
}

function fermerModal() {
    document.getElementById('modalResa').style.display = 'none';
}

// Fermer la modale en cliquant à l'extérieur
window.addEventListener('click', function(e) {
    var modal = document.getElementById('modalResa');
    if (modal && e.target === modal) fermerModal();
});

// Fermer avec Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        var modals = document.querySelectorAll('.modal-overlay');
        modals.forEach(function(m) { m.style.display = 'none'; });
    }
});

// --- Fermer modale de rappel cotisation ---
function fermerRappel() {
    var modal = document.getElementById('modalRappel');
    if (modal) modal.style.display = 'none';
}

// --- Callback Google Identity Services ---
// Appelé automatiquement quand l'utilisateur se connecte via le bouton Google
function onGoogleSignIn(response) {
    // Décoder le JWT pour récupérer l'email
    var parts = response.credential.split('.');
    var payload = JSON.parse(atob(parts[1]));
    var email = payload.email;

    // Récupérer le token CSRF (champ caché dans la page)
    var csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (!csrfInput) {
        console.error('Google Auth : token CSRF introuvable');
        return;
    }

    // Envoyer l'email Google au serveur via fetch (AJAX)
    fetch("/google-auth/", {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfInput.value
        },
        body: JSON.stringify({ email: email })
    })
    .then(function(resp) {
        if (!resp.ok) throw new Error('Erreur serveur : ' + resp.status);
        return resp.json();
    })
    .then(function(data) {
        if (data.success) {
            // Modale principale (base.html) : afficher le bouton Stripe
            var googleStep = document.getElementById('google-step');
            var stripeStep = document.getElementById('stripe-step');
            var emailDisplay = document.getElementById('google-email-display');
            if (googleStep) googleStep.style.display = 'none';
            if (stripeStep) stripeStep.style.display = 'block';
            if (emailDisplay) emailDisplay.textContent = data.email;

            // Modale rappel (home.html) : afficher le bouton Stripe
            var googleStepR = document.getElementById('google-step-rappel');
            var stripeStepR = document.getElementById('stripe-step-rappel');
            var emailDisplayR = document.getElementById('google-email-rappel');
            if (googleStepR) googleStepR.style.display = 'none';
            if (stripeStepR) stripeStepR.style.display = 'block';
            if (emailDisplayR) emailDisplayR.textContent = data.email;
        } else {
            Swal.fire('Erreur', data.error || 'Impossible de lier le compte Google.', 'error');
        }
    })
    .catch(function(err) {
        console.error('Google Auth erreur:', err);
        Swal.fire('Erreur', 'La connexion Google a échoué. Réessaie.', 'error');
    });
}

// --- Cocher / décocher tous les checkboxes (admin activation) ---
function cocherTout(source, classe) {
    var cases = document.querySelectorAll('.' + classe);
    cases.forEach(function(c) { c.checked = source.checked; });
}

// --- Confirmation d'annulation de réservation (SweetAlert2) ---
document.addEventListener('click', function(e) {
    var btn = e.target.closest('.btn-annuler');
    if (!btn) return;
    e.preventDefault();

    var url = btn.dataset.url;
    var joueurs = btn.dataset.joueurs;
    var type = btn.dataset.type;
    var court = btn.dataset.court;
    var horaire = btn.dataset.horaire;

    Swal.fire({
        title: 'Annuler cette réservation ?',
        html:
            '<div style="text-align:left; font-size:0.92em; line-height:1.8;">' +
            '<i class="fas fa-map-marker-alt" style="color:#C1440E;"></i> <b>' + court + '</b><br>' +
            '<i class="fas fa-clock" style="color:#C9A84C;"></i> ' + horaire + '<br>' +
            '<i class="fas fa-users" style="color:#2D5016;"></i> ' + joueurs + '<br>' +
            '<i class="fas fa-baseball-ball" style="color:#C1440E;"></i> ' + type +
            '</div>',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#C1440E',
        cancelButtonColor: '#6c757d',
        confirmButtonText: '<i class="fas fa-check"></i> Oui, annuler',
        cancelButtonText: 'Non, garder',
        background: '#FDF6F0',
        color: '#2C2C2C'
    }).then(function(result) {
        if (result.isConfirmed) {
            var csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;

            // Envoi de la suppression en AJAX pour éviter de recharger toute la page
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrf,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success) {
                    // Retirer le bouton d'annulation de la page sans rechargement
                    var ligne = btn.closest('tr');
                    if (ligne) {
                        ligne.style.transition = 'opacity 0.4s';
                        ligne.style.opacity = '0';
                        setTimeout(function() { ligne.remove(); }, 400);
                    }
                    Swal.fire({
                        icon: 'success',
                        title: 'Annulée',
                        text: data.message,
                        confirmButtonColor: '#C1440E',
                        background: '#FDF6F0',
                        timer: 2000,
                        showConfirmButton: false
                    });
                } else {
                    Swal.fire('Erreur', data.error, 'error');
                }
            })
            .catch(function() {
                Swal.fire('Erreur', 'Problème de connexion.', 'error');
            });
        }
    });
});
