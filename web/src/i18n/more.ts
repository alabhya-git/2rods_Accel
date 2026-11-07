// Strings for the three doors, express checkout, call-backs, proof routes, SIM users and My account.
// Every key exists in all 10 languages: nothing falls back to English.
type Dict = Record<string, string>

const en: Dict = {
  door_help: 'Help me choose', door_help_sub: 'We suggest what fits you.',
  door_express: 'I know what I need', door_express_sub: 'Your price in a minute.',
  door_person: 'Talk to a person', door_person_sub: 'A call in your language.', door_wa_sub: 'Same help, in a chat.',
  resume: 'Continue my order', express_title: 'Pick what you need', city_label: 'Your city', staff_label: 'People in your business',
  gst_question: 'Do you have a GSTIN?', yes_word: 'Yes', no_word: 'No', from_month: 'from {amount} a month', needs_gst: 'Needs a GSTIN',
  get_price: 'Get my price', all_in: 'Each month, with GST', due_today: 'Due today', after_emi: 'After {n} months',
  setup_instalments: 'Setup in {n} instalments', total_commit: 'Total over {n} months',
  today_spend: 'What do you pay today for phone and internet, each month?', vs_more: '{diff} more than today', vs_less: '{diff} less than today',
  callback_title: "We'll call you back", callback_intro: 'A person who speaks your language calls you. No sales pressure.',
  when_call: 'When should we call?', w_asap: 'As soon as possible', w_today_evening: 'Today, 6 to 9 pm', w_tomorrow_morning: 'Tomorrow, 9 to 12',
  w_tomorrow_evening: 'Tomorrow, 6 to 9 pm', w_after_9pm: 'After 9 pm today', call_me: 'Call me back', callback_done: 'Done. We will call {phone}: {window}.',
  route_title: 'What proof does your business have?', route_gst: 'GST certificate', route_udyam: 'Udyam, no GST', route_shop: 'Shop licence only',
  doc_shop_licence: 'Shop licence or trade licence', sim_title: 'Business SIM users',
  sim_intro: 'The law asks each SIM user to verify themselves. We send each one a link.', sim_name: 'Name', sim_invite: 'Send links',
  sim_verified: 'Verified', sim_waiting: 'Waiting for them', account_title: 'My account', one_bill: 'One bill for everything',
  next_debit: 'Next debit', get_help: 'Get help', setup_tasks: 'Finish setting up', refine_title: 'One question that changes your price',
  quote_changed: 'Your quote changed', on_hold: 'On hold', read_aloud: 'Read aloud', verify_me: 'Verify me with DigiLocker',
  sim_consent: 'I agree to share my identity for this SIM.', sim_done: 'You are verified. Your SIM can now go live.',
}

const hi: Dict = {
  door_help: 'चुनने में मदद करें', door_help_sub: 'हम सही प्लान सुझाएँगे।',
  door_express: 'मुझे पता है क्या चाहिए', door_express_sub: 'एक मिनट में कीमत।',
  door_person: 'किसी से बात करें', door_person_sub: 'आपकी भाषा में कॉल।', door_wa_sub: 'वही मदद, चैट में।',
  resume: 'मेरा ऑर्डर जारी रखें', express_title: 'जो चाहिए वो चुनें', city_label: 'आपका शहर', staff_label: 'आपके काम में कितने लोग',
  gst_question: 'क्या आपके पास जीएसटीआईएन है?', yes_word: 'हाँ', no_word: 'नहीं', from_month: '{amount} प्रति माह से', needs_gst: 'जीएसटीआईएन चाहिए',
  get_price: 'मेरी कीमत देखें', all_in: 'हर महीने, जीएसटी सहित', due_today: 'आज देना है', after_emi: '{n} महीने बाद',
  setup_instalments: 'सेटअप {n} किस्तों में', total_commit: '{n} महीनों में कुल',
  today_spend: 'आज फ़ोन और इंटरनेट पर हर महीने कितना खर्च होता है?', vs_more: 'आज से {diff} ज़्यादा', vs_less: 'आज से {diff} कम',
  callback_title: 'हम आपको कॉल करेंगे', callback_intro: 'आपकी भाषा बोलने वाला व्यक्ति कॉल करेगा। बिक्री का दबाव नहीं।',
  when_call: 'कब कॉल करें?', w_asap: 'जितनी जल्दी हो सके', w_today_evening: 'आज शाम 6 से 9', w_tomorrow_morning: 'कल सुबह 9 से 12',
  w_tomorrow_evening: 'कल शाम 6 से 9', w_after_9pm: 'आज रात 9 के बाद', call_me: 'मुझे कॉल करें', callback_done: 'हो गया। हम {phone} पर कॉल करेंगे: {window}।',
  route_title: 'आपके व्यवसाय का कौन-सा प्रमाण है?', route_gst: 'जीएसटी प्रमाणपत्र', route_udyam: 'उद्यम, जीएसटी नहीं', route_shop: 'सिर्फ़ दुकान लाइसेंस',
  doc_shop_licence: 'दुकान या ट्रेड लाइसेंस', sim_title: 'बिज़नेस सिम उपयोगकर्ता',
  sim_intro: 'कानून के अनुसार हर सिम उपयोगकर्ता खुद सत्यापन करे। हम हर एक को लिंक भेजेंगे।', sim_name: 'नाम', sim_invite: 'लिंक भेजें',
  sim_verified: 'सत्यापित', sim_waiting: 'उनका इंतज़ार', account_title: 'मेरा खाता', one_bill: 'सब कुछ एक बिल में',
  next_debit: 'अगली कटौती', get_help: 'मदद लें', setup_tasks: 'सेटअप पूरा करें', refine_title: 'एक सवाल जो आपकी कीमत बदलता है',
  quote_changed: 'आपका कोटेशन बदला', on_hold: 'रुका हुआ', read_aloud: 'पढ़कर सुनाएँ', verify_me: 'डिजीलॉकर से सत्यापन करें',
  sim_consent: 'मैं इस सिम के लिए अपनी पहचान साझा करने के लिए सहमत हूँ।', sim_done: 'आपका सत्यापन हो गया। अब सिम चालू हो सकता है।',
}

