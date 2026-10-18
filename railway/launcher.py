import json,os,pathlib,signal,subprocess,time,sys
DATA=pathlib.Path(os.getenv('DATA_DIR','/data'))
DATA.mkdir(parents=True,exist_ok=True)
if os.getuid()==0:
 for p in [DATA,DATA/'railway',DATA/'home',DATA/'xerj']:
  p.mkdir(exist_ok=True);os.chown(p,1000,1000)
 os.setgroups([]);os.setgid(1000);os.setuid(1000)
os.environ['HOME']=str(DATA/'home')
sys.path.insert(0,'/opt/railway')
from gateway import CREDS,KIND
if KIND=='xerj':
 config=DATA/'railway'/'xerj.toml'
 config.write_text('[server]\nbind_address="127.0.0.1"\nrest_port=18080\nes_compat_port=19200\ngrpc_port=18081\ndata_dir='+json.dumps(str(DATA/'xerj'))+'\n[auth]\nenabled=true\nadmin_api_key='+json.dumps(CREDS['XERJ_API_KEY'])+'\n[storage]\nwal_sync="sync"\nflush_size_mb=64\nflush_interval_secs=15\n')
 config.chmod(0o600)
 command=['/usr/local/bin/xerj','--config',str(config)]
 cwd='/app'
else:
 os.environ['DATABASE_URL']='sqlite:///'+str(DATA/'aurelio.db')
 command=['/opt/aurelio/backend/.venv/bin/python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','18080','--no-access-log']
 cwd='/opt/aurelio/backend'
children=[subprocess.Popen(command,cwd=cwd)]
children.append(subprocess.Popen([sys.executable,'-m','uvicorn','gateway:app','--host','0.0.0.0','--port',os.getenv('PORT','8080'),'--no-access-log'],cwd='/opt/railway'))
stopping=False
unexpected=False

def stop(*_):
 global stopping
 if stopping:return
 stopping=True
 for child in children:
  if child.poll() is None:child.terminate()
for s in [signal.SIGTERM,signal.SIGINT]:signal.signal(s,stop)
print(('XERJ' if KIND=='xerj' else 'Aurelio Finance')+' private service started; credentials are available in Railway variables.',flush=True)
while not stopping:
 if any(c.poll() is not None for c in children):unexpected=True;stop();break
 time.sleep(.25)
end=time.time()+25
for child in children:
 try:child.wait(timeout=max(.1,end-time.time()))
 except subprocess.TimeoutExpired:child.kill();child.wait()
if unexpected or any(c.returncode not in (0,-signal.SIGTERM) for c in children):sys.exit(1)
