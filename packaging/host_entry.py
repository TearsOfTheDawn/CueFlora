"""Console entry point: stdout is exclusively native messaging frames."""
from cueflora_host import main

if __name__ == '__main__':
    import sys
    if '--auth-self-check' in sys.argv:
        import argparse,json
        from pathlib import Path
        parser=argparse.ArgumentParser();parser.add_argument('--auth-self-check',action='store_true');parser.add_argument('--report',type=Path,required=True)
        args=parser.parse_args()
        try:
            from cueflora_host.auth_self_check import check
            result=check();code=0
        except Exception:
            result={'passed':False,'error':'Synthetic authentication self-check failed','genuineLogin':False,'inference':False};code=1
        with args.report.open('x',encoding='utf-8') as output:json.dump(result,output,indent=2)
        raise SystemExit(code)
    main()
