"""MEDISCAN AI — OCR & Prescription Analysis Engine"""
import re, os, logging
try:
    import cv2, numpy as np
    CV2_OK = True
except ImportError:
    CV2_OK = False
try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    OCR_OK = True
    # Common Tesseract paths on Windows
    for p in [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            break
except ImportError:
    OCR_OK = False

log = logging.getLogger(__name__)

from .medicine_db import MEDICINE_DB

# ── Drug Interaction Database ─────────────────────────────────────────────────
INTERACTIONS = [
    ({"warfarin","aspirin"},        "CRITICAL",  "Warfarin + Aspirin: Severe bleeding risk — combined antiplatelet and anticoagulant effect. Avoid unless cardiology directed."),
    ({"warfarin","ibuprofen"},      "CRITICAL",  "Warfarin + Ibuprofen: GI bleeding and elevated INR — avoid NSAIDs on warfarin."),
    ({"nitroglycerin","sildenafil"},"CRITICAL",  "Nitroglycerin + Sildenafil: FATAL hypotension — nitrates + PDE-5 inhibitors absolutely contraindicated."),
    ({"nitroglycerin","tadalafil"}, "CRITICAL",  "Nitroglycerin + Tadalafil: FATAL hypotension — contraindicated combination."),
    ({"metformin","alcohol"},       "HIGH",      "Metformin + Alcohol: Increased lactic acidosis risk. Avoid alcohol with metformin."),
    ({"methotrexate","aspirin"},    "CRITICAL",  "Methotrexate + Aspirin/NSAIDs: Methotrexate toxicity greatly increased — NSAIDs reduce renal clearance."),
    ({"sertraline","tramadol"},     "HIGH",      "Sertraline + Tramadol: Serotonin syndrome risk — agitation, hyperthermia, clonus. Avoid combination."),
    ({"lithium","ibuprofen"},       "HIGH",      "Lithium + Ibuprofen: NSAIDs reduce renal lithium clearance → lithium toxicity. Monitor levels."),
    ({"digoxin","amiodarone"},      "HIGH",      "Digoxin + Amiodarone: Digoxin levels doubled — reduce digoxin dose by 50%, monitor levels."),
    ({"carbamazepine","warfarin"},  "HIGH",      "Carbamazepine + Warfarin: Enzyme induction reduces warfarin efficacy — close INR monitoring required."),
    ({"phenytoin","warfarin"},      "HIGH",      "Phenytoin + Warfarin: Complex interaction — initially increases then decreases warfarin effect. Monitor INR closely."),
    ({"ciprofloxacin","theophylline"},"HIGH",    "Ciprofloxacin + Theophylline: Fluoroquinolones inhibit theophylline metabolism → toxicity. Reduce theophylline dose."),
    ({"aspirin","ibuprofen"},       "MODERATE",  "Aspirin + Ibuprofen: Ibuprofen may reduce cardioprotective aspirin effect. Space doses apart (aspirin first)."),
    ({"metformin","furosemide"},    "MODERATE",  "Metformin + Furosemide: Volume depletion can increase metformin-associated lactic acidosis risk."),
    ({"amiodarone","warfarin"},     "CRITICAL",  "Amiodarone + Warfarin: Amiodarone markedly potentiates warfarin — reduce warfarin dose ~30-50%, close INR monitoring."),
    ({"clarithromycin","atorvastatin"},"HIGH",   "Clarithromycin + Atorvastatin: Statin levels increased markedly → myopathy/rhabdomyolysis risk. Withhold statin."),
    ({"metronidazole","alcohol"},   "HIGH",      "Metronidazole + Alcohol: Disulfiram-like reaction — flushing, nausea, vomiting, palpitations. Avoid alcohol."),
    ({"diazepam","morphine"},       "CRITICAL",  "Diazepam + Morphine: Additive respiratory depression — risk of apnea/death. Use together with extreme caution."),
    ({"alprazolam","alcohol"},      "HIGH",      "Alprazolam + Alcohol: Enhanced CNS depression — sedation, respiratory depression, risk of death."),
    ({"doxycycline","calcium_carbonate"},"MODERATE","Doxycycline + Calcium: Calcium chelates doxycycline reducing absorption by up to 80%. Separate doses by 2–3 hours."),
    ({"ciprofloxacin","calcium_carbonate"},"MODERATE","Ciprofloxacin + Calcium: Calcium reduces fluoroquinolone absorption. Separate doses by 2 hours."),
    ({"ferrous_sulphate","doxycycline"},"MODERATE","Iron + Doxycycline: Iron chelates tetracyclines reducing absorption. Separate by 2–3 hours."),
    ({"omeprazole","clopidogrel"},  "MODERATE",  "Omeprazole + Clopidogrel: Omeprazole inhibits CYP2C19 reducing clopidogrel activation. Use pantoprazole instead."),
    ({"colchicine","clarithromycin"},"HIGH",     "Colchicine + Clarithromycin: Colchicine levels markedly elevated (P-gp + CYP3A4 inhibition) → toxicity risk."),
    ({"lithium","furosemide"},      "HIGH",      "Lithium + Furosemide: Dehydration from diuretic increases lithium retention → lithium toxicity. Monitor levels."),
    ({"warfarin","rifampicin"},     "HIGH",      "Warfarin + Rifampicin: Rifampicin induces CYP enzymes → greatly reduces warfarin efficacy. Major INR adjustments required."),
    ({"haloperidol","amiodarone"},  "HIGH",      "Haloperidol + Amiodarone: Combined QT prolongation risk — risk of Torsades de Pointes/fatal arrhythmia."),
    ({"domperidone","amiodarone"},  "HIGH",      "Domperidone + Amiodarone: QT prolongation risk — avoid combination."),
]

# ── Dosage Timing Codes ───────────────────────────────────────────────────────
TIMING_CODES = {
    "od": "Once daily","qd": "Once daily","qid": "Four times daily","bd": "Twice daily",
    "bid": "Twice daily","tds": "Three times daily","tid": "Three times daily",
    "sos": "When required (as needed)","prn": "When required (as needed)",
    "stat": "Immediately (single dose)","ac": "Before meals","pc": "After meals",
    "hs": "At bedtime","nocte": "At night","mane": "In the morning",
    "1-0-1": "Morning and night","1-1-1": "Three times daily","0-0-1": "Night only",
    "1-0-0": "Morning only","1-1-0": "Morning and afternoon",
}

# ── OCR Preprocessing ─────────────────────────────────────────────────────────

def _to_gray(img):
    """Convert to grayscale regardless of input channels."""
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img.copy()

def _deskew(gray):
    """Deskew image using projection-profile angle estimation."""
    try:
        coords = np.column_stack(np.where(gray < 128))
        if len(coords) < 10:
            return gray
        angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) < 0.5 or abs(angle) > 45:
            return gray
        (h, w) = gray.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
    except Exception:
        return gray

