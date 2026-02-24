- [ ] 41.1 Verify heartbeat and cron are functional
      Criterion: `python3 -m pytest tests/test_cron.py -v` passes and `python3 -c "from nanobot.cron.service import CronService; cs = CronService(); print('Cron service ready')"` returns ready
      File: `nanobot/cron/service.py`
      Blocker: None