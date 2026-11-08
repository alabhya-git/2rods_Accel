"""Recapture submission evidence against an isolated local demo, using synthetic applicants."""
import sys
from pathlib import Path
import httpx
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / 'docs/video/shots'
BASE = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://127.0.0.1:8007'
c = httpx.Client(base_url=BASE, timeout=120)

def post(path, data):
    r = c.post(path, json=data)
    r.raise_for_status()
    return r.json()

def order(sid=None, specimen='K09'):
    data = {'items': {'P02':1,'P07':25,'P16':25}, 'term_months':24, 'phone':'9876543210', 'specimen':specimen}
    if sid:
        data['session_id'] = sid
        session=c.get('/api/advisor/sessions/'+sid).json()
        data['items']={x['product_id']:x['qty'] for x in session['bundle']['lines']}
        data['items']['P09']=1
    else: data['profile'] = {'segment':'prof','business_type':'Insurance agency','employees':25,'sites':1,'city':'Visakhapatnam','city_tier':2,'has_gstin':True}
    o = post('/api/orders', data)
    return o, f"/api/orders/{o['order_id']}", f"?key={o['access_key']}"

def go(page, path):
    page.goto(BASE+path, wait_until='networkidle')
    page.wait_for_timeout(500)

def shot(page, *names):
    page.wait_for_timeout(350)
    for name in names:
        page.screenshot(path=str(SHOTS / (name+'.jpg')), type='jpeg', quality=92)
    assert 'Accel' not in page.locator('body').inner_text(), page.url
    print('Captured '+', '.join(names), flush=True)

