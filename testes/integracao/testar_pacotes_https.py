#!/usr/bin/env python3
"""TLS real on loopback: default distrust, explicit CA, HTTP downgrade rejection."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
from testar_pacotes import sf, fixture, lit

with tempfile.TemporaryDirectory(prefix='santafe-pacotes-https-') as temp:
    root=Path(temp); repo=root/'estático/bibliotecas/v1'; repo.mkdir(parents=True); source=root/'fonte'; fixture(source)
    sf(f'local b=garanta(A.empacote({lit(source)})); garanta(A.adicione({lit(repo)},b))')
    config=root/'openssl.cnf'
    config.write_text('[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n[dn]\nCN=localhost\n[ext]\nsubjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=critical,CA:TRUE\nkeyUsage=critical,keyCertSign,digitalSignature,keyEncipherment\n')
    cert=root/'cert.pem'; key=root/'key.pem'
    subprocess.run(['/usr/bin/openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
                    '-keyout',str(key),'-out',str(cert),'-config',str(config)],check=True,capture_output=True)
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(root),**kwargs)
        def log_message(self,*args): pass
        def do_GET(self):
            if self.path.startswith('/downgrade/'):
                self.send_response(302); self.send_header('Location','http://127.0.0.1:1/stolen'); self.end_headers()
            else: super().do_GET()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(cert,key)
    server.socket=context.wrap_socket(server.socket,server_side=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        url=f'https://127.0.0.1:{server.server_port}/est%C3%A1tico/bibliotecas/v1'
        project=root/'projeto'; project.mkdir()
        sf(f'garanta(C.instale({lit(project)},"exemplo","*",{{repositório={lit(url)}}}))',success=False)
        assert not (project/'.santafe/estado.json').exists()
        sf(f'garanta(C.instale({lit(project)},"exemplo","*",{{repositório={lit(url)},autoridadeCertificadora={lit(cert)}}}))')
        another=root/'outro'; another.mkdir()
        downgrade=f'https://127.0.0.1:{server.server_port}/downgrade'
        sf(f'garanta(C.instale({lit(another)},"exemplo","*",{{repositório={lit(downgrade)},autoridadeCertificadora={lit(cert)}}}))',success=False)
        assert not (another/'.santafe/estado.json').exists()
        for path in ('/bad%','/bad%2G','/%2e%2e/v1','/bad%00','/bad%252e','/bad%3fsecret'):
            invalid=f'https://127.0.0.1:{server.server_port}'+path
            result=sf(f'garanta(C.instale({lit(another)},"exemplo","*",{{repositório={lit(invalid)},autoridadeCertificadora={lit(cert)}}}))',success=False)
            assert 'URL do repositório' in result.stderr or 'URL de repositório' in result.stderr,result.stderr
    finally:
        server.shutdown(); server.server_close(); thread.join()
    print('Pacotes HTTPS: certificado obrigatório, CA explícita, download real e recusa de downgrade: ok')
