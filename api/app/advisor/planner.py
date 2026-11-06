"""The question that matters: after a recommendation, ask what changes the price most.

The engine looks at the assumptions it made (email for every employee, two SIMs, a
backup line, four cameras) and works out how much each one moves the monthly price.
The one or two biggest become tappable questions; each answer is a typed patch to the
profile, so the quote changes exactly and the change is shown as a difference.
"""
from __future__ import annotations

from ..engine.profile import Profile

Q = {
    "users": {
        "en": "How many people need business email?", "hi": "कितने लोगों को बिज़नेस ईमेल चाहिए?", "mr": "किती लोकांना बिझनेस ईमेल हवा?",
        "ta": "எத்தனை பேருக்கு வணிக மின்னஞ்சல் வேண்டும்?", "te": "ఎంత మందికి బిజినెస్ ఈమెయిల్ కావాలి?", "kn": "ಎಷ್ಟು ಜನರಿಗೆ ಬಿಸಿನೆಸ್ ಇಮೇಲ್ ಬೇಕು?",
        "gu": "કેટલા લોકોને બિઝનેસ ઈમેલ જોઈએ?", "bn": "কতজনের ব্যবসায়িক ইমেল লাগবে?", "ml": "എത്ര പേർക്ക് ബിസിനസ് ഇമെയിൽ വേണം?",
        "pa": "ਕਿੰਨੇ ਲੋਕਾਂ ਨੂੰ ਬਿਜ਼ਨਸ ਈਮੇਲ ਚਾਹੀਦੀ ਹੈ?"},
    "devices": {
        "en": "How many PCs and phones should we protect from viruses?", "hi": "कितने कंप्यूटर और फ़ोन को वायरस से बचाना है?",
        "mr": "किती कॉम्प्युटर आणि फोन व्हायरसपासून सुरक्षित करायचे?", "ta": "எத்தனை கணினிகள், போன்களை வைரஸிலிருந்து பாதுகாக்க வேண்டும்?",
        "te": "ఎన్ని కంప్యూటర్లు, ఫోన్లను వైరస్ నుండి కాపాడాలి?", "kn": "ಎಷ್ಟು ಕಂಪ್ಯೂಟರ್ ಮತ್ತು ಫೋನ್‌ಗಳನ್ನು ವೈರಸ್‌ನಿಂದ ರಕ್ಷಿಸಬೇಕು?",
        "gu": "કેટલા કમ્પ્યુટર અને ફોનને વાયરસથી બચાવવા છે?", "bn": "কতগুলো কম্পিউটার ও ফোন ভাইরাস থেকে সুরক্ষিত রাখতে হবে?",
        "ml": "എത്ര കമ്പ്യൂട്ടറുകളും ഫോണുകളും വൈറസിൽ നിന്ന് സംരക്ഷിക്കണം?", "pa": "ਕਿੰਨੇ ਕੰਪਿਊਟਰ ਅਤੇ ਫ਼ੋਨ ਵਾਇਰਸ ਤੋਂ ਬਚਾਉਣੇ ਹਨ?"},
    "lines": {
        "en": "How many business SIMs do you need?", "hi": "कितने बिज़नेस सिम चाहिए?", "mr": "किती बिझनेस सिम हवे?",
        "ta": "எத்தனை வணிக சிம் வேண்டும்?", "te": "ఎన్ని బిజినెస్ సిమ్‌లు కావాలి?", "kn": "ಎಷ್ಟು ಬಿಸಿನೆಸ್ ಸಿಮ್ ಬೇಕು?",
        "gu": "કેટલા બિઝનેસ સિમ જોઈએ?", "bn": "কতগুলো ব্যবসায়িক সিম লাগবে?", "ml": "എത്ര ബിസിനസ് സിം വേണം?", "pa": "ਕਿੰਨੇ ਬਿਜ਼ਨਸ ਸਿਮ ਚਾਹੀਦੇ ਹਨ?"},
    "cameras": {
        "en": "How many CCTV cameras?", "hi": "कितने सीसीटीवी कैमरे?", "mr": "किती सीसीटीव्ही कॅमेरे?", "ta": "எத்தனை சிசிடிவி கேமராக்கள்?",
        "te": "ఎన్ని సీసీటీవీ కెమెరాలు?", "kn": "ಎಷ್ಟು ಸಿಸಿಟಿವಿ ಕ್ಯಾಮೆರಾಗಳು?", "gu": "કેટલા સીસીટીવી કેમેરા?", "bn": "কতগুলো সিসিটিভি ক্যামেরা?",
        "ml": "എത്ര സിസിടിവി ക്യാമറകൾ?", "pa": "ਕਿੰਨੇ ਸੀਸੀਟੀਵੀ ਕੈਮਰੇ?"},
    "failover": {
        "en": "If the internet goes down, do you need a backup line that switches on by itself?",
        "hi": "इंटरनेट बंद होने पर क्या अपने-आप चालू होने वाली बैकअप लाइन चाहिए?",
        "mr": "इंटरनेट बंद पडल्यास आपोआप सुरू होणारी बॅकअप लाइन हवी का?",
        "ta": "இணையம் நின்றால் தானாக இயங்கும் மாற்று இணைப்பு வேண்டுமா?", "te": "ఇంటర్నెట్ ఆగితే దానంతట అదే ఆన్ అయ్యే బ్యాకప్ లైన్ కావాలా?",
        "kn": "ಇಂಟರ್ನೆಟ್ ನಿಂತರೆ ತಾನಾಗಿ ಆನ್ ಆಗುವ ಬ್ಯಾಕಪ್ ಲೈನ್ ಬೇಕೆ?", "gu": "ઇન્ટરનેટ બંધ થાય ત્યારે આપમેળે ચાલુ થતી બેકઅપ લાઇન જોઈએ?",
        "bn": "ইন্টারনেট বন্ধ হলে নিজে থেকে চালু হওয়া ব্যাকআপ লাইন লাগবে?", "ml": "ഇന്റർനെറ്റ് നിലച്ചാൽ സ്വയം ഓണാകുന്ന ബാക്കപ്പ് ലൈൻ വേണോ?",
        "pa": "ਇੰਟਰਨੈੱਟ ਬੰਦ ਹੋਣ 'ਤੇ ਆਪਣੇ-ਆਪ ਚੱਲਣ ਵਾਲੀ ਬੈਕਅੱਪ ਲਾਈਨ ਚਾਹੀਦੀ ਹੈ?"},
}
YES = {"en": "Yes", "hi": "हाँ", "mr": "हो", "ta": "ஆம்", "te": "అవును", "kn": "ಹೌದು", "gu": "હા", "bn": "হ্যাঁ", "ml": "അതെ", "pa": "ਹਾਂ"}
NO = {"en": "No", "hi": "नहीं", "mr": "नाही", "ta": "இல்லை", "te": "వద్దు", "kn": "ಬೇಡ", "gu": "ના", "bn": "না", "ml": "വേണ്ട", "pa": "ਨਹੀਂ"}

