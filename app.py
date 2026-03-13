import os, re
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, date
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR,'mediscan.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
app.secret_key = 'mediscan_ai_secret_key_2026'
db = SQLAlchemy(app)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXT = {'png','jpg','jpeg','bmp','tiff','webp','gif'}

# ── Database Models ────────────────────────────────────────────────────────────
class Scan(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    filename   = db.Column(db.String(200), nullable=False)
    scan_type  = db.Column(db.String(100), default='Medical Image')
    timestamp  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    result     = db.Column(db.JSON, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    def to_dict(self):
        return {"id":self.id,"filename":self.filename,"scan_type":self.scan_type,
                "timestamp":self.timestamp.isoformat(),"result":self.result,"confidence":self.confidence}

class CustomMedicine(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), unique=True, nullable=False)
    category     = db.Column(db.String(100))
    uses         = db.Column(db.JSON)
    dosage       = db.Column(db.String(255))
    alternatives = db.Column(db.JSON)
    warnings     = db.Column(db.JSON)
    def to_dict(self):
        return {"name":self.name.title(),"category":self.category or "Custom",
                "uses":self.uses or [],"dosage":self.dosage or "As directed",
                "alternatives":self.alternatives or [],"warnings":self.warnings or []}

with app.app_context():
    db.create_all()

from engine.model import engine
from engine.ocr_service import (
    perform_ocr, analyze_prescription, check_interactions,
    MEDICINE_DB, build_dosage_schedule
)

# ── Error Handlers ────────────────────────────────────────────────────────────
@app.errorhandler(413)
def too_large(e):
    return jsonify({"error":"File too large. Max 20MB allowed."}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error":"Resource not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error":"Internal server error"}), 500

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXT

# ── Pages ─────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/report')
def project_report():
    from flask import send_from_directory
    return send_from_directory(BASE_DIR, 'project_report.html')

@app.route('/er')
def er_diagram():
    from flask import send_from_directory
    return send_from_directory(BASE_DIR, 'er_diagram.html')

# ── Health Check ──────────────────────────────────────────────────────────────
@app.route('/api/health')
def health():
    return jsonify({"app":"Mediscan AI","status":"healthy","version":"3.0"})

# ── Upload & Analyze Scan ─────────────────────────────────────────────────────
@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error":"No file provided"}), 400
    f = request.files['file']
    if not f.filename or not allowed_file(f.filename):
        return jsonify({"error":"Invalid file type. Use PNG/JPG/JPEG/BMP/TIFF."}), 400
    filename = secure_filename(f.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    f.save(filepath)
    try:
        scan_type = request.form.get('scan_type', 'auto')
        quality   = engine.check_image_quality(filepath)
        analysis  = engine.analyze(filepath, scan_type=scan_type)
        analysis['quality_info'] = quality
        new = Scan(
            filename  = filename,
            scan_type = analysis.get('scan_type','Medical Image'),
            result    = {
                'findings':     analysis['findings'],
                'report':       analysis['report'],
                'scan_type':    analysis.get('scan_type'),
                'condition':    analysis.get('condition'),
                'severity':     analysis.get('severity'),
                'rois':         analysis.get('rois', []),
                'differential': analysis.get('differential', []),
            },
            confidence = analysis['confidence']
        )
        db.session.add(new)
        db.session.commit()
        return jsonify({"status":"success","analysis_type":"medical_image","data":analysis})
    except Exception as e:
        return jsonify({"error":f"Analysis failed: {str(e)}"}), 500

# ── Text Prescription ─────────────────────────────────────────────────────────
@app.route('/api/analyze-prescription', methods=['POST'])
def analyze_rx():
    data = request.json or {}
    text = data.get('text','').strip()
    if not text:
        return jsonify({"error":"No prescription text provided"}), 400
    custom = {m.name.lower(): m.to_dict() for m in CustomMedicine.query.all()}
    result = analyze_prescription(text, custom_db=custom)
    # Build dosage schedule
    result['dosage_schedule'] = build_dosage_schedule(result.get('medicines', []))
    try:
        med_count = len(result.get('medicines', []))
        conf = round(min(70.0 + med_count * 8.5, 98.0) if med_count else 30.0, 1)
        new = Scan(
            filename  = 'text_input',
            scan_type = 'Prescription',
            result    = {'findings':[m['name'] for m in result['medicines']],'summary':result.get('summary','')},
            confidence= conf
        )
        db.session.add(new)
        db.session.commit()
    except Exception:
        pass
    return jsonify({"status":"success","analysis_type":"prescription","data":result})

# ── Image Prescription (OCR) ──────────────────────────────────────────────────
@app.route('/api/upload-prescription', methods=['POST'])
def upload_prescription():
    if 'file' not in request.files:
        return jsonify({"error":"No file provided"}), 400
    f = request.files['file']
    if not f.filename or not allowed_file(f.filename):
        return jsonify({"error":"Invalid file type. Use PNG/JPG/JPEG/BMP/TIFF."}), 400
    filename = secure_filename(f.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    f.save(filepath)
    try:
        from engine.ocr_service import _extract_medicine_lines
        raw_text = perform_ocr(filepath)
        if raw_text.startswith('ERROR:'):
            return jsonify({"error": raw_text, "raw_text": raw_text}), 422
        filtered_text = _extract_medicine_lines(raw_text)
        custom = {m.name.lower(): m.to_dict() for m in CustomMedicine.query.all()}
        result = analyze_prescription(raw_text, custom_db=custom)
        result['raw_text']       = filtered_text
        result['dosage_schedule'] = build_dosage_schedule(result.get('medicines', []))
        new = Scan(
            filename  = filename,
            scan_type = 'Prescription',
            result    = {'findings':[m['name'] for m in result['medicines']],'summary':result.get('summary',''),'raw_text':filtered_text},
            confidence= 90.0 if result['medicines'] else 35.0
        )
        db.session.add(new)
        db.session.commit()
        return jsonify({"status":"success","analysis_type":"prescription","data":result})
    except Exception as e:
        return jsonify({"error":f"OCR failed: {str(e)}"}), 500

# ── Medicine Search ───────────────────────────────────────────────────────────
@app.route('/api/search-medicine')
def search_medicine():
    q = request.args.get('q','').lower().strip()
    if not q:
        return jsonify({"error":"Query required"}), 400
    custom  = {m.name.lower(): m.to_dict() for m in CustomMedicine.query.all()}
    combined = {**MEDICINE_DB, **custom}
    results  = []
    for name, info in combined.items():
        name_lower = name.lower().replace('_',' ')
        uses_text  = ' '.join(info.get('uses', [])).lower()
        cat_text   = info.get('category','').lower()
        alt_text   = ' '.join(info.get('alternatives', [])).lower()
        # Match on name, uses, category, or alternatives
        if (q in name_lower or q in uses_text or q in cat_text or q in alt_text):
            entry = info.copy()
            entry['name'] = name.replace('_',' ').title()
            results.append(entry)
    # Boost exact name matches to top
    results.sort(key=lambda r: (0 if q in r['name'].lower() else 1))
    return jsonify({"results": results[:20], "total": len(results)})

# ── Drug Interactions ─────────────────────────────────────────────────────────
@app.route('/api/check-interactions', methods=['POST'])
def check_drug_interactions():
    data = request.json or {}
    meds = data.get('medicines', [])
    if len(meds) < 2:
        return jsonify({"error":"Provide at least 2 medicine names"}), 400
    return jsonify({"interactions": check_interactions(meds)})

# ── Train / Add Custom Medicine ───────────────────────────────────────────────
@app.route('/api/train', methods=['POST'])
def train():
    data = request.json or {}
    name = data.get('name','').strip().lower()
    if not name:
        return jsonify({"error":"Medicine name is required"}), 400
    # Validate minimum fields
    category = data.get('category','Custom').strip()
    uses     = data.get('uses', [])
    if isinstance(uses, str):
        uses = [u.strip() for u in uses.split(',') if u.strip()]
    dosage   = data.get('dosage','As directed').strip()
    alts     = data.get('alternatives', [])
    if isinstance(alts, str):
        alts = [a.strip() for a in alts.split(',') if a.strip()]
    warnings = data.get('warnings', [])
    if isinstance(warnings, str):
        warnings = [w.strip() for w in warnings.split(',') if w.strip()]

    existing = CustomMedicine.query.filter_by(name=name).first()
    if existing:
        # Update existing entry
        existing.category     = category
        existing.uses         = uses
        existing.dosage       = dosage
        existing.alternatives = alts
        existing.warnings     = warnings
        db.session.commit()
        return jsonify({"status":"updated","message":f"'{name.title()}' updated successfully."})
    new = CustomMedicine(name=name, category=category, uses=uses,
                         dosage=dosage, alternatives=alts, warnings=warnings)
    db.session.add(new)
    db.session.commit()
    return jsonify({"status":"trained","message":f"'{name.title()}' added to Mediscan AI knowledge base."})

# ── List Custom Medicines ─────────────────────────────────────────────────────
@app.route('/api/custom-medicines')
def list_custom():
    meds = CustomMedicine.query.all()
    return jsonify({"medicines": [m.to_dict() for m in meds], "count": len(meds)})

# ── Delete Custom Medicine ─────────────────────────────────────────────────────
@app.route('/api/custom-medicines/delete/<name>', methods=['DELETE'])
def delete_custom(name):
    med = CustomMedicine.query.filter_by(name=name.lower()).first()
    if not med:
        return jsonify({"error":"Medicine not found"}), 404
    db.session.delete(med)
    db.session.commit()
    return jsonify({"status":"deleted"})

# ── History ───────────────────────────────────────────────────────────────────
@app.route('/api/history')
def get_history():
    scans = Scan.query.order_by(Scan.timestamp.desc()).all()
    return jsonify([s.to_dict() for s in scans])

@app.route('/api/history/delete/<int:scan_id>', methods=['DELETE'])
def delete_scan(scan_id):
    s = db.get_or_404(Scan, scan_id)   # Fixed: SQLAlchemy 2.0 compatible
    db.session.delete(s)
    db.session.commit()
    return jsonify({"status":"success"})

@app.route('/api/history/clear', methods=['DELETE'])
def clear_history():
    Scan.query.delete()
    db.session.commit()
    return jsonify({"status":"success"})

# ── Stats ─────────────────────────────────────────────────────────────────────
@app.route('/api/stats')
def get_stats():
    scans     = Scan.query.all()
    total     = len(scans)
    rx_count  = sum(1 for s in scans if s.scan_type == 'Prescription')
    avg_conf  = round(sum(s.confidence for s in scans) / total, 1) if total else 0
    high_acc  = sum(1 for s in scans if s.confidence >= 90)
    today     = date.today().isoformat()
    today_cnt = sum(1 for s in scans if s.timestamp.date().isoformat() == today)
    latest    = Scan.query.order_by(Scan.timestamp.desc()).first()
    custom_count = CustomMedicine.query.count()
    return jsonify({
        'total':           total,
        'scans':           total - rx_count,
        'prescriptions':   rx_count,
        'avg_confidence':  avg_conf,
        'high_accuracy':   high_acc,
        'today':           today_cnt,
        'custom_medicines': custom_count,
        'medicine_db_size': len(MEDICINE_DB) + custom_count,
        'latest':          latest.timestamp.isoformat() if latest else None,
    })

# ── Chat ──────────────────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
def chat():
    data  = request.json or {}
    query = data.get('query','').strip()
    context = data.get('context')
    if not query:
        return jsonify({"error":"No query provided"}), 400
    resp = engine.chat_with_reasoning(query, context=context)
    if resp['answer'] and 'here to help' not in resp['answer']:
        return jsonify(resp)
    # Medicine lookup fallback
    q = query.lower()
    custom   = {m.name.lower(): m.to_dict() for m in CustomMedicine.query.all()}
    combined = {**MEDICINE_DB, **custom}
    for name, info in combined.items():
        if name in q or any(u.lower() in q for u in info.get('uses',[])):
            warnings_str = '; '.join(info.get('warnings',[])) or 'None listed'
            alts_str     = ', '.join(info.get('alternatives',[])) or 'None listed'
            return jsonify({
                "answer": (
                    f"**{name.replace('_',' ').title()}** — *{info['category']}*\n\n"
                    f"**Uses:** {', '.join(info['uses'])}\n\n"
                    f"**Dosage:** {info['dosage']}\n\n"
                    f"**Alternatives:** {alts_str}\n\n"
                    f"**⚠ Warnings:** {warnings_str}"
                ),
                "reasoning": ["Matched medicine in knowledge base."]
            })
    return jsonify(resp)

# ── Translation ───────────────────────────────────────────────────────────────
TAMIL_MAP = {
    # Severity
    "Normal":"சாதாரண","Moderate":"மிதமான","High":"அதிக","Critical":"அவசர நிலை",
    "No evidence of":"காணப்படவில்லை","noted":"கவனிக்கப்பட்டது","present":"உள்ளது",
    "urgent":"அவசரமாக","recommended":"பரிந்துரைக்கப்படுகிறது",
    # Anatomy
    "lung":"நுரையீரல்","chest":"மார்பு","heart":"இதயம்","brain":"மூளை",
    "kidney":"சிறுநீரகம்","liver":"கல்லீரல்","spine":"முதுகெலும்பு",
    "bone":"எலும்பு","abdomen":"வயிறு","dental":"பல் மருத்துவம்",
    "right":"வலது","left":"இடது","lower":"கீழ்","upper":"மேல்","lobe":"மடல்",
    # Findings
    "Pneumonia":"நிமோனியா","fracture":"எலும்பு முறிவு","infection":"தொற்று",
    "consolidation":"நுரையீரல் திடமாதல்","pleural effusion":"நுரையீரல் தண்ணீர் தேக்கம்",
    "cardiomegaly":"இதய விரிவாக்கம்","pneumothorax":"நுரையீரல் சரிவு",
    "ischemic stroke":"இரத்த ஓட்ட பக்கவாதம்","hemorrhage":"இரத்த கசிவு",
    "tumor":"கட்டி","tuberculosis":"காசநோய்","osteoporosis":"எலும்பு வலுவிழப்பு",
    "appendicitis":"குடல்வால் வீக்கம்","diabetes":"நீரிழிவு நோய்",
    "hypertension":"உயர் இரத்த அழுத்தம்","scoliosis":"முதுகெலும்பு வளைவு",
    "abscess":"சீழ் கட்டி","calculus":"கற்கள்","caries":"பல் சிதைவு",
    # Clinical Actions
    "Follow-up":"தொடர் கண்காணிப்பு","Consult":"ஆலோசிக்கவும்",
    "treatment":"சிகிச்சை","specialist":"நிபுணர்","Impression":"முடிவு",
    "Antibiotic":"நுண்ணுயிர் எதிர்ப்பு மருந்து","therapy":"சிகிச்சை",
    "Monitor":"கண்காணிக்கவும்","oxygen saturation":"ஆக்சிஜன் அளவு",
    "consultation":"ஆலோசனை","surgery":"அறுவை சிகிச்சை",
    "referral":"பரிந்துரை","Urgent":"அவசரம்",
    # General
    "There is":"இங்கே","no improvement":"முன்னேற்றம் இல்லை","weeks":"வாரங்கள்",
    "daily":"தினமும்","pain":"வலி","swelling":"வீக்கம்","fever":"காய்ச்சல்",
}

@app.route('/api/translate', methods=['POST'])
def translate_report():
    data = request.json or {}
    text = data.get('text','')
    if not text:
        return jsonify({"translated":"","language":"Tamil"})
    result = text
    sorted_keys = sorted(TAMIL_MAP.keys(), key=len, reverse=True)
    count = 0
    for eng in sorted_keys:
        tam = TAMIL_MAP[eng]
        pattern = re.compile(r'\b' + re.escape(eng) + r'\b', re.IGNORECASE)
        new_r = pattern.sub(tam, result)
        if new_r != result:
            count += 1
        result = new_r
    if count == 0:
        result = "[Tamil Translation] " + text
    return jsonify({"translated": result, "language":"Tamil", "terms_translated": count})

@app.route('/api/translate-tanglish', methods=['POST'])
def translate_tanglish():
    data = request.json or {}
    text = data.get('text','')
    if not text:
        return jsonify({"translated":"","language":"Tanglish"})
    result = text
    sorted_keys = sorted(TAMIL_MAP.keys(), key=len, reverse=True)
    count  = 0
    for eng in sorted_keys:
        tam = TAMIL_MAP[eng]
        pattern = re.compile(r'\b' + re.escape(eng) + r'\b', re.IGNORECASE)
        def replace_tanglish(m):
            return f"{m.group(0)} ({tam})"
        new_r, n = pattern.subn(replace_tanglish, result)
        count += n
        result = new_r
    if count == 0:
        result = "[Tanglish Translation] " + text
    return jsonify({"translated": result, "language":"Tanglish", "terms_translated": count})

if __name__ == '__main__':
    # To share on local Wi-Fi, visit http://<your-ip>:5000
    app.run(host='0.0.0.0', debug=True, port=5000)
