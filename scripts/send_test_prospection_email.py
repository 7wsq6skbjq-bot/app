"""Send a test prospection email to info@portech.info with the new banner."""
import os
import resend
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
resend.api_key = os.getenv("RESEND_API_KEY")

PROSPECT_NAME = "Vitrerie Test Inc."

HTML = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portech — Sous-traitance quincaillerie</title>
</head>
<body style="margin:0;padding:0;background:#f3f6fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#0c182b;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f3f6fb;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border:1px solid #dde5f0;">
        <!-- HEADER BANNER -->
        <tr>
          <td>
            <img src="https://portech.info/email/email-header.png" width="600" height="120" alt="Portech — Quincaillerie de porte commerciale" style="display:block;width:100%;height:auto;border:0;">
          </td>
        </tr>
        <!-- BODY -->
        <tr>
          <td style="padding:32px 36px 8px 36px;font-size:15px;line-height:1.65;color:#0c182b;">
            <p style="margin:0 0 14px 0;">Bonjour {PROSPECT_NAME},</p>
            <p style="margin:0 0 14px 0;">Cédrick Pimparé, fondateur de Portech.</p>
            <p style="margin:0 0 14px 0;">On est spécialisés en <strong>quincaillerie de porte commerciale</strong> dans le Grand Montréal, Laval, la Rive-Sud et la Rive-Nord.</p>
            <p style="margin:0 0 14px 0;">Je vous contacte parce qu'on aide déjà plusieurs vitreries à gérer tout ce qui touche la quincaillerie commerciale et les portes aluminium.</p>
            <p style="margin:24px 0 14px 0;">Concrètement, voici ce qu'on peut faire pour vous :</p>

            <!-- BLOC 1 -->
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:18px 0;">
              <tr>
                <td style="border-left:3px solid #97b0d0;padding:6px 0 6px 16px;">
                  <p style="margin:0 0 6px 0;font-weight:700;color:#0c182b;font-size:15px;">Sous-traitance de quincaillerie sur vos projets</p>
                  <p style="margin:0 0 8px 0;color:#4b5d7a;font-size:14px;line-height:1.6;">Barres antipaniques, ferme-portes, serrures mortaises, dispositifs de sortie, ajustements, installation complète, etc.</p>
                  <p style="margin:0;color:#0c182b;font-size:14px;line-height:1.7;">Vous gardez votre client et votre marge.<br>Nous, on s'occupe de l'exécution.</p>
                </td>
              </tr>
            </table>

            <!-- BLOC 2 -->
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:18px 0;">
              <tr>
                <td style="border-left:3px solid #97b0d0;padding:6px 0 6px 16px;">
                  <p style="margin:0 0 6px 0;font-weight:700;color:#0c182b;font-size:15px;">Fourniture de portes aluminium prêtes à poser</p>
                  <p style="margin:0 0 8px 0;color:#4b5d7a;font-size:14px;line-height:1.6;">Portes usinées en atelier ou sur chantier, quincaillerie installée et ajustée avant livraison.</p>
                  <p style="margin:0;color:#0c182b;font-size:14px;line-height:1.7;">Moins de temps perdu sur le chantier.<br>Moins de coordination.<br>Finition plus propre et professionnelle.<br>Garantie que toute quincaillerie est adéquate et adaptée au système.</p>
                </td>
              </tr>
            </table>

            <!-- BLOC 3 -->
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:18px 0;">
              <tr>
                <td style="border-left:3px solid #97b0d0;padding:6px 0 6px 16px;">
                  <p style="margin:0 0 6px 0;font-weight:700;color:#0c182b;font-size:15px;">Aucun conflit avec votre activité</p>
                  <p style="margin:0;color:#0c182b;font-size:14px;line-height:1.7;">On ne fait pas de vitrage et on ne touche pas à vos installations de verre. Notre rôle est de compléter votre service, pas de le remplacer.</p>
                </td>
              </tr>
            </table>

            <p style="margin:28px 0 14px 0;">Si vous avez 15 minutes cette semaine, je serais content d'en discuter avec vous.</p>

            <!-- CTA -->
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0;">
              <tr>
                <td>
                  <a href="tel:+14383764177" style="display:inline-block;background:#0c182b;color:#ffffff;text-decoration:none;padding:14px 28px;font-weight:700;letter-spacing:0.5px;font-size:14px;">438 376-4177</a>
                </td>
                <td style="padding-left:12px;">
                  <a href="https://portech.info" style="display:inline-block;border:1px solid #0c182b;color:#0c182b;text-decoration:none;padding:13px 28px;font-weight:700;letter-spacing:0.5px;font-size:14px;">portech.info</a>
                </td>
              </tr>
            </table>

            <p style="margin:24px 0 4px 0;">Bonne journée!</p>
            <p style="margin:0 0 24px 0;">Cédrick Pimparé<br><span style="color:#4b5d7a;">Portech — Quincaillerie de porte commerciale</span></p>
          </td>
        </tr>

        <!-- FOOTER SIGNATURE -->
        <tr>
          <td>
            <img src="https://portech.info/email/email-footer.png" width="600" height="150" alt="Portech — 438 376-4177 — portech.info" style="display:block;width:100%;height:auto;border:0;">
          </td>
        </tr>

        <!-- UNSUBSCRIBE -->
        <tr>
          <td style="padding:16px 36px;border-top:1px solid #dde5f0;font-size:12px;color:#97aac6;line-height:1.5;">
            Vous recevez ce courriel parce que nous avons identifié votre entreprise comme partenaire potentiel.
            <a href="https://portech.info/desinscription" style="color:#97aac6;text-decoration:underline;">Se désinscrire</a>.
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

resp = resend.Emails.send({
    "from": "Portech <info@portech.info>",
    "to": ["info@portech.info"],
    "subject": "Sous-traitance quincaillerie + portes aluminium — Portech",
    "html": HTML,
})
print(f"Sent: id={resp.get('id')}")
