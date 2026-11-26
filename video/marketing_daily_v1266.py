"""Review-only integration until exact Worker and all captures have been approved.
Preserve the V1265.1 slot/date guards and V126 paid budget adapter.
"""
import datetime as dt,os,argparse
import marketing_daily_v1265 as previous
import marketing_daily_v1263 as base

def execute(now,env):
    if not base.live_authorized(env):raise RuntimeError("live mode not authorized")
    kind=env.get("DARKLINE_V126_EXPECTED_SLOT")
    day=env.get("DARKLINE_V126_EXPECTED_DATE")
    if not previous.dispatch_allowed(now,kind,day):return "SKIP_CHANGED_WINDOW"
    if kind!="video":return previous.run_extended(now,env)
    import daily_catalogue_v124 as old
    import demo_topics_v1266 as new
    import demo_renderer_v1266 as renderer
    import selection_v1266 as selection
    import autonomous_daily_v124 as daily
    saved=(old.TOPICS,old.validate_catalogue,daily.choose)
    try:
        old.TOPICS=new.TOPICS
        old.validate_catalogue=new.validate_catalogue
        daily.choose=selection.choose
        with renderer.install():return base.run_live(now,env)
    finally:old.TOPICS,old.validate_catalogue,daily.choose=saved
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--execute",action="store_true")
    args=p.parse_args()
    if not args.execute:p.error("explicit execution required")
    print(execute(dt.datetime.now(dt.timezone.utc),os.environ),flush=True)
