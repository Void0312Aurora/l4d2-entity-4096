import frida, sys, time
pid=int(sys.argv[1]); dur=float(sys.argv[2]); out=sys.argv[3]
session=frida.attach(pid)
script=session.create_script(open('/tmp/n27hook.js').read())
msgs=[]
def on_message(m,d):
    if m.get('type')=='send': msgs.append(m.get('payload'))
    else: msgs.append({'frida_error':str(m)[:400]})
script.on('message', on_message)
script.load()
time.sleep(dur)
with open(out,'w') as f:
    for m in msgs[-5000:]: f.write(str(m)+'\n')
session.detach()
