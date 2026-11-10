#!/usr/bin/env python3
"""Real executable corruption campaign: modifies on-disk state pages; executes each variant.
Never mutates original release images. Validates the whole emitted tableau independently.
"""
from pathlib import Path
import hashlib, json, random, struct, subprocess,tempfile,time
R=Path(__file__).resolve().parents[1]
IMAGE=(R/'native/seed/genesis.x86_64').read_bytes()
D=0x2000
START=D+128
rng=random.Random(0x5EC007)

def rows(image):return image[START:START+768]

def run(image,path):
 path.write_bytes(image);path.chmod(0o700)
 p=subprocess.run([str(path)],capture_output=True,timeout=4)
 return p.returncode,p.stdout

def main():
 report={'status':'IN_PROGRESS','single_bit_replica_runs':0,'double_bit_same_location_refusals':0,'digest_flip_refusals':0,'state_lane_single_bit_repairs':0,'whole_lane_repair':0,'fatal_failures':[]}
 t=time.monotonic()
 try:
  with tempfile.TemporaryDirectory(prefix='native-fault-') as d:
   path=Path(d)/'damaged.x86_64'
   rc,baseline=run(IMAGE,path)
   assert rc==0 and len(baseline)==len(IMAGE)
   exact_rows=rows(baseline)
   # 3 * 256 unique positions across all 192 words, including left/right edges.
   sampled=set([0,1,7,8,31,32,63,127,128,255,256,383,384,511,512,639,640,766,767])
   while len(sampled)<256:sampled.add(rng.randrange(768))
   for lane in range(3):
    for off in sorted(sampled):
     m=bytearray(IMAGE);m[START+lane*768+off]^=1<<rng.randrange(8)
     rc,out=run(m,path)
     assert rc==0 and len(out)==len(IMAGE) and rows(out)==exact_rows,(lane,off,rc)
     report['single_bit_replica_runs']+=1
   for off in sorted(sampled)[:96]:
    m=bytearray(IMAGE);bit=1<<rng.randrange(8)
    m[START+off]^=bit;m[START+768+off]^=bit
    rc,out=run(m,path)
    assert rc==74 and not out,('double lane',off,rc)
    report['double_bit_same_location_refusals']+=1
   for b in range(32):
    m=bytearray(IMAGE);m[D+96+(b//8)]^=1<<(b%8)
    rc,out=run(m,path)
    assert rc==74 and not out,('digest',b,rc)
    report['digest_flip_refusals']+=1
   for lane in range(3):
    for bit in range(64):
     m=bytearray(IMAGE);m[D+16+8*lane+(bit//8)]^=1<<(bit%8)
     rc,out=run(m,path)
     # Single ternary-plane state corruption is corrected if at most one replica is affected.
     assert rc==0 and rows(out)==exact_rows,(lane,bit,rc)
     report['state_lane_single_bit_repairs']+=1
   for lane in range(3):
    m=bytearray(IMAGE)
    for off in range(768):m[START+768*lane+off]^=0xff
    rc,out=run(m,path)
    assert rc==0 and rows(out)==exact_rows,(lane,rc)
    report['whole_lane_repair']+=1
  report['status']='PASS'
 except Exception as e:
  report['status']='FAIL';report['fatal_failures'].append(repr(e))
 finally:
  report['elapsed_seconds']=round(time.monotonic()-t,3)
  (R/'evidence/fault_campaign.json').write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps(report,indent=2))
 if report['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
