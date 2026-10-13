export const SITE_URL = 'https://apoorvdarshan.com'
export const SOCIAL_IMAGE = `${SITE_URL}/apoorv-darshan-social.png`

export const SEO_BY_PATH = {
  '/': {
    title: 'Apoorv Darshan — Developer & Open-Source Builder',
    description: 'Apoorv Darshan is a developer in Delhi building AI products, mobile apps, web tools, browser extensions, and open-source software.',
  },
  '/experience': {
    title: 'Experience — Apoorv Darshan',
    description: 'Explore Apoorv Darshan’s experience across full-stack development, AI training, mobile products, browser extensions, and content creation.',
  },
  '/education': {
    title: 'Education — Apoorv Darshan',
    description: 'Apoorv Darshan’s education in computer science, engineering, mathematics, and competitive examination preparation.',
  },
  '/projects': {
    title: 'Projects — Apoorv Darshan',
    description: 'Apps, AI experiments, developer tools, browser extensions, and independent software projects built by Apoorv Darshan.',
  },
  '/open-source': {
    title: 'Open Source — Apoorv Darshan',
    description: 'Open-source contributions by Apoorv Darshan across TensorFlow, Kubernetes, Flutter, freeCodeCamp, and other software communities.',
  },
}

export const SOCIAL_PROFILES = [
  'https://github.com/apoorvdarshan',
  'https://www.linkedin.com/in/apoorvdarshan/',
  'https://x.com/apoorvdarshan',
  'https://www.youtube.com/@apoorvdarshan',
]

export function canonicalUrl(path) {
  return path === '/' ? `${SITE_URL}/` : `${SITE_URL}${path}`
}

export function structuredData(path) {
  const page = SEO_BY_PATH[path] || SEO_BY_PATH['/']
  const url = canonicalUrl(path)
  const personId = `${SITE_URL}/#person`

  return {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Person',
        '@id': personId,
        name: 'Apoorv Darshan',
        url: `${SITE_URL}/`,
        image: `${SITE_URL}/android-chrome-512x512.png`,
        email: 'mailto:ad13dtu@gmail.com',
        address: { '@type': 'PostalAddress', addressLocality: 'Delhi', addressCountry: 'IN' },
        jobTitle: 'Software Developer',
        knowsAbout: ['Artificial intelligence', 'Open-source software', 'Web development', 'iOS development', 'Android development', 'Browser extensions'],
        sameAs: SOCIAL_PROFILES,
      },
      {
        '@type': path === '/' ? 'ProfilePage' : 'WebPage',
        '@id': `${url}#webpage`,
        url,
        name: page.title,
        description: page.description,
        inLanguage: 'en',
        isPartOf: { '@id': `${SITE_URL}/#website` },
        about: { '@id': personId },
        mainEntity: { '@id': personId },
      },
      {
        '@type': 'WebSite',
        '@id': `${SITE_URL}/#website`,
        url: `${SITE_URL}/`,
        name: 'Apoorv Darshan',
        description: SEO_BY_PATH['/'].description,
        inLanguage: 'en',
        publisher: { '@id': personId },
      },
    ],
  }
}