def scroll(page, y=0):
    page.evaluate('(y) => window.scrollTo(0,y)', y)
    page.wait_for_timeout(250)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={'width':390,'height':844},device_scale_factor=2)
    page = ctx.new_page()
    errors=[]
    page.on('pageerror', lambda e:errors.append(str(e)))
    go(page,'/?lang=en'); shot(page,'home_en')
    go(page,'/?lang=te'); shot(page,'home_te')
    go(page,'/advisor?lang=te'); shot(page,'adv_greet')
    box=page.get_by_role('textbox').first
    msg='విశాఖపట్నంలో మా ఇన్సూరెన్స్ ఏజెన్సీ ఉంది, 25 మంది ఉద్యోగులు. 1 Gbps ఇంటర్నెట్, ఈమెయిల్ కావాలి.'
    for i in range(1,7):
        box.fill(msg[:round(len(msg)*i/6)]);shot(page,f'adv_type1_{i}')
    with page.expect_response(lambda r:r.url.endswith('/messages') and r.request.method=='POST'):
        box.press('Enter');shot(page,'adv_wait1')
    page.wait_for_timeout(600);shot(page,'adv_ask_gstin')
    for i in range(1,4):
        box.fill('37LDYXK0296F1ZB'[:round(15*i/3)]);shot(page,f'adv_type2_{i}')
    with page.expect_response(lambda r:r.url.endswith('/messages') and r.request.method=='POST') as response:box.press('Enter')
    session=response.value.json();sid=session['session_id']
    assert session['bundle'], session['turn']
    page.wait_for_timeout(600);shot(page,'adv_reco_end')
    page.locator('.bubble-ai').last.scroll_into_view_if_needed();shot(page,'adv_reco_top')
    why=page.get_by_role('button',name='ఇది ఎందుకు?')
    if why.count():why.click()
    shot(page,'adv_why')
    go(page,f'/quote?session={sid}&lang=te');shot(page,'quote_top')
    addon=page.get_by_role('checkbox',name='Backup 4G/5G Failover')
    if addon.count():
        addon.scroll_into_view_if_needed();shot(page,'quote_addons');addon.click();page.wait_for_timeout(400)
    shot(page,'quote_failover_on')
    term=page.get_by_role('radio',name='24 నెలలు')
    if term.count():term.click()
    shot(page,'quote_24')
    phone=page.get_by_placeholder('98XXXXXXXX')
    phone.scroll_into_view_if_needed()
    for i in [1,2]:phone.fill('9876543210'[:i*5]);shot(page,f'quote_phone_{i}')
    o,api,key=order(sid)
    oid=o['order_id'];access=o['access_key']
    path=f'/order/{oid}'
    go(page,path+'/consent'+key+'&lang=te');shot(page,'consent_te')
    page.get_by_role('button',name='Change language').click();shot(page,'lang_menu')
    page.get_by_role('button',name='English',exact=True).click();shot(page,'consent_en')
    switches=page.get_by_role('switch')
    for switch in switches.all():
        if switch.is_enabled() and 'update' in (switch.get_attribute('aria-label') or '').lower():switch.click();break
    shot(page,'consent_updates_on')
    post(api+'/consent'+key,{'choices':{'kyc_verification':True,'service_delivery':True,'order_updates':True}})
    go(page,path+'/kyc'+key+'&lang=en');shot(page,'kyc_top')
    gst=page.locator('#gstin')
    if gst.count():
        for i in [1,2]:gst.fill('37LDYXK0296F1ZB'[:round(15*i/2)]);shot(page,f'kyc_gstin_{i}')
        check=page.get_by_role('button',name='Check',exact=True)
        if check.count():check.click();page.wait_for_timeout(400)
    else:shot(page,'kyc_gstin_1','kyc_gstin_2')
    shot(page,'kyc_registry','kyc_reading')
    page.get_by_text('Demo: use a specimen applicant').click()
    with page.expect_response(lambda r:r.url.split('?')[0].endswith('/kyc/specimen') and r.request.method=='POST',timeout=120000):
        page.get_by_role('button',name='K09',exact=True).click()
    page.wait_for_timeout(800);scroll(page,260);shot(page,'kyc_docs_1')
    scroll(page,800);shot(page,'kyc_docs_2','kyc_verified')
    for tag in ['K11','K06']:
        oo,aa,kk=order(specimen=tag)
        post(aa+'/consent'+kk,{'choices':{'kyc_verification':True,'service_delivery':True}})
        post(aa+'/kyc/specimen'+kk,{'specimen':tag})
        if tag=='K11':
            go(page,f"/order/{oo['order_id']}/kyc"+kk+'&lang=en');scroll(page,650);shot(page,'k11_fix');scroll(page,300);shot(page,'k11_bill')
    go(page,path+'/pay'+key+'&lang=en');shot(page,'pay_top')
    upi=page.get_by_placeholder('name@bank')
    for i in [1,2]:upi.fill('anita@okaxis'[:round(12*i/2)]);shot(page,f'pay_upi_{i}')
    post(api+'/pay'+key,{'method':'upi_autopay','upi_id':'anita@okaxis'})
    go(page,path+'/pay'+key+'&lang=en');shot(page,'pay_paid','pay_slot')
    days=c.get(api+'/slots'+key).json()['days'];slot=days[0]['date']+' '+days[0]['slots'][0]
    post(api+'/schedule'+key,{'slot':slot})
    go(page,f'/track/{oid}'+key+'&lang=en');shot(page,'track_progress')
    v=c.get(api+key).json();need=sum(x['qty'] for x in v['bundle']['lines'] if x['product_id'] in ['P07','P08'])
    if need:
        users=post(api+'/sim-users'+key,{'users':[{'name':f'Staff {i}','phone':f'98000000{i:02d}'} for i in range(need)]})
        for u in users['users']:post(f"/api/sim/{u['id']}/verify",{'method':'digilocker','consent':True})
    for i in range(10):
        v=post(api+'/advance'+key,{})
        if v['status']=='active':break
    go(page,f'/track/{oid}'+key+'&lang=en');shot(page,'track_live');scroll(page,1600);shot(page,'track_data')
    go(page,'/whatsapp?lang=en');page.screenshot(path=str(ROOT/'docs/screens/15_whatsapp.png'))
    desktop=b.new_context(viewport={'width':1440,'height':810},device_scale_factor=1.3333)
    dp=desktop.new_page()
    go(dp,'/partner?lang=en')
    dp.get_by_role('button',name='Partner (sales shop)').click();dp.get_by_role('button',name='Sign in',exact=True).click();dp.wait_for_timeout(1000)
    dp.get_by_role('button',name='Leads to call',exact=True).click();dp.wait_for_timeout(500);shot(dp,'partner_queue')
    call=dp.get_by_role('button',name='Call (masked)').first
    if call.count():call.click()
    shot(dp,'partner_call')
    dp.get_by_role('button',name='Metrics',exact=True).click();dp.wait_for_timeout(600);shot(dp,'partner_metrics')
    dp.get_by_role('button',name='Lead score',exact=True).click();dp.wait_for_timeout(500);dp.screenshot(path=str(ROOT/'docs/screens/13_partner_model.png'))
    reviewer=post('/api/staff/login',{'user':'reviewer-1','secret':'review-demo'})
    dp.evaluate('(w)=>{sessionStorage.setItem("staff",JSON.stringify(w));sessionStorage.setItem("staff_token",w.token)}',reviewer)
    go(dp,'/partner');dp.get_by_role('button',name='KYC reviews',exact=True).click();dp.wait_for_timeout(600);shot(dp,'partner_reviews')
    go(dp,'/judge?lang=en');dp.get_by_role('button',name='Run all',exact=True).click();dp.wait_for_timeout(700);shot(dp,'judge_scenarios')
    dp.get_by_role('button',name='Run OCR and checks').click();dp.wait_for_timeout(2000)
    dp.get_by_text('false rejections').wait_for(timeout=120000)
    dp.get_by_role('heading',name='Smart KYC on the 12 specimen applicants').scroll_into_view_if_needed();shot(dp,'judge_kyc')
    go(dp,f'/advisor?session={sid}&lang=en');dp.screenshot(path=str(ROOT/'docs/screens/10_advisor_desktop_why.png'))
    go(page,'/advisor?lang=hi');page.screenshot(path=str(ROOT/'docs/screens/16_advisor_hi.png'))
    b.close()

mapping={'01_home':'home_en','01b_home_te':'home_te','02_advisor':'adv_reco_top','03_quote':'quote_top','04_consent':'consent_en','05_kyc_empty':'kyc_top','06_kyc_verified':'kyc_verified','07_pay':'pay_paid','08_tracker':'track_live','11_judge':'judge_scenarios','12_partner_queue':'partner_queue','14_partner_metrics':'partner_metrics'}
deck={'1_advisor_te':'adv_reco_top','2_quote':'quote_top','3_consent':'consent_en','4_kyc_verified':'kyc_verified','4b_kyc_top':'kyc_docs_1','5_pay':'pay_paid','6_tracker':'track_progress','7_tracker_live':'track_live','debug_track':'track_progress'}
for folder,items in [('docs/screens',mapping),('docs/screens/deck',deck)]:
    for dst,src in items.items():Image.open(SHOTS/(src+'.jpg')).save(ROOT/folder/(dst+'.png'))
print('All submission screenshots refreshed; page errors:',errors,flush=True)
