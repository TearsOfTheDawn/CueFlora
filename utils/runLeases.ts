/** One live native port holds a crash-released lease for the entire logical Run. */
export function createRunLeases(connect:()=>ReturnType<typeof browser.runtime.connectNative>) {
    const held=new Map<string,{port:ReturnType<typeof browser.runtime.connectNative>;valid:boolean}>();
    return {
        async acquire(key:string):Promise<void>{
            if(held.has(key))throw Error('Run lease already bound.');
            const port=connect(),record={port,valid:false};held.set(key,record);
            await new Promise<void>((resolve,reject)=>{
                let phase='ping',settled=false;const requestId=crypto.randomUUID();
                const fail=()=>{record.valid=false;held.delete(key);if(!settled){settled=true;clearTimeout(timer);reject(Error('Run tracking requires the latest CueFlora helper. Upgrade/Repair, or wait for Setup to finish.'));}port.disconnect();};
                const timer=setTimeout(fail,10000);
                port.onDisconnect.addListener(()=>{record.valid=false;held.delete(key);if(!settled){settled=true;clearTimeout(timer);reject(Error('CueFlora Run tracking disconnected. Upgrade/Repair and start again.'));}});
                port.onMessage.addListener((incoming:unknown)=>{
                    const value=incoming as {status?:string;capabilities?:{runLeases?:string};requestId?:string;leased?:boolean};
                    if(phase==='ping'){
                        if(value?.status!=='PONG'||value.capabilities?.runLeases!=='run-leases-v1'){fail();return;}
                        phase='lease';port.postMessage({type:'RUN_LEASE',requestId});
                    }else if(value?.requestId===requestId&&value.leased===true){record.valid=true;settled=true;clearTimeout(timer);resolve();}
                    else fail();
                });
                try{port.postMessage({type:'PING'});}catch{fail();}
            });
        },
        valid(key:string){return held.get(key)?.valid===true;},
        release(key:string){const record=held.get(key);held.delete(key);if(record){record.valid=false;record.port.disconnect();}},
        releaseTab(tab:number){for(const key of held.keys())if(key.startsWith('cueflora_run_provider_'+tab+'_'))this.release(key);},
        busy(){return [...held.values()].some(value=>value.valid);},
    };
}
