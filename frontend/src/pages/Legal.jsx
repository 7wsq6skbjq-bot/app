import { Link } from "react-router-dom";
import { ShieldCheck, FileText, Mail, ArrowUpRight } from "lucide-react";

const Legal = () => {
    return (
        <div data-testid="page-legal">
            {/* HEADER */}
            <section
                data-testid="legal-header"
                className="relative bg-[#0c182b] text-white border-b border-[#1e3457] overflow-hidden"
            >
                <div className="absolute inset-0 bg-blueprint-dark pointer-events-none" />
                <div className="container-portech relative py-20 md:py-28">
                    <div className="tech-stamp text-[#97b0d0] mb-5">
                        Légal · Confidentialité
                    </div>
                    <h1 className="font-display font-bold uppercase tracking-tight text-5xl md:text-6xl leading-[0.92] max-w-4xl">
                        Mentions légales &<br />
                        politique de confidentialité.
                    </h1>
                    <p className="mt-6 max-w-2xl text-lg text-[#b2c3dd] leading-relaxed">
                        Tout ce que vous devez savoir sur l'éditeur du site
                        Portech, l'utilisation de vos données personnelles et
                        vos droits.
                    </p>
                </div>
            </section>

            {/* CONTENT */}
            <section className="bg-white border-b border-[#dde5f0]">
                <div className="container-portech py-16 md:py-24 max-w-4xl">
                    {/* Mentions légales */}
                    <article
                        data-testid="legal-mentions"
                        className="mb-16 pb-16 border-b border-[#dde5f0]"
                    >
                        <div className="flex items-center gap-3 mb-6">
                            <FileText className="w-6 h-6 text-[#2f4f7f]" />
                            <div className="tech-stamp text-[#2f4f7f]">
                                Section 01
                            </div>
                        </div>
                        <h2 className="font-display font-bold uppercase text-3xl md:text-4xl tracking-tight leading-tight mb-8">
                            Mentions légales
                        </h2>

                        <div className="space-y-6 text-[#1e3457] leading-relaxed">
                            <div>
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2 text-[#0c182b]">
                                    Éditeur du site
                                </h3>
                                <p>
                                    <strong>Portech</strong>
                                    <br />
                                    Quincaillerie de portes commerciales
                                    <br />
                                    Fondateur : Cédrick Pimparé
                                    <br />
                                    Zone de service : Grand Montréal, Québec, Canada
                                    <br />
                                    Courriel :{" "}
                                    <a
                                        href="mailto:portech.infos@gmail.com"
                                        className="text-[#2f4f7f] hover:text-[#0c182b] underline"
                                    >
                                        portech.infos@gmail.com
                                    </a>
                                </p>
                            </div>

                            <div>
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2 text-[#0c182b]">
                                    Hébergement
                                </h3>
                                <p>
                                    Le site est hébergé sur une infrastructure
                                    cloud nord-américaine. Pour toute demande
                                    technique liée à l'hébergement, vous pouvez
                                    écrire directement à l'adresse de contact
                                    ci-dessus.
                                </p>
                            </div>

                            <div>
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2 text-[#0c182b]">
                                    Propriété intellectuelle
                                </h3>
                                <p>
                                    L'ensemble du contenu de ce site
                                    (textes, photographies, logos, structure)
                                    est la propriété exclusive de Portech, sauf
                                    mention contraire. Toute reproduction,
                                    représentation, modification ou exploitation
                                    de tout ou partie de ce site, par quelque
                                    procédé que ce soit et sur quelque support
                                    que ce soit, sans autorisation écrite
                                    préalable, est strictement interdite et
                                    constitue une contrefaçon sanctionnée par
                                    la loi canadienne sur le droit d'auteur.
                                </p>
                            </div>

                            <div>
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2 text-[#0c182b]">
                                    Marques déposées
                                </h3>
                                <p>
                                    Les marques de quincaillerie mentionnées
                                    sur ce site (Adams Rite, Von Duprin,
                                    Sargent, LCN, Schlage, Yale, Norton,
                                    dormakaba, Corbin Russwin, Best, Hager,
                                    Stanley, etc.) sont des marques déposées de
                                    leurs propriétaires respectifs. Leur
                                    mention sur ce site sert uniquement à
                                    indiquer que Portech installe et entretient
                                    la quincaillerie de ces fabricants. Aucun
                                    lien commercial exclusif n'est sous-entendu.
                                </p>
                            </div>

                            <div>
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2 text-[#0c182b]">
                                    Limitation de responsabilité
                                </h3>
                                <p>
                                    Les informations présentes sur ce site sont
                                    fournies à titre informatif. Portech
                                    s'efforce de maintenir à jour le contenu,
                                    mais ne peut garantir l'exactitude
                                    permanente de toutes les informations.
                                    L'utilisation des informations contenues
                                    sur ce site se fait sous la seule
                                    responsabilité de l'utilisateur.
                                </p>
                            </div>
                        </div>
                    </article>

                    {/* Politique de confidentialité */}
                    <article data-testid="legal-privacy">
                        <div className="flex items-center gap-3 mb-6">
                            <ShieldCheck className="w-6 h-6 text-[#2f4f7f]" />
                            <div className="tech-stamp text-[#2f4f7f]">
                                Section 02
                            </div>
                        </div>
                        <h2 className="font-display font-bold uppercase text-3xl md:text-4xl tracking-tight leading-tight mb-8">
                            Politique de confidentialité
                        </h2>

                        <div className="space-y-6 text-[#1e3457] leading-relaxed">
                            <div>
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2 text-[#0c182b]">
                                    Données collectées via le formulaire
                                </h3>
                                <p>
                                    Lorsque vous remplissez notre formulaire de
                                    soumission, nous collectons uniquement les
                                    informations que vous fournissez
                                    volontairement :
                                </p>
                                <ul className="list-disc pl-6 mt-3 space-y-1.5">
                                    <li>Nom et prénom</li>
                                    <li>Nom de votre entreprise (facultatif)</li>
                                    <li>Numéro de téléphone</li>
                                    <li>Adresse courriel</li>
                                    <li>Lieu des travaux à effectuer</li>
                                    <li>Type de projet (facultatif)</li>
                                    <li>Description du besoin</li>
                                </ul>
                            </div>

                            <div>
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2 text-[#0c182b]">
                                    Utilisation des données
                                </h3>
                                <p>
                                    Vos informations sont utilisées
                                    exclusivement pour :
                                </p>
                                <ul className="list-disc pl-6 mt-3 space-y-1.5">
                                    <li>
                                        Vous recontacter et vous soumettre une
                                        proposition pour vos travaux
                                    </li>
                                    <li>
                                        Préparer la visite ou la soumission de
                                        votre projet
                                    </li>
                                    <li>
                                        Conserver un historique de nos échanges
                                        commerciaux
                                    </li>
                                </ul>
                                <p className="mt-3">
                                    <strong className="text-[#0c182b]">
                                        Vos données ne sont jamais revendues, ni
                                        louées, ni partagées avec des tiers à
                                        des fins commerciales.
                                    </strong>
                                </p>
                            </div>

                            <div>
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2 text-[#0c182b]">
                                    Sous-traitants techniques
                                </h3>
                                <p>
                                    Pour faire fonctionner le site et le
                                    formulaire, nous utilisons :
                                </p>
                                <ul className="list-disc pl-6 mt-3 space-y-1.5">
                                    <li>
                                        Un service d'envoi de courriels
                                        transactionnels (Resend) pour nous
                                        notifier des nouvelles demandes
                                    </li>
                                    <li>
                                        Une base de données chiffrée pour
                                        conserver les soumissions
                                    </li>
                                </ul>
                                <p className="mt-3">
                                    Ces sous-traitants sont liés par leurs
                                    propres politiques de confidentialité et ne
                                    réutilisent pas vos données à d'autres
                                    fins.
                                </p>
                            </div>

                            <div>
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2 text-[#0c182b]">
                                    Durée de conservation
                                </h3>
                                <p>
                                    Vos données sont conservées le temps
                                    nécessaire au traitement de votre demande
                                    et, le cas échéant, pendant la durée de la
                                    relation commerciale, plus la durée légale
                                    de conservation des documents commerciaux
                                    au Québec.
                                </p>
                            </div>

                            <div>
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2 text-[#0c182b]">
                                    Vos droits (Loi 25 — Québec)
                                </h3>
                                <p>
                                    Conformément à la Loi 25 du Québec sur la
                                    protection des renseignements personnels,
                                    vous disposez à tout moment du droit :
                                </p>
                                <ul className="list-disc pl-6 mt-3 space-y-1.5">
                                    <li>
                                        D'accéder aux informations vous
                                        concernant
                                    </li>
                                    <li>
                                        De demander la rectification des
                                        informations inexactes
                                    </li>
                                    <li>
                                        De demander la suppression de vos
                                        données
                                    </li>
                                    <li>
                                        De vous opposer au traitement de vos
                                        données
                                    </li>
                                    <li>
                                        De porter plainte auprès de la
                                        Commission d'accès à l'information du
                                        Québec
                                    </li>
                                </ul>
                                <p className="mt-3">
                                    Pour exercer ces droits, écrivez-nous à{" "}
                                    <a
                                        href="mailto:portech.infos@gmail.com"
                                        className="text-[#2f4f7f] hover:text-[#0c182b] underline"
                                    >
                                        portech.infos@gmail.com
                                    </a>
                                    . Nous vous répondrons dans un délai de 30
                                    jours.
                                </p>
                            </div>

                            <div>
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2 text-[#0c182b]">
                                    Témoins (cookies)
                                </h3>
                                <p>
                                    Le site Portech n'utilise{" "}
                                    <strong>aucun témoin de suivi
                                    publicitaire</strong>. Seuls les témoins
                                    techniques strictement nécessaires au
                                    fonctionnement du site (session, sécurité)
                                    sont utilisés.
                                </p>
                            </div>

                            <div>
                                <h3 className="font-display font-bold uppercase text-lg tracking-tight mb-2 text-[#0c182b]">
                                    Mise à jour de cette politique
                                </h3>
                                <p>
                                    Cette politique peut être mise à jour pour
                                    refléter des changements légaux ou
                                    techniques. La date de la dernière mise à
                                    jour est indiquée ci-dessous.
                                </p>
                                <p className="mt-3 text-sm text-[#4b5d7a]">
                                    <em>Dernière mise à jour : avril 2026</em>
                                </p>
                            </div>
                        </div>
                    </article>

                    {/* CTA */}
                    <div className="mt-14 p-8 border border-[#dde5f0] bg-[#f3f6fb]">
                        <div className="flex items-start gap-4">
                            <Mail className="w-6 h-6 text-[#2f4f7f] flex-shrink-0 mt-0.5" />
                            <div>
                                <h3 className="font-display font-bold uppercase text-xl tracking-tight mb-3 text-[#0c182b]">
                                    Une question sur vos données ?
                                </h3>
                                <p className="text-[#1e3457] leading-relaxed mb-5">
                                    On vous répond dans les 30 jours. Pas de
                                    formulaire compliqué : un simple courriel
                                    suffit.
                                </p>
                                <Link
                                    to="/contact"
                                    data-testid="legal-cta-contact"
                                    className="btn-primary"
                                >
                                    Nous contacter
                                    <ArrowUpRight className="w-4 h-4" />
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
};

export default Legal;