def _clahe(gray, clip=2.5, tile=(8, 8)):
    """Apply CLAHE — dramatically improves local contrast for handwriting."""
    clahe_obj = cv2.createCLAHE(clipLimit=clip, tileGridSize=tile)
    return clahe_obj.apply(gray)

def _gamma_correct(gray, gamma=1.4):
    """Gamma correction — brightens dark/faded ink on digital photos."""
    inv = 1.0 / gamma
    table = np.array([(i / 255.0) ** inv * 255 for i in range(256)], dtype=np.uint8)
    return cv2.LUT(gray, table)

def _sauvola_thresh(gray, window=25, k=0.2):
    """
    Sauvola local thresholding — ideal for uneven lighting and shadows on prescriptions.
    Threshold formula: T = mean * (1 + k * (std/128 - 1))
    """
    gray_f = gray.astype(np.float32)
    mean = cv2.blur(gray_f, (window, window))
    mean_sq = cv2.blur(gray_f ** 2, (window, window))
    std = np.sqrt(np.maximum(mean_sq - mean ** 2, 0))
    threshold = mean * (1.0 + k * (std / 128.0 - 1.0))
    return np.where(gray_f < threshold, 0, 255).astype(np.uint8)

def _denoise_nlm(gray):
    """Non-local means denoising — removes camera noise while preserving ink edges."""
    if not CV2_OK:
        return gray
    return cv2.fastNlMeansDenoising(gray, h=12, templateWindowSize=7, searchWindowSize=21)

# ─ Preprocessing Pipelines ───────────────────────────────────────────────────

def _preprocess_printed_v1(img):
    """Otsu threshold — optimal for clean laser-printed documents."""
    gray = _to_gray(img)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    return cv2.dilate(thresh, kernel, iterations=1)

