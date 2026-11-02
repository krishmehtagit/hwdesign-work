"""Intent-derived oracle, NumPy reference, and Waveflow-schema stimuli."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from histogram import HistogramCmdHdr, HistogramRespHdr, HistogramError
from waveflow.utils.burst_io import StreamBurst, read_bursts, write_bursts
CONFIG, DATA, READ, END = 0, 1, 2, 3

@dataclass(frozen=True)
class Cmd:
    code:int; tx:int; lo:int=0; shift:int=0; nbins:int=0; samples:tuple[int,...]=()
    nsamp:int|None=None; header:str='ok'; data_last:bool=True
    @property
    def announced(self): return len(self.samples) if self.nsamp is None else self.nsamp
@dataclass(frozen=True)
class Scenario: cmds:tuple[Cmd,...]

def header(c):
    h=HistogramCmdHdr(); h.code=c.code; h.tx_id=c.tx; h.lo=c.lo; h.shift=c.shift; h.nbins=c.nbins; h.nsamp=c.announced; return h.serialize(word_bw=32)
def response(tx,n):
    h=HistogramRespHdr(); h.tx_id=tx; h.ndata=n; return h.serialize(word_bw=32)
def numpy_hist(samples,lo,shift,nbins):
    x=np.asarray(samples,dtype=np.int16).astype(np.int32); o=x-int(lo); below=int(np.sum(o<0)); idx=o[o>=0]>>shift; above=int(np.sum(idx>=nbins)); return np.bincount(idx[idx<nbins],minlength=nbins).astype(np.uint32),below,above
def expected(sc):
    bins=np.zeros(256,dtype=np.uint32); below=np.uint32(0); above=np.uint32(0); configured=False; lo=shift=nbins=0; out=[]; st={'halted':0,'error':0,'tx_id':0}
    for c in sc.cmds:
        if c.header=='early': st={'halted':1,'error':1,'tx_id':c.tx}; break
        if c.header=='missing': st={'halted':1,'error':2,'tx_id':c.tx}; break
        if c.code not in (CONFIG,DATA,READ,END): st={'halted':1,'error':3,'tx_id':c.tx}; break
        if c.code in (DATA,READ) and not configured: st={'halted':1,'error':4,'tx_id':c.tx}; break
        if c.code==CONFIG:
            if not(1<=c.nbins<=256 and 0<=c.shift<=15): st={'halted':1,'error':5,'tx_id':c.tx}; break
            bins.fill(0); below=np.uint32(0); above=np.uint32(0); lo,shift,nbins=c.lo,c.shift,c.nbins; configured=True
        elif c.code==DATA:
            if not(1<=c.announced<=4096): st={'halted':1,'error':5,'tx_id':c.tx}; break
            # The early-TLAST command processes the received prefix, then halts.
            received=c.samples
            for x in received:
                o=int(x)-lo
                if o<0: below=np.uint32(int(below)+1)
                elif (o>>shift)>=nbins: above=np.uint32(int(above)+1)
                else: bins[o>>shift]=np.uint32(int(bins[o>>shift])+1)
            if len(received)<c.announced: st={'halted':1,'error':6,'tx_id':c.tx}; break
            if not c.data_last: st={'halted':1,'error':7,'tx_id':c.tx}; break
            out.append(StreamBurst(response(c.tx,0),True))
        elif c.code==READ:
            out += [StreamBurst(response(c.tx,nbins+2),True),StreamBurst(np.r_[bins[:nbins],below,above].astype(np.uint32),True)]
        else: break
    return out,st

def scenarios():
    same=tuple([0]*4096); base=lambda t: Scenario((Cmd(CONFIG,t,0,0,1),Cmd(DATA,t+1,samples=(0,)),Cmd(READ,t+2),Cmd(END,t+3)))
    d={
      'hand_edges':Scenario((Cmd(CONFIG,1,-2,1,4),Cmd(DATA,2,samples=(-3,-2,-1,0,5,6)),Cmd(READ,3),Cmd(END,4))),
      'nbins_256_edges':Scenario((Cmd(CONFIG,5,-32768,0,256),Cmd(DATA,6,samples=(-32768,-32767,32767)),Cmd(READ,7),Cmd(END,8))),
      'nsamp_1':Scenario((Cmd(CONFIG,9,0,15,1),Cmd(DATA,10,samples=(-1,)),Cmd(READ,11),Cmd(END,12))),
      'same_bin_4096':Scenario((Cmd(CONFIG,13,0,0,1),Cmd(DATA,14,samples=same),Cmd(READ,15),Cmd(END,16))),
      'clear':Scenario((Cmd(CONFIG,20,0,0,2),Cmd(DATA,21,samples=(0,1,2)),Cmd(READ,22),Cmd(CONFIG,23,-10,2,3),Cmd(READ,24),Cmd(END,25))),
      'header_early':Scenario((Cmd(CONFIG,30,0,0,1,header='early'),)),
      'header_missing':Scenario((Cmd(CONFIG,31,0,0,1,header='missing'),)),
      'unknown_command':Scenario((Cmd(4,32),)),
      'data_before_config':Scenario((Cmd(DATA,33,samples=(0,)),)),
      'read_before_config':Scenario((Cmd(READ,34),)),
      'bad_nbins_zero':Scenario((Cmd(CONFIG,35,0,0,0),)),
      'bad_nbins_257':Scenario((Cmd(CONFIG,36,0,0,257),)),
      'bad_shift_16':Scenario((Cmd(CONFIG,37,0,16,1),)),
      'bad_nsamp_zero':Scenario((Cmd(CONFIG,38,0,0,1),Cmd(DATA,39,nsamp=0))),
      'bad_nsamp_4097':Scenario((Cmd(CONFIG,40,0,0,1),Cmd(DATA,41,samples=tuple([0]*4097),nsamp=4097))),
      'data_early':Scenario((Cmd(CONFIG,42,0,0,1),Cmd(DATA,43,samples=(0,0),nsamp=4))),
      'data_missing':Scenario((Cmd(CONFIG,44,0,0,1),Cmd(DATA,45,samples=(0,),data_last=False))),
      # Deliberately malformed in two ways: framing wins before opcode/dependency checks.
      'priority_header_unknown':Scenario((Cmd(4,46,header='missing'),)),
      # Unconfigured DATA with nsamp=0: dependency error wins before bad parameter.
      'priority_no_config_bad_nsamp':Scenario((Cmd(DATA,47,nsamp=0),)),
    }
    # Each fatal activation is immediately followed in the ordered suite by a clean new activation.
    for n in list(d):
        if n not in ('hand_edges','nbins_256_edges','nsamp_1','same_bin_4096','clear'):
            d['fresh_after_'+n]=base(100+len(d)*4)
    return d

def stimulus(sc):
    a=[]
    for c in sc.cmds:
        h=header(c)
        if c.header=='early': a.append(StreamBurst(h[:1],True)); continue
        a.append(StreamBurst(h,c.header=='ok'))
        if c.code==DATA and c.samples:a.append(StreamBurst(np.asarray(c.samples,dtype=np.int16).astype(np.uint16),c.data_last))
    return a
def write_scenarios(root:Path,word_bw=32):
    root.mkdir(parents=True,exist_ok=True); ns=[]
    for n,s in scenarios().items():
        d=root/n; d.mkdir(parents=True,exist_ok=True); (d/'csim').mkdir(exist_ok=True); (d/'cosim').mkdir(exist_ok=True); o,st=expected(s); write_bursts(stimulus(s),d/'in'); write_bursts(o,d/'expected'); (d/'expected_status.json').write_text(json.dumps(st)+'\n'); (d/'scenario.json').write_text(json.dumps({'pysim':False,'cosim':True})+'\n'); ns.append(n)
    (root/'scenarios.txt').write_text('\n'.join(ns)+'\n'); return ns
def check(root:Path,stage:str,names=None):
    ans={}
    for n in names or (root/'scenarios.txt').read_text().split():
        d=root/n; w=read_bursts(d/'expected'); g=read_bursts(d/stage) if (d/stage/'words.bin').exists() else []; p=[]
        if len(w)!=len(g) or any(not np.array_equal(a.words,b.words) or a.tlast!=b.tlast for a,b in zip(w,g)):p.append('stream mismatch')
        q=d/stage/'status.json'; x=json.loads(q.read_text()) if q.exists() else None; y=json.loads((d/'expected_status.json').read_text())
        if x!=y:p.append(f'status {x} expected {y}')
        ans[n]=p
    return ans
def run_model(root:Path):
    """Protocol-model result, independent from the C++ output files."""
    for n,s in scenarios().items():
        d=root/n; o,st=expected(s); write_bursts(o,d/'model'); (d/'model'/'status.json').write_text(json.dumps(st)+'\n')
def verify_numpy_and_hand():
    b,lo,hi=numpy_hist((-3,-2,-1,0,5,6),-2,1,4)
    assert b.tolist()==[2,1,0,1] and lo==1 and hi==1
    b,lo,hi=numpy_hist((0,)*4096,0,0,1)
    assert b.tolist()==[4096] and lo==0 and hi==0
    return {'hand_edges':'PASS','numpy_bincount':'PASS'}
