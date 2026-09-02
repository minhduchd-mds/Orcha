"""Read-only health check or authenticated local shutdown for launchers."""
import argparse,json,urllib.error,urllib.request

def request(base,path,body=None,token=None):
    headers={'Content-Type':'application/json'}
    if token:headers['X-Orcha-Token']=token
    data=json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(urllib.request.Request(base+'/'+path,data=data,headers=headers),timeout=2) as response:return json.load(response)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['health','stop']);parser.add_argument('--port',type=int,default=11435);args=parser.parse_args();base='http://127.0.0.1:'+str(args.port)
    try:
        health=request(base,'health')
        if args.action=='health':return 0 if health.get('ok') and health.get('product')=='Orcha' and health.get('version')=='7.6.0' and health.get('api_security') else 1
        if health.get('product')!='Orcha' and not health.get('version'):return 1
        try:token=request(base,'api/session').get('token')
        except urllib.error.HTTPError as error:
            if error.code!=404:raise
            token=None
        return 0 if request(base,'api/app/shutdown',{},token).get('ok') else 1
    except (OSError,ValueError):return 1
if __name__=='__main__':raise SystemExit(main())