const mr: Dict = {
  door_help: 'निवडायला मदत करा', door_help_sub: 'आम्ही योग्य पर्याय सुचवू.',
  door_express: 'मला काय हवे ते माहीत आहे', door_express_sub: 'एका मिनिटात किंमत.',
  door_person: 'व्यक्तीशी बोला', door_person_sub: 'तुमच्या भाषेत कॉल.', door_wa_sub: 'तीच मदत, चॅटवर.',
  resume: 'माझी ऑर्डर सुरू ठेवा', express_title: 'हवे ते निवडा', city_label: 'तुमचे शहर', staff_label: 'व्यवसायात किती लोक',
  gst_question: 'तुमच्याकडे जीएसटीआयएन आहे का?', yes_word: 'हो', no_word: 'नाही', from_month: 'दरमहा {amount} पासून', needs_gst: 'जीएसटीआयएन लागतो',
  get_price: 'माझी किंमत पाहा', all_in: 'दरमहा, जीएसटीसह', due_today: 'आज भरायचे', after_emi: '{n} महिन्यांनंतर',
  setup_instalments: 'सेटअप {n} हप्त्यांत', total_commit: '{n} महिन्यांत एकूण',
  today_spend: 'आज फोन आणि इंटरनेटवर दरमहा किती खर्च होतो?', vs_more: 'आजपेक्षा {diff} जास्त', vs_less: 'आजपेक्षा {diff} कमी',
  callback_title: 'आम्ही तुम्हाला कॉल करू', callback_intro: 'तुमची भाषा बोलणारी व्यक्ती कॉल करेल. विक्रीचा दबाव नाही.',
  when_call: 'कधी कॉल करू?', w_asap: 'लवकरात लवकर', w_today_evening: 'आज संध्याकाळी 6 ते 9', w_tomorrow_morning: 'उद्या सकाळी 9 ते 12',
  w_tomorrow_evening: 'उद्या संध्याकाळी 6 ते 9', w_after_9pm: 'आज रात्री 9 नंतर', call_me: 'मला कॉल करा', callback_done: 'झाले. आम्ही {phone} वर कॉल करू: {window}.',
  route_title: 'तुमच्या व्यवसायाचा कोणता पुरावा आहे?', route_gst: 'जीएसटी प्रमाणपत्र', route_udyam: 'उद्यम, जीएसटी नाही', route_shop: 'फक्त दुकान परवाना',
  doc_shop_licence: 'दुकान किंवा व्यापार परवाना (गुमास्ता)', sim_title: 'बिझनेस सिम वापरकर्ते',
  sim_intro: 'कायद्यानुसार प्रत्येक सिम वापरकर्त्याने स्वतः पडताळणी करावी. आम्ही प्रत्येकाला लिंक पाठवू.', sim_name: 'नाव', sim_invite: 'लिंक पाठवा',
  sim_verified: 'पडताळले', sim_waiting: 'त्यांची वाट', account_title: 'माझे खाते', one_bill: 'सर्व काही एका बिलात',
  next_debit: 'पुढील कपात', get_help: 'मदत घ्या', setup_tasks: 'सेटअप पूर्ण करा', refine_title: 'तुमची किंमत बदलणारा एक प्रश्न',
  quote_changed: 'तुमचे कोटेशन बदलले', on_hold: 'थांबवले', read_aloud: 'वाचून दाखवा', verify_me: 'डिजीलॉकरने पडताळणी करा',
  sim_consent: 'या सिमसाठी माझी ओळख शेअर करायला मी तयार आहे.', sim_done: 'तुमची पडताळणी झाली. आता सिम सुरू होऊ शकते.',
}

const ta: Dict = {
  door_help: 'தேர்வு செய்ய உதவுங்கள்', door_help_sub: 'ஏற்றதைப் பரிந்துரைப்போம்.',
  door_express: 'எனக்கு என்ன வேண்டும் தெரியும்', door_express_sub: 'ஒரு நிமிடத்தில் விலை.',
  door_person: 'ஒருவரிடம் பேசுங்கள்', door_person_sub: 'உங்கள் மொழியில் அழைப்பு.', door_wa_sub: 'அதே உதவி, சாட்டில்.',
  resume: 'என் ஆர்டரைத் தொடரவும்', express_title: 'தேவையானதைத் தேர்ந்தெடுங்கள்', city_label: 'உங்கள் நகரம்', staff_label: 'தொழிலில் எத்தனை பேர்',
  gst_question: 'உங்களிடம் ஜிஎஸ்டிஐஎன் உள்ளதா?', yes_word: 'ஆம்', no_word: 'இல்லை', from_month: 'மாதம் {amount} முதல்', needs_gst: 'ஜிஎஸ்டிஐஎன் தேவை',
  get_price: 'என் விலையைப் பார்க்கவும்', all_in: 'ஒவ்வொரு மாதமும், ஜிஎஸ்டி உட்பட', due_today: 'இன்று செலுத்த வேண்டியது', after_emi: '{n} மாதங்களுக்குப் பிறகு',
  setup_instalments: 'அமைப்பு {n} தவணைகளில்', total_commit: '{n} மாதங்களில் மொத்தம்',
  today_spend: 'இன்று போன் மற்றும் இணையத்துக்கு மாதம் எவ்வளவு செலவு?', vs_more: 'இன்றைவிட {diff} அதிகம்', vs_less: 'இன்றைவிட {diff} குறைவு',
  callback_title: 'நாங்கள் உங்களை அழைப்போம்', callback_intro: 'உங்கள் மொழி பேசுபவர் அழைப்பார். விற்பனை அழுத்தம் இல்லை.',
  when_call: 'எப்போது அழைக்கலாம்?', w_asap: 'விரைவில்', w_today_evening: 'இன்று மாலை 6 முதல் 9', w_tomorrow_morning: 'நாளை காலை 9 முதல் 12',
  w_tomorrow_evening: 'நாளை மாலை 6 முதல் 9', w_after_9pm: 'இன்று இரவு 9க்குப் பிறகு', call_me: 'என்னை அழையுங்கள்', callback_done: 'சரி. {phone} எண்ணுக்கு அழைப்போம்: {window}.',
  route_title: 'உங்கள் தொழிலுக்கு என்ன ஆதாரம் உள்ளது?', route_gst: 'ஜிஎஸ்டி சான்றிதழ்', route_udyam: 'உத்யம், ஜிஎஸ்டி இல்லை', route_shop: 'கடை உரிமம் மட்டும்',
  doc_shop_licence: 'கடை அல்லது வர்த்தக உரிமம்', sim_title: 'வணிக சிம் பயனர்கள்',
  sim_intro: 'சட்டப்படி ஒவ்வொரு சிம் பயனரும் தாமே சரிபார்க்க வேண்டும். ஒவ்வொருவருக்கும் இணைப்பு அனுப்புவோம்.', sim_name: 'பெயர்', sim_invite: 'இணைப்புகளை அனுப்பு',
  sim_verified: 'சரிபார்க்கப்பட்டது', sim_waiting: 'காத்திருக்கிறது', account_title: 'என் கணக்கு', one_bill: 'அனைத்துக்கும் ஒரே பில்',
  next_debit: 'அடுத்த கழிவு', get_help: 'உதவி பெறுங்கள்', setup_tasks: 'அமைப்பை முடிக்கவும்', refine_title: 'உங்கள் விலையை மாற்றும் ஒரு கேள்வி',
  quote_changed: 'உங்கள் விலைப்புள்ளி மாறியது', on_hold: 'நிறுத்தி வைக்கப்பட்டது', read_aloud: 'படித்துக் காட்டு', verify_me: 'டிஜிலாக்கர் மூலம் சரிபார்',
  sim_consent: 'இந்த சிம்முக்காக என் அடையாளத்தைப் பகிர ஒப்புக்கொள்கிறேன்.', sim_done: 'சரிபார்க்கப்பட்டீர்கள். சிம் இப்போது இயங்கலாம்.',
}

