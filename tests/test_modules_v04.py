import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from zensigil import run, check, test as test_program
from zensigil.modules import file_modules
from zensigil.programs import encode_program, decode_program, unpack_program
from zensigil.server import Handler


class ModuleTests(unittest.TestCase):
    def test_composition_and_diamond_imports(self):
        modules = {'lib/a.zs': 'use "lib/shared.zs"\nfn one():\n    return shared(1)\n',
                   'lib/b.zs': 'use "lib/shared.zs"\nfn two():\n    return shared(2)\n',
                   'lib/shared.zs': 'fn shared(n: integer) -> integer:\n    return n * 3\n'}
        result=run('use "lib/a.zs"\nuse "lib/b.zs"\nemit [one(), two()]',{},modules=modules)
        self.assertTrue(result['ok'],result)
        self.assertEqual(result['values'],[[3,6]])
        self.assertTrue(check('use "lib/a.zs"',modules=modules)['ok'])

    def test_imports_are_pure_and_failures_are_located(self):
        result=run('emit 9\nuse "lib/bad.zs"',{},modules={'lib/bad.zs':'say "side effect"'})
        self.assertEqual(result['diagnostics'][0]['code'],'E_IMPORT')
        self.assertEqual(result['diagnostics'][0]['source_name'],'lib/bad.zs')
        self.assertEqual(result['values'],[])
        result=run('use "lib/math.zs"\nemit divide(0)',{},modules={'lib/math.zs':'fn divide(n):\n    return 1 / n\n'})
        error=result['diagnostics'][0]
        self.assertEqual(error['source_name'],'lib/math.zs')
        self.assertEqual(error['source_line'],'    return 1 / n')
        self.assertEqual(error['line'],2)
        self.assertEqual(error['call_trace'][0]['line'],2)

    def test_bad_paths_and_cycles_are_structured(self):
        for path in ['../outside.zs','/outside.zs','https://example.test/a.zs','a\\b.zs']:
            source='say "start"\nuse '+json.dumps(path)
            result=run(source,{})
            self.assertEqual(result['diagnostics'][0]['code'],'E_IMPORT')
            self.assertEqual(result['diagnostics'][0]['line'],2)
            self.assertEqual(result['diagnostics'][0]['source_line'],source.split('\n')[1])
        result=run('use "a.zs"',{},modules={'a.zs':'use "b.zs"','b.zs':'use "a.zs"'})
        self.assertFalse(result['ok']);self.assertIn('cycle',result['diagnostics'][0]['message'])
        for modules in [{'a.zs':'','A.zs':''},{'a.zs':'','a.zs/b.zs':''},{'a.zs':None},{'a.zs':'x'*65537}]:
            self.assertFalse(run('emit 1',{},modules=modules)['ok'])

    def test_unicode_separators_do_not_move_source_lines(self):
        source='say "a\u2028b\u0085c"\nemit 1 / 0\n'
        error=run(source,{})['diagnostics'][0]
        self.assertEqual(error['line'],2);self.assertEqual(error['source_line'],'emit 1 / 0')

    def test_tests_do_not_require_main_input_or_execute_main(self):
        source='emit customer\nwhile true:\n    say "main"\ntest "isolated":\n    require true, "ok"\n'
        result=test_program(source)
        self.assertTrue(result['ok'],result);self.assertEqual(result['passed'],1)
        self.assertEqual(result['values'],[])
        result=test_program('test "one":\n    var count = 1\ntest "two":\n    require count == 1, "isolated"')
        self.assertFalse(result['ok']);self.assertEqual(result['diagnostics'][0]['code'],'E_NAME')

    def test_portable_modules_roundtrip_and_collision_safe_unpack(self):
        program={'format':'zensigil-program','format_version':1,'language_version':'0.4.0','name':'Modules',
                 'source':'use "program.zs"\nemit two()','data_text':'{}','contract_text':'','proposal_contract_text':'',
                 'modules':{'program.zs':'fn two():\n    return 2\n','input.json/helper.zs':'# nested\n'}}
        decoded=decode_program(encode_program(program));self.assertEqual(decoded,dict(program,language_version='0.8.0',tests={}))
        with tempfile.TemporaryDirectory() as parent:
            path=Path(parent)/'new';names=unpack_program(decoded,path)
            self.assertEqual((path/'program.zs').read_text(),program['modules']['program.zs'])
            self.assertEqual((path/'_program.zs').read_text(),program['source'])
            self.assertIn('_input.json',names)

    def test_file_loading_cannot_leave_the_root(self):
        with tempfile.TemporaryDirectory() as parent:
            base=Path(parent);root=base/'project';root.mkdir();entry=root/'main.zs';entry.write_text('use "lib.zs"')
            outside=base/'outside.zs';outside.write_text('fn hidden():\n    return 1')
            try:(root/'lib.zs').symlink_to(outside)
            except OSError:self.skipTest('Symlinks unavailable in this environment')
            with self.assertRaises(Exception) as found:file_modules(entry.read_text(),entry)
            self.assertEqual(found.exception.code,'E_IMPORT')

    def test_executable_conformance_corpus(self):
        source=(Path(__file__).resolve().parents[1]/'conformance/language.zs').read_text(encoding='utf-8')
        result=test_program(source)
        self.assertTrue(result['ok'],result);self.assertEqual(result['total'],8)


class ModuleHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Quiet(Handler):
            def log_message(self,*args):pass
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Quiet)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=3)
    def post(self,route,payload):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        c.request('POST','/api/'+route,json.dumps(payload),{'Content-Type':'application/json'})
        response=c.getresponse();body=json.loads(response.read());c.close()
        self.assertEqual(response.status,200,body);return body
    def test_http_test_and_format_are_independent_from_main_inputs(self):
        result=self.post('test',{'source':'emit missing\ntest "yes":\n    require true, "yes"'})
        self.assertTrue(result['ok']);self.assertEqual(result['passed'],1)
        formatted=self.post('format',{'source':'emit  1+2\n','data_text':'{unfinished'})
        self.assertTrue(formatted['ok']);self.assertEqual(formatted['source'],'emit 1 + 2\n')
    def test_early_contract_errors_keep_the_test_response_shape(self):
        for field in ['contract_text','proposal_contract_text']:
            result=self.post('test',{'source':'test "ok":\n    require true, "yes"',field:'{bad'})
            self.assertFalse(result['ok']);self.assertEqual(result['mode'],'test')
            self.assertEqual(result['tests'],[]);self.assertEqual(result['values'],[])
            self.assertEqual(result['total'],0)
    def test_http_module_failure_is_atomic(self):
        result=self.post('run',{'source':'use "lib.zs"\nemit bad()','data':{},'modules':{'lib.zs':'fn bad():\n    return 1 / 0'}})
        self.assertFalse(result['ok']);self.assertEqual(result['values'],[])
        self.assertEqual(result['diagnostics'][0]['source_name'],'lib.zs')
        self.assertEqual(result['diagnostics'][0]['source_line'],'    return 1 / 0')
