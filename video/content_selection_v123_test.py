import unittest
from content_selection_v123 import CATALOGUE,select_for_approved,choose_next_topic,StopSafely
PASS=(200,{"status":"DRY_RUN_OK","sideEffects":False})
DUP=(422,{"status":"V122_BLOCKED","detail":"Semantic duplicate or closely related content; publishing stopped (score 0.702)"})
TOPIC_PASS=(200,{"status":"V123_TOPIC_AVAILABLE","sideEffects":False})
TOPIC_DUP=(422,{"status":"V123_TOPIC_DUPLICATE"})
class SelectionTest(unittest.TestCase):
    def test_approved_topic_only(self):
        calls=[]
        def check(c):
            calls.append(c)
            return DUP if len(calls)==1 else PASS
        c,_=select_for_approved("web",check)
        self.assertEqual(c.angle,"references")
        self.assertTrue(all(x.topic=="web" for x in calls))
    def test_all_duplicate(self):
        calls=[]
        def check(c):calls.append(c);return DUP
        self.assertEqual(select_for_approved("web",check),(None,None))
        self.assertEqual(len(calls),3)
    def test_timeout_stops(self):
        calls=[]
        def check(c):calls.append(c);return 503,{}
        with self.assertRaises(StopSafely):select_for_approved("web",check)
        self.assertEqual(len(calls),1)
    def test_wrong_destination_stops(self):
        with self.assertRaises(StopSafely):select_for_approved("web",lambda c:(422,{"status":"V122_BLOCKED","detail":"Wrong destination"}))
    def test_uncertain_mutation_stops(self):
        with self.assertRaises(StopSafely):select_for_approved("web",lambda c:(422,{"status":"V122_BLOCKED","detail":"Buffer outcome uncertain; inspect before retry"}))
    def test_false_success_stops(self):
        with self.assertRaises(StopSafely):select_for_approved("web",lambda c:(200,{"status":"DRY_RUN_OK","sideEffects":True}))
    def test_topic_switch(self):
        calls=[]
        def check(c):calls.append(c.topic);return TOPIC_DUP if c.topic=="auto" else TOPIC_PASS
        self.assertEqual(choose_next_topic({"web"},check).topic,"menu")
        self.assertEqual(calls,["auto","menu"])
    def test_no_topic(self):
        self.assertIsNone(choose_next_topic({"web"},lambda c:TOPIC_DUP))
    def test_topic_infrastructure_failure(self):
        with self.assertRaises(StopSafely):choose_next_topic({"web"},lambda c:(503,{}))
    def test_caption_grounded_shape(self):
        self.assertEqual(len(CATALOGUE),5)
        for c in CATALOGUE:
            self.assertIn("AI-narráció",c.text)
            self.assertIn("https://darkline-studio.web.app/",c.text)
            self.assertTrue(60<=len(c.text)<=2000)
if __name__=="__main__":unittest.main(verbosity=2)
