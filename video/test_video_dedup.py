import tempfile, unittest, subprocess
from pathlib import Path
from video_dedup import fingerprint,compare,check,validate,script_text

A={"scenes":[{"heading":"Online időpontfoglalás","detail":"Vendégek egyszerűen választhatnak szabad időpontot a naptárban."}]}
B={"scenes":[{"heading":"Digitális étlap","detail":"Az étterem vendégei QR kóddal érik el a friss fogásokat."}]}
C={"scenes":[{"heading":"ONLINE IDŐPONTFOGLALÁS!","detail":"Vendégek egyszerűen választhatnak szabad időpontot a naptárban."}]}

def make(path,pattern):
    subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i",pattern,"-t","4","-c:v","libx264","-pix_fmt","yuv420p","-threads","1",str(path)],check=True)

class VideoDedupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        p=Path(cls.temp.name)
        cls.a=p/"a.mp4";cls.b=p/"b.mp4";cls.re=p/"re.mp4"
        make(cls.a,"testsrc2=size=128x224:rate=12")
        make(cls.b,"color=c=yellow:size=128x224:rate=12")
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(cls.a),"-c:v","libx264","-crf","32","-threads","1",str(cls.re)],check=True)
        cls.fa=fingerprint(cls.a,A);cls.fb=fingerprint(cls.b,B);cls.fr=fingerprint(cls.re,B)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_exact(self):self.assertEqual(compare(self.fa,self.fa),"identical file")
    def test_storyboard(self):self.assertEqual(compare(self.fa,fingerprint(self.b,C)),"same or near-identical storyboard")
    def test_recompressed(self):self.assertEqual(compare(self.fa,self.fr),"near-identical visual sequence")
    def test_different(self):self.assertIsNone(compare(self.fa,self.fb))
    def test_duplicate_blocks(self):
        with self.assertRaisesRegex(ValueError,"VIDEO_DUPLICATE"):check(self.fa,[("old",self.fr)])
    def test_new_passes(self):check(self.fb,[("old",self.fa)])
    def test_broken_history_blocks(self):
        with self.assertRaises(ValueError):check(self.fa,[("old",{})])
    def test_missing_storyboard(self):
        with self.assertRaises(ValueError):script_text({})
    def test_invalid_frames(self):
        with self.assertRaises(ValueError):validate({**self.fa,"frames":[]})

if __name__=="__main__":unittest.main()
