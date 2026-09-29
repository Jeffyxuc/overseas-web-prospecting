"""Offline behavioral checks using explicitly fictional example.com businesses."""
import base64
from contextlib import redirect_stdout
from email import policy
from email.parser import BytesParser
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
import workflow as w

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII=')


def call(fn, **args):
    with redirect_stdout(io.StringIO()):
        return fn(NS(**args))


def fixture(root, kind='catalog', finish=True):
    root = Path(root)
    names = {'catalog':'Sample & Co — Fictional Bakery','booking':'Sample Studio — Fictional Services','quote':'Sample Works — Fictional Home Services'}
    call(w.init, run=str(root), location='Fictional sample region', industry=kind, language='en')
    raw = root / 'work/raw.json'
    w.write(raw, [{'title':names[kind],'place_id':'fictional-one','address':'Illustrative address only','website':'https://example.com/','link':'https://example.com/maps/one','review_rating':4.5,'review_count':12}])
    pool = root / 'work/pool.json'
    call(w.normalize, input=str(raw), out=str(pool))
    bid = w.read(pool)['businesses'][0]['id']
    fact = {'kind':'fact','text':'Synthetic test fixture; not researched from a real business.','source_url':'https://example.com/','observed_at':w.now()}
    inp = root / 'work/shortlist.json'
    w.write(inp, {'coverage_note':'One explicitly fictional test fixture, not live discovery.','candidates':[{'business_id':bid,'priority':'medium','website_status':'reviewed','reason':'Exercise the workflow with synthetic data.','opportunity':'Demonstrate a local request journey.','evidence':[fact]}]})
    call(w.shortlist, run=str(root), pool=str(pool), input=str(inp))
    call(w.select, run=str(root), business_id=bid, message='TEST FIXTURE: select sample')
    analysis = root / 'work/analysis.json'
    w.write(analysis, {'business_id':bid,'summary':'Fictional sample; no real business research performed.','findings':[fact], 'contacts':[{'email':'hello@example.com','source_url':'https://example.com/contact','checked_at':w.now()}]})
    call(w.analysis, run=str(root), input=str(analysis))
    plan = root / 'work/plan.json'
    w.write(plan, {'business_id':bid,'goal':'Synthetic example of an independent business website concept.','pages':['Single page concept'],'visual_direction':'Warm editorial typography and abstract shapes.','interactions':['Choose an option and date; preview an unsent request.'],'materials':'Fictional text and CSS decoration only.','demo_limits':'No real order, payment, booking or message.','delivery':'Local-only test; no actual public hosting.'})
    call(w.plan, run=str(root), input=str(plan))
    call(w.approve, run=str(root), message='TEST FIXTURE approval, not a production user approval')
    config = root / 'work/config.json'
    items = {'catalog':[('Morning loaf','An illustrative product for exploring the pickup concept.'),('Seasonal bake','A sample selection; no actual product, price or availability.'),('Weekend box','A demonstration option for a planned visit.')], 'booking':[('A moment to unwind','A fictional appointment option for testing the booking journey.'),('A fresh start','Illustrative service content, ready to replace with researched details.'),('A little extra care','A sample service; no real appointments are available.')], 'quote':[('Everyday maintenance','A fictional service used to demonstrate a quote request.'),('A room refreshed','An illustrative scope for planning a small project.'),('A bigger change','A sample project category, not an actual service offer.')]}
    taglines = {'catalog':'Good things. Worth making time for.','booking':'A little time, just for you.','quote':'Good care for the place you call home.'}
    w.write(config, {'business_id':bid,'name':names[kind],'tagline':taglines[kind],'intro':'A fictional business created to demonstrate this Skill. Explore the sample design and try a request preview.','address':'Fictional example — no physical business or address.','eyebrow':'Fictional sample · '+kind,'items':[{'title':t,'description':d} for t,d in items[kind]]})
    call(w.scaffold, run=str(root), kind=kind, input=str(config))
    profile = root / 'work/profile.json'
    w.write(profile, {'name':'Sample Sender','company':'Example Studio','company_description':'an independent web design studio','location':'Example City','signature':'Sample Sender\nExample Studio','from_email':'sender@example.com'})
    if finish:
        shot = root / 'screenshots/desktop.png'
        shot.parent.mkdir(parents=True,exist_ok=True)
        shot.write_bytes(PNG)
        mark_demo(root,bid)
    return root, bid


def mark_demo(root, bid, shared=False):
    doc = {'business_id':bid,'source_path':'demo','checks':{k:{'passed':True,'evidence':'Synthetic assertion for script test only; not browser verification.'} for k in ['desktop','mobile','core_flow','content','no_real_submission']}, 'screenshots':[{'path':'screenshots/desktop.png','caption':'Synthetic test image','captured_at':w.now()}], 'public_access':{'verified':False}}
    if shared:
        doc['public_access'] = {'verified':True,'no_login':True,'url':'https://example.com/fictional-demo','checked_at':w.now(),'evidence':'Synthetic fixture only. Not a real deployed demo.'}
    path = root / 'work/demo-ready.json'
    w.write(path,doc)
    call(w.demo_ready,run=str(root),input=str(path))