def _preprocess_printed_v2(img):
    """Adaptive threshold for printed text with shadows/uneven background."""
    gray = _to_gray(img)
    gray = _clahe(gray, clip=2.0, tile=(12, 12))
    gray = cv2.bilateralFilter(gray, 7, 60, 60)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    return cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

def _preprocess_handwritten_v1(img):
    """Conservative: CLAHE + bilateral + Gaussian adaptive threshold."""
    gray = _to_gray(img)
    gray = _deskew(gray)
    gray = _clahe(gray)
    gray = cv2.bilateralFilter(gray, 11, 80, 80)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4
    )
    kernel = np.ones((2, 2), np.uint8)
    return cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

def _preprocess_handwritten_v2(img):
    """Aggressive: Double CLAHE + mean adaptive threshold."""
    gray = _to_gray(img)
    gray = _deskew(gray)
    gray = _clahe(gray)
    gray = _clahe(gray)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 8
    )
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_open)
    kernel_close = np.ones((2, 3), np.uint8)
    return cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel_close)

def _preprocess_handwritten_v3(img):
    """Stroke-enhance: Sharpening + Gaussian adaptive threshold."""
    gray = _to_gray(img)
    gray = _deskew(gray)
    gray = _clahe(gray)
    blur = cv2.GaussianBlur(gray, (0, 0), 3)
    sharpened = cv2.addWeighted(gray, 1.6, blur, -0.6, 0)
    thresh = cv2.adaptiveThreshold(
        sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 13, 3
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
    return cv2.dilate(thresh, kernel, iterations=1)

def _preprocess_handwritten_v4(img):
    """Experimental: NLM denoising + Gamma + Sauvola local threshold."""
    gray = _to_gray(img)
    gray = _deskew(gray)
    gray = _gamma_correct(gray, gamma=1.5)
    gray = _denoise_nlm(gray)
    gray = _clahe(gray, clip=3.0, tile=(6, 6))
    sauvola = _sauvola_thresh(gray, window=31, k=0.18)
    kernel = np.ones((2, 2), np.uint8)
    return cv2.morphologyEx(sauvola, cv2.MORPH_CLOSE, kernel)

# Medical vocabulary for OCR scoring
_MED_TOKENS = {
    'tab','cap','inj','syr','mg','mcg','ml','bd','od','tds','tid','qid','sos','prn',
    'stat','once','twice','daily','morning','night','before','after','meal',
    'amoxicillin','paracetamol','ibuprofen','metformin','omeprazole','atorvastatin',
    'amlodipine','aspirin','insulin','cetirizine','salbutamol','losartan','enalapril'
}

def _score_result(text):
    """Robust OCR scoring: rewards medical words and penalises non-ASCII junk."""
    words = re.findall(r'[a-zA-Z0-9]{3,}', text)
    unique = {w.lower() for w in words}
    score = len(unique) * 2 + len(words)
    score += sum(5 for w in unique if w in _MED_TOKENS)
    junk = len(re.findall(r'[^\x20-\x7E\n]', text))
    score -= junk * 3
    return score


# ── Post-processing & Consensus ──────────────────────────────────────────────

_OCR_FIXES = [
    (re.compile(r'(?<=[a-z])0(?=[a-z])', re.I),          'o'), # 0 -> o
    (re.compile(r'(?<=[a-z])1(?=[a-z])', re.I),          'l'), # 1 -> l
    (re.compile(r'\|(?=[a-zA-Z])', re.I),                'l'), # | -> l
    (re.compile(r'\brn\b'),                              'm'), # rn -> m
    (re.compile(r'\bTob\.?', re.I),                      'Tab.'),
    (re.compile(r'\bCop\.?', re.I),                      'Cap.'),
    (re.compile(r'\blnj\.?', re.I),                      'Inj.'),
    (re.compile(r'(?<=[A-Za-z])S(?=\s*\d)', re.I),       '5'), # S -> 5
    (re.compile(r'[\u2014\u2013]'),                       '-'), # dashes
    (re.compile(r'[ \t]{3,}'),                           '  '),
    (re.compile(r'\n{3,}'),                              '\n\n'),
]

def _apply_ocr_fixes(text):
    """Apply regex-based character corrections."""
    for pattern, replacement in _OCR_FIXES:
        text = pattern.sub(replacement, text)
    return text.strip()

def _token_vote_consensus(results):
    """Picks result with highest overlap across multiple OCR runs."""
    from collections import Counter
    freq = Counter()
    for r in results:
        tokens = set(re.findall(r'[\w.%-]+', r.lower()))
        freq.update(tokens)
    
    def score(res):
        tokens = re.findall(r'[\w.%-]+', res.lower())
        return sum(freq[t] for t in tokens)
        
    return max(results, key=score) if results else ''

def perform_ocr(filepath):
    """Refined 3-phase OCR engine for medical prescriptions."""
    if not OCR_OK:
        return "ERROR: OCR dependencies missing. Please install Tesseract."
        
    try:
        pil_img = Image.open(filepath).convert("RGB")
        w, h = pil_img.size
        
        # Phase 1: Adaptive scaling & Fast Pass
        scale = 4 if min(w, h) < 600 else (3 if min(w, h) < 1200 else 2)
        if w * scale * h * scale > 12_000_000: scale = max(1, scale - 1)
        
        img = pil_img.resize((w*scale, h*scale), Image.LANCZOS)
        enhanced = ImageEnhance.Contrast(img).enhance(2.0)
        enhanced = ImageEnhance.Sharpness(enhanced).enhance(3.0)
        
        all_results = []
        for psm in [3, 4, 6, 11]:
            for oem in [1, 3]:
                try:
                    cfg = f'--oem {oem} --psm {psm} -l eng -c preserve_interword_spaces=1'
                    txt = pytesseract.image_to_string(enhanced, config=cfg)
                    if txt.strip(): all_results.append(txt)
                except Exception: pass
        
        # Early exit if fast pass is high quality
        if all_results:
            best_fast = _token_vote_consensus(all_results)
            if _score_result(best_fast) >= 20:
                return _apply_ocr_fixes(best_fast)
        
        # Phase 2: CV2 Preprocessing pipelines
        if CV2_OK:
            arr = np.array(img)
            pipelines = [
                _preprocess_printed_v1, _preprocess_printed_v2,
                _preprocess_handwritten_v1, _preprocess_handwritten_v2,
                _preprocess_handwritten_v3, _preprocess_handwritten_v4
            ]
            for pipe in pipelines:
                try:
                    processed = pipe(arr)
                    p_pil = Image.fromarray(processed)
                    for psm in [4, 6, 11, 13]:
                        for oem in [1, 3]:
                            try:
                                cfg = f'--oem {oem} --psm {psm} -l eng -c preserve_interword_spaces=1'
                                txt = pytesseract.image_to_string(p_pil, config=cfg)
                                if txt.strip(): all_results.append(txt)
                            except Exception: pass
                except Exception: continue
                
        if not any(r.strip() for r in all_results):
            return "ERROR: Could not detect text. Please use high resolution image."
            
        # Phase 3: Consensus & Post-processing
        best = _token_vote_consensus(all_results)
        return _apply_ocr_fixes(best)
        
    except Exception as e:
        log.error(f"OCR failure: {e}")
        return f"ERROR: Technical failure - {str(e)}"



# ── Medicine-line Extractor ───────────────────────────────────────────────────
# Patterns that strongly indicate a prescription medicine line
_RX_INDICATORS = re.compile(
    r"""
    \b(?:
        tab\.?|cap\.?|caps\.?|inj\.?|syr\.?|oint\.?|drops?|susp\.?|sol\.?  # dosage forms
        |tablet|capsule|injection|syrup|suspension|ointment|cream|gel|patch  # dosage forms (full)
    )\b                                                                        # form prefix
    |
    \b\d+\s*(?:mg|mcg|ml|g|iu|u|units?|meq)\b                               # dosage amount
    |
    \b(?:od|bd|bid|tds|tid|qid|sos|prn|stat|mane|nocte|hs|ac|pc)\b          # timing code
    |
    \b(?:once|twice|thrice|1-0-1|1-1-1|0-0-1)\b                             # timing words
    |
    \b(?:x\s*\d+\s*days?|for\s+\d+\s*days?)\b                               # duration
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Patterns that indicate a NON-medicine header/footer line
_HEADER_PATTERNS = re.compile(
    r"""
    \b(?:
        dr\.?|doctor|physician|consultant|mbbs|md|ms|frcs|fcps|bds|dgo      # doctor titles
        |clinic|hospital|centre|center|dispensary|pharmacy|chemist            # place words
        |address|ph\.?|phone|tel\.?|mob(?:ile)?|email|fax|pin|post           # contact info
        |patient|p\.?name|age|sex|gender|weight|height|blood                 # patient header
        |reg\.?\s*no|registration|uhid|op\.?\s*no|ip\.?\s*no                 # record numbers
        |signature|sign\.|seal|stamp|date|d/?o|diagnosis|rx\s*no             # signature/stamp
        |follow.?up|review|advised|refer                                      # follow-up notes
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

def _extract_medicine_lines(text):
    """
    Extract only the medicine-prescription lines from OCR text.
    Lines that contain dosage forms, amounts, or timing codes are kept.
    Header/address/doctor-info lines are removed.
    Returns filtered text, or empty string if nothing medicine-like found.
    """
    lines = text.splitlines()
    medicine_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or len(stripped) < 3:
            continue
        has_rx = bool(_RX_INDICATORS.search(stripped))
        has_header = bool(_HEADER_PATTERNS.search(stripped))
        # Keep if it looks like an Rx line and not purely a header
        if has_rx and not has_header:
            medicine_lines.append(stripped)
        elif has_rx:  # has both — keep (e.g. "Tab. Amoxicillin – Dr. Advised")
            medicine_lines.append(stripped)
    return '\n'.join(medicine_lines)  # returns '' if nothing found

# ── Fuzzy Medicine Matching ───────────────────────────────────────────────────
# Common words that appear in prescriptions but are NOT medicine names
_NOISE_WORDS = {
    'tab', 'cap', 'inj', 'syr', 'tab.', 'cap.', 'inj.', 'sir', 'sir.',
    'the', 'and', 'for', 'with', 'take', 'once', 'twice', 'three', 'daily',
    'after', 'before', 'meal', 'meals', 'food', 'water', 'morning', 'night',
    'days', 'week', 'month', 'dose', 'doses', 'tablet', 'capsule', 'injection',
    'syrup', 'drops', 'apply', 'topically', 'oral', 'externally', 'times',
    'patient', 'doctor', 'hospital', 'clinic', 'date', 'sign', 'please',
    'name', 'age', 'sex', 'male', 'female', 'address', 'phone', 'reg',
    'number', 'prescription', 'prescribed', 'advice', 'follow', 'continue',
}

def _fuzzy_match(word, db_keys, threshold=0.78):
    """Fuzzy matching — tightened to avoid OCR noise false positives."""
    word_lower = word.lower().strip().rstrip('.,;:()')
    # Require minimum 5 chars and not a known noise/stop word
    if len(word_lower) < 5 or word_lower in _NOISE_WORDS:
        return None

    best_match, best_score = None, 0.0
    for key in db_keys:
        # Substring match — only if word is at least 60% of the key length
        if (key in word_lower or word_lower in key) and len(word_lower) >= len(key) * 0.60:
            return key

        # N-gram bigram similarity
        shorter, longer = (word_lower, key) if len(word_lower) <= len(key) else (key, word_lower)
        if len(shorter) < 4:
            continue
        matches = sum(1 for i in range(len(shorter) - 1) if shorter[i:i+2] in longer)
        denom = len(shorter) + len(longer) - 2
        score = (2.0 * matches) / denom if denom > 0 else 0
        # Length penalty: penalise words very different in length
        len_diff = abs(len(word_lower) - len(key))
        adjusted = score - (len_diff * 0.06)
        if adjusted > best_score:
            best_score, best_match = adjusted, key

    return best_match if best_score >= threshold else None

def analyze_prescription(text, custom_db=None):
    """Analyze prescription text: identify medicines, dosage codes, interactions."""
    # Filter out doctor headers, addresses, signatures — keep only medicine lines
    filtered_text = _extract_medicine_lines(text)
    # If filter found nothing medicine-like, fall back to the full text
    working_text = filtered_text if filtered_text.strip() else text

    combined_db = {**MEDICINE_DB, **(custom_db or {})}
    db_keys = list(combined_db.keys())

    words = re.split(r'[\s,;:/\n]+', working_text)
    found_medicines = {}
    dosage_notes = {}

    # Detect dosage timing codes
    text_lower = working_text.lower()
    detected_timings = {code: label for code, label in TIMING_CODES.items() if re.search(r'\b' + re.escape(code) + r'\b', text_lower)}

    # Extract medicine names
    i = 0
    while i < len(words):
        w = words[i].lower().strip().rstrip('.,;:)([]')
        # Skip very short words and known noise words
        if len(w) < 4 or w in _NOISE_WORDS:
            i += 1
            continue
        # Direct match first (exact), then fuzzy (only for words ≥5 chars)
        match = w if w in combined_db else (_fuzzy_match(w, db_keys) if len(w) >= 5 else None)
        if match and match not in found_medicines:
            info = combined_db[match].copy()
            info['name'] = match.replace('_', ' ').title()
            
            # Extract specific dosage and timing from nearby text (e.g., "500mg BD")
            nearby = ' '.join(words[max(0, i-1):min(len(words), i+8)])
            dose_val = re.search(r'\d+\s*(?:mg|mcg|ml|g|IU|U|units?|mEq)', nearby, re.IGNORECASE)
            time_val = re.search(r'\b(?:od|bd|bid|tds|tid|qid|sos|prn|stat|mane|nocte|hs|ac|pc|1-0-1|1-1-1|0-0-1)\b', nearby, re.IGNORECASE)
            
            custom_dosage = []
            if dose_val: custom_dosage.append(dose_val.group())
            if time_val: custom_dosage.append(time_val.group().upper())
            
            if custom_dosage:
                info['dosage'] = ' '.join(custom_dosage)
                dosage_notes[match] = ' '.join(custom_dosage)
            
            found_medicines[match] = info
        i += 1

    medicines_list = list(found_medicines.values())

    # Detected interactions
    interactions = check_interactions(list(found_medicines.keys()))

    # Summary line
    if medicines_list:
        summary = f"Found {len(medicines_list)} medicine(s): {', '.join(m['name'] for m in medicines_list)}"
        if detected_timings:
            summary += f" | Dosage codes: {', '.join(f'{k.upper()}={v}' for k,v in detected_timings.items())}"
    else:
        summary = "No recognisable medicines found. Please ensure the prescription image is clear."

    return {
        "medicines": medicines_list,
        "interactions": interactions,
        "timings_detected": detected_timings,
        "dosage_notes": dosage_notes,
        "summary": summary,
        "raw_text": text,
    }

def check_interactions(medicine_names):
    """Check for known drug interactions among a list of medicine names."""
    meds_lower = {m.lower().strip() for m in medicine_names}
    alerts = []
    for pair, severity, message in INTERACTIONS:
        if pair.issubset(meds_lower):
            alerts.append({"severity": severity, "message": message, "drugs": list(pair)})
    return alerts

# ── Safety Metadata ───────────────────────────────────────────────────────────
# pregnancy: FDA category (A=safest, B, C, D, X=contraindicated)
# alcohol: True = avoid alcohol
# driving: True = avoid driving
SAFETY_METADATA = {
    "paracetamol":    {"pregnancy": "B", "alcohol": True,  "driving": False},
    "ibuprofen":      {"pregnancy": "C", "alcohol": True,  "driving": False},
    "aspirin":        {"pregnancy": "D", "alcohol": True,  "driving": False},
    "diclofenac":     {"pregnancy": "C", "alcohol": True,  "driving": False},
    "tramadol":       {"pregnancy": "C", "alcohol": True,  "driving": True},
    "morphine":       {"pregnancy": "C", "alcohol": True,  "driving": True},
    "codeine":        {"pregnancy": "C", "alcohol": True,  "driving": True},
    "amoxicillin":    {"pregnancy": "B", "alcohol": False, "driving": False},
    "azithromycin":   {"pregnancy": "B", "alcohol": False, "driving": False},
    "ciprofloxacin":  {"pregnancy": "C", "alcohol": False, "driving": False},
    "metronidazole":  {"pregnancy": "B", "alcohol": True,  "driving": False},
    "doxycycline":    {"pregnancy": "D", "alcohol": False, "driving": False},
    "metformin":      {"pregnancy": "B", "alcohol": True,  "driving": False},
    "glibenclamide":  {"pregnancy": "C", "alcohol": True,  "driving": True},
    "gliclazide":     {"pregnancy": "C", "alcohol": True,  "driving": True},
    "insulin":        {"pregnancy": "B", "alcohol": True,  "driving": True},
    "empagliflozin":  {"pregnancy": "C", "alcohol": False, "driving": False},
    "amlodipine":     {"pregnancy": "C", "alcohol": False, "driving": False},
    "atenolol":       {"pregnancy": "D", "alcohol": False, "driving": True},
    "metoprolol":     {"pregnancy": "C", "alcohol": False, "driving": True},
    "sertraline":     {"pregnancy": "C", "alcohol": True,  "driving": True},
    "fluoxetine":     {"pregnancy": "C", "alcohol": True,  "driving": True},
    "diazepam":       {"pregnancy": "D", "alcohol": True,  "driving": True},
    "alprazolam":     {"pregnancy": "D", "alcohol": True,  "driving": True},
    "warfarin":       {"pregnancy": "X", "alcohol": True,  "driving": False},
    "omeprazole":     {"pregnancy": "C", "alcohol": False, "driving": False},
    "prednisolone":   {"pregnancy": "C", "alcohol": False, "driving": False},
    "levothyroxine":  {"pregnancy": "A", "alcohol": False, "driving": False},
    "cetirizine":     {"pregnancy": "B", "alcohol": False, "driving": True},
    "promethazine":   {"pregnancy": "C", "alcohol": True,  "driving": True},
    "phenytoin":      {"pregnancy": "D", "alcohol": True,  "driving": True},
    "carbamazepine":  {"pregnancy": "D", "alcohol": True,  "driving": True},
    "lithium":        {"pregnancy": "D", "alcohol": False, "driving": True},
    "sildenafil":     {"pregnancy": "B", "alcohol": True,  "driving": False},
    "zolpidem":       {"pregnancy": "C", "alcohol": True,  "driving": True},
    "atorvastatin":   {"pregnancy": "X", "alcohol": True,  "driving": False},
    "rosuvastatin":   {"pregnancy": "X", "alcohol": True,  "driving": False},
}

# ── Dosage Schedule Builder ───────────────────────────────────────────────────
# Maps timing codes to (morning, afternoon, night) boolean tuple
_SCHEDULE_MAP = {
    "od":    (True,  False, False),
    "qd":    (True,  False, False),
    "mane":  (True,  False, False),
    "1-0-0": (True,  False, False),
    "nocte": (False, False, True),
    "hs":    (False, False, True),
    "0-0-1": (False, False, True),
    "bd":    (True,  False, True),
    "bid":   (True,  False, True),
    "1-0-1": (True,  False, True),
    "tds":   (True,  True,  True),
    "tid":   (True,  True,  True),
    "1-1-1": (True,  True,  True),
    "qid":   (True,  True,  True),
    "1-1-0": (True,  True,  False),
    "sos":   (False, False, False),  # as needed
    "prn":   (False, False, False),  # as needed
    "stat":  (True,  False, False),  # once
}

def build_dosage_schedule(medicines_list):
    """
    Build a dosage schedule grid from a list of medicine dicts.
    Returns a list of dicts: {name, morning, afternoon, night, dosage}.
    """
    schedule = []
    for med in medicines_list:
        name   = med.get('name', '?')
        dosage = med.get('dosage', 'As directed')
        # Infer timing from dosage string
        dose_lower = dosage.lower()
        morning = afternoon = night = False
        matched = False
        for code, (m, a, n) in _SCHEDULE_MAP.items():
            if re.search(r'\b' + re.escape(code) + r'\b', dose_lower):
                morning, afternoon, night = m, a, n
                matched = True
                break
        # Fallback heuristics for numeric patterns
        if not matched:
            if 'once' in dose_lower or 'od' in dose_lower:
                morning = True
            elif 'twice' in dose_lower or 'bd' in dose_lower:
                morning = night = True
            elif 'thrice' in dose_lower or 'tds' in dose_lower or 'tid' in dose_lower:
                morning = afternoon = night = True
            else:
                morning = True  # default to morning if unknown
        schedule.append({
            "name":      name,
            "dosage":    dosage,
            "morning":   morning,
            "afternoon": afternoon,
            "night":     night,
            "safety":    SAFETY_METADATA.get(name.lower().replace(' ','_'), {})
        })
    return schedule
