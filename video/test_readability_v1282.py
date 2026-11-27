"""Offline regression: no private video, account secret, network action or voice call."""
import tempfile
from pathlib import Path
import numpy as np
import readability_v1282 as r

def main():
    assert len(r.CONTEXT)==len(r.DEVICES)==10
    assert r.DEVICES.count('desktop')==r.DEVICES.count('mobile')==5
    for s in range(10):
        frame=np.zeros((1920,1080,3),dtype=np.uint8)
        original=frame.copy(); allowed=np.zeros((1920,1080),bool)
        for x,y,p in r.patches(s):
            h,w=p.shape[:2]
            assert x>=0 and y>=0 and x+w<=1080 and y+h<1429
            assert not allowed[y:y+h,x:x+w].any()
            allowed[y:y+h,x:x+w]=True
            frame[y:y+h,x:x+w]=p
        assert np.array_equal(frame[~allowed],original[~allowed])
        assert np.array_equal(frame[1429:],original[1429:])
        assert np.any(frame)
    with tempfile.TemporaryDirectory() as d:
        a=Path(d)/'fake.mp4'; b=Path(d)/'timing.json'; c=Path(d)/'output.mp4'
        a.write_bytes(b'fake');b.write_text('{}')
        try:r.main(a,b,c)
        except ValueError:pass
        else:raise AssertionError('unapproved source accepted')
        assert not c.exists()
    print('V1282_PASS 10 safe context layers; 5+5 device allocation; rejected unrelated source; zero private audio access')
if __name__=='__main__':main()
