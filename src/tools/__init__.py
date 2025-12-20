"""
Tools for LangGraph Workflow
Eligibility Engine and Application API
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class EligibilityTool:
    """
    Tool 1: Eligibility Engine
    Checks user eligibility for government schemes
    """
    
    def __init__(self, schemes_db_path: str = 'data/schemes_hindi.json'):
        self.schemes_db_path = schemes_db_path
        self.schemes = self._load_schemes()
        logger.info(f"Eligibility Tool initialized with {len(self.schemes)} schemes")
    
    def _load_schemes(self) -> List[Dict]:
        """Load schemes from database"""
        try:
            path = Path(self.schemes_db_path)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('schemes', [])
            else:
                logger.warning(f"Schemes DB not found: {path}")
                return self._get_default_schemes()
        except Exception as e:
            logger.error(f"Error loading schemes: {e}")
            return self._get_default_schemes()
    
    def _get_default_schemes(self) -> List[Dict]:
        """Default schemes if DB not available"""
        return [
            {
                'id': 'PM_KISAN',
                'name_hindi': 'पीएम-किसान',
                'name_english': 'PM-KISAN',
                'description_hindi': 'किसानों के लिए वित्तीय सहायता',
                'benefits': 'सालाना 6000 रुपये',
                'eligibility': {
                    'occupation': ['farmer', 'agriculture'],
                    'min_age': 18,
                    'max_income': 200000
                }
            }
        ]
    
    def execute(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute eligibility check
        
        Args:
            user_profile: User profile data
            
        Returns:
            Eligible and ineligible schemes
        """
        logger.info("[TOOL] Executing eligibility check")
        
        eligible = []
        ineligible = []
        
        for scheme in self.schemes:
            result = self._check_scheme(scheme, user_profile)
            
            if result['eligible']:
                eligible.append({**scheme, 'eligible': True, 'reasons': result['reasons']})
            else:
                ineligible.append({**scheme, 'eligible': False, 'reasons': result['reasons']})
        
        logger.info(f"[TOOL] Found {len(eligible)} eligible schemes")
        
        return {
            'eligible_schemes': eligible,
            'ineligible_schemes': ineligible,
            'total_checked': len(self.schemes)
        }
    
    def _check_scheme(self, scheme: Dict, profile: Dict) -> Dict:
        """Check if profile matches scheme eligibility"""
        eligibility = scheme.get('eligibility', {})
        is_eligible = True
        reasons = []
        
        # Check age
        if 'min_age' in eligibility:
            if profile.get('age') is None or profile['age'] < eligibility['min_age']:
                is_eligible = False
                reasons.append(f"उम्र {eligibility['min_age']} से अधिक होनी चाहिए")
        
        if 'max_age' in eligibility:
            if profile.get('age') is None or profile['age'] > eligibility['max_age']:
                is_eligible = False
                reasons.append(f"उम्र {eligibility['max_age']} से कम होनी चाहिए")
        
        # Check income
        if 'max_income' in eligibility:
            if profile.get('income') is None or profile['income'] > eligibility['max_income']:
                is_eligible = False
                reasons.append(f"आय {eligibility['max_income']} से कम होनी चाहिए")
        
        # Check gender
        if 'gender' in eligibility:
            if profile.get('gender') != eligibility['gender']:
                is_eligible = False
                reasons.append(f"लिंग {eligibility['gender']} होना चाहिए")
        
        # Check category
        if 'category' in eligibility:
            categories = eligibility['category'] if isinstance(eligibility['category'], list) else [eligibility['category']]
            if profile.get('category') not in categories:
                is_eligible = False
                reasons.append(f"श्रेणी {', '.join(categories)} में होनी चाहिए")
        
        # Check occupation
        if 'occupation' in eligibility:
            occupations = eligibility['occupation'] if isinstance(eligibility['occupation'], list) else [eligibility['occupation']]
            if profile.get('occupation') not in occupations:
                is_eligible = False
                reasons.append(f"व्यवसाय {', '.join(occupations)} होना चाहिए")
        
        # Check student status
        if 'is_student' in eligibility:
            if profile.get('is_student') != eligibility['is_student']:
                is_eligible = False
                if eligibility['is_student']:
                    reasons.append("छात्र होना चाहिए")
        
        # Check disability
        if 'has_disabilities' in eligibility:
            if profile.get('has_disabilities') != eligibility['has_disabilities']:
                is_eligible = False
                if eligibility['has_disabilities']:
                    reasons.append("विकलांगता होनी चाहिए")
        
        # Check marital status
        if 'marital_status' in eligibility:
            if profile.get('marital_status') != eligibility['marital_status']:
                is_eligible = False
                reasons.append(f"वैवाहिक स्थिति {eligibility['marital_status']} होनी चाहिए")
        
        if is_eligible:
            reasons = ['सभी पात्रता शर्तें पूरी होती हैं']
        
        return {'eligible': is_eligible, 'reasons': reasons}


class ApplicationTool:
    """
    Tool 2: Application API
    Submits applications to mock government portal
    """
    
    def __init__(self):
        self.applications = []
        logger.info("Application Tool initialized")
    
    def execute(self, scheme_id: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute application submission
        
        Args:
            scheme_id: ID of scheme to apply for
            user_profile: User profile data
            
        Returns:
            Application result with ID
        """
        logger.info(f"[TOOL] Submitting application for scheme: {scheme_id}")
        
        # Create application
        application = {
            'application_id': f"APP_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'scheme_id': scheme_id,
            'user_profile': user_profile,
            'status': 'submitted',
            'timestamp': datetime.now().isoformat(),
            'estimated_processing_days': 15
        }
        
        self.applications.append(application)
        
        logger.info(f"[TOOL] Application submitted: {application['application_id']}")
        
        return application
    
    def get_status(self, application_id: str) -> Dict[str, Any]:
        """Get application status"""
        for app in self.applications:
            if app['application_id'] == application_id:
                return app
        
        return {'error': 'Application not found'}
    
    def list_applications(self) -> List[Dict[str, Any]]:
        """List all applications"""
        return self.applications
