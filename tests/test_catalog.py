import copy,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('catalog',ROOT/'scripts/catalog.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog=json.loads((ROOT/'catalog.json').read_text())
        self.hashes=json.loads((ROOT/'asset-hashes.json').read_text())
        self.lock=json.loads((ROOT/'reference-lock.json').read_text())
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.video=root/'fixture.mp4';self.video.write_bytes(b'unit-test-fixture-only')
        evidence=root/'handoff.json';evidence.write_text('{}')
        self.batch={'schemaVersion':1,'date':'2026-10-18','clips':[{
            'id':'MC-036','label':'Guest SOURCE123 01','topic':'Test','category':'Interview','source':'SOURCE123.MP4',
            'privateNotes':'DO NOT COPY','warnings':['Internal wording must not be copied'],
            'versions':[{'number':1,'video_path':str(self.video),'sha256':mod.digest(self.video),
                         'evidence_path':str(evidence),'duration':3,'ranges':[[1,4]]}]}]}
    def test_existing_catalog_and_ids(self):
        mod.validate(self.catalog,self.lock)
        self.assertEqual(len(self.catalog['clips']),35)
        self.assertEqual(sum(len(c['versions']) for c in self.catalog['clips']),56)
    def test_import_is_idempotent_without_private_metadata(self):
        a=mod.import_batch(self.catalog,self.hashes,self.lock,self.batch)
        b=mod.import_batch(*a,self.batch)
        self.assertEqual(a,b)
        serialized=json.dumps(a)
        self.assertNotIn(str(self.video),serialized)
        self.assertNotIn('DO NOT COPY',serialized)
        self.assertNotIn('Internal wording',serialized)
        self.assertTrue(a[0]['clips'][-1]['versions'][0]['captionQA'])
    def test_changed_bytes_rejected(self):
        self.video.write_bytes(b'wrong edition')
        with self.assertRaisesRegex(ValueError,'Wrong export bytes'):
            mod.import_batch(self.catalog,self.hashes,self.lock,self.batch)
    def test_known_missing_file_does_not_select_another(self):
        self.video.unlink()
        out,hashes,_=mod.import_batch(self.catalog,self.hashes,self.lock,self.batch)
        self.assertEqual(out['clips'][-1]['versions'][0]['video'],'/media/MC-036-v1.mp4')
        with self.assertRaisesRegex(ValueError,'mapping missing'):mod.materialize(out,hashes,{})
    def test_unresolved_stays_unlinked(self):
        v=self.batch['clips'][0]['versions'][0];v.update(sha256=None,missingReason='Unverified identity')
        out,_,_=mod.import_batch(self.catalog,self.hashes,self.lock,self.batch)
        self.assertIsNone(out['clips'][-1]['versions'][0]['video'])
        self.assertIsNone(next(c for c in out['clips'] if c['id']=='MC-025')['versions'][0]['video'])
    def test_revisions_keep_labels_and_require_new_versions(self):
        a=mod.import_batch(self.catalog,self.hashes,self.lock,self.batch)
        self.batch['clips'][0]['versions'][0]['number']=2
        b=mod.import_batch(*a,self.batch)
        self.assertEqual([v['id'] for v in b[0]['clips'][-1]['versions']],['v2','v1'])
        self.batch['clips'][0]['label']='Guest SOURCE123 02'
        with self.assertRaisesRegex(ValueError,'Stable label'):mod.import_batch(*b,self.batch)
    def test_release_needs_exact_hash_and_safe_url(self):
        mapping={k:{'url':'https://fixture.public.blob.vercel-storage.com/'+k,'sha256':v} for k,v in self.hashes.items()}
        out=mod.materialize(self.catalog,self.hashes,mapping)
        self.assertTrue(out['clips'][0]['versions'][0]['video'].startswith('https://'))
        key=self.catalog['clips'][0]['versions'][0]['video'][7:]
        mapping[key]['sha256']='0'*64
        with self.assertRaises(ValueError):mod.materialize(self.catalog,self.hashes,mapping)
        mapping[key]['sha256']=self.hashes[key];mapping[key]['url']='https://'+'fixture-user'+'@'+'fixture.public.blob.vercel-storage.com/test'
        with self.assertRaises(ValueError):mod.materialize(self.catalog,self.hashes,mapping)
    def test_private_field_or_removed_identity_rejected(self):
        self.catalog['clips'][0]['notes']='hidden'
        with self.assertRaises(ValueError):mod.validate(self.catalog,self.lock)
        del self.catalog['clips'][0]
        with self.assertRaises(ValueError):mod.validate(self.catalog,self.lock)

if __name__=='__main__':unittest.main()