QTY_PRODUCTS = {"users": ("P16",), "devices": ("P20",), "lines": ("P07", "P08"), "cameras": ("P23",)}


def _options(current: int) -> list[int]:
    opts = sorted({current, max(1, current // 2), 1, current + 2} - {0})
    return opts[:4]


def refinements(bundle: dict | None, profile: Profile, lang: str, limit: int = 2) -> list[dict]:
    if not bundle:
        return []
    lang = lang if lang in YES else "en"
    lines = {ln["product_id"]: ln for ln in bundle.get("lines", [])}
    out = []
    for key, pids in QTY_PRODUCTS.items():
        ln = next((lines[p] for p in pids if p in lines), None)
        if not ln or key in profile.qty or ln["source"] == "asked" and key != "users":
            continue  # only assumptions are worth a question
        out.append({"key": key, "question": Q[key][lang], "impact": ln["monthly"], "product_id": ln["product_id"],
                    "options": [{"label": str(n), "patch": {"qty": {key: n}}, "monthly_delta": ln["unit_price"] * (n - ln["qty"])}
                                for n in _options(ln["qty"])]})
    fo = lines.get("P09")
    if fo and fo["source"] == "recommended":
        out.append({"key": "failover", "question": Q["failover"][lang], "impact": fo["monthly"], "product_id": "P09",
                    "options": [{"label": YES[lang], "patch": {"add_needs": ["failover"]}, "monthly_delta": 0},
                                {"label": NO[lang], "patch": {"remove_needs": ["failover"]}, "monthly_delta": -fo["monthly"]}]})
    out.sort(key=lambda r: -r["impact"])
    return out[:limit]


def diff(before: dict | None, after: dict) -> dict:
    """What changed in the quote, for the 'your quote changed' line."""
    b = {ln["product_id"]: ln for ln in (before or {}).get("lines", [])}
    a = {ln["product_id"]: ln for ln in after.get("lines", [])}
    return {"added": [a[p]["name"] for p in a if p not in b], "removed": [b[p]["name"] for p in b if p not in a],
            "changed": [{"name": a[p]["name"], "from": b[p]["qty"], "to": a[p]["qty"]} for p in a if p in b and a[p]["qty"] != b[p]["qty"]],
            "monthly_before": (before or {}).get("monthly"), "monthly_after": after.get("monthly")}
