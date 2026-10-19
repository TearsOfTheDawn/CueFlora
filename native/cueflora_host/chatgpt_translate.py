"""One subscription Responses POST. No transport retry or paid API fallback."""
import json
import time
import httpx
from .chatgpt_auth import RESOURCE, access_token
from .translate import TranslationError, _ordered_translation_texts


def translation_schema(count):
    return {'type':'object','properties':{'translations':{'type':'array','items':{'type':'object',
        'properties':{'id':{'type':'integer','minimum':0,'maximum':count-1},'text':{'type':'string'}},
        'required':['id','text'],'additionalProperties':False},'minItems':count,'maxItems':count}},
        'required':['translations'],'additionalProperties':False}


def events(chunks, deadline=180, clock=time.monotonic):
    """Bound individual SSE events and total stream bytes, including keepalive spam."""
    buffer=b''; size=0; started=clock()
    for chunk in chunks:
        if clock()-started>deadline: raise TranslationError('ChatGPT translation timed out.',kind='network')
        size+=len(chunk)
        if size>8*1024*1024: raise TranslationError('ChatGPT stream exceeded its size limit.',kind='protocol')
        buffer+=chunk
        buffer=buffer.replace(b'\r\n',b'\n')
        while b'\n\n' in buffer:
            raw,buffer=buffer.split(b'\n\n',1)
            if len(raw)>1024*1024: raise TranslationError('Oversized ChatGPT stream event.',kind='protocol')
            data=b'\n'.join(line[5:].lstrip() for line in raw.split(b'\n') if line.startswith(b'data:'))
            if not data or data==b'[DONE]': continue
            try: value=json.loads(data)
            except (ValueError,UnicodeError): raise TranslationError('Invalid ChatGPT stream.',kind='protocol') from None
            if not isinstance(value,dict): raise TranslationError('Invalid ChatGPT stream event.',kind='protocol')
            yield value
        if len(buffer)>1024*1024: raise TranslationError('Oversized ChatGPT stream event.',kind='protocol')


def error_message(code):
    if code in ('subscription_sharing_usage_limit_exceeded','subscription_sharing_usage_unavailable'):
        return 'ChatGPT plan usage is unavailable or its limit was reached. Open Manage usage; no paid API fallback was used.'
    return 'ChatGPT translation failed. Check sign-in, model eligibility and structured-output support; no paid API fallback was used.'


def consume_events(stream, count):
    output=[]; length=0; completed=False
    for event in stream:
        kind=event.get('type')
        if kind=='response.output_text.delta':
            delta=event.get('delta')
            if not isinstance(delta,str): raise TranslationError('Invalid ChatGPT output delta.',kind='protocol')
            output.append(delta); length+=len(delta)
            if length>500000: raise TranslationError('ChatGPT output exceeded its limit.',kind='output')
        elif kind in ('response.failed','response.incomplete','error','response.refusal.delta'):
            response=event.get('response',{}); detail=response.get('error',{}) if isinstance(response,dict) else {}
            raise TranslationError(error_message(detail.get('code') if isinstance(detail,dict) else None),kind='http')
        elif kind=='response.completed':
            response=event.get('response')
            if not isinstance(response,dict) or response.get('status')!='completed': raise TranslationError('Invalid ChatGPT completion event.',kind='protocol')
            completed=True; break
    if not completed: raise TranslationError('ChatGPT stream ended before response.completed. Retry explicitly; no automatic request was made.',kind='network')
    try: parsed=json.loads(''.join(output))
    except ValueError: raise TranslationError('ChatGPT returned invalid structured translation JSON.',kind='output') from None
    return _ordered_translation_texts(parsed,count,'stop',{})


def translate(cues, system_prompt, account_ref, model, on_progress=None, capture=None, source_indexes=None):
    # Authentication/refresh must succeed before this function attempts inference.
    token=access_token(account_ref)
    body={'model':model,'instructions':system_prompt,
        'input':[{'role':'user','content':json.dumps({'cues':[{'id':index,'text':cue['text']} for index,cue in enumerate(cues)]},ensure_ascii=False)}],
        'store':False,'stream':True,'text':{'format':{'type':'json_schema','name':'subtitle_translation','strict':True,'schema':translation_schema(len(cues))}}}
    if on_progress: on_progress('translate','Translating using ChatGPT plan…')
    request_record=capture.record('translation-request',{'body':body,'sourceCues':cues,'sourceIndexes':source_indexes,'backend':'chatgpt'}) if capture else None
    started=time.monotonic()
    try:
        with httpx.Client(timeout=httpx.Timeout(180,connect=10),follow_redirects=False) as client:
            with client.stream('POST',RESOURCE+'/responses',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},json=body) as response:
                if response.status_code in (401,403): raise TranslationError('ChatGPT authentication expired or was denied. Sign in again; no API fallback was used.',kind='auth')
                if response.status_code!=200: raise TranslationError('ChatGPT rejected this translation. Check plan usage, model and structured-output support; no API fallback was used.',kind='http')
                if 'text/event-stream' not in response.headers.get('content-type',''): raise TranslationError('ChatGPT did not return a Responses stream.',kind='protocol')
                texts=consume_events(events(response.iter_bytes()),len(cues))
        if capture: capture.record('translation-response',{'requestRecord':request_record,'translations':texts,'completed':True})
        return {'translations':texts,'requestCount':1,'finishReason':'stop','durationMs':round((time.monotonic()-started)*1000)}
    except httpx.HTTPError:
        raise TranslationError('ChatGPT connection failed or timed out. Retry explicitly; no automatic request or paid fallback was made.',kind='network') from None
