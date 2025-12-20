"""
Hindi Prompts for LLM
All prompts are in Hindi and request structured JSON responses
"""

INTENT_CLASSIFICATION_PROMPT = """
आप एक भारतीय सरकारी योजना सहायक हैं।

उपयोगकर्ता का कथन: "{user_input}"

कृपया निम्नलिखित में से उपयोगकर्ता का इरादा (intent) पहचानें:
1. "find_schemes" - योजनाएं खोजना
2. "apply_scheme" - योजना के लिए आवेदन करना
3. "check_eligibility" - पात्रता जांचना
4. "provide_info" - जानकारी प्रदान करना
5. "clarify_doubt" - संदेह स्पष्ट करना

JSON प्रारूप में प्रतिक्रिया दें:
{{
    "intent": "<पहचानी गई intent>",
    "confidence": <0.0 से 1.0>,
    "reasoning": "<कारण>",
    "alternatives": ["<अन्य संभावित intent>"]
}}
"""

INFORMATION_EXTRACTION_PROMPT = """
आप एक भारतीय सरकारी योजना सहायक हैं।

उपयोगकर्ता का कथन:
"{user_input}"

कार्य:
केवल वही जानकारी निकालें जो उपयोगकर्ता ने स्पष्ट रूप से कही हो।
कोई अनुमान, उदाहरण या व्याख्या न करें।

⚠️ अत्यंत महत्वपूर्ण नियम:
1. केवल वैध JSON लौटाएं
2. कोई Markdown, ```json```, उदाहरण या अतिरिक्त टेक्स्ट न लिखें
3. यदि कोई जानकारी नहीं दी गई है, तो उसका मान null रखें
4. extracted_fields में केवल वही फ़ील्ड डालें जो उपयोगकर्ता ने स्पष्ट रूप से बताए हों
5. यदि कोई फ़ील्ड स्पष्ट नहीं है, तो उसे extracted_fields में न डालें

निकाली जाने वाली जानकारी:
- age
- annual_income
- gender
- category
- state
- occupation

JSON प्रारूप (इसी क्रम में):
{{
  "confidence": 0.0,
  "extracted_fields": [],
  "age": null,
  "annual_income": null,
  "gender": null,
  "category": null,
  "state": null,
  "occupation": null
}}
"""



CONTRADICTION_DETECTION_PROMPT = """
आप एक भारतीय सरकारी योजना सहायक हैं।

पहले कहा गया: {previous_info}
अब कहा गया: {current_input}

क्या यहाँ कोई विरोधाभास है? यदि हाँ, तो क्या स्पष्टीकरण आवश्यक है?

JSON प्रारूप में प्रतिक्रिया दें:
{{
    "is_contradiction": <true/false>,
    "should_clarify": <true/false>,
    "fields_conflicted": ["<विरोधाभास वाली फील्ड>"],
    "clarification_question": "<स्पष्टीकरण प्रश्न या null>",
    "reasoning": "<विश्लेषण>"
}}
"""

RESPONSE_GENERATION_PROMPT = """
आप एक सहानुभूतिपूर्ण भारतीय सरकारी योजना सहायक हैं।

संदर्भ:
- उपयोगकर्ता का प्रश्न: "{user_question}"
- वर्तमान प्रोफाइल: {user_profile}
- अगला कदम: {next_action}
- पात्र योजनाएं (यदि कोई हों): {eligible_schemes}

निर्देश (अत्यंत महत्वपूर्ण):
1. यदि पात्र योजनाएं उपलब्ध हैं (सूची खाली नहीं है),
   तो आपको योजना का नाम और संक्षिप्त विवरण अनिवार्य रूप से बताना होगा।
2. केवल सामान्य या धन्यवाद वाला उत्तर स्वीकार्य नहीं है।
3. यदि कोई योजना उपलब्ध नहीं है और जानकारी अधूरी है,
   तो आवश्यक जानकारी स्पष्ट रूप से पूछें।
4. प्रतिक्रिया 2–4 वाक्यों में, स्पष्ट और उपयोगी हो।

JSON प्रारूप में प्रतिक्रिया दें:
{{
    "response": "<हिंदी में स्पष्ट उत्तर>",
    "tone": "पेशेदार/मैत्रीपूर्ण/उदार",
    "includes_scheme": <true/false>,
    "includes_clarification": <true/false>
}}
"""


EVALUATION_PROMPT = """
आप एक भारतीय सरकारी योजना सहायक हैं।

वर्तमान उपयोगकर्ता प्रोफाइल:
{user_profile}

कृपया निम्नलिखित का मूल्यांकन करें:
1. क्या प्रोफाइल पूर्ण है?
2. कौन सी जानकारी अभी भी आवश्यक है?
3. अगला कदम क्या होना चाहिए?

JSON प्रारूप में प्रतिक्रिया दें:
{{
    "profile_complete": <true/false>,
    "missing_fields": ["<अभी भी आवश्यक फील्ड>"],
    "can_proceed_with_search": <true/false>,
    "next_step": "ask_for_info/search_schemes/apply_scheme/clarify_contradiction",
    "reasoning": "<मूल्यांकन विवरण>"
}}
"""

# Quick-reference mapping
PROMPTS = {
    'intent_classification': INTENT_CLASSIFICATION_PROMPT,
    'information_extraction': INFORMATION_EXTRACTION_PROMPT,
    'contradiction_detection': CONTRADICTION_DETECTION_PROMPT,
    'response_generation': RESPONSE_GENERATION_PROMPT,
    'evaluation': EVALUATION_PROMPT,
}


def get_prompt(prompt_type: str, **kwargs) -> str:
    """
    Get formatted prompt
    
    Args:
        prompt_type: Type of prompt needed
        **kwargs: Variables to interpolate into prompt
        
    Returns:
        Formatted prompt string
    """
    if prompt_type not in PROMPTS:
        raise ValueError(f"Unknown prompt type: {prompt_type}")
    
    prompt = PROMPTS[prompt_type]
    return prompt.format(**kwargs)
