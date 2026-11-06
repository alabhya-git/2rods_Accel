"""Rule-based understanding of what an owner types or says, in 10 Indian languages.

This runs on every message, LLM or not: it is fast, deterministic and catches the
numbers, IDs and rule-relevant facts reliably. An LLM, when configured, adds the
nuance on top (paraphrases, unusual business types, long free-form answers).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from ..data_store import store
from .normalise import loanword_needs

# ---- language ------------------------------------------------------------------

SCRIPT_RANGES = [
    ("pa", 0x0A00, 0x0A7F), ("gu", 0x0A80, 0x0AFF), ("bn", 0x0980, 0x09FF), ("ta", 0x0B80, 0x0BFF),
    ("te", 0x0C00, 0x0C7F), ("kn", 0x0C80, 0x0CFF), ("ml", 0x0D00, 0x0D7F), ("deva", 0x0900, 0x097F),
]
MARATHI_MARKERS = ("आहे", "आहेत", "माझ", "आमच", "करायच", "पाहिजे", "नाही", "ळ", "किती", "आणि")
HINGLISH = {"hai", "hain", "mera", "meri", "mere", "chahiye", "chaiye", "kitna", "kitne", "nahi", "nahin", "dukaan", "dukan",
            "karna", "hamara", "hamari", "humko", "mujhe", "kya", "aur", "wala", "wali", "sirf", "log", "kaam", "bhai", "ji", "theek"}


def detect_language(text: str) -> str | None:
    counts: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for code, lo, hi in SCRIPT_RANGES:
            if lo <= cp <= hi:
                counts[code] = counts.get(code, 0) + 1
    if counts:
        code = max(counts, key=counts.get)
        if code == "deva":
            return "mr" if any(m in text for m in MARATHI_MARKERS) and "है" not in text else "hi"
        return code
    words = set(re.findall(r"[a-z]+", text.lower()))
    if len(words & HINGLISH) >= 2:
        return "hi"
    return None


def normalise_digits(text: str) -> str:
    out = []
    for ch in text:
        if ch.isdigit() and not ("0" <= ch <= "9"):
            try:
                out.append(str(unicodedata.digit(ch)))
                continue
            except ValueError:
                pass
        out.append(ch)
    return "".join(out)


# ---- vocabularies ----------------------------------------------------------------

NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "fifty": 50,
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhe": 6, "che": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "दोन": 2, "पाच": 5, "सहा": 6, "आठ": 8,
}
PEOPLE = r"(?:staff|people|persons?|employees?|workers?|members?|team|log|logon|लोग|कर्मचारी|लोक|कामगार|பேர்|ஊழியர்கள்|మంది|ఉద్యోగులు|ಜನ|ಸಿಬ್ಬಂದಿ|લોકો|કર્મચારી|জন|কর্মী|പേർ|ജീവനക്കാർ|ਲੋਕ|ਕਰਮਚਾਰੀ)"
SITES = r"(?:stores?|outlets?|branch(?:es)?|sites?|locations?|shops?|gyms?|clinics?|restaurants?|hotels?|schools?|centres?|centers?|offices?|showrooms?|counters? across|दुकानें|दुकान|शाखा(?:एं|एँ)?|शाखा|ब्रांच|கிளைகள்|బ్రాంచ్లు|బ్రాంచీలు|ಶಾಖೆ|શાખા|শাখা|ശാഖ|ਸ਼ਾਖਾਵਾਂ)"
VEHICLES = r"(?:trucks?|vehicles?|vans?|cars?|bikes?|tempos?|lorries|गाड़ियां|गाड़ियाँ|ट्रक)"

BUSINESS_KEYWORDS: list[tuple[str, str, str]] = [
    # (regex, business type label, segment)
    (r"kirana|grocery|general store|provision|किराना|किराणा|மளிகை|కిరాణా|ಕಿರಾಣಿ|કરિયાણા|মুদি|പലചരക്ക്|ਕਰਿਆਨਾ", "Kirana store", "micro"),
    (r"pharmacy chain|chemist chain|medical stores", "Pharmacy chain", "multi"),
    (r"pharmacy|chemist|medical store|medicine shop|दवा|मेडिकल|मेडिकल स्टोर|फार्मेसी|மருந்தகம்|மெடிக்கல்|మెడికల్|ఫార్మసీ|ಮೆಡಿಕಲ್|ಔಷಧ|મેડિકલ|દવાની|ওষুধ|ফার্মেসি|മെഡിക്കൽ|ਮੈਡੀਕਲ|ਦਵਾਈ", "Pharmacy", "micro"),
    (r"salon|parlou?r|barber|spa\b|सैलून|पार्लर|सलून|சலூன்|அழகு நிலைய|సెలూన్|పార్లర్|ಸಲೂನ್|ಪಾರ್ಲರ್|સલૂન|પાર્લર|সেলুন|পার্লার|സലൂൺ|പാർലർ|ਸੈਲੂਨ|ਪਾਰਲਰ", "Salon", "micro"),
    (r"bakery chain|bakeries", "Bakery chain", "multi"),
    (r"bake house|bakery|बेकरी|பேக்கரி|బేకరీ|ಬೇಕರಿ|બેકરી|বেকারি|ബേക്കറി|ਬੇਕਰੀ", "Bakery", "micro"),
    (r"boutique|clothes shop|garment shop|बुटीक|कपड़े", "Boutique", "micro"),
    (r"hardware", "Hardware store", "micro"),
    (r"mobile repair|phone repair|mobile shop", "Mobile repair shop", "micro"),
    (r"optician|optical|spectacles|चश्मा", "Optician", "micro"),
    (r"stationery|xerox|photocopy", "Stationery shop", "micro"),
    (r"sweet shop|mithai|halwai|मिठाई", "Sweet shop", "micro"),
    (r"dental|dentist|डेंटल|दांत|दंत|பல் மருத்துவ|டென்டல்|డెంటల్|దంత|ಡೆಂಟಲ್|ದಂತ|ડેન્ટલ|દાંત|ডেন্টাল|দাঁত|ഡെന്റൽ|ദന്ത|ਡੈਂਟਲ|ਦੰਦ", "Dental clinic", "prof"),
    (r"physio", "Physiotherapy clinic", "prof"),
    (r"diagnostic|pathology|lab\b", "Diagnostic lab", "prof"),
    (r"\bca\b|chartered accountant|accountant|tax consultant", "CA firm", "prof"),
    (r"law office|lawyer|advocate|legal", "Law office", "prof"),
    (r"coaching|tuition|classes|institute|कोचिंग|ट्यूशन|क्लासेस|கோச்சிங்|டியூஷன்|பயிற்சி மைய|కోచింగ్|ట్యూషన్|ಕೋಚಿಂಗ್|ಟ್ಯೂಷನ್|કોચિંગ|ટ્યુશન|কোচিং|টিউশন|കോച്ചിംഗ്|ട്യൂഷൻ|ਕੋਚਿੰਗ|ਟਿਊਸ਼ਨ", "Coaching centre", "prof"),
    (r"architect", "Architecture studio", "prof"),
    (r"insurance|बीमा|इंश्योरेंस|इन्शुरन्स|विमा|காப்பீடு|இன்சூரன்ஸ்|బీమా|ఇన్సూరెన్స్|ఇన్సురెన్స్|ವಿಮೆ|ಇನ್ಶೂರೆನ್ಸ್|ಇನ್ಸೂರೆನ್ಸ್|વીમા|ઇન્શ્યોરન્સ|বিমা|ইন্স্যুরেন্স|ഇൻഷുറൻസ്|ഇൻഷൂറൻസ്|ਬੀਮਾ|ਇੰਸ਼ੋਰੈਂਸ", "Insurance agency", "prof"),
    (r"real estate|property dealer|broker|realty", "Real estate agency", "prof"),
    (r"travel agen|tours? (?:and|&) travels?|travels", "Travel agency", "prof"),
    (r"clinic|doctor|hospital|nursing home|क्लिनिक|डॉक्टर|கிளினிக்|క్లినిక్|ಕ್ಲಿನಿಕ್|ક્લિનિક|ক্লিনিক|ക്ലിനിക്|ਕਲੀਨਿਕ", "Clinic", "prof"),
    (r"office|consultan|agency|ऑफिस|दफ्तर|कार्यालय|एजेंसी|एजन्सी|அலுவலகம்|ஆபீஸ்|ஏஜென்சி|ఆఫీస్|కార్యాలయం|ఏజెన్సీ|ಕಚೇರಿ|ಆಫೀಸ್|ಏಜೆನ್ಸಿ|ઓફિસ|કાર્યાલય|એજન્સી|অফিস|কার্যালয়|এজেন্সি|ഓഫീസ്|ഏജൻസി|ਦਫ਼ਤਰ|ਦਫਤਰ|ਆਫ਼ਿਸ|ਏਜੰਸੀ", "Office", "prof"),
    (r"restaurant chain|restaurants|cafes|outlets", "Restaurant chain", "multi"),
    (r"hotel", "Budget hotel group", "multi"),
    (r"gym", "Gym chain", "multi"),
    (r"pre-?school|play ?school", "Pre-school chain", "multi"),
    (r"apparel|fashion chain|clothing chain", "Apparel retail chain", "multi"),
    (r"electronics", "Electronics retail chain", "multi"),
    (r"logistics|transport|trucks|courier|fleet", "Logistics firm", "multi"),
    (r"chain|branches|stores across", "Retail chain", "multi"),
    (r"auto.?parts?|automobile parts|spare parts unit", "Auto-parts unit", "mfg"),
    (r"food processing", "Food processing unit", "mfg"),
    (r"furniture|carpentry|woodcraft|wood work", "Furniture workshop", "mfg"),
    (r"packaging", "Packaging unit", "mfg"),
    (r"plastic|moulding|molding", "Plastic moulding unit", "mfg"),
    (r"printing press|printers|printing", "Printing press", "mfg"),
    (r"textile|weaving|garment factory|powerloom", "Textile unit", "mfg"),
    (r"factory|manufactur|plant\b|unit\b|workshop|फैक्ट्री|कारखाना|कारखान|தொழிற்சாலை|ఫ్యాక్టరీ|ಕಾರ್ಖಾನೆ|ફેક્ટરી|কারখানা|ഫാക്ടറി|ਫੈਕਟਰੀ", "Manufacturing unit", "mfg"),
    (r"restaurant|cafe|dhaba|hotel|होटल|ढाबा|रेस्टोरेंट|रेस्टॉरंट|हॉटेल|உணவகம்|ஹோட்டல்|రెస్టారెంట్|హోటల్|ಹೋಟೆಲ್|ರೆಸ್ಟೋರೆಂಟ್|રેસ્ટોરન્ટ|હોટલ|রেস্তোরাঁ|হোটেল|ഹോട്ടൽ|റെസ്റ്റോറന്റ്|ਰੈਸਟੋਰੈਂਟ|ਢਾਬਾ|ਹੋਟਲ", "Restaurant", "micro"),
    (r"shop|store|dukaan|dukan|दुकान|கடை|దుకాణం|ಅಂಗಡಿ|દુકાન|দোকান|കട|ਦੁਕਾਨ", "Shop", "micro"),
]

NEED_KEYWORDS: list[tuple[str, str]] = [
    (r"1\s?gbps|1\s?gig|gigabit|1000\s?mbps|\b1\s?g\b(?! ?b\b)", "high_speed"),
    (r"leased line|dedicated (?:line|internet)|\bill\b|99\.\d+\s?%|uptime sla|never go down|लीज्ड", "dedicated_line"),
    (r"wh?ats?\s?a+p+|वॉट्सऐप|व्हाट्सएप|वॉट्सएप|வாட்ஸ்அப்|వాట్సాప్|ವಾಟ್ಸಾಪ್|વોટ્સએપ|হোয়াটসঅ্যাপ|വാട്ട്സ്ആപ്പ്|ਵਟਸਐਪ", "whatsapp"),
    (r"cctv|camera|कैमरा|सीसीटीवी|கேமரா|కెమెరా|ಕ್ಯಾಮೆರಾ|કેમેરા|ক্যামেরা|ക്യാമറ|ਕੈਮਰਾ", "cctv"),
    (r"\bpos\b|billing|card machine|swipe|बिलिंग|பில்லிங்|బిల్లింగ్|ಬಿಲ್ಲಿಂಗ್|બિલિંગ|বিলিং|ബില്ലിംഗ്|ਬਿਲਿੰਗ", "pos"),
    (r"website|web ?site|online presence|वेबसाइट|இணையதளம்|வெப்சைட்|వెబ్సైట్|ವೆಬ್ಸೈಟ್|વેબસાઇટ|ওয়েবসাইট|വെബ്സൈറ്റ്|ਵੈੱਬਸਾਈਟ|ਵੈਬਸਾਈਟ", "website"),
    (r"e-?mail|mailbox|ईमेल|gmail|மின்னஞ்சல்|இமெயில்|ஈமெயில்|ఈమెయిల్|ఇమెయిల్|ఈ-మెయిల్|ಇಮೇಲ್|ಈಮೇಲ್|ઈમેલ|ઇમેઇલ|ইমেল|ইমেইল|ഇമെയിൽ|ഇ-മെയിൽ|ਈਮੇਲ", "email"),
    (r"backup(?! internet)(?! line)|cloud storage|बैकअप|பேக்கப்|బ్యాకప్|ಬ್ಯಾಕಪ್|બેકઅપ|ব্যাকআপ|ബാക്കപ്പ്|ਬੈਕਅੱਪ", "backup"),
    (r"antivirus|anti-virus|ransomware|endpoint|virus|वायरस|வைரஸ்|వైరస్|ವೈರಸ್|વાયરસ|ভাইরাস|വൈറസ്|ਵਾਇਰਸ", "endpoint"),
    (r"firewall|फ़ायरवॉल|फायरवॉल", "firewall"),
    (r"failover|backup internet|backup line|second line|4g backup|5g backup", "failover"),
    (r"sd-?wan|central(?:ly)? manag|manage all (?:stores|sites|branches)", "sdwan"),
    (r"static ip|fixed ip|public ip", "static_ip"),
    (r"ivr|cloud telephony|telephony|landline|call recording|office phone", "telephony"),
    (r"toll[- ]?free|1800", "toll_free"),
    (r"\bsms\b|bulk sms|text messages", "sms"),
    (r"machine monitoring|\biot\b|sensors?\b|machine uptime|energy use", "iot"),
    (r"vehicle tracking|fleet|gps tracker|gps|track (?:my )?(?:trucks|vehicles)", "fleet"),
    (r"guest wi-?fi|customer wi-?fi|wi-?fi for (?:customers|visitors|guests)|visitor wi-?fi|wifi|wi-fi|वाईफाई|वाई-फाई|வைஃபை|వైఫై|ವೈಫೈ|વાઇફાઇ|ওয়াইফাই|വൈഫൈ|ਵਾਈਫਾਈ", "guest_wifi"),
    (r"mobile plan|mobile line|postpaid|\bsims?\b|mobile connection|phone line|मोबाइल प्लान|सिम|मोबाइल|சிம்|மொபைல்|సిమ్|మొబైల్|ಸಿಮ್|ಮೊಬೈಲ್|સિમ|મોબાઇલ|সিম|মোবাইল|സിം|മൊബൈൽ|ਸਿਮ|ਮੋਬਾਈਲ", "mobile_lines"),
    (r"internet|broadband|fib(?:re|er)|\bnet\b|wifi connection|upi (?:keeps )?(?:fails|failing)|upi|इंटरनेट|नेट|इंटरनेट|இணையம்|ఇంటర్నెట్|ಇಂಟರ್ನೆಟ್|ઇન્ટરનેટ|ইন্টারনেট|ഇന്റർനെറ്റ്|ਇੰਟਰਨੈੱਟ", "internet"),
]

ONLY = r"\b(?:only|just|sirf|bas)\b|सिर्फ|केवल|फक्त|மட்டும்|మాత్రమే|ಮಾತ್ರ|ફક્ત|শুধু|മാത്രം|ਸਿਰਫ਼"
NO_GST = r"(?:gst|gstin|जीएसटी|ஜிஎஸ்டி|జీఎస్టీ|జిఎస్టి|ಜಿಎಸ್ಟಿ|જીએસટી|জিএসটি|ജിഎസ്ടി|ਜੀਐਸਟੀ).{0,14}?(?:नहीं|नाही|இல்லை|లేదు|ಇಲ್ಲ|નથી|নেই|ഇല്ല|ਨਹੀਂ)|no gst|without gst|not (?:gst )?registered|gst (?:nahi|nahin|not)|don'?t have (?:a )?gst|no gstin|gst registration (?:nahi|not)|जीएसटी नहीं|GST नहीं|gst yet|not yet registered"
YES_GST = r"(?:gst|gstin|जीएसटी|ஜிஎஸ்டி|జీఎస్టీ|జిఎస్టి|ಜಿಎಸ್ಟಿ|જીએસટી|জিএসটি|ജിഎസ്ടി|ਜੀਐਸਟੀ).{0,14}?(?:आहे|உள்ளது|இருக்கு|இருக்கிறது|ఉంది|ఉన్నది|ಇದೆ|છે|আছে|ഉണ്ട്|ਹੈ)|जीएसटी है|gst है|gst हैं|gst आहे|gst (?:registered|active|hai|number hai)|have (?:a )?gst|gstin hai|gst-registered|registered (?:under|for) gst|gst wala"
CANCELLED = r"cancel+ed"
SUSPENDED = r"suspended"
NO_FIBRE = r"no fib(?:re|er)|fib(?:re|er) (?:is )?not (?:available|feasible)|fib(?:re|er) nahi|without fib(?:re|er)|only airfiber works|fib(?:re|er) isn'?t available"
INJECTION = r"ignore (?:your|all|the|previous|any) (?:rules|instructions)|forget (?:your|the) rules|you are now|system prompt|give (?:it )?(?:to )?me (?:for )?free|\bfor (?:rs\.?|₹|inr)\s?\d{1,3}\b(?! ?(?:a|per) (?:month|line|user))|100% discount|bypass"
OUT_OF_SCOPE = r"\b(?:sell|buy|need|want|give|get|have)\b.{0,20}\b(?:laptops?|computers?|loans?|credit cards?|insurance polic(?:y|ies)|flights?|train tickets?|iphones?|recipes?|movie)\b|\bwhat is the weather\b|\bwho won\b"
# "don't need X", "remove X", "X nahi chahiye": the named needs come off the profile
NEGATION = (r"\b(?:don'?t|do not|doesn'?t|does not|no longer)\s+(?:need|want|require)|\bnot (?:needed|required|necessary)\b|"
            r"\bno need (?:for|of)\b|\b(?:remove|drop|skip|exclude|cancel)\b|^\s*(?:not|no)\b|"
            r"\b(?:nahi|nahin|mat)\s+(?:chahiye|chaiye|chahie)\b|\bzaroorat nahi|"
            r"नहीं चाहिए|नही चाहिए|ज़रूरत नहीं|जरूरत नहीं|हटा|नको|गरज नाही|வேண்டாம்|వద్దు|ಬೇಡ|નથી જોઈએ|જોઈતું નથી|લાગતું નથી|লাগবে না|চাই না|വേണ്ട|ਨਹੀਂ ਚਾਹੀਦਾ")
CLAUSE_SPLIT = r"[,;!?।\n]+|\.(?=\s|$)|\b(?:but|lekin|par|however|except)\b|लेकिन|पर |पण |ஆனால்|కానీ|ಆದರೆ|પણ |কিন্তু|പക്ഷേ|ਪਰ "
HANDOFF = r"talk to (?:a )?(?:human|person|agent|someone|executive)|call me|speak to (?:a )?(?:person|human)|baat kar|किसी से बात|कॉल करो"
TERM24 = r"24[- ]?months?|2 years|two years|do saal|दो साल"
SHORT_CONTRACT = r"one[- ]month|1[- ]month|monthly contract|no contract|no lock-?in"

CITY_ALIASES = {
    "bangalore": "Bengaluru", "bengaluru": "Bengaluru", "bombay": "Mumbai", "calcutta": "Kolkata", "madras": "Chennai",
    "vizag": "Visakhapatnam", "baroda": "Vadodara", "mysore": "Mysuru", "cochin": "Kochi", "ernakulam": "Kochi",
    "new delhi": "Delhi", "gurgaon": "Gurugram", "poona": "Pune",
    "दिल्ली": "Delhi", "मुंबई": "Mumbai", "पुणे": "Pune", "जयपुर": "Jaipur", "लखनऊ": "Lucknow", "पटना": "Patna", "इंदौर": "Indore",
    "भोपाल": "Bhopal", "नागपुर": "Nagpur", "नागपूर": "Nagpur", "नाशिक": "Nashik", "सूरत": "Surat", "अहमदाबाद": "Ahmedabad", "कोलकाता": "Kolkata",
    "चेन्नई": "Chennai", "हैदराबाद": "Hyderabad", "बेंगलुरु": "Bengaluru", "लुधियाना": "Ludhiana", "वडोदरा": "Vadodara",
    "சென்னை": "Chennai", "கோயம்புத்தூர்": "Coimbatore", "హైదరాబాద్": "Hyderabad", "విశాఖపట్నం": "Visakhapatnam",
    "ಬೆಂಗಳೂರು": "Bengaluru", "ಬೆಂಗಳೂರ": "Bengaluru", "ಮೈಸೂರು": "Mysuru", "ಮೈಸೂರ": "Mysuru", "విజయవాడ": "Vijayawada", "மதுரை": "Madurai", "കൊച്ചി": "Kochi", "কলকাতা": "Kolkata", "અમદાવાદ": "Ahmedabad",
    "સુરત": "Surat", "વડોદરા": "Vadodara", "ਲੁਧਿਆਣਾ": "Ludhiana", "मुम्बई": "Mumbai", "पुण्यात": "Pune", "पुण्याला": "Pune", "मुंबईत": "Mumbai", "नागपुरात": "Nagpur", "नाशिकमध्ये": "Nashik", "दिल्लीत": "Delhi",
}
# Cities outside the leads data: tier by the usual classification
EXTRA_TIERS = {"Gurugram": 1, "Noida": 1, "Chandigarh": 2, "Kanpur": 2, "Agra": 2, "Varanasi": 2, "Madurai": 2, "Thane": 1,
               "Navi Mumbai": 1, "Vijayawada": 2, "Raipur": 2, "Ranchi": 2, "Bhubaneswar": 2, "Guwahati": 2, "Dehradun": 2,
               "Amritsar": 2, "Jalandhar": 2, "Rajkot": 2, "Aurangabad": 2, "Mangaluru": 2, "Thiruvananthapuram": 2, "Kozhikode": 2}
CITY_STATE_EXTRA = {"Gurugram": "Haryana", "Noida": "Uttar Pradesh", "Chandigarh": "Chandigarh", "Thane": "Maharashtra", "Navi Mumbai": "Maharashtra"}

GSTIN_IN_TEXT = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
PIN_IN_TEXT = re.compile(r"(?<![\dA-Z])[1-9]\d{5}(?![\dA-Z])")


@dataclass
class Extracted:
    language: str | None = None
    business_type: str | None = None
    segment: str | None = None
    employees: int | None = None
    sites: int | None = None
    city: str | None = None
    city_tier: int | None = None
    state: str | None = None
    pincode: str | None = None
    gstin: str | None = None
    has_gstin: bool | None = None
    gstin_status: str | None = None
    fibre_feasible: bool | None = None
    needs: set[str] = field(default_factory=set)
    only: bool = False
    qty: dict[str, int] = field(default_factory=dict)
    budget: int | None = None
    current_spend: int | None = None
    term_months: int | None = None
    speed_mbps: int | None = None
    uptime_pct: float | None = None
    removed: set[str] = field(default_factory=set)
    intents: set[str] = field(default_factory=set)
    bare_number: int | None = None
    yes: bool = False
    no: bool = False


def _num(s: str) -> int | None:
    s = s.strip().lower().replace(",", "")
    if s.isdigit():
        return int(s)
    return NUM_WORDS.get(s)


# a single describing word ("garment", "retail", "postpaid", "CNC"); never a people word or a linking word
ADJ = r"(?!(?:" + PEOPLE + r"|in|at|of|and|or|with|from|for|across|per|more|other|the|our|my|total|each|every|lakh|crore|rs|rupees)(?![\w\u0900-\u0dff]))[a-z\u0900-\u0dff]{2,}"

NUM = r"(\d[\d,]*|" + "|".join(sorted((re.escape(k) for k in NUM_WORDS), key=len, reverse=True)) + r")"


def extract(raw: str) -> Extracted:
    text = normalise_digits(raw).replace("\u200c", "").replace("\u200d", "")  # zero-width joiners from Indic keyboards
    low = text.lower()
    e = Extracted(language=detect_language(text))

    m = GSTIN_IN_TEXT.search(text.upper())
    if m:
        e.gstin, e.has_gstin = m.group(), True
    scrub = GSTIN_IN_TEXT.sub(" ", text.upper()).lower() if m else low

    pm = PIN_IN_TEXT.search(GSTIN_IN_TEXT.sub(" ", text.upper()))
    if pm and not re.search(r"(?:rs\.?|₹|inr|budget)\s*" + pm.group(), low):
        e.pincode = pm.group()

    # quantities
    def grab(pattern: str) -> int | None:
        # "4 stores", and "4 garment stores": one describing word may sit between number and noun
        mm = re.search(NUM + r"\s*[-]?\s*(?:" + ADJ + r"\s+)?(?:" + pattern + r")", scrub)
        if mm:
            return _num(mm.group(1))
        mm = re.search(r"(?:" + pattern + r")\s*(?:of|:)?\s*" + NUM + r"\b", scrub)
        return _num(mm.group(1)) if mm else None

    e.employees = grab(PEOPLE) or grab(r"(?:-person|person)")
    if e.employees is None:
        mm = re.search(r"team of\s+" + NUM, scrub)
        e.employees = _num(mm.group(1)) if mm else None
    # sites add up: "2 shops in Jaipur and 1 in Ajmer" is 3 sites
    site_counts = [_num(mm.group(1)) for mm in re.finditer(NUM + r"\s*[-]?\s*(?:" + ADJ + r"\s+)?(?:" + SITES + r")", scrub)]
    site_counts = [n for n in site_counts if n]
    if site_counts:
        site_counts += [n for mm in re.finditer(r"(?:\band\b|,|\baur\b|और)\s*" + NUM + r"\s+(?:more\s+)?(?:in|at|में)\s", scrub)
                        if (n := _num(mm.group(1)))]
        e.sites = sum(site_counts)
    else:
        e.sites = grab(SITES)
    v = grab(VEHICLES)
    if v:
        e.qty["vehicles"] = v
    for key, pat in (("cameras", r"cameras?|कैमरे"), ("counters", r"(?:billing )?counters?"), ("lines", r"(?:sims?|mobile lines?|phone lines?|lines|connections|numbers)"),
                     ("users", r"(?:email (?:ids?|accounts?|users?)|users|mailboxes)"), ("machines", r"machines?|मशीन"), ("channels", r"channels?")):
        q = grab(pat)
        if q:
            e.qty[key] = q
    if "lines" not in e.qty and re.search(r"\b(?:a|an|one|single|ek)\s+(?:mobile|phone|postpaid|sim)\b", scrub):
        e.qty["lines"] = 1

    bm = re.search(r"(?:budget|under|within|max(?:imum)?|upto|up to|बजट)\D{0,12}?(\d[\d,]{2,})", scrub) or \
        re.search(r"(?:rs\.?|₹|inr)\s*(\d[\d,]{2,})\s*(?:a|per|/)\s*(?:month|mo)", scrub) or \
        re.search(r"(\d[\d,]{2,})\s*(?:rs|rupees|₹|रुपये)\s*(?:a|per|/|महीना|प्रति)", scrub)
    # what they pay today ("we spend Rs 900 a month on the hotspot"): shown beside the quote, never used as a budget
    sp = re.search(r"(?:currently|today|right now|abhi|अभी|pay(?:ing)?|spend(?:ing)?|kharcha|खर्च)\D{0,24}?(\d[\d,]{2,})", scrub)
    if sp:
        e.current_spend = int(sp.group(1).replace(",", ""))
    explicit_budget = re.search(r"(?:budget|under|within|max(?:imum)?|upto|up to|बजट)\D{0,12}?(\d[\d,]{2,})", scrub)
    if bm and (explicit_budget or not sp):
        e.budget = int(bm.group(1).replace(",", ""))

    sm = re.search(r"(\d{2,4})\s?mbps", scrub)
    if sm:
        e.speed_mbps = int(sm.group(1))
    if re.search(r"1\s?gbps|1\s?gig|gigabit|\b1\s?g\b", scrub):
        e.speed_mbps = 1000
    um = re.search(r"(99(?:\.\d+)?)\s?%", scrub)
    if um:
        e.uptime_pct = float(um.group(1))

    for pattern, label, seg in BUSINESS_KEYWORDS:
        if re.search(pattern, scrub, flags=re.I):
            e.business_type, e.segment = label, seg
            break
    # a "Shop"/"Restaurant" with several sites is a multi-site business
    if e.segment == "micro" and e.sites and e.sites >= 2:
        e.segment = "multi"
        e.business_type = {"Restaurant": "Restaurant chain", "Bakery": "Bakery chain", "Pharmacy": "Pharmacy chain"}.get(e.business_type, e.business_type or "Retail chain")
    # data-backed business types map to their segment exactly
    seg_map = store().business_segment
    if e.business_type in seg_map:
        e.segment = seg_map[e.business_type]

    # needs, clause by clause: a negated clause removes what it names
    for clause in re.split(CLAUSE_SPLIT, scrub, flags=re.I):
        if not clause.strip():
            continue
        found = {need for pattern, need in NEED_KEYWORDS if re.search(pattern, clause, flags=re.I)} | loanword_needs(clause)
        if found and re.search(NEGATION, clause, flags=re.I):
            if re.search(NO_FIBRE, clause):
                found -= {"internet", "high_speed", "dedicated_line"}  # "no fibre here" still wants internet
            e.removed |= found
        else:
            e.needs |= found
    e.needs -= e.removed
    if "high_speed" in e.needs or "dedicated_line" in e.needs:
        e.needs.discard("internet")
    if e.uptime_pct and e.uptime_pct >= 99.5:
        e.needs.add("dedicated_line")
    if re.search(ONLY, scrub, flags=re.I) and e.needs:
        e.only = True
    if e.qty.get("vehicles") and "fleet" not in e.needs and re.search(r"track", scrub):
        e.needs.add("fleet")
    if e.qty.get("machines") and re.search(r"monitor|track|uptime|sensor|connect|watch|निगरानी", scrub):
        e.needs.add("iot")

    if re.search(CANCELLED, scrub):
        e.has_gstin, e.gstin_status = True, "Cancelled"
    elif re.search(SUSPENDED, scrub):
        e.has_gstin, e.gstin_status = True, "Suspended"
    elif re.search(NO_GST, scrub, flags=re.I):
        e.has_gstin = False
    elif re.search(YES_GST, scrub, flags=re.I) and not e.gstin:
        e.has_gstin, e.gstin_status = True, "Declared"
    if re.search(NO_FIBRE, scrub):
        e.fibre_feasible = False
    if re.search(TERM24, scrub):
        e.term_months = 24
    if re.search(SHORT_CONTRACT, scrub):
        e.intents.add("short_contract")
    if re.search(INJECTION, scrub, flags=re.I):
        e.intents.add("injection")
    if re.search(OUT_OF_SCOPE, scrub, flags=re.I):
        e.intents.add("out_of_scope")
    if re.search(HANDOFF, scrub, flags=re.I):
        e.intents.add("handoff")

    ds = store()
    cities = {c.lower(): c for c in list(ds.city_tier) + list(EXTRA_TIERS)}
    for alias, city in CITY_ALIASES.items():
        cities.setdefault(alias.lower(), city)
    for name in sorted(cities, key=len, reverse=True):
        if re.search(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", scrub):
            c = cities[name]
            e.city = c
            e.city_tier = ds.city_tier.get(c) or EXTRA_TIERS.get(c)
            e.state = ds.city_state.get(c) or CITY_STATE_EXTRA.get(c)
            break

    stripped = scrub.strip(" .!?")
    if re.fullmatch(NUM, stripped):
        e.bare_number = _num(stripped)
    if re.fullmatch(r"(?:yes|yeah|yep|ha+n?|haan|ji|ok|okay|sure|continue|हाँ|हां|हो|ஆம்|అవును|ಹೌದು|હા|হ্যাঁ|അതെ|ਹਾਂ)(?:$|[\s.,!?।]).*", stripped):
        e.yes = True
    if re.fullmatch(r"(?:no|nope|nahi|nahin|नहीं|नाही|இல்லை|లేదు|ಇಲ್ಲ|ના|না|ഇല്ല|ਨਹੀਂ)(?:$|[\s.,!?।]).*", stripped):
        e.no = True
    return e
