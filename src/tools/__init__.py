"""
Tools for LangGraph Workflow
Eligibility Engine and Application API (FIXED)
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


# =========================
# ELIGIBILITY TOOL
# =========================

class EligibilityTool:
    """
    Tool 1: Eligibility Engine (STATE-AWARE)
    - Excludes already applied schemes
    - Gives clear rejection reasons
    """

    def __init__(self, schemes_db_path: str = 'data/schemes_hindi.json'):
        self.schemes_db_path = schemes_db_path
        self.schemes = self._load_schemes()
        logger.info(f"Eligibility Tool initialized with {len(self.schemes)} schemes")

    def _load_schemes(self) -> List[Dict]:
        try:
            path = Path(self.schemes_db_path)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f).get('schemes', [])
            else:
                logger.warning(f"Schemes DB not found: {path}")
                return self._get_default_schemes()
        except Exception as e:
            logger.error(f"Error loading schemes: {e}")
            return self._get_default_schemes()

    def _get_default_schemes(self) -> List[Dict]:
        return [
            {
                "id": "PM_KISAN",
                "name_hindi": "पीएम-किसान",
                "description_hindi": "किसानों के लिए वित्तीय सहायता",
                "benefits": "सालाना 6000 रुपये",
                "eligibility": {
                    "occupation": ["farmer", "agriculture"],
                    "min_age": 18,
                    "max_income": 200000,
                },
            }
        ]

    def execute(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[TOOL] Executing eligibility check")

        eligible = []
        ineligible = []

        applied_schemes = set(user_profile.get("applied_schemes", []))

        for scheme in self.schemes:
            # 🚫 HARD BLOCK: already applied
            if scheme["id"] in applied_schemes:
                ineligible.append({
                    **scheme,
                    "eligible": False,
                    "reasons": ["इस योजना के लिए पहले ही आवेदन किया जा चुका है"]
                })
                continue

            result = self._check_scheme(scheme, user_profile)

            if result["eligible"]:
                eligible.append({**scheme, "eligible": True, "reasons": result["reasons"]})
            else:
                ineligible.append({**scheme, "eligible": False, "reasons": result["reasons"]})

        logger.info(f"[TOOL] Found {len(eligible)} eligible schemes")

        return {
            "eligible_schemes": eligible,
            "ineligible_schemes": ineligible,
            "total_checked": len(self.schemes),
        }

    def _check_scheme(self, scheme: Dict, profile: Dict) -> Dict:
        eligibility = scheme.get("eligibility", {})
        reasons = []

        age = profile.get("age")
        income = profile.get("income")
        gender = profile.get("gender")
        occupation = profile.get("occupation")
        category = profile.get("category")

        if "min_age" in eligibility and (age is None or age < eligibility["min_age"]):
            reasons.append(f"उम्र {eligibility['min_age']} से अधिक होनी चाहिए")

        if "max_age" in eligibility and (age is None or age > eligibility["max_age"]):
            reasons.append(f"उम्र {eligibility['max_age']} से कम होनी चाहिए")

        if "max_income" in eligibility and (income is None or income > eligibility["max_income"]):
            reasons.append(f"आय {eligibility['max_income']} से कम होनी चाहिए")

        if "gender" in eligibility and gender != eligibility["gender"]:
            reasons.append(f"लिंग {eligibility['gender']} होना चाहिए")

        if "category" in eligibility:
            allowed = eligibility["category"]
            allowed = allowed if isinstance(allowed, list) else [allowed]
            if category not in allowed:
                reasons.append(f"श्रेणी {', '.join(allowed)} में होनी चाहिए")

        if "occupation" in eligibility:
            allowed = eligibility["occupation"]
            allowed = allowed if isinstance(allowed, list) else [allowed]
            if occupation not in allowed:
                reasons.append(f"व्यवसाय {', '.join(allowed)} होना चाहिए")

        if reasons:
            return {"eligible": False, "reasons": reasons}

        return {"eligible": True, "reasons": ["सभी पात्रता शर्तें पूरी होती हैं"]}


# =========================
# APPLICATION TOOL
# =========================

class ApplicationTool:
    """
    Tool 2: Application API (SAFE)
    - Prevents duplicate applications
    """

    def __init__(self):
        self.applications: List[Dict[str, Any]] = []
        logger.info("Application Tool initialized")

    def execute(self, scheme_id: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[TOOL] Submitting application for scheme: {scheme_id}")

        # 🚫 DUPLICATE CHECK
        for app in self.applications:
            if app["scheme_id"] == scheme_id:
                return {
                    "error": "already_applied",
                    "message": "इस योजना के लिए पहले ही आवेदन किया जा चुका है",
                }

        application = {
            "application_id": f"APP_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "scheme_id": scheme_id,
            "user_profile": user_profile,
            "status": "submitted",
            "timestamp": datetime.now().isoformat(),
            "estimated_processing_days": 15,
        }

        self.applications.append(application)

        logger.info(f"[TOOL] Application submitted: {application['application_id']}")
        return application

    def get_status(self, application_id: str) -> Dict[str, Any]:
        for app in self.applications:
            if app["application_id"] == application_id:
                return app
        return {"error": "Application not found"}

    def list_applications(self) -> List[Dict[str, Any]]:
        return self.applications
