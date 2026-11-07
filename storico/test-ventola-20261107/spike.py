import multiprocessing as mp,time,glob,os
mp=mp.get_context('fork')
hw=[os.path.dirname(p) for p in glob.glob('/sys/class/hwmon/hwmon*/name') if open(p).read().strip()=='coretemp'][0]
def pkg(): return int(open(hw+'/temp1_input').read())//1000
def burn(stop):
    while not stop.is_set():
        x=0
        for i in range(20000): x+=i*i
def run(n,dur=2.0,limit=90):
    while pkg()>55: time.sleep(.5)
    stop=mp.Event();ps=[mp.Process(target=burn,args=(stop,),daemon=True) for _ in range(n)]
    t0=time.time();r=[(0,pkg())]
    for p in ps:p.start()
    while time.time()-t0<dur:
        t=pkg();r.append((round(time.time()-t0,2),t))
        if t>=limit: break
        time.sleep(.05)
    stop.set()
    for p in ps:p.join()
    te=time.time()
    while time.time()-te<1.5:
        r.append((round(time.time()-t0,2),pkg()));time.sleep(.2)
    print(n,'thread',' '.join(f'{a}:{b}' for a,b in r))
    time.sleep(6)
if __name__=='__main__':
    for n in (1,4,22): run(n)