const te: Dict = {
  door_help: 'ఎంచుకోవడంలో సహాయం', door_help_sub: 'సరైనది సూచిస్తాం.',
  door_express: 'నాకు ఏం కావాలో తెలుసు', door_express_sub: 'ఒక నిమిషంలో ధర.',
  door_person: 'ఒకరితో మాట్లాడండి', door_person_sub: 'మీ భాషలో కాల్.', door_wa_sub: 'అదే సహాయం, చాట్‌లో.',
  resume: 'నా ఆర్డర్ కొనసాగించు', express_title: 'కావాల్సింది ఎంచుకోండి', city_label: 'మీ నగరం', staff_label: 'వ్యాపారంలో ఎంత మంది',
  gst_question: 'మీకు జీఎస్టీఐఎన్ ఉందా?', yes_word: 'అవును', no_word: 'లేదు', from_month: 'నెలకు {amount} నుండి', needs_gst: 'జీఎస్టీఐఎన్ అవసరం',
  get_price: 'నా ధర చూపించు', all_in: 'ప్రతి నెల, జీఎస్టీతో', due_today: 'ఈరోజు చెల్లించాల్సింది', after_emi: '{n} నెలల తర్వాత',
  setup_instalments: 'సెటప్ {n} వాయిదాల్లో', total_commit: '{n} నెలల్లో మొత్తం',
  today_spend: 'ఈరోజు ఫోన్, ఇంటర్నెట్‌కు నెలకు ఎంత ఖర్చవుతోంది?', vs_more: 'ఈరోజు కంటే {diff} ఎక్కువ', vs_less: 'ఈరోజు కంటే {diff} తక్కువ',
  callback_title: 'మేమే మీకు కాల్ చేస్తాం', callback_intro: 'మీ భాష మాట్లాడే వ్యక్తి కాల్ చేస్తారు. అమ్మకం ఒత్తిడి ఉండదు.',
  when_call: 'ఎప్పుడు కాల్ చేయాలి?', w_asap: 'వీలైనంత త్వరగా', w_today_evening: 'ఈరోజు సాయంత్రం 6 నుండి 9', w_tomorrow_morning: 'రేపు ఉదయం 9 నుండి 12',
  w_tomorrow_evening: 'రేపు సాయంత్రం 6 నుండి 9', w_after_9pm: 'ఈరోజు రాత్రి 9 తర్వాత', call_me: 'నాకు కాల్ చేయండి', callback_done: 'సరే. {phone} కు కాల్ చేస్తాం: {window}.',
  route_title: 'మీ వ్యాపారానికి ఏ రుజువు ఉంది?', route_gst: 'జీఎస్టీ సర్టిఫికెట్', route_udyam: 'ఉద్యమ్, జీఎస్టీ లేదు', route_shop: 'షాప్ లైసెన్స్ మాత్రమే',
  doc_shop_licence: 'షాప్ లేదా ట్రేడ్ లైసెన్స్', sim_title: 'బిజినెస్ సిమ్ వినియోగదారులు',
  sim_intro: 'చట్టం ప్రకారం ప్రతి సిమ్ వినియోగదారు స్వయంగా ధృవీకరించాలి. ప్రతి ఒక్కరికీ లింక్ పంపుతాం.', sim_name: 'పేరు', sim_invite: 'లింకులు పంపు',
  sim_verified: 'ధృవీకరించబడింది', sim_waiting: 'వారి కోసం వేచి ఉంది', account_title: 'నా ఖాతా', one_bill: 'అన్నింటికీ ఒకే బిల్లు',
  next_debit: 'తదుపరి కోత', get_help: 'సహాయం పొందండి', setup_tasks: 'సెటప్ పూర్తి చేయండి', refine_title: 'మీ ధరను మార్చే ఒక ప్రశ్న',
  quote_changed: 'మీ కొటేషన్ మారింది', on_hold: 'నిలిపివేయబడింది', read_aloud: 'చదివి వినిపించు', verify_me: 'డిజిలాకర్‌తో ధృవీకరించు',
  sim_consent: 'ఈ సిమ్ కోసం నా గుర్తింపు పంచుకోవడానికి అంగీకరిస్తున్నాను.', sim_done: 'మీరు ధృవీకరించబడ్డారు. ఇప్పుడు సిమ్ ప్రారంభం కావచ్చు.',
}

