"""Original deterministic offline 30s score. No samples, external services, or dependencies beyond numpy."""
from pathlib import Path
import json, wave, hashlib, math
import numpy as np

ROOT = Path(__file__).resolve().parent
SR = 48000
DURATION = 30.0
N = int(SR * DURATION)
rng = np.random.default_rng(20261015)
bus = np.zeros((N, 2), dtype=np.float64)
events = []

def add(sig, start, gain=1., pan=0., room=0.):
    sig=np.asarray(sig,dtype=np.float64)
    p=np.array([math.cos((pan+1)*math.pi/4),math.sin((pan+1)*math.pi/4)])
    i=int(start*SR); end=min(N,i+len(sig)); k=max(0,-i)
    if end>max(i,0): bus[max(i,0):end]+=sig[k:k+end-max(i,0),None]*p*gain
    if room:
        for delay, level, side in [(0.083,.23,-.45),(.139,.16,.4),(.233,.10,-.15),(.379,.065,.25)]:
            add(sig,start+delay,gain*room*level,side,0)

def tt(d): return np.arange(int(d*SR))/SR

def soften(x, ms=3):
    n=min(int(ms/1000*SR),len(x)//2)
    if n: x[:n]*=np.sin(np.linspace(0,np.pi/2,n))**2; x[-n:]*=np.linspace(1,0,n)**2
    return x

def struck(midi,d=3.0,vel=.15,pan=0,start=0,warm=True):
    t=tt(d); f=440*2**((midi-69)/12)
    y=np.zeros_like(t)
    for h in range(1,9):
        # Very slight stretched partials; upper partials decay sooner like a soft struck string.
        freq=f*h*np.sqrt(1+.000085*h*h)
        decay=(2.45 if warm else 1.25)/(1+.30*(h-1))
        y += (1/h**1.65)*np.sin(2*np.pi*freq*t+.045*h)*np.exp(-t/decay)
    y*=1-np.exp(-t/.006)
    soften(y,8)
    add(y,start,vel,pan,.8 if warm else .48)

def click(start,vel=.1,pan=0,weight=1.):
    t=tt(.105)
    noise=rng.standard_normal(len(t))
    # Smoothed noise avoids brittle white-noise splatter.
    noise=np.convolve(noise,np.ones(13)/13,mode='same')
    y=.65*np.sin(2*np.pi*(580-220*t)*t)*np.exp(-t/.012)
    y+=.5*noise*np.exp(-t/.009)+.42*np.sin(2*np.pi*142*t)*np.exp(-t/.027)*weight
    add(soften(y,1.7),start,vel,pan,.25)

# Machine: contained low pulse, accelerando ticks and sparse F minor/add9 glass intervals.
t=tt(11.2)
fade=np.minimum(t/.5,1)*np.minimum(np.maximum((11.2-t)/.04,0),1)
pulse=(.44+.56*np.sin(2*np.pi*.86*t)**4)
low=np.sin(2*np.pi*65.406*t)*pulse*.033+np.sin(2*np.pi*130.812*t)*.008
add(low*fade,0,1,0,.25)
for s,m,v,p in [(0.35,53,.065,-.2),(2.45,60,.055,.25),(4.9,56,.062,-.3),(7.55,67,.051,.3),(9.35,60,.06,-.1)]:
    struck(m,2.1,v,p,s,False)
s=.34
while s<10.6:
    speed=(s/10.6)**2
    click(s,.023+.024*speed,(-1 if int(s*10)%2 else 1)*.27,.3)
    s+=.68-.50*speed
for s in [1.,3.8,6.7,8.2,9.6]:
    click(s,.14,0,1.3); click(s+.062,.044,.18,.3)
    events.append({'time':s,'cue':'weighted paper-cut/cash-register sale'})
# Accelerating mechanical whirl ends exactly at 11.2, followed by zero machinery.
t=tt(.6); u=t/.6
whirl=(np.sin(2*np.pi*(180*t+440*t*t))+.30*np.sin(2*np.pi*(360*t+880*t*t)))
whirl*=np.sin(np.pi*np.minimum(u*1.5,1)/2)*np.minimum((.6-t)/.025,1)
add(whirl,10.6,.045,0,.0)
for s in np.arange(10.61,11.17,.065): click(float(s),.04,0,.4)
# Cancel any pre-transition reverb tails in the machine score, preserving the abrupt change.
bus[int(11.2*SR):]=0
bus[int(11.17*SR):int(11.2*SR)]*=np.linspace(1,0,int(.03*SR))[:,None]
events.append({'time':11.2,'cue':'complete removal of machinery; warm struck tones'})

# Small warm personal space: sparse F minor colors, enough silence for the invitation.
for s,m,v,p in [(11.24,53,.105,-.15),(11.29,60,.071,.12),(11.38,68,.066,.24),(13.75,67,.062,.12),(15.1,60,.055,-.2)]:
    struck(m,4.2,v,p,s,True)
# Very low-level filtered room air (not a heavy atmospheric music bed).
t=tt(18.8); air=rng.standard_normal(len(t)); air=np.convolve(air,np.ones(121)/121,mode='same')
air*=np.minimum(t/.5,1)*np.minimum((18.8-t)/1.1,1)
add(air,11.2,.008,0,0)
# Gentle original two-note phone notification.
for s,f in [(12.,880),(12.145,1174.659)]:
    t=tt(.44); x=(np.sin(2*np.pi*f*t)+.17*np.sin(2*np.pi*2*f*t))*np.exp(-t/.105)
    x*=1-np.exp(-t/.006); add(soften(x,5),s,.045,.28,.18)
events.append({'time':12.,'cue':'soft two-tone phone ping'})

# Empty room after the invitation: modest resonance, not a horror sting.
t=tt(3.7)
y=(np.sin(2*np.pi*87.307*t)+.3*np.sin(2*np.pi*130.812*t))*np.exp(-t/1.1)
y*=1-np.exp(-t/.025)
add(soften(y,15),16.3,.075,-.05,.65)
for s in [17.15,18.55,20.0,21.55,23.15,24.8]: click(s,.030,-.2,.35)
events.append({'time':16.3,'cue':'restrained empty-room resonance and slow isolated ticks'})
# Paper feed: short, smooth, dry friction and tiny roller bumps.
t=tt(.64); z=rng.standard_normal(len(t)); z=np.convolve(z,np.ones(18)/18,mode='same')
env=np.sin(np.pi*t/.64)**1.4
y=z*env*(.55+.45*np.sin(2*np.pi*23*t)**2)
add(soften(y,8),20.2,.10,.15,.05)
events.append({'time':20.2,'cue':'short paper feed'})
# Negative stamp is soft mechanical closure, no comic buzzer.
t=tt(.21); z=rng.standard_normal(len(t)); z=np.convolve(z,np.ones(24)/24,mode='same')
y=.6*np.sin(2*np.pi*171*t)*np.exp(-t/.027)+z*np.exp(-t/.017)
add(soften(y,2.5),23.3,.12,0,.12)
events.append({'time':23.3,'cue':'subdued dry negative stamp'})
# Final unresolved F minor add9; upper G remains suspended rather than resolving.
for off,m,v,p in [(0,41,.060,-.1),(.025,53,.070,-.2),(.070,60,.050,.0),(.115,68,.053,.14),(.23,79,.049,.28)]:
    struck(m,4.8,v,p,25.2+off,True)
events.append({'time':25.2,'cue':'unresolved F minor/add9 chord and suspended upper G'})
# All final sound closes into a full second of digital silence.
fade_start=int(28.15*SR); fade_end=int(29.0*SR)
bus[fade_start:fade_end]*=np.linspace(1,0,fade_end-fade_start)[:,None]**1.5
bus[fade_end:]=0
# Gentle DC/infra-bass removal via FFT, identical phase for each channel; no subsonic rumble.
for c in range(2):
    ft=np.fft.rfft(bus[:,c]); hz=np.fft.rfftfreq(N,1/SR)
    filt=1-np.exp(-(hz/35)**4)
    bus[:,c]=np.fft.irfft(ft*filt,n=N)
# Remove filter's tiny wraparound residue and enforce the defined quiet endpoints.
bus[:int(.012*SR)]*=np.linspace(0,1,int(.012*SR))[:,None]
bus[fade_end:]=0
peak=float(np.max(np.abs(bus))); target=10**(-3/20)
bus*=target/max(peak,1e-12)
# PCM-24 output uses no stochastic dither so the last second stays exact silence.
pcm=np.rint(np.clip(bus,-1,1)*8388607).astype(np.int32)
packed=np.column_stack([(pcm.ravel()&255),((pcm.ravel()>>8)&255),((pcm.ravel()>>16)&255)]).astype(np.uint8).tobytes()
wav=ROOT/'soundtrack.wav'
with wave.open(str(wav),'wb') as w:
    w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR); w.writeframes(packed)
metrics={'sample_rate_hz':SR,'channels':2,'pcm_bits':24,'duration_seconds':DURATION,'samples_per_channel':N,
 'max_sample_peak_dbfs':float(20*np.log10(np.max(np.abs(bus)))), 'rms_dbfs':float(20*np.log10(np.sqrt(np.mean(bus**2)))),
 'last_second_peak':float(np.max(np.abs(bus[-SR:]))),'original_generation':'deterministic additive synthesis and filtered seeded noise; no samples; no external services',
 'human_listening':'NOT_PERFORMED','events':events,'sha256':hashlib.sha256(wav.read_bytes()).hexdigest(),
 'artifacts':[str(ROOT/'synth.py'),str(wav),str(ROOT/'metrics.json')]}
(ROOT/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in metrics.items() if k not in ('events','artifacts')},ensure_ascii=False,indent=2))
