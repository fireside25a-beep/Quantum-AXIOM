#!/usr/bin/env python3
"""Native x86-64 ECC matrix, all bit positions in the three 768-byte tableau lanes.
These tests verify accepted native reparations against an uncorrupted native execution.
The source image is never overwritten. Test only against the local assembler-built input.
"""
import hashlib,json,os,random,subprocess,tempfile,time
from pathlib import Path
R=Path(__file__).resolve().parents[1]
IMAGE=(R/'native/seed/genesis.x86_64').read_bytes()
D=0x2000;T=D+128;LANE_SIZE=768
OUT=R/'evidence'
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 t0=time.monotonic()
 with tempfile.TemporaryDirectory(prefix='axiom-fault-injection-') as folder:
  f=Path(folder)/'run.x86_64'
  f.write_bytes(IMAGE);f.chmod(0o700)
  def execute(image):
   f.write_bytes(image)
   p=subprocess.run([str(f)],capture_output=True,timeout=4)
   return p.returncode,p.stdout
  rc,base=execute(IMAGE)
  assert rc==0 and len(base)==len(IMAGE),(rc,len(base))
  reference=base[T:T+LANE_SIZE]
  assert base[T+LANE_SIZE:T+2*LANE_SIZE]==reference
  assert base[T+2*LANE_SIZE:T+3*LANE_SIZE]==reference
  tested=0
  # Exhaust the entire lane matrix (3 * 768 * 8 = 18432 native executions).
  for lane in range(3):
   for byte in range(LANE_SIZE):
    for bit in range(8):
     b=bytearray(IMAGE);b[T+lane*LANE_SIZE+byte]^=1<<bit
     rc,result=execute(b)
     assert rc==0 and len(result)==len(IMAGE),(lane,byte,bit,'exit',rc,len(result))
     assert result[T:T+LANE_SIZE]==reference,(lane,byte,bit,'tableau parity mismatch')
     for replica in (1,2):assert result[T+replica*LANE_SIZE:T+(replica+1)*LANE_SIZE]==reference
     tested+=1
  pair_rejected=0
  for byte in range(0,LANE_SIZE,3):
   for lane_pair in ((0,1),(0,2),(1,2)):
    b=bytearray(IMAGE)
    for lane in lane_pair:b[T+lane*LANE_SIZE+byte]^=1
    rc,data=execute(b)
    assert rc==74 and not data,(byte,lane_pair,rc,len(data))
    pair_rejected+=1
  # A whole missing/overwritten lane is recoverable (all other two lanes agree).
  whole_lane_corrected=0
  for lane in range(3):
   b=bytearray(IMAGE)
   b[T+lane*LANE_SIZE:T+(lane+1)*LANE_SIZE]=b'\xff'*LANE_SIZE
   rc,data=execute(b)
   assert rc==0 and data[T:T+LANE_SIZE]==reference,(lane,rc)
   whole_lane_corrected+=1
  # Explicit 2-bit and 4-bit errors in one lane; majority is at lane granularity.
  rng=random.Random(0xA110C7)
  multi_bit_corrected=0
  for lane in range(3):
   for j in range(40):
    b=bytearray(IMAGE)
    for _ in range(2+j%3):
     off=rng.randrange(LANE_SIZE);mask=1<<rng.randrange(8)
     b[T+lane*LANE_SIZE+off]^=mask
    rc,data=execute(b)
    assert rc==0 and data[T:T+LANE_SIZE]==reference,(lane,j,rc)
    multi_bit_corrected+=1
  r={'status':'PASS','platform':os.uname().sysname+' '+os.uname().machine,
     'reference_image_sha256':digest(IMAGE),'reference_after_execution_tableau_sha256':digest(reference),
     'single_bit_native_execution_repairs':tested,'all_3_x_768_x_8_positions_covered':tested==3*768*8,
     'two_lane_same_bit_native_refusals':pair_rejected,
     'whole_lane_repairs':whole_lane_corrected,'multi_bit_one_lane_repairs':multi_bit_corrected,
     'model':'triplicated lane-majority ECC plus 32-bit unkeyed tableau digest; not malicious-code authenticity',
     'elapsed_seconds':round(time.monotonic()-t0,3)}
 OUT.mkdir(exist_ok=True,parents=True)
 (OUT/'full_memory_fault_matrix.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r,indent=2))
if __name__=='__main__':main()