const kn: Dict = {
  door_help: 'ಆಯ್ಕೆಗೆ ಸಹಾಯ ಮಾಡಿ', door_help_sub: 'ಸೂಕ್ತವಾದುದನ್ನು ಸೂಚಿಸುತ್ತೇವೆ.',
  door_express: 'ನನಗೆ ಏನು ಬೇಕು ಗೊತ್ತು', door_express_sub: 'ಒಂದು ನಿಮಿಷದಲ್ಲಿ ಬೆಲೆ.',
  door_person: 'ಒಬ್ಬರೊಂದಿಗೆ ಮಾತನಾಡಿ', door_person_sub: 'ನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ ಕರೆ.', door_wa_sub: 'ಅದೇ ಸಹಾಯ, ಚಾಟ್‌ನಲ್ಲಿ.',
  resume: 'ನನ್ನ ಆರ್ಡರ್ ಮುಂದುವರಿಸಿ', express_title: 'ಬೇಕಾದುದನ್ನು ಆರಿಸಿ', city_label: 'ನಿಮ್ಮ ನಗರ', staff_label: 'ವ್ಯಾಪಾರದಲ್ಲಿ ಎಷ್ಟು ಜನ',
  gst_question: 'ನಿಮ್ಮ ಬಳಿ ಜಿಎಸ್‌ಟಿಐಎನ್ ಇದೆಯೇ?', yes_word: 'ಹೌದು', no_word: 'ಇಲ್ಲ', from_month: 'ತಿಂಗಳಿಗೆ {amount} ರಿಂದ', needs_gst: 'ಜಿಎಸ್‌ಟಿಐಎನ್ ಬೇಕು',
  get_price: 'ನನ್ನ ಬೆಲೆ ನೋಡಿ', all_in: 'ಪ್ರತಿ ತಿಂಗಳು, ಜಿಎಸ್‌ಟಿ ಸೇರಿ', due_today: 'ಇಂದು ಪಾವತಿಸಬೇಕಾದದ್ದು', after_emi: '{n} ತಿಂಗಳ ನಂತರ',
  setup_instalments: 'ಸೆಟಪ್ {n} ಕಂತುಗಳಲ್ಲಿ', total_commit: '{n} ತಿಂಗಳಲ್ಲಿ ಒಟ್ಟು',
  today_spend: 'ಇಂದು ಫೋನ್ ಮತ್ತು ಇಂಟರ್ನೆಟ್‌ಗೆ ತಿಂಗಳಿಗೆ ಎಷ್ಟು ಖರ್ಚು?', vs_more: 'ಇಂದಿಗಿಂತ {diff} ಹೆಚ್ಚು', vs_less: 'ಇಂದಿಗಿಂತ {diff} ಕಡಿಮೆ',
  callback_title: 'ನಾವೇ ನಿಮಗೆ ಕರೆ ಮಾಡುತ್ತೇವೆ', callback_intro: 'ನಿಮ್ಮ ಭಾಷೆ ಮಾತನಾಡುವವರು ಕರೆ ಮಾಡುತ್ತಾರೆ. ಮಾರಾಟದ ಒತ್ತಡವಿಲ್ಲ.',
  when_call: 'ಯಾವಾಗ ಕರೆ ಮಾಡಲಿ?', w_asap: 'ಆದಷ್ಟು ಬೇಗ', w_today_evening: 'ಇಂದು ಸಂಜೆ 6 ರಿಂದ 9', w_tomorrow_morning: 'ನಾಳೆ ಬೆಳಿಗ್ಗೆ 9 ರಿಂದ 12',
  w_tomorrow_evening: 'ನಾಳೆ ಸಂಜೆ 6 ರಿಂದ 9', w_after_9pm: 'ಇಂದು ರಾತ್ರಿ 9ರ ನಂತರ', call_me: 'ನನಗೆ ಕರೆ ಮಾಡಿ', callback_done: 'ಆಯಿತು. {phone} ಗೆ ಕರೆ ಮಾಡುತ್ತೇವೆ: {window}.',
  route_title: 'ನಿಮ್ಮ ವ್ಯಾಪಾರಕ್ಕೆ ಯಾವ ಪುರಾವೆ ಇದೆ?', route_gst: 'ಜಿಎಸ್‌ಟಿ ಪ್ರಮಾಣಪತ್ರ', route_udyam: 'ಉದ್ಯಮ್, ಜಿಎಸ್‌ಟಿ ಇಲ್ಲ', route_shop: 'ಅಂಗಡಿ ಪರವಾನಗಿ ಮಾತ್ರ',
  doc_shop_licence: 'ಅಂಗಡಿ ಅಥವಾ ವ್ಯಾಪಾರ ಪರವಾನಗಿ', sim_title: 'ಬಿಸಿನೆಸ್ ಸಿಮ್ ಬಳಕೆದಾರರು',
  sim_intro: 'ಕಾನೂನಿನ ಪ್ರಕಾರ ಪ್ರತಿ ಸಿಮ್ ಬಳಕೆದಾರರು ಸ್ವತಃ ಪರಿಶೀಲಿಸಬೇಕು. ಪ್ರತಿಯೊಬ್ಬರಿಗೂ ಲಿಂಕ್ ಕಳುಹಿಸುತ್ತೇವೆ.', sim_name: 'ಹೆಸರು', sim_invite: 'ಲಿಂಕ್ ಕಳುಹಿಸಿ',
  sim_verified: 'ಪರಿಶೀಲಿಸಲಾಗಿದೆ', sim_waiting: 'ಅವರಿಗಾಗಿ ಕಾಯುತ್ತಿದೆ', account_title: 'ನನ್ನ ಖಾತೆ', one_bill: 'ಎಲ್ಲದಕ್ಕೂ ಒಂದೇ ಬಿಲ್',
  next_debit: 'ಮುಂದಿನ ಕಡಿತ', get_help: 'ಸಹಾಯ ಪಡೆಯಿರಿ', setup_tasks: 'ಸೆಟಪ್ ಪೂರ್ಣಗೊಳಿಸಿ', refine_title: 'ನಿಮ್ಮ ಬೆಲೆ ಬದಲಿಸುವ ಒಂದು ಪ್ರಶ್ನೆ',
  quote_changed: 'ನಿಮ್ಮ ಕೊಟೇಶನ್ ಬದಲಾಗಿದೆ', on_hold: 'ತಡೆಹಿಡಿಯಲಾಗಿದೆ', read_aloud: 'ಓದಿ ಹೇಳಿ', verify_me: 'ಡಿಜಿಲಾಕರ್ ಮೂಲಕ ಪರಿಶೀಲಿಸಿ',
  sim_consent: 'ಈ ಸಿಮ್‌ಗಾಗಿ ನನ್ನ ಗುರುತು ಹಂಚಿಕೊಳ್ಳಲು ಒಪ್ಪುತ್ತೇನೆ.', sim_done: 'ನೀವು ಪರಿಶೀಲಿಸಲ್ಪಟ್ಟಿದ್ದೀರಿ. ಈಗ ಸಿಮ್ ಆರಂಭವಾಗಬಹುದು.',
}

const gu: Dict = {
  door_help: 'પસંદગીમાં મદદ કરો', door_help_sub: 'અમે યોગ્ય સૂચવીશું.',
  door_express: 'મને ખબર છે શું જોઈએ', door_express_sub: 'એક મિનિટમાં કિંમત.',
  door_person: 'કોઈની સાથે વાત કરો', door_person_sub: 'તમારી ભાષામાં કૉલ.', door_wa_sub: 'એ જ મદદ, ચેટમાં.',
  resume: 'મારો ઓર્ડર ચાલુ રાખો', express_title: 'જોઈએ તે પસંદ કરો', city_label: 'તમારું શહેર', staff_label: 'વ્યવસાયમાં કેટલા લોકો',
  gst_question: 'શું તમારી પાસે જીએસટીઆઈએન છે?', yes_word: 'હા', no_word: 'ના', from_month: 'મહિને {amount} થી', needs_gst: 'જીએસટીઆઈએન જોઈએ',
  get_price: 'મારી કિંમત જુઓ', all_in: 'દર મહિને, જીએસટી સહિત', due_today: 'આજે ચૂકવવાનું', after_emi: '{n} મહિના પછી',
  setup_instalments: 'સેટઅપ {n} હપ્તામાં', total_commit: '{n} મહિનામાં કુલ',
  today_spend: 'આજે ફોન અને ઇન્ટરનેટ પર મહિને કેટલો ખર્ચ થાય છે?', vs_more: 'આજ કરતાં {diff} વધુ', vs_less: 'આજ કરતાં {diff} ઓછું',
  callback_title: 'અમે તમને કૉલ કરીશું', callback_intro: 'તમારી ભાષા બોલનાર વ્યક્તિ કૉલ કરશે. વેચાણનું દબાણ નહીં.',
  when_call: 'ક્યારે કૉલ કરીએ?', w_asap: 'શક્ય તેટલું જલ્દી', w_today_evening: 'આજે સાંજે 6 થી 9', w_tomorrow_morning: 'કાલે સવારે 9 થી 12',
  w_tomorrow_evening: 'કાલે સાંજે 6 થી 9', w_after_9pm: 'આજે રાત્રે 9 પછી', call_me: 'મને કૉલ કરો', callback_done: 'થઈ ગયું. {phone} પર કૉલ કરીશું: {window}.',
  route_title: 'તમારા વ્યવસાયનો કયો પુરાવો છે?', route_gst: 'જીએસટી પ્રમાણપત્ર', route_udyam: 'ઉદ્યમ, જીએસટી નથી', route_shop: 'ફક્ત દુકાન લાઇસન્સ',
  doc_shop_licence: 'દુકાન અથવા વેપાર લાઇસન્સ', sim_title: 'બિઝનેસ સિમ વપરાશકર્તાઓ',
  sim_intro: 'કાયદા મુજબ દરેક સિમ વપરાશકર્તાએ જાતે ચકાસણી કરવી પડે. અમે દરેકને લિંક મોકલીશું.', sim_name: 'નામ', sim_invite: 'લિંક મોકલો',
  sim_verified: 'ચકાસાયેલ', sim_waiting: 'તેમની રાહ', account_title: 'મારું ખાતું', one_bill: 'બધું એક જ બિલમાં',
  next_debit: 'આગામી કપાત', get_help: 'મદદ મેળવો', setup_tasks: 'સેટઅપ પૂર્ણ કરો', refine_title: 'તમારી કિંમત બદલતો એક પ્રશ્ન',
  quote_changed: 'તમારું ક્વોટેશન બદલાયું', on_hold: 'અટકાવેલ', read_aloud: 'વાંચી સંભળાવો', verify_me: 'ડિજીલોકરથી ચકાસણી કરો',
  sim_consent: 'આ સિમ માટે મારી ઓળખ શેર કરવા હું સંમત છું.', sim_done: 'તમારી ચકાસણી થઈ ગઈ. હવે સિમ ચાલુ થઈ શકે છે.',
}

