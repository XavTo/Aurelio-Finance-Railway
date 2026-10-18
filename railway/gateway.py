"""Private Railway ingress. Upstream processes stay on loopback."""
import asyncio,base64,hashlib,hmac,json,os,secrets,time
from pathlib import Path
from urllib.parse import urlsplit
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse,JSONResponse,RedirectResponse,StreamingResponse

KIND=os.getenv('APP_KIND','xerj')
DATA=Path(os.getenv('DATA_DIR','/data'))
PUBLIC_URL=os.getenv('PUBLIC_URL','').rstrip('/')
SECURE=os.getenv('SECURE_COOKIES','true').lower()!='false'
COOKIE='railway_private_session'
MAX_BODY=32*1024*1024
HOP={'connection','keep-alive','proxy-authenticate','proxy-authorization','te','trailer','transfer-encoding','upgrade','host','content-length'}
secrets_file=DATA/'railway'/'secrets.json'

def credentials():
 secrets_file.parent.mkdir(parents=True,exist_ok=True)
 saved=json.loads(secrets_file.read_text()) if secrets_file.exists() else {}
 changed=False
 for key in ['APP_PASSWORD','SESSION_SECRET']+(['XERJ_API_KEY'] if KIND=='xerj' else []):
  value=os.getenv(key) or saved.get(key) or secrets.token_urlsafe(32)
  if len(value)<16:raise ValueError(key+' must contain at least 16 characters')
  if saved.get(key)!=value:saved[key]=value;changed=True
 if changed:
  tmp=secrets_file.with_suffix('.tmp');tmp.write_text(json.dumps(saved));tmp.chmod(0o600);tmp.replace(secrets_file)
 return saved
CREDS=credentials()

def matches(a,b):return hmac.compare_digest(hashlib.sha256(a.encode()).digest(),hashlib.sha256(b.encode()).digest())
def signed_cookie():
 payload=str(int(time.time()+7*86400))+'.'+secrets.token_hex(16)
 return payload+'.'+hmac.new(CREDS['SESSION_SECRET'].encode(),(payload+hashlib.sha256(CREDS['APP_PASSWORD'].encode()).hexdigest()).encode(),hashlib.sha256).hexdigest()
def valid_cookie(value):
 try:
  exp,nonce,sig=value.split('.');payload=exp+'.'+nonce
  expected=hmac.new(CREDS['SESSION_SECRET'].encode(),(payload+hashlib.sha256(CREDS['APP_PASSWORD'].encode()).hexdigest()).encode(),hashlib.sha256).hexdigest()
  return int(exp)>time.time() and hmac.compare_digest(expected,sig)
 except (ValueError,AttributeError):return False

def owner(request):
 auth=request.headers.get('authorization','')
 if auth.startswith('Basic '):
  try:
   user,password=base64.b64decode(auth[6:],validate=True).decode().split(':',1)
   if user=='admin' and matches(password,CREDS['APP_PASSWORD']):return True
  except (ValueError,UnicodeError):pass
 if KIND=='xerj' and (auth.startswith('ApiKey ') or auth.startswith('Bearer ')):
  if matches(auth.split(' ',1)[1],CREDS['XERJ_API_KEY']):return True
 return valid_cookie(request.cookies.get(COOKIE,''))
def origin_ok(request):
 origin=request.headers.get('origin')
 if not origin:return True
 expected=PUBLIC_URL or str(request.base_url).rstrip('/')
 return origin.rstrip('/')==expected

def private_response(response):
 response.headers['Cache-Control']='private, no-store'
 response.headers['X-Content-Type-Options']='nosniff'
 response.headers['Referrer-Policy']='same-origin'
 response.headers['X-Frame-Options']='DENY'
 return response

def denied(request):
 if request.method=='GET' and 'text/html' in request.headers.get('accept',''):
  return RedirectResponse('/_railway/login',status_code=303)
 return JSONResponse({'error':'Authentication required'},401,headers={'WWW-Authenticate':'Basic realm="Private Railway workspace"'})

@asynccontextmanager
async def lifespan(app):
 async with httpx.AsyncClient(timeout=httpx.Timeout(300,connect=10),follow_redirects=False) as client:
  app.state.client=client
  yield
app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
FAILURES={}

@app.middleware('http')
async def guards(request,call_next):
 try:
  if int(request.headers.get('content-length','0'))>MAX_BODY:return private_response(JSONResponse({'error':'Maximum request size is 32 MB'},413))
 except ValueError:return private_response(JSONResponse({'error':'Invalid content length'},400))
 if request.method not in ('GET','HEAD','OPTIONS') and not origin_ok(request):return private_response(JSONResponse({'error':'Origin rejected'},403))
 return private_response(await call_next(request))

@app.get('/healthz')
async def health(request:Request):
 url='http://127.0.0.1:18080/v1/health' if KIND=='xerj' else 'http://127.0.0.1:18080/api/health'
 headers={'Authorization':'ApiKey '+CREDS['XERJ_API_KEY']} if KIND=='xerj' else {}
 try:
  r=await request.app.state.client.get(url,headers=headers,timeout=3)
  if r.is_success:return JSONResponse({'status':'ok'})
 except httpx.HTTPError:pass
 return JSONResponse({'status':'starting'},503)

@app.get('/_railway/login')
async def login_page(request:Request):
 if owner(request):return RedirectResponse('/',303)
 return HTMLResponse(Path('/opt/railway/login.html').read_text().replace('{{APP_NAME}}','XERJ' if KIND=='xerj' else 'Aurelio Finance'))

