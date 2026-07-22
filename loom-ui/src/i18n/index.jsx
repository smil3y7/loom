// Loom UI — i18n
// Brez hardcoded stringov — vsi teksti so tukaj.
// Dodajanje jezika: dodaj objekt v TRANSLATIONS in vnos v LANGUAGES.

export const LANGUAGES = [
  { code: 'sl', name: 'Slovenščina' },
  { code: 'en', name: 'English' },
]

const TRANSLATIONS = {
  sl: {
    // Nav
    'nav.dashboard': 'Pregled',
    'nav.search': 'Iskanje',
    'nav.patterns': 'Vzorci',
    'nav.clusters': 'Grupi',
    'nav.settings': 'Nastavitve',
    'nav.help': 'Pomoč',

    // Dashboard
    'dashboard.title': 'Pregled',
    'dashboard.subtitle': 'Semantična kontinuitetna plast',
    'dashboard.connecting': 'Vzpostavljam povezavo z Loom engine...',
    'dashboard.offline': 'Loom engine ni dosegljiv',
    'dashboard.offline.hint': 'Preveri ali Docker container teče in poskusi znova.',
    'dashboard.retry': 'Poskusi znova',
    'dashboard.stat.dreams': 'Sanj v arhivu',
    'dashboard.stat.embedded': 'Z embedingom',
    'dashboard.stat.clusters': 'Semantičnih grupi',
    'dashboard.stat.threads': 'Ponavljajočih vzorcev',
    'dashboard.stat.queued': 'V vrsti za procesiranje',
    'dashboard.sources': 'Viri sanj',
    'dashboard.source.ok': 'Dosegljiv',
    'dashboard.source.fail': 'Nedosegljiv',
    'dashboard.recentThreads': 'Zadnji vzorci',
    'dashboard.noThreads': 'Še ni zaznanih vzorcev. Poženi Vzorci → Zaznej vzorce.',
    'dashboard.quickSearch': 'Hitro iskanje',
    'dashboard.searchPlaceholder': 'Vtipkaj besedo ali stavek...',

    // Search
    'search.title': 'Semantično iskanje',
    'search.subtitle': 'Iščeš po pomenu, ne po besedah.',
    'search.placeholder': 'Vtipkaj besedo ali stavek...',
    'search.button': 'Išči',
    'search.results': 'Rezultati',
    'search.noResults': 'Ni rezultatov za',
    'search.similarity': 'Podobnost',
    'search.source': 'Vir',
    'search.language': 'Jezik',
    'search.filter.language': 'Jezik',
    'search.filter.source': 'Vir',
    'search.filter.all': 'Vsi',
    'search.loading': 'Iščem...',
    'search.similar': 'Podobne sanje',
    'search.noEmbeddings': 'Ni embedingov. Najprej generiraj semantične vektorje.',

    // Patterns
    'patterns.title': 'Ponavljajoči vzorci',
    'patterns.subtitle': 'Semantični vzorci ki se ponavljajo skozi čas.',
    'patterns.count': 'vzorcev',
    'patterns.score': 'Rezultat',
    'patterns.dreams': 'sanj',
    'patterns.span': 'razpon',
    'patterns.days': 'dni',
    'patterns.sample': 'Vzorčne sanje',
    'patterns.confirm': 'Potrdi vzorec',
    'patterns.reject': 'Zavrni',
    'patterns.rename': 'Ime vzorca',
    'patterns.confirmed': 'Potrjen',
    'patterns.rejected': 'Zavrnjen',
    'patterns.noPatterns': 'Še ni vzorcev. Najprej generiraj embedinge in poženi clustering.',
    'patterns.emotions': 'Čustva',
    'patterns.runFirst': 'Zaznej vzorce',

    // Clusters
    'clusters.title': 'Semantični grupi',
    'clusters.subtitle': 'Vse semantične grupe iz tvojega arhiva.',
    'clusters.coherence': 'koherentnost',
    'clusters.type': 'Tip',
    'clusters.noData': 'Ni grupi. Poženi clustering.',

    // Settings
    'settings.title': 'Nastavitve',
    'settings.language': 'Jezik vmesnika',
    'settings.theme': 'Tema',
    'settings.theme.light': 'Svetla',
    'settings.theme.dark': 'Temna',
    'settings.theme.system': 'Sistemska',
    'settings.api': 'API nastavitve',
    'settings.apiUrl': 'API URL',
    'settings.apiUrl.hint': 'Lokalno: http://localhost:8000',
    'settings.save': 'Shrani',
    'settings.saved': 'Shranjeno',
    'settings.about': 'O aplikaciji',
    'settings.version.ui': 'Verzija vmesnika',
    'settings.version.backend': 'Verzija engine-a',
    'settings.version.mismatch': 'Verziji se ne ujemata — priporočamo osvežitev strani ali posodobitev enega od delov.',

    // Help
    'help.title': 'Pomoč',
    'help.what': 'Kaj je Loom?',
    'help.what.text': 'Loom je semantična kontinuitetna plast za tvoje sanje. Poveže podatke iz različnih sanjskih dnevnikov in zazna ponavljajoče vzorce skozi čas.',
    'help.search': 'Kako deluje iskanje?',
    'help.search.text': 'Iskanje deluje po pomenu, ne po besedah. "Staro mesto" in "ancient city" vrneta iste rezultate. Deluje v slovenščini in angleščini.',
    'help.patterns': 'Kaj so vzorci?',
    'help.patterns.text': 'Vzorci so semantično podobne sanje ki se ponavljajo skozi daljše obdobje. Loom jih zazna avtomatsko — ti odločiš ali so smiselni.',
    'help.embeddings': 'Kaj so embedingi?',
    'help.embeddings.text': 'Embedingi so matematični vektorji ki opisujejo pomen vsake sanje. Ustvarijo se enkrat in ostanejo lokalno na tvojem računalniku.',
    'help.privacy': 'Zasebnost',
    'help.privacy.text': 'Vse teče lokalno. Tvoje sanje ne gredo nikamor. Embedingi se generirajo lokalno z modelom ki je nameščen na tvojem računalniku.',

    // Common
    'common.loading': 'Nalagam...',
    'common.show_more': '+ {n} več',
    'common.show_less': '▲ Manj',
    'common.show_content': '▽ Pokaži vsebino',
    'common.hide_content': '△ Skrij vsebino',
    'common.clear': 'Počisti',
    'common.no_title': '(brez naslova)',
    'common.view_full': 'Celotno besedilo',

    // Patterns extra
    'patterns.unconfirmed': 'Nepotrjeni',
    'patterns.suggested': 'predlagano ime na podlagi vsebin',
    'patterns.sort.score': 'Po rezultatu',
    'patterns.sort.size': 'Po številu sanj',
    'patterns.sort.date': 'Po zadnji pojavitvi',
    'patterns.sort.label': 'Razvrsti',

    // Clusters extra
    'clusters.sample': 'Vzorčne sanje',
    'clusters.expand': '▼ Vzorčne sanje',
    'clusters.collapse': '▲ Zapri',
    'clusters.about': 'Clusteri so semantične grupe sanj ki opisujejo podobne izkušnje. Klikni na grup za vzorčne sanje.',

    // Search extra
    'search.clear': 'Počisti',
    'search.show_more': 'Pokaži več',
    'search.full_text': 'Celotno besedilo',
    'search.full_text_close': 'Zapri',
    'search.similar_title': 'Podobne sanje za:',
    'search.loading_index': 'Gradim iskalni index...',
    'common.error': 'Napaka',
    'common.retry': 'Poskusi znova',
    'common.close': 'Zapri',
    'common.confirm': 'Potrdi',
    'common.cancel': 'Prekliči',
    'common.save': 'Shrani',
    'common.days': 'dni',
    'common.dreams': 'sanj',
    'common.from': 'od',
    'common.to': 'do',
    'common.unknown': 'neznano',
    'common.engine_online': 'Engine povezan',
    'common.engine_offline': 'Engine ni dosegljiv',
    'common.api_unreachable': 'API nedosegljiv. Preveri ali Loom engine teče.',
  },

  en: {
    // Nav
    'nav.dashboard': 'Dashboard',
    'nav.search': 'Search',
    'nav.patterns': 'Patterns',
    'nav.clusters': 'Clusters',
    'nav.settings': 'Settings',
    'nav.help': 'Help',

    // Dashboard
    'dashboard.title': 'Dashboard',
    'dashboard.subtitle': 'Semantic Continuity Layer',
    'dashboard.connecting': 'Connecting to Loom engine...',
    'dashboard.offline': 'Loom engine is not reachable',
    'dashboard.offline.hint': 'Check if the Docker container is running and try again.',
    'dashboard.retry': 'Retry',
    'dashboard.stat.dreams': 'Dreams in archive',
    'dashboard.stat.embedded': 'With embedding',
    'dashboard.stat.clusters': 'Semantic clusters',
    'dashboard.stat.threads': 'Recurring patterns',
    'dashboard.stat.queued': 'Queued for processing',
    'dashboard.sources': 'Dream sources',
    'dashboard.source.ok': 'Connected',
    'dashboard.source.fail': 'Unreachable',
    'dashboard.recentThreads': 'Recent patterns',
    'dashboard.noThreads': 'No patterns detected yet. Run Patterns → Detect patterns.',
    'dashboard.quickSearch': 'Quick search',
    'dashboard.searchPlaceholder': 'Type a word or phrase...',

    // Search
    'search.title': 'Semantic search',
    'search.subtitle': 'Search by meaning, not by words.',
    'search.placeholder': 'Type a word or phrase...',
    'search.button': 'Search',
    'search.results': 'Results',
    'search.noResults': 'No results for',
    'search.similarity': 'Similarity',
    'search.source': 'Source',
    'search.language': 'Language',
    'search.filter.language': 'Language',
    'search.filter.source': 'Source',
    'search.filter.all': 'All',
    'search.loading': 'Searching...',
    'search.similar': 'Similar dreams',
    'search.noEmbeddings': 'No embeddings. Generate semantic vectors first.',

    // Patterns
    'patterns.title': 'Recurring patterns',
    'patterns.subtitle': 'Semantic patterns that repeat across time.',
    'patterns.count': 'patterns',
    'patterns.score': 'Score',
    'patterns.dreams': 'dreams',
    'patterns.span': 'span',
    'patterns.days': 'days',
    'patterns.sample': 'Sample dreams',
    'patterns.confirm': 'Confirm pattern',
    'patterns.reject': 'Reject',
    'patterns.rename': 'Pattern name',
    'patterns.confirmed': 'Confirmed',
    'patterns.rejected': 'Rejected',
    'patterns.noPatterns': 'No patterns yet. Generate embeddings and run clustering first.',
    'patterns.emotions': 'Emotions',
    'patterns.runFirst': 'Detect patterns',

    // Clusters
    'clusters.title': 'Semantic clusters',
    'clusters.subtitle': 'All semantic clusters from your archive.',
    'clusters.coherence': 'coherence',
    'clusters.type': 'Type',
    'clusters.noData': 'No clusters. Run clustering first.',

    // Settings
    'settings.title': 'Settings',
    'settings.language': 'Interface language',
    'settings.theme': 'Theme',
    'settings.theme.light': 'Light',
    'settings.theme.dark': 'Dark',
    'settings.theme.system': 'System',
    'settings.api': 'API settings',
    'settings.apiUrl': 'API URL',
    'settings.apiUrl.hint': 'Local: http://localhost:8000',
    'settings.save': 'Save',
    'settings.saved': 'Saved',
    'settings.about': 'About',
    'settings.version.ui': 'UI version',
    'settings.version.backend': 'Engine version',
    'settings.version.mismatch': 'Versions do not match — try refreshing the page or updating one of the components.',

    // Help
    'help.title': 'Help',
    'help.what': 'What is Loom?',
    'help.what.text': 'Loom is a semantic continuity layer for your dreams. It connects data from different dream journals and detects recurring patterns across time.',
    'help.search': 'How does search work?',
    'help.search.text': 'Search works by meaning, not by words. "Staro mesto" and "old town" return the same results. Works in Slovenian and English.',
    'help.patterns': 'What are patterns?',
    'help.patterns.text': 'Patterns are semantically similar dreams that recur over longer periods. Loom detects them automatically — you decide if they feel meaningful.',
    'help.embeddings': 'What are embeddings?',
    'help.embeddings.text': 'Embeddings are mathematical vectors that describe the meaning of each dream. They are generated once and stay locally on your computer.',
    'help.privacy': 'Privacy',
    'help.privacy.text': 'Everything runs locally. Your dreams go nowhere. Embeddings are generated locally with a model installed on your computer.',

    // Common
    'common.loading': 'Loading...',
    'common.show_more': '+ {n} more',
    'common.show_less': '▲ Less',
    'common.show_content': '▽ Show content',
    'common.hide_content': '△ Hide content',
    'common.clear': 'Clear',
    'common.no_title': '(no title)',
    'common.view_full': 'Full text',

    // Patterns extra
    'patterns.unconfirmed': 'Unconfirmed',
    'patterns.suggested': 'suggested name based on content',
    'patterns.sort.score': 'By score',
    'patterns.sort.size': 'By dream count',
    'patterns.sort.date': 'By last occurrence',
    'patterns.sort.label': 'Sort',

    // Clusters extra
    'clusters.sample': 'Sample dreams',
    'clusters.expand': '▼ Sample dreams',
    'clusters.collapse': '▲ Close',
    'clusters.about': 'Clusters are semantic groups of dreams describing similar experiences. Click a cluster to see sample dreams.',

    // Search extra
    'search.clear': 'Clear',
    'search.show_more': 'Show more',
    'search.full_text': 'Full text',
    'search.full_text_close': 'Close',
    'search.similar_title': 'Similar dreams for:',
    'search.loading_index': 'Building search index...',
    'common.error': 'Error',
    'common.retry': 'Retry',
    'common.close': 'Close',
    'common.confirm': 'Confirm',
    'common.cancel': 'Cancel',
    'common.save': 'Save',
    'common.days': 'days',
    'common.dreams': 'dreams',
    'common.from': 'from',
    'common.to': 'to',
    'common.unknown': 'unknown',
    'common.engine_online': 'Engine online',
    'common.engine_offline': 'Engine offline',
    'common.api_unreachable': 'API unreachable. Check if the Loom engine is running.',
  },
}

// Hook za uporabo v komponentah
import { createContext, useContext, useState } from 'react'

const I18nContext = createContext(null)

export function I18nProvider({ children }) {
  const saved = localStorage.getItem('loom_language') || 'sl'
  const [lang, setLangState] = useState(saved)

  function setLang(code) {
    setLangState(code)
    localStorage.setItem('loom_language', code)
  }

  function t(key, vars = {}) {
    const str = TRANSLATIONS[lang]?.[key] || TRANSLATIONS['sl']?.[key] || key
    return Object.entries(vars).reduce(
      (s, [k, v]) => s.replace(`{${k}}`, v), str
    )
  }

  return (
    <I18nContext.Provider value={{ lang, setLang, t, languages: LANGUAGES }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n() {
  return useContext(I18nContext)
}