def mail_input(root,bid,recipient='hello@example.com'):
    state = w.load_run(root)
    path = root / 'work/copy.json'
    w.write(path, {'business_id':bid,'demo_sha256':state['demo']['sha256'],'recipient':recipient,'subject':'A website concept for a fictional sample','greeting':'Hi Sample team,','observation':'This is a fictional demonstration, not a real prospecting message.','demo_intro':'I created a local website concept showing a request preview.','business_value':'Visitors can choose an option and a date before reviewing a simulated request.','disclosure':'Independent demonstration only. No real request, payment or email is sent.','chinese_translation':'虚构测试邮件，仅用于检查文件生成，不得发送。'})
    return path


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'run'

    def tearDown(self):
        self.tmp.cleanup()

    def test_jsonl_dedupe_preserves_branches_and_merges_emails(self):
        p = Path(self.tmp.name) / 'raw.json'
        rows = [{'title':'Shop','place_id':'a','address':'A','website':'https://example.com','emails':'one@example.com'}, {'title':'Shop','place_id':'a','address':'A','emails':['two@example.com']}, {'title':'Shop','place_id':'b','address':'B','website':'https://example.com'}, {'title':''}]
        p.write_text('\n'.join(json.dumps(x) for x in rows),encoding='utf-8')
        out = p.with_name('pool.json')
        call(w.normalize,input=str(p),out=str(out))
        data = w.read(out)
        self.assertEqual(len(data['businesses']),2)
        self.assertEqual(data['skipped_no_name'],1)
        self.assertEqual(data['businesses'][0]['emails_unverified'],['one@example.com','two@example.com'])

    def test_csv_multiline_and_bom(self):
        p = Path(self.tmp.name) / 'raw.csv'
        p.write_text('title,address,website\n"Sample, Bakery","Line one\nLine two",https://example.com\n',encoding='utf-8-sig')
        out=p.with_name('pool.json')
        call(w.normalize,input=str(p),out=str(out))
        self.assertEqual(w.read(out)['businesses'][0]['address'],'Line one\nLine two')

    def test_complete_mail_mime_and_escaping(self):
        root,bid = fixture(self.root)
        mark_demo(root,bid,shared=True)
        copy = mail_input(root,bid)
        doc=w.read(copy);doc['observation']='<script>alert(1)</script>';w.write(copy,doc)
        call(w.mail,run=str(root),input=str(copy),profile=str(root/'work/profile.json'))
        state=w.load_run(root)
        self.assertEqual(state['stage'],'complete')
        out=root/state['email']['path']
        msg=BytesParser(policy=policy.default).parsebytes((out/'outreach-draft.eml').read_bytes())
        self.assertEqual(str(msg['To']),'hello@example.com')
        self.assertTrue(msg.get_body(preferencelist=('plain',)))
        body=msg.get_body(preferencelist=('html',)).get_content()
        self.assertIn('cid:demo-preview',body)
        self.assertIn('&lt;script&gt;',body)
        self.assertNotIn('<script>',body)
        images=[p for p in msg.walk() if p.get_content_maintype()=='image']
        self.assertEqual(len(images),1)
        self.assertEqual(images[0].get_content_type(),'image/png')
        self.assertEqual(images[0].get_payload(decode=True),PNG)

    def test_local_demo_produces_draft_without_eml(self):
        root,bid=fixture(self.root)
        copy=mail_input(root,bid)
        call(w.mail,run=str(root),input=str(copy),profile=str(root/'work/profile.json'))
        state=w.load_run(root);out=root/state['email']['path']
        self.assertEqual(state['stage'],'email_needs_input')
        self.assertFalse((out/'outreach-draft.eml').exists())
        self.assertNotIn('no login or installation required',(out/'email.txt').read_text(encoding='utf-8'))

    def test_missing_email_is_draft(self):
        root,bid=fixture(self.root)
        mark_demo(root,bid,True)
        copy=mail_input(root,bid,'')
        call(w.mail,run=str(root),input=str(copy),profile=str(root/'work/profile.json'))
        state=w.load_run(root)
        self.assertEqual(state['email']['status'],'needs_input')
        self.assertFalse((root/state['email']['path']/'outreach-draft.eml').exists())

    def test_guessed_email_rejected(self):
        root,bid=fixture(self.root)
        copy=mail_input(root,bid,'invented@example.com')
        with self.assertRaisesRegex(ValueError,'Recipient'):
            call(w.mail,run=str(root),input=str(copy),profile=str(root/'work/profile.json'))

    def test_stale_source_rejected(self):
        root,bid=fixture(self.root)
        copy=mail_input(root,bid)
        with (root/'demo/styles.css').open('a') as f:f.write('\nbody{color:red}')
        with self.assertRaisesRegex(ValueError,'source changed'):
            call(w.mail,run=str(root),input=str(copy),profile=str(root/'work/profile.json'))

    def test_changed_screenshot_rejected(self):
        root,bid=fixture(self.root)
        (root/'screenshots/desktop.png').write_bytes(PNG+b'changed')
        with self.assertRaisesRegex(ValueError,'Screenshot changed'):
            w.current_demo(root,w.load_run(root))

    def test_new_plan_invalidates_approval_and_demo(self):
        root,bid=fixture(self.root)
        plan=w.read(root/'work/plan.json');plan['goal']='Changed';w.write(root/'work/plan.json',plan)
        call(w.plan,run=str(root),input=str(root/'work/plan.json'))
        state=w.load_run(root)
        self.assertNotIn('approval',state);self.assertNotIn('demo',state)
        with self.assertRaisesRegex(ValueError,'not been approved'):w.approved(root,state)

    def test_select_invalidates_downstream_but_retains_history(self):
        root,bid=fixture(self.root)
        before=list((root/'records').glob('*.json'))
        call(w.select,run=str(root),business_id=bid,message='TEST: choose again')
        state=w.load_run(root)
        self.assertNotIn('analysis',state);self.assertNotIn('plan',state)
        self.assertEqual(len(list((root/'records').glob('*.json'))),len(before))

    def test_outside_screenshot_rejected(self):
        root,bid=fixture(self.root)
        doc=w.read(root/'work/demo-ready.json');doc['screenshots'][0]['path']='../../outside.png';w.write(root/'work/demo-ready.json',doc)
        with self.assertRaisesRegex(ValueError,'inside'):
            call(w.demo_ready,run=str(root),input=str(root/'work/demo-ready.json'))

    def test_private_or_local_link_rejected(self):
        root,bid=fixture(self.root)
        doc=w.read(root/'work/demo-ready.json');doc['public_access']={'verified':True,'no_login':True,'url':'http://127.0.0.1:8000','evidence':'TEST','checked_at':w.now()};w.write(root/'work/demo-ready.json',doc)
        with self.assertRaisesRegex(ValueError,'external'):
            call(w.demo_ready,run=str(root),input=str(root/'work/demo-ready.json'))

    def test_header_injection_rejected(self):
        root,bid=fixture(self.root)
        copy=mail_input(root,bid);doc=w.read(copy);doc['subject']='Test\nBcc: other@example.com';w.write(copy,doc)
        with self.assertRaisesRegex(ValueError,'header'):
            call(w.mail,run=str(root),input=str(copy),profile=str(root/'work/profile.json'))

    def test_record_tampering_rejected(self):
        root,bid=fixture(self.root)
        state=w.load_run(root);path=root/state['plan']['path'];doc=w.read(path);doc['goal']='tampered';w.write(path,doc)
        with self.assertRaisesRegex(ValueError,'changed outside'):w.approved(root,state)

    def test_wrong_customer_rejected(self):
        root,bid=fixture(self.root)
        doc=w.read(root/'work/analysis.json');doc['business_id']='wrong';w.write(root/'work/analysis.json',doc)
        with self.assertRaisesRegex(ValueError,'another customer'):
            call(w.analysis,run=str(root),input=str(root/'work/analysis.json'))

    def test_all_three_starters_and_script_escape(self):
        for kind in ('catalog','booking','quote'):
            root,bid=fixture(Path(self.tmp.name)/kind,kind,False)
            self.assertTrue((root/'demo/index.html').exists())
            self.assertIn('"kind": "'+kind+'"',(root/'demo/config.js').read_text(encoding='utf-8'))
            with self.assertRaisesRegex(ValueError,'already exists'):
                call(w.scaffold,run=str(root),kind=kind,input=str(root/'work/config.json'))

    def test_install_does_not_overwrite(self):
        dest=Path(self.tmp.name)/'skills'
        script=w.SKILL/'scripts/install.py'
        r=subprocess.run([sys.executable,str(script),'--skills-dir',str(dest)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        marker=dest/'overseas-web-prospecting/keep.txt';marker.write_text('keep')
        r=subprocess.run([sys.executable,str(script),'--skills-dir',str(dest)],capture_output=True,text=True)
        self.assertEqual(r.returncode,2);self.assertEqual(marker.read_text(),'keep')

    def test_invalid_image_rejected(self):
        root,bid=fixture(self.root)
        (root/'screenshots/desktop.png').write_bytes(b'<html>not an image</html>')
        with self.assertRaisesRegex(ValueError,'Screenshot must'):
            mark_demo(root,bid)

    def test_contact_refresh_preserves_design_and_updates_recipient(self):
        root,bid=fixture(self.root)
        mark_demo(root,bid,True)
        before=w.load_run(root)
        path=root/'work/contacts.json'
        w.write(path,{'business_id':bid,'contacts':[{'email':'new@example.com','source_url':'https://example.com/contact','checked_at':w.now()}]})
        call(w.contacts,run=str(root),input=str(path))
        after=w.load_run(root)
        self.assertEqual(before['approval'],after['approval'])
        self.assertEqual(before['demo'],after['demo'])
        copy=mail_input(root,bid,'new@example.com')
        call(w.mail,run=str(root),input=str(copy),profile=str(root/'work/profile.json'))
        self.assertEqual(w.load_run(root)['stage'],'complete')


if __name__=='__main__':
    unittest.main(verbosity=2)