const bn: Dict = {
  door_help: 'বেছে নিতে সাহায্য করুন', door_help_sub: 'উপযুক্তটি সুপারিশ করব।',
  door_express: 'আমি জানি কী দরকার', door_express_sub: 'এক মিনিটে দাম।',
  door_person: 'কারও সাথে কথা বলুন', door_person_sub: 'আপনার ভাষায় কল।', door_wa_sub: 'একই সাহায্য, চ্যাটে।',
  resume: 'আমার অর্ডার চালিয়ে যান', express_title: 'যা দরকার বেছে নিন', city_label: 'আপনার শহর', staff_label: 'ব্যবসায় কতজন',
  gst_question: 'আপনার কি জিএসটিআইএন আছে?', yes_word: 'হ্যাঁ', no_word: 'না', from_month: 'মাসে {amount} থেকে', needs_gst: 'জিএসটিআইএন লাগবে',
  get_price: 'আমার দাম দেখুন', all_in: 'প্রতি মাসে, জিএসটি সহ', due_today: 'আজ দিতে হবে', after_emi: '{n} মাস পরে',
  setup_instalments: 'সেটআপ {n} কিস্তিতে', total_commit: '{n} মাসে মোট',
  today_spend: 'আজ ফোন ও ইন্টারনেটে মাসে কত খরচ হয়?', vs_more: 'আজকের চেয়ে {diff} বেশি', vs_less: 'আজকের চেয়ে {diff} কম',
  callback_title: 'আমরা আপনাকে কল করব', callback_intro: 'আপনার ভাষায় কথা বলা একজন কল করবেন। বিক্রির চাপ নেই।',
  when_call: 'কখন কল করব?', w_asap: 'যত তাড়াতাড়ি সম্ভব', w_today_evening: 'আজ সন্ধ্যা 6 থেকে 9', w_tomorrow_morning: 'কাল সকাল 9 থেকে 12',
  w_tomorrow_evening: 'কাল সন্ধ্যা 6 থেকে 9', w_after_9pm: 'আজ রাত 9টার পরে', call_me: 'আমাকে কল করুন', callback_done: 'হয়ে গেছে। {phone} নম্বরে কল করব: {window}।',
  route_title: 'আপনার ব্যবসার কোন প্রমাণ আছে?', route_gst: 'জিএসটি সার্টিফিকেট', route_udyam: 'উদ্যম, জিএসটি নেই', route_shop: 'শুধু দোকানের লাইসেন্স',
  doc_shop_licence: 'দোকান বা ট্রেড লাইসেন্স', sim_title: 'ব্যবসায়িক সিম ব্যবহারকারী',
  sim_intro: 'আইন অনুযায়ী প্রতিটি সিম ব্যবহারকারীকে নিজে যাচাই করতে হবে। আমরা প্রত্যেককে লিংক পাঠাব।', sim_name: 'নাম', sim_invite: 'লিংক পাঠান',
  sim_verified: 'যাচাই হয়েছে', sim_waiting: 'তাঁদের অপেক্ষায়', account_title: 'আমার অ্যাকাউন্ট', one_bill: 'সবকিছুর জন্য একটি বিল',
  next_debit: 'পরবর্তী কাটা', get_help: 'সাহায্য নিন', setup_tasks: 'সেটআপ শেষ করুন', refine_title: 'আপনার দাম বদলায় এমন একটি প্রশ্ন',
  quote_changed: 'আপনার কোটেশন বদলেছে', on_hold: 'আটকে আছে', read_aloud: 'পড়ে শোনান', verify_me: 'ডিজিলকার দিয়ে যাচাই করুন',
  sim_consent: 'এই সিমের জন্য আমার পরিচয় শেয়ার করতে আমি সম্মত।', sim_done: 'আপনার যাচাই হয়েছে। এখন সিম চালু হতে পারে।',
}

