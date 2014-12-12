import aiogevent
import aiotest.run
import gevent

config = aiotest.TestConfig()
config.asyncio = aiogevent.asyncio
config.socketpair = aiogevent.socketpair
config.new_event_pool_policy = aiogevent.EventLoopPolicy
config.sleep = gevent.sleep
config.support_threads = False
aiotest.run.main(config)
