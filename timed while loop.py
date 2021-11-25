import time

duration = 20   # [seconds]
time_start = time.time()

while time.time() < time_start + duration:
    print(time.time())
    time.sleep(.5)
