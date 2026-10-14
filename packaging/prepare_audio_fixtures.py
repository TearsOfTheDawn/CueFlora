"""One-time synthetic fixture authoring, not a build dependency or inference tool."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import math
import struct
import subprocess
import tempfile
import wave


def fixtures(encoder):
    encoder = Path(encoder).resolve()
    result = {'schema':1,'content':'Synthetic 440 Hz tone only; no speech or private media',
        'authoringToolSha256':hashlib.sha256(encoder.read_bytes()).hexdigest(),
        'authoringToolVersion':subprocess.check_output([str(encoder),'-version'],text=True).splitlines()[0], 'files':{}}
    with tempfile.TemporaryDirectory(prefix='cueflora-fixture-') as temporary:
        folder = Path(temporary); source = folder/'tone.wav'
        with wave.open(str(source),'wb') as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(16000)
            stream.writeframes(b''.join(struct.pack('<h',int(8000*math.sin(2*math.pi*440*i/16000))) for i in range(8000)))
        for extension,codec in [('m4a','aac'),('mp3','libmp3lame'),('flac','flac'),('ogg','libvorbis'),('webm','libopus')]:
            output = folder/('tone.'+extension)
            subprocess.run([str(encoder),'-v','error','-y','-i',str(source),'-c:a',codec,str(output)],check=True)
            data = output.read_bytes()
            result['files'][output.name] = {'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest(),
                'durationSeconds':0.5,'signal':'440Hz, 16000Hz mono input, amplitude 8000/32768; lossy formats are not exact PCM'}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--encoder',type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(fixtures(args.encoder),indent=2))
