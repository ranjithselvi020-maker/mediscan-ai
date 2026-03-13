
// ── Theme & Language Controls ──────────────────────────────────────────────

// ── 1. THEME TOGGLE ──────────────────────────────────────────────────────────
(function initTheme() {
    const btn = document.getElementById('themeToggleBtn');
    const body = document.body;
    const saved = localStorage.getItem('mediscan-theme') || 'dark';
    if (saved === 'light') { body.classList.add('light-theme'); if (btn) btn.textContent = '☀️'; }

    btn?.addEventListener('click', () => {
        const isLight = body.classList.toggle('light-theme');
        btn.textContent = isLight ? '☀️' : '🌙';
        localStorage.setItem('mediscan-theme', isLight ? 'light' : 'dark');
    });
})();

// ── 2. FULL-PAGE TRANSLATION (EN ↔ தமிழ்) ────────────────────────────────────
const UI_TRANSLATIONS = {
    // Nav
    'nav.dashboard': { en: '🏠 Dashboard', ta: '🏠 டாஷ்போர்டு' },
    'nav.history': { en: '📋 History', ta: '📋 வரலாறு' },
    'nav.status': { en: 'AI Online', ta: 'AI இணையத்தில்' },

    // Hero
    'hero.badge': { en: 'Mediscan-AI · Powered by Clinical AI Engine', ta: 'Mediscan-AI · மருத்துவ AI எஞ்சினால் இயக்கப்படுகிறது' },
    'hero.h1a': { en: 'Intelligent', ta: 'நுண்ணறிவு' },
    'hero.h1b': { en: 'Medical Diagnostics', ta: 'மருத்துவ நோயறிதல்' },
    'hero.h1c': { en: 'at Your Fingertips', ta: 'உங்கள் விரல் நுனியில்' },
    'hero.sub': {
        en: 'Upload medical scans for instant AI analysis, or paste your prescription text for a detailed medicine breakdown. Supports Chest X-Ray, Brain CT/MRI, Bone X-Ray, Abdomen CT, Spine X-Ray, and Dental OPG.',
        ta: 'உடனடி AI பகுப்பாய்வுக்கு மருத்துவ ஸ்கேன்களை பதிவேற்றவும் அல்லது விரிவான மருந்து பகுப்பாய்வுக்கு உங்கள் மருந்துச் சீட்டு உரையை ஒட்டவும். மார்பு X-Ray, மூளை CT/MRI, எலும்பு X-Ray, வயிறு CT, முதுகெலும்பு X-Ray, பல் OPG ஆதரவு.'
    },
    'hero.stat.acc': { en: 'Accuracy', ta: 'துல்லியம்' },
    'hero.stat.time': { en: 'Analysis Time', ta: 'பகுப்பாய்வு நேரம்' },
    'hero.stat.med': { en: 'Medicines', ta: 'மருந்துகள்' },
    'hero.stat.type': { en: 'Scan Types', ta: 'ஸ்கேன் வகைகள்' },
    'hero.stat.avail': { en: 'Available', ta: 'கிடைக்கிறது' },

    // Mode Tabs
    'tab.scan': { en: 'Scan Analyzer', ta: 'ஸ்கேன் பகுப்பாய்வி' },
    'tab.rx': { en: 'Prescription Reader', ta: 'மருந்துச்சீட்டு வாசகர்' },
    'tab.search': { en: 'Medicine Search', ta: 'மருந்து தேடல்' },

    // Scan Panel
    'scan.title': { en: '🔬 Medical Image Analysis', ta: '🔬 மருத்துவ படம் பகுப்பாய்வு' },
    'scan.sub': { en: 'Upload a medical scan for instant AI-powered diagnostic analysis', ta: 'உடனடி AI சக்தி வாய்ந்த நோயறிதல் பகுப்பாய்வுக்கு மருத்துவ ஸ்கேனை பதிவேற்றவும்' },
    'scan.seltype': { en: 'Select Scan Type', ta: 'ஸ்கேன் வகையை தேர்ந்தெடுக்கவும்' },
    'scan.chest': { en: 'Chest X-Ray', ta: 'மார்பு X-Ray' },
    'scan.brain': { en: 'Brain CT/MRI', ta: 'மூளை CT/MRI' },
    'scan.bone': { en: 'Bone X-Ray', ta: 'எலும்பு X-Ray' },
    'scan.abdomen': { en: 'Abdomen CT', ta: 'வயிறு CT' },
    'scan.spine': { en: 'Spine X-Ray', ta: 'முதுகெலும்பு X-Ray' },
    'scan.dental': { en: 'Dental OPG', ta: 'பல் OPG' },
    'scan.drop': { en: 'Drag & Drop or Click to Upload', ta: 'இழுத்து விடுங்கள் அல்லது கிளிக் செய்து பதிவேற்றவும்' },
    'scan.dropsub': { en: 'PNG, JPG, JPEG, BMP, TIFF · Max 20MB', ta: 'PNG, JPG, JPEG, BMP, TIFF · அதிகபட்சம் 20MB' },
    'scan.btn': { en: '🔬 Analyze Medical Image', ta: '🔬 மருத்துவ படத்தை பகுப்பாய்வு செய்' },

    // Angle Toolbar
    'angle.title': { en: '🔄 Scan Angle', ta: '🔄 ஸ்கேன் கோணம்' },
    'angle.custom': { en: 'Custom:', ta: 'தனிப்பயன்:' },
    'angle.ccw': { en: '↺ CCW', ta: '↺ இட' },
    'angle.cw': { en: '↻ CW', ta: '↻ வல' },
    'angle.reset': { en: '⟳ Reset', ta: '⟳ மீட்டமை' },
    'angle.reanalyze': { en: '🔬 Re-analyze at this Angle', ta: '🔬 இந்த கோணத்தில் மீண்டும் பகுப்பாய்வு' },

    // Rx Panel
    'rx.title': { en: '💊 Prescription Reader', ta: '💊 மருந்துச்சீட்டு வாசகர்' },
    'rx.sub': { en: 'Upload a prescription photo or paste text — our AI extracts and analyzes all medicines, dosages & interactions.', ta: 'மருந்துச்சீட்டு புகைப்படத்தை பதிவேற்றவும் அல்லது உரையை ஒட்டவும் — AI அனைத்து மருந்துகள், அளவுகள் & தாக்கங்களை பிரித்தெடுத்து பகுப்பாய்வு செய்யும்.' },
    'rx.imgTab': { en: '📷 Upload Image', ta: '📷 படம் பதிவேற்று' },
    'rx.txtTab': { en: '✏️ Paste Text', ta: '✏️ உரை ஒட்டு' },
    'rx.drop': { en: 'Drag & Drop or Click to Upload Prescription', ta: 'மருந்துச்சீட்டை இழுத்து விடுங்கள் அல்லது கிளிக் செய்யுங்கள்' },
    'rx.dropsub': { en: 'Printed or Handwritten · PNG, JPG, JPEG, BMP, TIFF · Max 20MB', ta: 'அச்சிட்டது அல்லது கையெழுத்து · PNG, JPG, JPEG, BMP, TIFF · அதிகபட்சம் 20MB' },
    'rx.ocrBtn': { en: '📷 Extract & Analyze Prescription', ta: '📷 மருந்துச்சீட்டை பிரித்தெடு & பகுப்பாய்வு செய்' },
    'rx.textPlaceholder': { en: 'Paste prescription text here...', ta: 'மருந்துச்சீட்டு உரையை இங்கே ஒட்டவும்...' },
    'rx.analyzeTextBtn': { en: '💊 Analyze Prescription', ta: '💊 மருந்துச்சீட்டை பகுப்பாய்வு செய்' },

    // Medicine Search
    'search.title': { en: '🔍 Medicine Search', ta: '🔍 மருந்து தேடல்' },
    'search.sub': { en: 'Search our database of 200+ medicines by name or condition', ta: '200+ மருந்துகளின் தரவுத்தளத்தில் பெயர் அல்லது நோயால் தேடுங்கள்' },
    'search.placeholder': { en: 'Search medicine name or condition...', ta: 'மருந்து பெயர் அல்லது நோயை தேடுங்கள்...' },
    'search.btn': { en: '🔍', ta: '🔍' },

    // Sidebar
    'side.stats': { en: '📊 Live Stats', ta: '📊 நேரடி புள்ளிவிவரங்கள்' },
    'side.total': { en: 'Total Scans', ta: 'மொத்த ஸ்கேன்கள்' },
    'side.acc': { en: 'Avg Accuracy', ta: 'சராசரி துல்லியம்' },
    'side.images': { en: 'Images', ta: 'படங்கள்' },
    'side.rxcount': { en: 'Prescriptions', ta: 'மருந்துச்சீட்டுகள்' },
    'side.how': { en: '📋 How It Works', ta: '📋 எப்படி செயல்படுகிறது' },
    'side.step1': { en: '<strong>Select</strong> scan type', ta: '<strong>தேர்வு</strong> ஸ்கேன் வகை' },
    'side.step2': { en: '<strong>Upload</strong> medical image or <strong>Paste</strong> prescription text', ta: '<strong>பதிவேற்று</strong> மருத்துவ படம் அல்லது <strong>ஒட்டு</strong> மருந்துச்சீட்டு உரை' },
    'side.step3': { en: '<strong>Get</strong> instant findings, report & confidence', ta: '<strong>பெறு</strong> உடனடி கண்டுபிடிப்புகள், அறிக்கை & நம்பகத்தன்மை' },
    'side.step4': { en: '<strong>Search</strong> 200+ medicines by name or condition', ta: '<strong>தேடு</strong> 200+ மருந்துகளை பெயர் அல்லது நோயால்' },
    'side.step5': { en: '<strong>Translate 🇮🇳</strong> report to Tamil if needed', ta: '<strong>மொழிபெயர்</strong> அறிக்கையை தமிழில்' },
    'side.disclaimer': { en: '⚠️ For informational purposes only. Always consult a qualified medical professional.', ta: '⚠️ தகவல் நோக்கங்களுக்காக மட்டுமே. எப்போதும் தகுதிவாய்ந்த மருத்துவரை அணுகவும்.' },
};

let currentLang = localStorage.getItem('mediscan-lang') || 'en';

function applyTranslations(lang) {
    currentLang = lang;
    localStorage.setItem('mediscan-lang', lang);
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        const t = UI_TRANSLATIONS[key];
        if (!t) return;
        const val = t[lang] || t['en'];
        // Use innerHTML for entries that contain <strong> etc.
        if (val.includes('<')) el.innerHTML = val;
        else el.textContent = val;
    });
    // Update lang button label
    const btn = document.getElementById('langToggleBtn');
    if (btn) btn.textContent = lang === 'en' ? 'தமிழ்' : 'EN';
}

(function initLangToggle() {
    // Apply saved language on load
    applyTranslations(currentLang);

    const btn = document.getElementById('langToggleBtn');
    btn?.addEventListener('click', () => {
        applyTranslations(currentLang === 'en' ? 'ta' : 'en');
    });
})();