const ml: Dict = {
  door_help: 'തിരഞ്ഞെടുക്കാൻ സഹായിക്കൂ', door_help_sub: 'യോജിച്ചത് പറഞ്ഞുതരാം.',
  door_express: 'എനിക്ക് എന്ത് വേണമെന്ന് അറിയാം', door_express_sub: 'ഒരു മിനിറ്റിൽ വില.',
  door_person: 'ഒരാളോട് സംസാരിക്കൂ', door_person_sub: 'നിങ്ങളുടെ ഭാഷയിൽ കോൾ.', door_wa_sub: 'അതേ സഹായം, ചാറ്റിൽ.',
  resume: 'എന്റെ ഓർഡർ തുടരുക', express_title: 'വേണ്ടത് തിരഞ്ഞെടുക്കൂ', city_label: 'നിങ്ങളുടെ നഗരം', staff_label: 'ബിസിനസിൽ എത്ര പേർ',
  gst_question: 'നിങ്ങൾക്ക് ജിഎസ്ടിഐഎൻ ഉണ്ടോ?', yes_word: 'ഉണ്ട്', no_word: 'ഇല്ല', from_month: 'മാസം {amount} മുതൽ', needs_gst: 'ജിഎസ്ടിഐഎൻ വേണം',
  get_price: 'എന്റെ വില കാണൂ', all_in: 'ഓരോ മാസവും, ജിഎസ്ടി ഉൾപ്പെടെ', due_today: 'ഇന്ന് അടയ്ക്കേണ്ടത്', after_emi: '{n} മാസത്തിനു ശേഷം',
  setup_instalments: 'സെറ്റപ്പ് {n} തവണകളായി', total_commit: '{n} മാസത്തിൽ ആകെ',
  today_spend: 'ഇന്ന് ഫോണിനും ഇന്റർനെറ്റിനും മാസം എത്ര ചെലവാകുന്നു?', vs_more: 'ഇന്നത്തേക്കാൾ {diff} കൂടുതൽ', vs_less: 'ഇന്നത്തേക്കാൾ {diff} കുറവ്',
  callback_title: 'ഞങ്ങൾ നിങ്ങളെ വിളിക്കാം', callback_intro: 'നിങ്ങളുടെ ഭാഷ സംസാരിക്കുന്നയാൾ വിളിക്കും. വിൽപ്പന സമ്മർദ്ദമില്ല.',
  when_call: 'എപ്പോൾ വിളിക്കണം?', w_asap: 'എത്രയും വേഗം', w_today_evening: 'ഇന്ന് വൈകിട്ട് 6 മുതൽ 9 വരെ', w_tomorrow_morning: 'നാളെ രാവിലെ 9 മുതൽ 12 വരെ',
  w_tomorrow_evening: 'നാളെ വൈകിട്ട് 6 മുതൽ 9 വരെ', w_after_9pm: 'ഇന്ന് രാത്രി 9ന് ശേഷം', call_me: 'എന്നെ വിളിക്കൂ', callback_done: 'ശരി. {phone} നമ്പറിൽ വിളിക്കാം: {window}.',
  route_title: 'നിങ്ങളുടെ ബിസിനസിന് എന്ത് തെളിവുണ്ട്?', route_gst: 'ജിഎസ്ടി സർട്ടിഫിക്കറ്റ്', route_udyam: 'ഉദ്യം, ജിഎസ്ടി ഇല്ല', route_shop: 'കട ലൈസൻസ് മാത്രം',
  doc_shop_licence: 'കട അല്ലെങ്കിൽ ട്രേഡ് ലൈസൻസ്', sim_title: 'ബിസിനസ് സിം ഉപയോക്താക്കൾ',
  sim_intro: 'നിയമപ്രകാരം ഓരോ സിം ഉപയോക്താവും സ്വയം സ്ഥിരീകരിക്കണം. ഓരോരുത്തർക്കും ലിങ്ക് അയയ്ക്കാം.', sim_name: 'പേര്', sim_invite: 'ലിങ്കുകൾ അയയ്ക്കൂ',
  sim_verified: 'സ്ഥിരീകരിച്ചു', sim_waiting: 'അവരെ കാത്തിരിക്കുന്നു', account_title: 'എന്റെ അക്കൗണ്ട്', one_bill: 'എല്ലാത്തിനും ഒരു ബിൽ',
  next_debit: 'അടുത്ത കിഴിവ്', get_help: 'സഹായം നേടൂ', setup_tasks: 'സെറ്റപ്പ് പൂർത്തിയാക്കൂ', refine_title: 'നിങ്ങളുടെ വില മാറ്റുന്ന ഒരു ചോദ്യം',
  quote_changed: 'നിങ്ങളുടെ ക്വട്ടേഷൻ മാറി', on_hold: 'തടഞ്ഞുവച്ചു', read_aloud: 'വായിച്ചു കേൾപ്പിക്കൂ', verify_me: 'ഡിജിലോക്കർ വഴി സ്ഥിരീകരിക്കൂ',
  sim_consent: 'ഈ സിമ്മിനായി എന്റെ തിരിച്ചറിയൽ പങ്കിടാൻ ഞാൻ സമ്മതിക്കുന്നു.', sim_done: 'നിങ്ങൾ സ്ഥിരീകരിച്ചു. ഇനി സിം പ്രവർത്തിക്കാം.',
}

