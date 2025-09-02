import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        translation: {
          deploymentHistory: 'Deployment History',
          service: 'Service',
          environment: 'Environment',
          tag: 'Tag',
          prUrl: 'PR URL',
          status: 'Status',
          createdAt: 'Created At',
          approvedBy: 'Approved By',
          all: 'All',
          dev: 'DEV',
          stag: 'STAG',
          prod: 'PROD',
          loading: 'Loading...',
          noDeployments: 'No deployments found',
          previous: 'Previous',
          next: 'Next',
          page: 'Page',
          of: 'of',
          deploymentsByService: 'Deployments by Service',
          error: {
            servicesFetch: 'Failed to fetch services',
            historyFetch: 'Failed to fetch deployment history'
          },
          prLink: 'Pull Request Link'
        }
      },
      fr: {
        translation: {
          deploymentHistory: 'Historique des Déploiements',
          service: 'Service',
          environment: 'Environnement',
          tag: 'Tag',
          prUrl: 'URL PR',
          status: 'Statut',
          createdAt: 'Créé le',
          approvedBy: 'Approuvé par',
          all: 'Tous',
          dev: 'DEV',
          stag: 'STAG',
          prod: 'PROD',
          loading: 'Chargement...',
          noDeployments: 'Aucun déploiement trouvé',
          previous: 'Précédent',
          next: 'Suivant',
          page: 'Page',
          of: 'de',
          deploymentsByService: 'Déploiements par Service',
          error: {
            servicesFetch: 'Échec de la récupération des services',
            historyFetch: 'Échec de la récupération de l’historique'
          },
          prLink: 'Lien de la Pull Request'
        }
      }
    },
    fallbackLng: 'en',
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage']
    }
  });

export default i18n;