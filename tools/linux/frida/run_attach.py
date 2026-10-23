import frida, hashlib, sys, time
from pathlib import Path
pid=int(sys.argv[1]); dur=float(sys.argv[2]); out=sys.argv[3]
script_path=Path(__file__).with_name("n27_frame_hooks.js")
src=script_path.read_text()
sha=hashlib.sha256(src.encode()).hexdigest()
session=frida.attach(pid)
script=session.create_script(src)
msgs=[]
def on_message(m,d):
    if m.get('type')=='send': msgs.append(m.get('payload'))
    else: msgs.append({'frida_error':str(m)[:400]})
script.on('message', on_message)
script.load()
time.sleep(dur)
with open(out,'w') as f:
    f.write("script=%s sha256=%s\n" % (script_path, sha))
    for m in msgs[-8000:]: f.write(str(m)+'\n')
session.detach()