@app.post('/_railway/login')
async def login(request:Request):
 now=time.time();bucket=request.client.host if request.client else 'all'
 times=[t for t in FAILURES.get(bucket,[]) if now-t<60]
 if len(times)>=8:return JSONResponse({'error':'Too many attempts. Try again in one minute.'},429)
 try:
  body=await request.json();password=str(body.get('password',''))
 except (ValueError,AttributeError):return JSONResponse({'error':'Invalid request'},400)
 if len(password)>4096 or not matches(password,CREDS['APP_PASSWORD']):
  FAILURES[bucket]=times+[now];return JSONResponse({'error':'Incorrect password'},401)
 FAILURES.pop(bucket,None)
 response=JSONResponse({'ok':True})
 response.set_cookie(COOKIE,signed_cookie(),max_age=7*86400,httponly=True,secure=SECURE,samesite='strict',path='/')
 return response

@app.post('/_railway/logout')
async def logout():
 r=JSONResponse({'ok':True});r.delete_cookie(COOKIE,path='/',secure=SECURE,httponly=True,samesite='strict');return r

@app.get('/_railway/config')
async def config(request:Request):
 if not owner(request):return denied(request)
 base=PUBLIC_URL or str(request.base_url).rstrip('/')
 return {'name':'XERJ' if KIND=='xerj' else 'Aurelio Finance','url':base,'apiKey':CREDS.get('XERJ_API_KEY'),'version':os.getenv('UPSTREAM_VERSION',''),'dataPath':'/data/xerj' if KIND=='xerj' else '/data/aurelio.db','auth':True}

@app.get('/_railway/indices')
async def indices(request:Request):
 if KIND!='xerj':return JSONResponse({'error':'Not found'},404)
 if not owner(request):return denied(request)
 r=await request.app.state.client.get('http://127.0.0.1:19200/_cat/indices?format=json',headers={'Authorization':'ApiKey '+CREDS['XERJ_API_KEY']})
 return JSONResponse(r.json(),r.status_code)

@app.post('/_railway/import')
async def import_docs(request:Request):
 if KIND!='xerj':return JSONResponse({'error':'Not found'},404)
 if not owner(request):return denied(request)
 import re
 try:
  body=await request.json();index=body.get('index','');docs=body.get('documents',[])
  if not re.fullmatch('[a-z][a-z0-9_-]{0,63}',index) or not isinstance(docs,list) or not 1<=len(docs)<=10000 or not all(isinstance(d,dict) for d in docs):return JSONResponse({'error':'Use a lowercase index name and an array of 1 to 10000 documents'},400)
 except (ValueError,AttributeError):return JSONResponse({'error':'Invalid JSON'},400)
 raw=''.join(json.dumps({'index':{'_index':index,'_id':hashlib.sha256(json.dumps(doc,sort_keys=True).encode()).hexdigest()}})+'\n'+json.dumps(doc)+'\n' for doc in docs)
 r=await request.app.state.client.post('http://127.0.0.1:19200/_bulk?refresh=true',content=raw.encode(),headers={'Authorization':'ApiKey '+CREDS['XERJ_API_KEY'],'Content-Type':'application/x-ndjson'})
 return JSONResponse(r.json(),r.status_code)

@app.post('/_railway/search')
async def search(request:Request):
 if KIND!='xerj':return JSONResponse({'error':'Not found'},404)
 if not owner(request):return denied(request)
 import re
 try:
  b=await request.json();index=b.get('index','');q=b.get('query','')
  if not re.fullmatch('[a-z][a-z0-9_-]{0,63}',index) or not isinstance(q,str) or len(q)>10000:return JSONResponse({'error':'Invalid index or query'},400)
 except (ValueError,AttributeError):return JSONResponse({'error':'Invalid JSON'},400)
 r=await request.app.state.client.post('http://127.0.0.1:19200/'+index+'/_search',json={'query':{'query_string':{'query':q}} if q else {'match_all':{}},'size':20},headers={'Authorization':'ApiKey '+CREDS['XERJ_API_KEY']})
 return JSONResponse(r.json(),r.status_code)

@app.api_route('/{path:path}',methods=['GET','HEAD','POST','PUT','PATCH','DELETE','OPTIONS'])
async def proxy(path:str,request:Request):
 if KIND=='xerj' and not path and 'text/html' in request.headers.get('accept',''):
  if not owner(request):return denied(request)
  return HTMLResponse(Path('/opt/railway/dashboard.html').read_text())
 auth=request.headers.get('authorization','')
 is_owner=owner(request)
 # Non-owner API credentials are verified by the engine itself, retaining scoped keys.
 if not is_owner and not (KIND=='xerj' and (auth.startswith('ApiKey ') or auth.startswith('Bearer '))):return denied(request)
 native=KIND=='xerj' and (path=='v1' or path.startswith('v1/'))
 port=18080 if native or KIND=='aurelio' else 19200
 url=f'http://127.0.0.1:{port}/'+path
 if request.url.query:url+='?'+request.url.query
 body=await request.body()
 if len(body)>MAX_BODY:return JSONResponse({'error':'Maximum request size is 32 MB'},413)
 headers={k:v for k,v in request.headers.items() if k.lower() not in HOP|{'cookie'}}
 if KIND=='xerj':headers['authorization']='ApiKey '+CREDS['XERJ_API_KEY'] if is_owner else auth
 else:headers.pop('authorization',None)
 try:
  upstream=await request.app.state.client.send(request.app.state.client.build_request(request.method,url,headers=headers,content=body),stream=True)
 except httpx.HTTPError:return JSONResponse({'error':'Application is temporarily unavailable'},503)
 async def content():
  try:
   async for chunk in upstream.aiter_raw():yield chunk
  finally:await upstream.aclose()
 return StreamingResponse(content(),status_code=upstream.status_code,headers={k:v for k,v in upstream.headers.items() if k.lower() not in HOP})
