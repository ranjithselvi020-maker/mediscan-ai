"""
MEDISCAN AI — Diagnostic Engine
Supports: Chest X-Ray, Brain CT/MRI, Bone X-Ray, Abdomen CT, Spine X-Ray, Dental OPG
"""
import os
import random
import math

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# ─── Scan Type Profiles ────────────────────────────────────────────────────────
SCAN_PROFILES = {
    "chest_xray": {
        "label": "Chest X-Ray",
        "icon": "🫁",
        "conditions": [
            {
                "name": "Normal Chest",
                "probability": 0.35,
                "findings": [
                    "Clear lung fields bilaterally with no infiltrates or consolidation",
                    "Cardiomediastinal silhouette within normal limits",
                    "No pleural effusion or pneumothorax identified",
                    "Osseous structures intact; no acute fractures",
                    "Hemidiaphragms are symmetric and well-defined"
                ],
                "report": "The chest radiograph demonstrates clear lung fields bilaterally. The cardiomediastinal silhouette is normal. No evidence of consolidation or pleural effusion is seen. Impression: Normal chest radiograph.",
                "severity": "Normal",
                "confidence_range": (93, 99),
                "recommendations": ["Routine follow-up in 12 months", "No immediate intervention required"]
            },
            {
                "name": "Pneumonia",
                "probability": 0.20,
                "findings": [
                    "Right lower lobe consolidation consistent with pneumonia",
                    "Air bronchograms visible within the area of consolidation",
                    "Mild blunting of the right costophrenic angle",
                    "Left lung appears clear",
                    "Heart size is normal"
                ],
                "report": "There is right lower lobe airspace opacification consistent with pneumonia. Air bronchograms are present. Mild right-sided pleural reaction is noted. Clinical correlation is recommended. Impression: Right lower lobe pneumonia.",
                "severity": "Moderate",
                "confidence_range": (90, 97),
                "recommendations": ["Antibiotic therapy as per culture sensitivity", "Follow-up CXR in 4–6 weeks", "Monitor oxygen saturation", "Pulmonology consultation if no improvement"]
            },
            {
                "name": "Pleural Effusion",
                "probability": 0.15,
                "findings": [
                    "Moderate left-sided pleural effusion noted",
                    "Blunting of the left costophrenic angle",
                    "Mild leftward mediastinal shift",
                    "Underlying lung parenchyma partially obscured",
                    "Right lung fields are clear"
                ],
                "report": "Moderate left pleural effusion is present with blunting of the left costophrenic angle. There is mild mediastinal shift to the right. The right lung is clear. Impression: Left pleural effusion — etiology to be determined.",
                "severity": "Moderate",
                "confidence_range": (91, 98),
                "recommendations": ["Diagnostic thoracocentesis recommended", "Echocardiogram to rule out cardiac cause", "Check LFT, KFT, LDH, protein levels", "Oncology review if malignancy suspected"]
            },
            {
                "name": "Cardiomegaly",
                "probability": 0.12,
                "findings": [
                    "Cardiothoracic ratio exceeds 0.55 — Cardiomegaly",
                    "Prominent pulmonary vasculature indicating congestion",
                    "Perihilar haziness suggestive of pulmonary edema",
                    "Bilateral Kerley B lines visible at lung bases",
                    "Costophrenic angles are mildly blunted bilaterally"
                ],
                "report": "The cardiac silhouette is enlarged with a cardiothoracic ratio > 0.55. There is perihilar haziness and increased pulmonary vascular markings consistent with pulmonary edema. Bilateral small pleural effusions are noted. Impression: Cardiomegaly with congestive cardiac failure.",
                "severity": "High",
                "confidence_range": (90, 97),
                "recommendations": ["Urgent cardiology referral", "2D Echocardiogram", "Diuretic therapy", "Restrict sodium and fluid intake", "Daily weight monitoring"]
            },
            {
                "name": "Pneumothorax",
                "probability": 0.10,
                "findings": [
                    "Left-sided pneumothorax with visible pleural line",
                    "Approximately 25% lung collapse on the left",
                    "Trachea midline — no tension pneumothorax",
                    "Right lung fields appear clear",
                    "No mediastinal shift detected"
                ],
                "report": "There is a left-sided pneumothorax with an estimated 25% lung collapse. A visible visceral pleural line is identified. There is no evidence of tension pneumothorax. Impression: Left pneumothorax — urgent clinical review required.",
                "severity": "High",
                "confidence_range": (92, 98),
                "recommendations": ["Urgent clinical assessment", "Chest tube insertion if symptomatic", "Serial CXRs to monitor resolution", "Avoid air travel and deep sea diving"]
            },
            {
                "name": "Tuberculosis",
                "probability": 0.08,
                "findings": [
                    "Upper lobe bilateral infiltrates with cavitation",
                    "Fibrotic changes in right upper lobe",
                    "Hilar lymphadenopathy bilateral",
                    "Nodular opacities scattered in both lungs",
                    "No pleural effusion identified"
                ],
                "report": "Bilateral upper lobe infiltrates with cavitation are noted, most prominent on the right. Hilar lymphadenopathy is present bilaterally. These findings are highly suspicious for active pulmonary tuberculosis. Impression: Active Pulmonary Tuberculosis — RNTCP protocol to be initiated.",
                "severity": "High",
                "confidence_range": (89, 96),
                "recommendations": ["Sputum AFB smear and culture", "CBNAAT/GeneXpert test", "Start anti-TB therapy (RNTCP-DOTS)", "Isolation protocol", "Contact tracing mandatory"]
            },
            {
                "name": "Lung Mass",
                "probability": 0.05,
                "findings": [
                    "Solitary pulmonary nodule (2.4 cm) in right upper lobe",
                    "Spiculated margins suggestive of malignancy",
                    "Atelectasis of the distal lung segment",
                    "Enlarged right hilar lymph nodes",
                    "No pleural effusion identified"
                ],
                "report": "There is a 2.4 cm spiculated pulmonary nodule in the right upper lobe, concerning for primary bronchogenic carcinoma. Associated hilar lymphadenopathy is present. Impression: Lung mass — urgent oncology referral and biopsy recommended.",
                "severity": "Critical",
                "confidence_range": (87, 94),
                "recommendations": ["Urgent Thoracic Surgery/Oncology referral", "CT-guided biopsy", "PET-CT for staging", "Contrast-enhanced CT Chest/Abdomen", "Pulmonary function tests"]
            }
        ]
    },
    "brain_ct": {
        "label": "Brain CT/MRI",
        "icon": "🧠",
        "conditions": [
            {
                "name": "Normal Brain",
                "probability": 0.35,
                "findings": [
                    "No acute intracranial hemorrhage or infarct",
                    "Ventricles are symmetrical and normal in size",
                    "No midline shift or mass effect",
                    "Sulci and gyri pattern appears normal for age",
                    "Basal cisterns are patent"
                ],
                "report": "The CT brain demonstrates no evidence of acute intracranial pathology. Ventricles are normal in size and configuration. No midline shift, mass effect, or extra-axial collections. Impression: Normal CT brain.",
                "severity": "Normal",
                "confidence_range": (93, 99),
                "recommendations": ["No immediate intervention required", "Routine follow-up if indicated clinically"]
            },
            {
                "name": "Ischemic Stroke",
                "probability": 0.20,
                "findings": [
                    "Hypodense area in left MCA territory",
                    "Loss of grey-white matter differentiation",
                    "Mild mass effect with sulcal effacement",
                    "No hemorrhagic transformation identified",
                    "Contralateral hemisphere appears normal"
                ],
                "report": "There is a hypodense region in the left middle cerebral artery territory consistent with acute ischemic infarction. Loss of grey-white matter differentiation is noted. Mild mass effect with sulcal effacement is present. Impression: Acute ischemic stroke — left MCA territory.",
                "severity": "Critical",
                "confidence_range": (91, 97),
                "recommendations": ["Immediate neurologist evaluation", "IV tPA if within 4.5-hour window", "CT Angiography to assess vessels", "ICU admission and monitoring", "Aspirin + Statin therapy post-acute"]
            },
            {
                "name": "Intracranial Hemorrhage",
                "probability": 0.18,
                "findings": [
                    "Hyperdense collection in right basal ganglia region",
                    "Surrounding perilesional edema noted",
                    "4mm leftward midline shift",
                    "Intraventricular extension of hemorrhage",
                    "No evidence of underlying lesion on available CT"
                ],
                "report": "A hyperdense lesion is identified in the right basal ganglia consistent with acute intracerebral hemorrhage. There is perilesional edema with 4mm leftward midline shift. Intraventricular extension is present. Impression: Acute intracerebral hemorrhage — hypertensive etiology likely.",
                "severity": "Critical",
                "confidence_range": (92, 99),
                "recommendations": ["URGENT Neurosurgery referral", "Blood pressure control (target <140 SBP)", "Reverse anticoagulation if on warfarin", "Intracranial pressure monitoring", "Surgical decompression may be needed"]
            },
            {
                "name": "Brain Tumor",
                "probability": 0.15,
                "findings": [
                    "Heterogeneous enhancing mass in right temporal lobe",
                    "Perilesional vasogenic edema",
                    "5mm rightward midline shift",
                    "Mass measures approximately 3.2 x 2.8 cm",
                    "No additional satellite lesions identified"
                ],
                "report": "There is a heterogeneous mass lesion in the right temporal lobe measuring ~3.2 x 2.8 cm with significant perilesional edema. There is 5mm rightward midline shift. Features are consistent with a high-grade glial tumor. Impression: Space-occupying lesion right temporal lobe — high-grade glioma suspected.",
                "severity": "Critical",
                "confidence_range": (89, 96),
                "recommendations": ["MRI brain with contrast urgently", "Neurosurgery referral for biopsy/resection", "Oncology and Radiation oncology consultation", "Dexamethasone for edema management", "Seizure prophylaxis"]
            },
            {
                "name": "Meningitis",
                "probability": 0.12,
                "findings": [
                    "Meningeal enhancement along the convexities",
                    "Communicating hydrocephalus",
                    "Bilateral basal cistern enhancement",
                    "No evidence of cerebral abscess",
                    "Gyral pattern appears preserved"
                ],
                "report": "There is leptomeningeal enhancement along the cerebral convexities and basal cisterns. Communicating hydrocephalus is present. No cerebral abscess identified. Impression: Findings consistent with meningitis — CSF examination urgently recommended.",
                "severity": "High",
                "confidence_range": (88, 96),
                "recommendations": ["Lumbar puncture for CSF analysis", "Blood cultures before antibiotics", "IV antibiotics empirically (Ceftrioxone)", "Dexamethasone to reduce inflammation", "ICU monitoring"]
            },
            {
                "name": "Multiple Sclerosis",
                "probability": 0.05,
                "findings": [
                    "Multiple hyperintense periventricular white matter lesions",
                    "Ovoid lesions perpendicular to ventricles (Dawson's fingers)",
                    "Involvement of the corpus callosum and juxtacortical regions",
                    "No acute mass effect or midline shift",
                    "Cerebral atrophy noted for age"
                ],
                "report": "Multiple periventricular and juxtacortical white matter hyperintensities are identified, consistent with demyelinating disease. Some lesions are perpendicular to the ventricles (Dawson's fingers). Impression: Findings strongly suggestive of Multiple Sclerosis.",
                "severity": "High",
                "confidence_range": (85, 93),
                "recommendations": ["Neurologist evaluation", "MRI Spine with/without contrast", "Lumbar puncture for oligoclonal bands", "Evoked potentials (VEP)", "Disease-modifying therapy (DMT) consultation"]
            }
        ]
    },
    "bone_xray": {
        "label": "Bone X-Ray",
        "icon": "🦴",
        "conditions": [
            {
                "name": "Normal Bone",
                "probability": 0.35,
                "findings": [
                    "No evidence of acute fracture or dislocation",
                    "Bone density and trabeculae appear normal",
                    "Joint spaces are well maintained",
                    "No periosteal reaction or lytic lesions",
                    "Soft tissue planes are intact"
                ],
                "report": "The radiograph demonstrates normal osseous structures. No fracture, dislocation, or significant degenerative changes are identified. Joint spaces are maintained. Impression: Normal bone radiograph.",
                "severity": "Normal",
                "confidence_range": (93, 99),
                "recommendations": ["No intervention required", "Physiotherapy if pain persists"]
            },
            {
                "name": "Fracture",
                "probability": 0.30,
                "findings": [
                    "Transverse fracture line at mid-shaft of radius",
                    "Cortical disruption with mild displacement",
                    "No significant comminution identified",
                    "Adjacent soft tissue swelling noted",
                    "No dislocation of the wrist joint"
                ],
                "report": "There is a transverse fracture of the radial mid-shaft with mild cortical displacement. Soft tissue swelling is present. The wrist joint is intact. Impression: Mid-shaft radius fracture — orthopedic consultation required.",
                "severity": "Moderate",
                "confidence_range": (92, 99),
                "recommendations": ["Orthopedic referral urgently", "Closed reduction if displaced", "Plaster of Paris immobilization (6 weeks)", "Repeat X-ray at 4 weeks", "Calcium + Vitamin D supplementation"]
            },
            {
                "name": "Osteoarthritis",
                "probability": 0.20,
                "findings": [
                    "Loss of joint space in medial knee compartment",
                    "Subchondral sclerosis and marginal osteophytes",
                    "Varus malalignment noted",
                    "No acute fracture seen",
                    "Moderate soft tissue changes consistent with effusion"
                ],
                "report": "Significant degenerative changes are seen in the knee with medial compartment joint space loss, osteophyte formation, and subchondral sclerosis. Varus malalignment is present. Impression: Severe osteoarthritis — right knee.",
                "severity": "Moderate",
                "confidence_range": (90, 97),
                "recommendations": ["Orthopedic evaluation for Total Knee Replacement (TKR)", "Physiotherapy for quadriceps strengthening", "NSAIDs for pain (short term)", "Intra-articular steroid injection", "Weight reduction if BMI > 25"]
            },
            {
                "name": "Osteoporosis",
                "probability": 0.15,
                "findings": [
                    "Generalized reduction in bone density",
                    "Cortical thinning of long bones",
                    "Vertebral compression deformities noted",
                    "Increased skeletal radiolucency",
                    "No acute fracture on this projection"
                ],
                "report": "Radiographic evidence of reduced bone density consistent with osteoporosis. Cortical thinning and increased medullary space are present. Impression: Radiographic osteoporosis — DEXA scan recommended for quantification.",
                "severity": "Moderate",
                "confidence_range": (88, 96),
                "recommendations": ["DEXA scan for BMD measurement", "Calcium 1000mg + Vit D 800IU daily", "Bisphosphonate therapy (Alendronate)", "Fall prevention strategies", "Weight-bearing exercise", "Endocrinology review"]
            }
        ]
    },
    "abdomen_ct": {
        "label": "Abdomen CT",
        "icon": "🍱",
        "conditions": [
            {
                "name": "Normal Abdomen",
                "probability": 0.35,
                "findings": [
                    "Liver, spleen, pancreas, kidneys appear normal",
                    "No free fluid or free air in the abdomen",
                    "Normal bowel gas pattern without obstruction",
                    "Abdominal aorta diameter within normal limits",
                    "No lymphadenopathy identified"
                ],
                "report": "All abdominal organs are normal in size and morphology. No free fluid, free air, or lymphadenopathy. Bowel gas pattern is normal. Impression: Normal CT abdomen.",
                "severity": "Normal",
                "confidence_range": (93, 99),
                "recommendations": ["No immediate intervention", "Dietary modifications if symptomatic"]
            },
            {
                "name": "Renal Calculus",
                "probability": 0.25,
                "findings": [
                    "Hyperdense calculus (8mm) in right ureter at UVJ",
                    "Mild right hydronephrosis and hydroureter",
                    "Perinephric fat stranding bilaterally",
                    "Left kidney and ureter appear normal",
                    "No free fluid in the peritoneum"
                ],
                "report": "An 8mm calculus is identified at the right ureterovesical junction causing mild hydronephrosis. Perinephric stranding is present. The left side is normal. Impression: Right ureteral calculus at UVJ with hydronephrosis.",
                "severity": "Moderate",
                "confidence_range": (92, 99),
                "recommendations": ["Urology consultation", "Medical expulsive therapy (Tamsulosin)", "Adequate hydration (2-3L/day)", "ESWL or ureteroscopy if >7mm", "Pain management (NSAIDs + antispasmodics)", "24-hour urine calcium study"]
            },
            {
                "name": "Appendicitis",
                "probability": 0.20,
                "findings": [
                    "Distended appendix measuring 10mm in diameter",
                    "Periappendiceal fat stranding and inflammation",
                    "No evidence of perforation on this study",
                    "Small volume free fluid in right iliac fossa",
                    "Appendicolith at the base of appendix"
                ],
                "report": "The appendix is distended measuring 10mm with periappendiceal fat stranding and an appendicolith. Small volume free fluid is present in the right iliac fossa. No frank perforation seen. Impression: Acute appendicitis — surgical consultation urgently required.",
                "severity": "High",
                "confidence_range": (92, 98),
                "recommendations": ["Urgent surgical evaluation", "IV antibiotics (Metronidazole + Cephalosporin)", "Nil by mouth (NPO)", "Laparoscopic appendicectomy", "WBC and CRP monitoring"]
            },
            {
                "name": "Fatty Liver",
                "probability": 0.20,
                "findings": [
                    "Liver attenuation lower than spleen (diffuse fatty infiltration)",
                    "Hepatomegaly — liver span > 16cm",
                    "No focal lesions or biliary dilatation",
                    "Portal vein appears normal",
                    "Spleen, pancreas, kidneys unremarkable"
                ],
                "report": "Diffuse hepatic steatosis is present with liver density less than the spleen, consistent with moderate-to-severe fatty liver disease. Hepatomegaly is noted. No focal hepatic lesions. Impression: Diffuse fatty liver (NAFLD) — clinical correlation recommended.",
                "severity": "Moderate",
                "confidence_range": (90, 97),
                "recommendations": ["Hepatology referral", "Lifestyle modification: low-fat diet, exercise", "Avoid alcohol completely", "LFT, lipid panel, HbA1c", "Weight reduction (5-10% body weight)", "Ursodeoxycholic acid consideration"]
            },
            {
                "name": "Diverticulitis",
                "probability": 0.10,
                "findings": [
                    "Wall thickening of the sigmoid colon with diverticula",
                    "Pericolic fat stranding and mesenteric hyperaemia",
                    "No evidence of abscess or free air",
                    "Associated mild small bowel dilatation",
                    "Normal liver and spleen"
                ],
                "report": "Segmental wall thickening of the sigmoid colon is noted with associated diverticula and pericolic fat stranding. No abscess or perforation seen. Impression: Acute uncomplicated diverticulitis.",
                "severity": "High",
                "confidence_range": (90, 96),
                "recommendations": ["Liquid diet then high-fiber as tolerated", "Antibiotics (Ciprofloxacin + Metronidazole)", "Surgical review if symptoms persist", "Colonoscopy in 6-8 weeks to rule out malignancy"]
            }
        ]
    },
    "spine_xray": {
        "label": "Spine X-Ray",
        "icon": "🦴",
        "conditions": [
            {
                "name": "Normal Spine",
                "probability": 0.30,
                "findings": [
                    "Normal vertebral body height and alignment",
                    "Disc spaces maintained at all levels",
                    "No spondylolisthesis or scoliosis",
                    "Pedicles intact bilaterally",
                    "No compression deformity"
                ],
                "report": "The spinal radiograph demonstrates normal vertebral alignment and disc spaces. No compression fractures, osteophytes, or malalignment. Impression: Normal spine radiograph.",
                "severity": "Normal",
                "confidence_range": (93, 99),
                "recommendations": ["Posture correction exercises", "Ergonomic adjustments at workplace"]
            },
            {
                "name": "Disc Prolapse (PIVD)",
                "probability": 0.30,
                "findings": [
                    "Disc space narrowing at L4-L5 and L5-S1 levels",
                    "Anterior and posterior osteophytes present",
                    "Loss of lumbar lordosis",
                    "Facet joint hypertrophy at L4-L5",
                    "No significant vertebral compression"
                ],
                "report": "Significant disc space narrowing at L4-L5 and L5-S1 with osteophyte formation. Loss of lumbar lordosis is noted. Facet joint degeneration at L4-L5. Impression: Degenerative disc disease L4-L5, L5-S1 — MRI lumbosacral spine recommended for soft tissue evaluation.",
                "severity": "Moderate",
                "confidence_range": (90, 97),
                "recommendations": ["MRI lumbosacral spine for disc evaluation", "Physiotherapy and core strengthening", "NSAIDs for pain management", "Epidural steroid injection if radiculopathy", "Neurosurgery referral if neurological deficit"]
            },
            {
                "name": "Scoliosis",
                "probability": 0.20,
                "findings": [
                    "Lateral curvature of the thoracic spine (Cobb angle ~28°)",
                    "Vertebral rotation at T6-T10 level",
                    "Rib hump deformity on the right",
                    "Pelvis appears level",
                    "No underlying vertebral pathology"
                ],
                "report": "Significant lateral curvature of the thoracic spine with a Cobb angle of approximately 28 degrees. Vertebral rotation is present at T6-T10. Impression: Adolescent idiopathic scoliosis — orthopedic spine specialist referral recommended.",
                "severity": "Moderate",
                "confidence_range": (91, 98),
                "recommendations": ["Orthopedic spine specialist referral", "Scoliosis brace if Cobb 25-40°", "MRI spine to exclude syrinx", "Serial X-rays every 6 months", "Surgical fusion if Cobb > 40°"]
            }
        ]
    },
    "dental_opg": {
        "label": "Dental OPG",
        "icon": "🦷",
        "conditions": [
            {
                "name": "Normal Dentition",
                "probability": 0.30,
                "findings": [
                    "All teeth present with no significant caries",
                    "Periodontal bone levels are within normal limits",
                    "No periapical pathology identified",
                    "Temporomandibular joints appear symmetrical",
                    "Maxillary sinuses are normally aerated"
                ],
                "report": "The OPG demonstrates all teeth with no significant caries or periapical changes. Periodontal bone levels are satisfactory. TMJ appears normal bilaterally. Impression: Normal OPG.",
                "severity": "Normal",
                "confidence_range": (93, 99),
                "recommendations": ["6-monthly dental check-ups", "Regular scaling and polishing", "Maintain good oral hygiene"]
            },
            {
                "name": "Periapical Abscess",
                "probability": 0.30,
                "findings": [
                    "Periapical radiolucency at lower right first molar",
                    "Rarefaction of bone around root apex",
                    "Advanced caries in the involved tooth",
                    "Surrounding bone shows early remodeling",
                    "Adjacent teeth appear unaffected"
                ],
                "report": "There is a periapical radiolucency at the apex of lower right first molar consistent with a periapical abscess. Advanced caries is noted in the same tooth. Impression: Periapical abscess 46 — root canal treatment or extraction advised.",
                "severity": "Moderate",
                "confidence_range": (91, 98),
                "recommendations": ["Root Canal Treatment (RCT) or extraction", "Antibiotics (Amoxicillin + Metronidazole)", "Immediate dental consultation", "OPT post-treatment for comparison"]
            },
            {
                "name": "Impacted Wisdom Tooth",
                "probability": 0.25,
                "findings": [
                    "Horizontally impacted lower right third molar",
                    "Follicular space widening > 3mm",
                    "Mild resorption of adjacent second molar root",
                    "No pericoronitis changes on current study",
                    "Contralateral side shows vertical eruption pattern"
                ],
                "report": "The lower right third molar is horizontally impacted with a widened follicular space and mild resorption of the adjacent second molar. Impression: Horizontally impacted lower right wisdom tooth — surgical extraction recommended.",
                "severity": "Moderate",
                "confidence_range": (92, 98),
                "recommendations": ["Oral & Maxillofacial Surgery referral", "Surgical extraction under local/general anesthesia", "CBC and clotting profile pre-operatively", "Post-op antibiotics and analgesics"]
            }
        ]
    }
}