const pa: Dict = {
  door_help: 'ਚੁਣਨ ਵਿੱਚ ਮਦਦ ਕਰੋ', door_help_sub: 'ਅਸੀਂ ਸਹੀ ਚੀਜ਼ ਸੁਝਾਵਾਂਗੇ।',
  door_express: 'ਮੈਨੂੰ ਪਤਾ ਹੈ ਕੀ ਚਾਹੀਦਾ', door_express_sub: 'ਇੱਕ ਮਿੰਟ ਵਿੱਚ ਕੀਮਤ।',
  door_person: 'ਕਿਸੇ ਨਾਲ ਗੱਲ ਕਰੋ', door_person_sub: 'ਤੁਹਾਡੀ ਭਾਸ਼ਾ ਵਿੱਚ ਕਾਲ।', door_wa_sub: 'ਉਹੀ ਮਦਦ, ਚੈਟ ਵਿੱਚ।',
  resume: 'ਮੇਰਾ ਆਰਡਰ ਜਾਰੀ ਰੱਖੋ', express_title: 'ਜੋ ਚਾਹੀਦਾ ਚੁਣੋ', city_label: 'ਤੁਹਾਡਾ ਸ਼ਹਿਰ', staff_label: 'ਕਾਰੋਬਾਰ ਵਿੱਚ ਕਿੰਨੇ ਲੋਕ',
  gst_question: 'ਕੀ ਤੁਹਾਡੇ ਕੋਲ ਜੀਐਸਟੀਆਈਐਨ ਹੈ?', yes_word: 'ਹਾਂ', no_word: 'ਨਹੀਂ', from_month: '{amount} ਪ੍ਰਤੀ ਮਹੀਨਾ ਤੋਂ', needs_gst: 'ਜੀਐਸਟੀਆਈਐਨ ਲੋੜੀਂਦਾ',
  get_price: 'ਮੇਰੀ ਕੀਮਤ ਵੇਖੋ', all_in: 'ਹਰ ਮਹੀਨੇ, ਜੀਐਸਟੀ ਸਮੇਤ', due_today: 'ਅੱਜ ਦੇਣਾ ਹੈ', after_emi: '{n} ਮਹੀਨਿਆਂ ਬਾਅਦ',
  setup_instalments: 'ਸੈੱਟਅੱਪ {n} ਕਿਸ਼ਤਾਂ ਵਿੱਚ', total_commit: '{n} ਮਹੀਨਿਆਂ ਵਿੱਚ ਕੁੱਲ',
  today_spend: 'ਅੱਜ ਫ਼ੋਨ ਅਤੇ ਇੰਟਰਨੈੱਟ ʼਤੇ ਹਰ ਮਹੀਨੇ ਕਿੰਨਾ ਖ਼ਰਚਾ ਹੁੰਦਾ ਹੈ?', vs_more: 'ਅੱਜ ਨਾਲੋਂ {diff} ਵੱਧ', vs_less: 'ਅੱਜ ਨਾਲੋਂ {diff} ਘੱਟ',
  callback_title: 'ਅਸੀਂ ਤੁਹਾਨੂੰ ਕਾਲ ਕਰਾਂਗੇ', callback_intro: 'ਤੁਹਾਡੀ ਭਾਸ਼ਾ ਬੋਲਣ ਵਾਲਾ ਵਿਅਕਤੀ ਕਾਲ ਕਰੇਗਾ। ਵਿਕਰੀ ਦਾ ਦਬਾਅ ਨਹੀਂ।',
  when_call: 'ਕਦੋਂ ਕਾਲ ਕਰੀਏ?', w_asap: 'ਜਿੰਨੀ ਜਲਦੀ ਹੋ ਸਕੇ', w_today_evening: 'ਅੱਜ ਸ਼ਾਮ 6 ਤੋਂ 9', w_tomorrow_morning: 'ਕੱਲ੍ਹ ਸਵੇਰੇ 9 ਤੋਂ 12',
  w_tomorrow_evening: 'ਕੱਲ੍ਹ ਸ਼ਾਮ 6 ਤੋਂ 9', w_after_9pm: 'ਅੱਜ ਰਾਤ 9 ਤੋਂ ਬਾਅਦ', call_me: 'ਮੈਨੂੰ ਕਾਲ ਕਰੋ', callback_done: 'ਹੋ ਗਿਆ। ਅਸੀਂ {phone} ʼਤੇ ਕਾਲ ਕਰਾਂਗੇ: {window}।',
  route_title: 'ਤੁਹਾਡੇ ਕਾਰੋਬਾਰ ਦਾ ਕਿਹੜਾ ਸਬੂਤ ਹੈ?', route_gst: 'ਜੀਐਸਟੀ ਸਰਟੀਫਿਕੇਟ', route_udyam: 'ਉਦਯਮ, ਜੀਐਸਟੀ ਨਹੀਂ', route_shop: 'ਸਿਰਫ਼ ਦੁਕਾਨ ਲਾਇਸੈਂਸ',
  doc_shop_licence: 'ਦੁਕਾਨ ਜਾਂ ਵਪਾਰ ਲਾਇਸੈਂਸ', sim_title: 'ਬਿਜ਼ਨਸ ਸਿਮ ਵਰਤੋਂਕਾਰ',
  sim_intro: 'ਕਾਨੂੰਨ ਅਨੁਸਾਰ ਹਰ ਸਿਮ ਵਰਤੋਂਕਾਰ ਨੂੰ ਖ਼ੁਦ ਪੁਸ਼ਟੀ ਕਰਨੀ ਪੈਂਦੀ ਹੈ। ਅਸੀਂ ਹਰ ਇੱਕ ਨੂੰ ਲਿੰਕ ਭੇਜਾਂਗੇ।', sim_name: 'ਨਾਮ', sim_invite: 'ਲਿੰਕ ਭੇਜੋ',
  sim_verified: 'ਪੁਸ਼ਟੀ ਹੋਈ', sim_waiting: 'ਉਹਨਾਂ ਦੀ ਉਡੀਕ', account_title: 'ਮੇਰਾ ਖਾਤਾ', one_bill: 'ਹਰ ਚੀਜ਼ ਲਈ ਇੱਕ ਬਿੱਲ',
  next_debit: 'ਅਗਲੀ ਕਟੌਤੀ', get_help: 'ਮਦਦ ਲਓ', setup_tasks: 'ਸੈੱਟਅੱਪ ਪੂਰਾ ਕਰੋ', refine_title: 'ਤੁਹਾਡੀ ਕੀਮਤ ਬਦਲਣ ਵਾਲਾ ਇੱਕ ਸਵਾਲ',
  quote_changed: 'ਤੁਹਾਡਾ ਕੋਟੇਸ਼ਨ ਬਦਲਿਆ', on_hold: 'ਰੋਕਿਆ ਗਿਆ', read_aloud: 'ਪੜ੍ਹ ਕੇ ਸੁਣਾਓ', verify_me: 'ਡਿਜੀਲਾਕਰ ਨਾਲ ਪੁਸ਼ਟੀ ਕਰੋ',
  sim_consent: 'ਮੈਂ ਇਸ ਸਿਮ ਲਈ ਆਪਣੀ ਪਛਾਣ ਸਾਂਝੀ ਕਰਨ ਲਈ ਸਹਿਮਤ ਹਾਂ।', sim_done: 'ਤੁਹਾਡੀ ਪੁਸ਼ਟੀ ਹੋ ਗਈ। ਹੁਣ ਸਿਮ ਚਾਲੂ ਹੋ ਸਕਦਾ ਹੈ।',
}

// navigation: home and the orders placed on this phone
const NAV: Record<string, [string, string, string]> = {
  en: ['Home', 'My orders', 'No orders on this phone yet.'],
  hi: ['होम', 'मेरे ऑर्डर', 'इस फ़ोन पर अभी कोई ऑर्डर नहीं है।'],
  mr: ['होम', 'माझ्या ऑर्डर', 'या फोनवर अजून कोणतीही ऑर्डर नाही.'],
  ta: ['முகப்பு', 'என் ஆர்டர்கள்', 'இந்த போனில் இன்னும் ஆர்டர் இல்லை.'],
  te: ['హోమ్', 'నా ఆర్డర్లు', 'ఈ ఫోన్‌లో ఇంకా ఆర్డర్లు లేవు.'],
  kn: ['ಮುಖಪುಟ', 'ನನ್ನ ಆರ್ಡರ್‌ಗಳು', 'ಈ ಫೋನ್‌ನಲ್ಲಿ ಇನ್ನೂ ಆರ್ಡರ್ ಇಲ್ಲ.'],
  gu: ['હોમ', 'મારા ઓર્ડર', 'આ ફોન પર હજી કોઈ ઓર્ડર નથી.'],
  bn: ['হোম', 'আমার অর্ডার', 'এই ফোনে এখনও কোনো অর্ডার নেই।'],
  ml: ['ഹോം', 'എന്റെ ഓർഡറുകൾ', 'ഈ ഫോണിൽ ഇതുവരെ ഓർഡറുകളില്ല.'],
  pa: ['ਹੋਮ', 'ਮੇਰੇ ਆਰਡਰ', 'ਇਸ ਫ਼ੋਨ ʼਤੇ ਅਜੇ ਕੋਈ ਆਰਡਰ ਨਹੀਂ।'],
}
for (const [k, [home, mine, none]] of Object.entries(NAV)) {
  Object.assign(({ en, hi, mr, ta, te, kn, gu, bn, ml, pa } as Record<string, Dict>)[k], { home, my_orders: mine, no_orders: none })
}

