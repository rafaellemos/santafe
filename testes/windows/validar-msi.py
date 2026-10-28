"""Execute the complete installed WiX ICE suite, preserving delivered MSI bytes."""
from pathlib import Path
import collections,hashlib,json,os,re,shutil,subprocess,sys,traceback
import msilib as m
out=Path(sys.argv[2]);msi=Path(sys.argv[1]).resolve();out.mkdir(exist_ok=True)
result={'candidato':'dados.25','resultado':'em_execucao','validacao_visual':False,'testes':[]}
try:
 roots=[Path(os.environ.get('WIX','C:/inexistente'))/'bin']
 pf=Path(os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)'))
 roots.extend(p/'bin' for p in pf.glob('WiX Toolset*'))
 smoke=next((r/'smoke.exe' for r in roots if (r/'smoke.exe').is_file()),None)
 if smoke is None:raise RuntimeError('WiX Smoke ausente no runner; ICE não executado')
 before=hashlib.sha256(msi.read_bytes()).hexdigest()
 check=subprocess.run([str(smoke),str(msi),'-nologo'],capture_output=True,timeout=180)
 (out/'ice-completo.log').write_bytes(check.stdout+check.stderr)
 warnings=collections.Counter(re.findall(rb'warning SMOK[0-9]+ : (ICE[0-9]+):',check.stdout+check.stderr))
 result.update(ferramenta=str(smoke),codigo=check.returncode,avisos={k.decode():v for k,v in warnings.items()},avisos_suprimidos=False)
 # ICE91 is expected for an exclusively per-user MSI. ALLUSERS is explicitly
 # refused and tested. Keep these warnings in the full log; do not suppress ICE.
 if set(warnings)-{b'ICE91'}:raise RuntimeError('Avisos ICE exigem revisão: '+str(warnings))
 if check.returncode:
  lines=(check.stdout+check.stderr).decode('utf-8','replace').splitlines()
  errors=[line.split(' : error ',1)[-1] for line in lines if ' : error ' in line]
  raise RuntimeError('ICE recusou o MSI (log completo preservado): '+repr(errors)[-1200:])
 result['testes'].append({'nome':'suite-completa-ice','passou':True})
 # A malformed foreign key must be refused by the same validator.
 bad=out/'fixture-ice-invalido.msi';shutil.copyfile(msi,bad)
 db=m.OpenDatabase(str(bad),m.MSIDBOPEN_TRANSACT)
 v=db.OpenView("UPDATE `Component` SET `Directory_` = 'DiretorioAusente' WHERE `Component` = 'Registration'");v.Execute(None);v.Close();v=None;db.Commit();db=None
 control=subprocess.run([str(smoke),str(bad),'-nologo'],capture_output=True,timeout=180)
 (out/'ice-controle-invalido.log').write_bytes(control.stdout+control.stderr)
 if control.returncode==0 or b'ICE03' not in control.stdout+control.stderr:raise RuntimeError('Controle inválido não recusado por ICE03')
 result['testes'].append({'nome':'controle-chave-estrangeira-invalida','passou':True})
 bad.unlink()
 if hashlib.sha256(msi.read_bytes()).hexdigest()!=before:raise RuntimeError('Validador alterou o MSI original')
 result['testes'].append({'nome':'msi-original-preservado','passou':True})
 result['resultado']='passou_ice_completo'
except Exception as e:
 result['resultado']='falhou';result['falha']=str(e);traceback.print_exc()
finally:
 (out/'ice.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
raise SystemExit(0 if result['resultado']=='passou_ice_completo' else 1)