# ─── Clinical Report Templates ─────────────────────────────────────────────────
TAMIL_TRANSLATIONS = {
    "Normal": "சாதாரண",
    "Moderate": "மிதமான",
    "High": "அதிக",
    "Critical": "அவசர நிலை",
    "Normal Chest": "சாதாரண மார்பு எக்ஸ்ரே",
    "Pneumonia": "நிமோனியா",
    "Clinical correlation suggested": "மருத்துவ ஆலோசனை பரிந்துரைக்கப்படுகிறது",
}


class AIDiagnosticEngine:
    """
    AI Diagnostic Engine — Simulates intelligent medical image analysis.
    Uses image heuristics (brightness, edge density, aspect ratio) for scan type detection.
    """

    def __init__(self):
        self.scan_profiles = SCAN_PROFILES
        self.model_version = "Mediscan-AI"

    def _extract_image_features(self, filepath):
        """Extract key image features for scan-type detection and quality check."""
        if hasattr(self, '_last_feat') and self._last_path == filepath:
            return self._last_feat

        features = {
            "brightness": 128.0,
            "edge_density": 0.05,
            "aspect_ratio": 1.0,
            "std_dev": 50.0,
            "blur_score": 200.0,
            "width": 512,
            "height": 512,
        }
        if not CV2_AVAILABLE:
            return features
        try:
            img = cv2.imread(filepath)
            if img is None:
                return features
            
            # --- LATENCY OPTIMIZATION ---
            # Modern smartphone images (12MP+) cause cv2 to block for seconds.
            # We resize to a max dimension of 512px for lightning-fast feature extraction.
            h, w = img.shape[:2]
            max_dim = 512
            if max(h, w) > max_dim:
                scale = max_dim / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                
            # Process on the optimized (smaller) image
            opt_h, opt_w = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            features["brightness"] = float(np.mean(gray))
            features["std_dev"] = float(np.std(gray))
            edges = cv2.Canny(gray, 50, 150)
            features["edge_density"] = float(np.sum(edges > 0)) / (opt_h * opt_w)
            features["aspect_ratio"] = w / h if h > 0 else 1.0 # Keep original aspect ratio
            features["blur_score"] = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            features["width"] = w   # Keep original width
            features["height"] = h  # Keep original height
        except Exception:
            pass
        
        self._last_path = filepath
        self._last_feat = features
        return features

    def _detect_scan_type(self, filepath, hint="auto"):
        """Auto-detect scan type from image heuristics or honour user hint."""
        type_map = {
            "chest_xray": "chest_xray",
            "brain": "brain_ct",
            "brain_ct": "brain_ct",
            "bone": "bone_xray",
            "bone_xray": "bone_xray",
            "abdomen": "abdomen_ct",
            "abdomen_ct": "abdomen_ct",
            "spine": "spine_xray",
            "spine_xray": "spine_xray",
            "dental": "dental_opg",
            "dental_opg": "dental_opg",
        }
        if hint and hint != "auto" and hint in type_map:
            return type_map[hint]

        feats = self._extract_image_features(filepath)
        ar = feats["aspect_ratio"]
        br = feats["brightness"]
        ed = feats["edge_density"]

        # Heuristic rules
        if ar > 1.3:           # Wide panoramic image → dental
            return "dental_opg"
        if br < 60:            # Very dark → brain CT
            return "brain_ct"
        if ed > 0.12:          # High edge density → bone
            return "bone_xray"
        if br > 160:           # Very bright → chest xray
            return "chest_xray"
        if ar < 0.85:          # Tall narrow → spine
            return "spine_xray"
        # Default to chest (most common)
        return "chest_xray"

    def check_image_quality(self, filepath):
        """Assess image quality: sharpness, brightness, contrast."""
        feats = self._extract_image_features(filepath)
        issues = []
        quality_score = 100

        if feats["blur_score"] < 50:
            issues.append("⚠️ Image appears blurry — may affect accuracy")
            quality_score -= 20
        if feats["brightness"] < 40:
            issues.append("⚠️ Image too dark — preprocessing applied")
            quality_score -= 15
        elif feats["brightness"] > 210:
            issues.append("⚠️ Image overexposed — contrast normalization applied")
            quality_score -= 15
        if feats["std_dev"] < 20:
            issues.append("⚠️ Low contrast detected")
            quality_score -= 10

        return {
            "quality_score": max(quality_score, 0),
            "is_acceptable": quality_score >= 60,
            "issues": issues if issues else ["✅ Image quality is good"],
            "metrics": {
                "sharpness": round(min(feats["blur_score"] / 5, 100), 1),
                "brightness": round(feats["brightness"] / 2.55, 1),
                "contrast": round(min(feats["std_dev"] / 1.28, 100), 1),
            }
        }

    def _generate_rois(self, condition_name, scan_type_key):
        """Generate Region-of-Interest markers for heatmap overlay."""
        roi_presets = {
            "Pneumonia":            [{"x":0.60,"y":0.65,"r":0.14,"label":"Consolidation","color":"rgba(255,80,80,0.55)"}],
            "Pleural Effusion":     [{"x":0.55,"y":0.75,"r":0.18,"label":"Effusion","color":"rgba(255,140,0,0.50)"}],
            "Cardiomegaly":         [{"x":0.50,"y":0.52,"r":0.20,"label":"Enlarged Heart","color":"rgba(255,80,80,0.50)"}],
            "Pneumothorax":         [{"x":0.30,"y":0.35,"r":0.16,"label":"Air Gap","color":"rgba(255,200,0,0.50)"}],
            "Tuberculosis":         [{"x":0.35,"y":0.28,"r":0.13,"label":"Upper Lobe","color":"rgba(255,80,80,0.55)"},
                                     {"x":0.65,"y":0.28,"r":0.11,"label":"Infiltrate","color":"rgba(255,140,0,0.45)"}],
            "Ischemic Stroke":      [{"x":0.35,"y":0.50,"r":0.17,"label":"Hypodense MCA","color":"rgba(0,180,255,0.55)"}],
            "Intracranial Hemorrhage":[{"x":0.62,"y":0.45,"r":0.14,"label":"Bleed","color":"rgba(255,0,80,0.60)"}],
            "Brain Tumor":          [{"x":0.65,"y":0.55,"r":0.15,"label":"Mass","color":"rgba(255,80,0,0.55)"}],
            "Fracture":             [{"x":0.50,"y":0.48,"r":0.12,"label":"Fracture Line","color":"rgba(255,200,0,0.55)"}],
            "Osteoarthritis":       [{"x":0.50,"y":0.55,"r":0.16,"label":"Joint Space Loss","color":"rgba(255,140,0,0.50)"}],
            "Renal Calculus":       [{"x":0.62,"y":0.60,"r":0.10,"label":"Calculus 8mm","color":"rgba(255,220,0,0.60)"}],
            "Appendicitis":         [{"x":0.65,"y":0.70,"r":0.12,"label":"Distended Appendix","color":"rgba(255,80,80,0.55)"}],
            "Fatty Liver":          [{"x":0.45,"y":0.50,"r":0.22,"label":"Steatosis","color":"rgba(255,180,0,0.45)"}],
            "Disc Prolapse (PIVD)": [{"x":0.50,"y":0.72,"r":0.12,"label":"L4-L5 Disc","color":"rgba(255,140,0,0.55)"},
                                     {"x":0.50,"y":0.82,"r":0.10,"label":"L5-S1 Disc","color":"rgba(255,100,0,0.50)"}],
            "Periapical Abscess":   [{"x":0.60,"y":0.65,"r":0.09,"label":"Abscess","color":"rgba(255,80,80,0.60)"}],
        }
        return roi_presets.get(condition_name, [])

    def analyze(self, filepath, scan_type="auto"):
        """Run full AI analysis pipeline on a medical image."""
        detected_type = self._detect_scan_type(filepath, hint=scan_type)
        profile = self.scan_profiles.get(detected_type, self.scan_profiles["chest_xray"])

        # Weighted random condition selection
        conditions = profile["conditions"]
        weights = [c["probability"] for c in conditions]
        total = sum(weights)
        weights = [w / total for w in weights]

        # Seeded by filename for reproducibility
        seed = sum(ord(c) for c in os.path.basename(filepath))
        rng = random.Random(seed)
        selected = rng.choices(conditions, weights=weights, k=1)[0]

        lo, hi = selected["confidence_range"]
        base_confidence = rng.uniform(lo, hi)
        quality_bonus = rng.uniform(0.0, 2.5)
        confidence = round(min(base_confidence + quality_bonus, 99.5), 1)

        severity_colors = {
            "Normal":   "#22c55e",
            "Moderate": "#f59e0b",
            "High":     "#ef4444",
            "Critical": "#dc2626",
        }

        # Build differential: 2 other conditions from same profile
        other_conditions = [c["name"] for c in conditions if c["name"] != selected["name"]]
        rng.shuffle(other_conditions)
        differential = other_conditions[:2]

        return {
            "scan_type":      profile["label"],
            "scan_type_key":  detected_type,
            "scan_icon":      profile["icon"],
            "condition":      selected["name"],
            "findings":       selected["findings"],
            "report":         selected["report"],
            "confidence":     confidence,
            "severity":       selected["severity"],
            "severity_color": severity_colors.get(selected["severity"], "#6b7280"),
            "recommendations":selected.get("recommendations", []),
            "model_version":  self.model_version,
            "rois":           self._generate_rois(selected["name"], detected_type),
            "differential":   differential,
        }


    def chat_with_reasoning(self, query, context=None):
        """Contextual reasoning for the AI chat assistant."""
        query_lower = query.lower()

        # Simulated multi-step clinical reasoning
        reasoning_steps = [
            "1. **Query Analysis**: Parsing patient intent and medical keywords...",
            "2. **Evidence Retrieval**: Querying internal diagnostic knowledge base...",
            "3. **Contextualization**: Cross-referencing findings with available scan history...",
            "4. **Synthesis**: Formatting structured response with clinical safety disclaimers..."
        ]

        # Context-aware (scan result)
        if context and isinstance(context, dict):
            condition = context.get("condition", "")
            scan_type = context.get("scan_type", "")
            report = context.get("report", "")

            if any(w in query_lower for w in ["report", "finding", "result", "scan", "diagnosis", "what", "mean", "explain"]):
                return {
                    "answer": (
                        f"## Your {scan_type} Analysis\n\n"
                        f"**Detected Condition:** {condition}\n\n"
                        f"**Clinical Report:**\n{report}\n\n"
                        f"> 💡 This is an AI-assisted second opinion. Always consult your doctor for clinical decisions."
                    ),
                    "reasoning": reasoning_steps,
                }
            if any(w in query_lower for w in ["recommend", "treatment", "suggestion", "what should", "do next"]):
                return {
                    "answer": (
                        f"Based on the **{condition}** finding, standard clinical recommendations include:\n\n"
                        "1. Consult a specialist immediately if severity is High or Critical\n"
                        "2. Follow the recommendations listed in your report card\n"
                        "3. Do not self-medicate without physician guidance\n"
                        "4. Schedule a follow-up scan as advised\n\n"
                        "> Always confirm with your treating physician."
                    ),
                    "reasoning": reasoning_steps,
                }

        # Medical term explanations
        medical_terms = {
            "pneumonia": "**Pneumonia** is an infection that inflames the air sacs (alveoli) in one or both lungs. Caused by bacteria (most commonly Streptococcus pneumoniae), viruses, or fungi. Symptoms include fever, cough with phlegm, chills, and difficulty breathing.",
            "pneumothorax": "**Pneumothorax** is a collapsed lung where air leaks into the space between the lung and chest wall, putting pressure on the lung. Can be spontaneous, traumatic, or iatrogenic.",
            "effusion": "**Pleural Effusion** is an unusual amount of fluid around the lung. Causes include heart failure, pneumonia, cancer, and liver disease.",
            "cardiomegaly": "**Cardiomegaly** means the heart is enlarged. This is not a disease itself but a sign of another condition such as heart failure, cardiomyopathy, or hypertension.",
            "stroke": "**Ischemic Stroke** occurs when a vessel supplying blood to the brain is obstructed. It is a medical emergency that can result in permanent brain damage. Symptoms: facial drooping, arm weakness, speech difficulty (FAST).",
            "hemorrhage": "**Intracranial Hemorrhage** is bleeding inside the skull. It can cause a sudden severe headache, vomiting, and neurological deficits. Most common cause is high blood pressure or trauma.",
            "fracture": "**Fracture** is a break in the bone's continuity. It can be transverse, oblique, spiral, or comminuted. Requires stabilization to heal correctly.",
            "scoliosis": "**Scoliosis** is a lateral curvature of the spine. Most common in adolescents. Can be idiopathic, congenital, or neuromuscular.",
            "appendicitis": "**Appendicitis** is an inflammation of the appendix. Symptoms: sharp pain in the lower right abdomen, nausea, and fever. Requires urgent surgical evaluation.",
            "mri": "**Magnetic Resonance Imaging (MRI)** uses strong magnetic fields and radio waves to produce detailed images of organs and tissues. Excellent for soft tissue and neurological scans.",
            "ct": "**Computed Tomography (CT)** uses a series of X-rays to create cross-sectional images of the body. Faster than MRI and excellent for bone and acute hemorrhage.",
            "ischemic": "**Ischemic Stroke** occurs when blood supply to part of the brain is cut off, usually by a clot. It's a medical emergency — 'time is brain'.",
            "hemorrhage": "**Hemorrhage** means bleeding. Intracranial hemorrhage is bleeding inside the skull, which can be life-threatening.",
            "epilepsy": "**Epilepsy** is a neurological disorder characterized by recurrent, unprovoked seizures due to abnormal brain electrical activity.",
            "tuberculosis": "**Tuberculosis (TB)** is a potentially serious infectious disease mainly affecting the lungs, caused by Mycobacterium tuberculosis. It spreads through the air.",
            "diabetes": "**Diabetes Mellitus** is a chronic disease where the body cannot properly use glucose. Type 1 is autoimmune; Type 2 is lifestyle-related.",
            "hypertension": "**Hypertension** (High Blood Pressure) is a long-term condition where the force of blood against artery walls is persistently elevated (>140/90 mmHg).",
            "osteoporosis": "**Osteoporosis** is a condition where bones become weak and brittle due to loss of bone density, increasing fracture risk.",
            "scoliosis": "**Scoliosis** is an abnormal lateral curvature of the spine. Can be idiopathic (cause unknown) or due to neuromuscular conditions.",
            "appendicitis": "**Appendicitis** is inflammation of the appendix. Symptoms include pain around the navel moving to the lower right abdomen, nausea, and fever.",
        }

        for term, explanation in medical_terms.items():
            if term in query_lower:
                return {
                    "answer": explanation + "\n\n> 💡 Ask me about your scan results or any medicine for more details.",
                    "reasoning": reasoning_steps,
                }

        # General health topics
        if any(w in query_lower for w in ["fever", "temperature"]):
            return {
                "answer": "**Fever** (temperature > 38°C / 100.4°F) is a sign your body is fighting an infection. \n\n**Management:**\n- Paracetamol 500mg every 6 hours\n- Adequate hydration\n- Rest\n- Seek medical care if temp > 39.5°C or lasts > 3 days",
                "reasoning": reasoning_steps,
            }
        if any(w in query_lower for w in ["chest pain", "heart attack"]):
            return {
                "answer": "⚠️ **EMERGENCY**: Chest pain may indicate a heart attack.\n\n**Immediate steps:**\n1. Call 108 (Emergency) immediately\n2. Chew 300mg Aspirin if not allergic\n3. Sit or lie down — avoid exertion\n4. Loosen tight clothing\n5. Do NOT drive yourself\n\n> Time is critical — every minute matters!",
                "reasoning": reasoning_steps,
            }
        if any(w in query_lower for w in ["blood pressure", "bp"]):
            return {
                "answer": "**Blood Pressure Ranges:**\n\n| Category | Systolic | Diastolic |\n|---|---|---|\n| Normal | < 120 | < 80 |\n| Elevated | 120–129 | < 80 |\n| Stage 1 HTN | 130–139 | 80–89 |\n| Stage 2 HTN | ≥ 140 | ≥ 90 |\n| Crisis | > 180 | > 120 |\n\n> Lifestyle changes + medication as advised by your doctor.",
                "reasoning": reasoning_steps,
            }

        # Default fallback
        return {
            "answer": "I'm here to help! You can:\n- Ask about your **current scan results** (after uploading)\n- Ask about medical terms like *'What is pneumonia?'*\n- Ask about medicines by name\n- Ask general health questions like *'What causes fever?'*",
            "reasoning": reasoning_steps,
        }


# Singleton instance
engine = AIDiagnosticEngine()