// consent for the optional second reader (AI reading of business documents)
const AI: Record<string, [string, string, string]> = {
  en: ['AI reading of my business documents', 'An AI service (Anthropic, outside India) reads your GST, Udyam, shop licence or bill to fill your details. ID cards are never sent. Say no and our own reader and a person check them.', 'Not used to train AI.'],
  hi: ['मेरे व्यवसाय के दस्तावेज़ एआई से पढ़वाना', 'एक एआई सेवा (एंथ्रोपिक, भारत से बाहर) आपका जीएसटी, उद्यम, दुकान लाइसेंस या बिल पढ़कर जानकारी भरती है। पहचान पत्र कभी नहीं भेजे जाते। मना करने पर हमारा अपना रीडर और एक व्यक्ति जाँच करेंगे।', 'एआई को सिखाने में इस्तेमाल नहीं होता।'],
  mr: ['माझी व्यवसाय कागदपत्रे एआयने वाचणे', 'एक एआय सेवा (अँथ्रॉपिक, भारताबाहेर) तुमचे जीएसटी, उद्यम, दुकान परवाना किंवा बिल वाचून माहिती भरते. ओळखपत्रे कधीच पाठवली जात नाहीत. नकार दिल्यास आमचा स्वतःचा रीडर आणि एक व्यक्ती तपासतील.', 'एआयला शिकवण्यासाठी वापरले जात नाही.'],
  ta: ['என் வணிக ஆவணங்களை ஏஐ படிப்பது', 'ஒரு ஏஐ சேவை (ஆந்த்ரோபிக், இந்தியாவுக்கு வெளியே) உங்கள் ஜிஎஸ்டி, உத்யம், கடை உரிமம் அல்லது ரசீதைப் படித்து விவரங்களை நிரப்பும். அடையாள அட்டைகள் ஒருபோதும் அனுப்பப்படாது. மறுத்தால் எங்கள் சொந்த ரீடரும் ஒருவரும் சரிபார்ப்பார்கள்.', 'ஏஐக்கு பயிற்சி அளிக்கப் பயன்படுத்தப்படாது.'],
  te: ['నా వ్యాపార పత్రాలను ఏఐ చదవడం', 'ఒక ఏఐ సేవ (ఆంత్రోపిక్, భారతదేశం బయట) మీ జీఎస్టీ, ఉద్యమ్, షాప్ లైసెన్స్ లేదా బిల్లును చదివి వివరాలు నింపుతుంది. గుర్తింపు కార్డులు ఎప్పుడూ పంపబడవు. వద్దంటే మా స్వంత రీడర్, ఒక వ్యక్తి తనిఖీ చేస్తారు.', 'ఏఐకి శిక్షణ ఇవ్వడానికి వాడబడదు.'],
  kn: ['ನನ್ನ ವ್ಯಾಪಾರ ದಾಖಲೆಗಳನ್ನು ಎಐ ಓದುವುದು', 'ಒಂದು ಎಐ ಸೇವೆ (ಆಂಥ್ರೋಪಿಕ್, ಭಾರತದ ಹೊರಗೆ) ನಿಮ್ಮ ಜಿಎಸ್‌ಟಿ, ಉದ್ಯಮ್, ಅಂಗಡಿ ಪರವಾನಗಿ ಅಥವಾ ಬಿಲ್ ಓದಿ ವಿವರ ತುಂಬುತ್ತದೆ. ಗುರುತಿನ ಚೀಟಿಗಳನ್ನು ಎಂದಿಗೂ ಕಳುಹಿಸುವುದಿಲ್ಲ. ಬೇಡವೆಂದರೆ ನಮ್ಮದೇ ರೀಡರ್ ಮತ್ತು ಒಬ್ಬ ವ್ಯಕ್ತಿ ಪರಿಶೀಲಿಸುತ್ತಾರೆ.', 'ಎಐಗೆ ತರಬೇತಿ ನೀಡಲು ಬಳಸುವುದಿಲ್ಲ.'],
  gu: ['મારા વ્યવસાયના દસ્તાવેજો એઆઈ વડે વાંચવા', 'એક એઆઈ સેવા (એન્થ્રોપિક, ભારત બહાર) તમારું જીએસટી, ઉદ્યમ, દુકાન લાઇસન્સ અથવા બિલ વાંચી વિગતો ભરે છે. ઓળખપત્રો ક્યારેય મોકલાતા નથી. ના પાડો તો અમારું પોતાનું રીડર અને એક વ્યક્તિ ચકાસશે.', 'એઆઈને તાલીમ આપવા માટે વપરાતું નથી.'],
  bn: ['আমার ব্যবসার নথি এআই দিয়ে পড়ানো', 'একটি এআই পরিষেবা (অ্যানথ্রোপিক, ভারতের বাইরে) আপনার জিএসটি, উদ্যম, দোকানের লাইসেন্স বা বিল পড়ে তথ্য পূরণ করে। পরিচয়পত্র কখনও পাঠানো হয় না। না বললে আমাদের নিজস্ব রিডার ও একজন ব্যক্তি যাচাই করবেন।', 'এআই প্রশিক্ষণে ব্যবহার হয় না।'],
  ml: ['എന്റെ ബിസിനസ് രേഖകൾ എഐ വായിക്കുന്നത്', 'ഒരു എഐ സേവനം (ആന്ത്രോപിക്, ഇന്ത്യക്ക് പുറത്ത്) നിങ്ങളുടെ ജിഎസ്ടി, ഉദ്യം, കട ലൈസൻസ് അല്ലെങ്കിൽ ബിൽ വായിച്ച് വിവരങ്ങൾ പൂരിപ്പിക്കും. തിരിച്ചറിയൽ കാർഡുകൾ ഒരിക്കലും അയയ്ക്കില്ല. വേണ്ടെന്ന് പറഞ്ഞാൽ ഞങ്ങളുടെ സ്വന്തം റീഡറും ഒരാളും പരിശോധിക്കും.', 'എഐയെ പരിശീലിപ്പിക്കാൻ ഉപയോഗിക്കില്ല.'],
  pa: ['ਮੇਰੇ ਕਾਰੋਬਾਰੀ ਦਸਤਾਵੇਜ਼ ਏਆਈ ਤੋਂ ਪੜ੍ਹਾਉਣਾ', 'ਇੱਕ ਏਆਈ ਸੇਵਾ (ਐਂਥ੍ਰੋਪਿਕ, ਭਾਰਤ ਤੋਂ ਬਾਹਰ) ਤੁਹਾਡਾ ਜੀਐਸਟੀ, ਉਦਯਮ, ਦੁਕਾਨ ਲਾਇਸੈਂਸ ਜਾਂ ਬਿੱਲ ਪੜ੍ਹ ਕੇ ਵੇਰਵੇ ਭਰਦੀ ਹੈ। ਪਛਾਣ ਪੱਤਰ ਕਦੇ ਨਹੀਂ ਭੇਜੇ ਜਾਂਦੇ। ਨਾਂਹ ਕਹਿਣ ʼਤੇ ਸਾਡਾ ਆਪਣਾ ਰੀਡਰ ਅਤੇ ਇੱਕ ਵਿਅਕਤੀ ਜਾਂਚ ਕਰਨਗੇ।', 'ਏਆਈ ਨੂੰ ਸਿਖਾਉਣ ਲਈ ਵਰਤਿਆ ਨਹੀਂ ਜਾਂਦਾ।'],
}
for (const [k, [title, use, keep]] of Object.entries(AI)) {
  Object.assign(({ en, hi, mr, ta, te, kn, gu, bn, ml, pa } as Record<string, Dict>)[k], { p_ai_document_reading: title, p_ai_document_reading_use: use, p_ai_document_reading_keep: keep })
}

export const MORE: Record<string, Dict> = { en, hi, mr, ta, te, kn, gu, bn, ml, pa }
