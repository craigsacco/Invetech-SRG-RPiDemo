#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(1, 'Libraries')
sys.path.insert(1, 'Libraries/Adafruit_Python_PureIO')
sys.path.insert(1, 'Libraries/Adafruit_Python_GPIO')
sys.path.insert(1, 'Libraries/webpy')

import time, web, json, threading
from Adafruit_GPIO import GPIO
from Drivers.DS1624 import DS1624
from Drivers.MAX127 import MAX127
from Drivers.LM35OnMAX127 import LM35OnMAX127
from Drivers.HIH3610OnMAX127 import HIH3610OnMAX127
from Drivers.MS5534 import MS5534
from Drivers.SimpleLED import SimpleLED


class StationServer(object):

    DATA = {}
    DATA_MUTEX = threading.Lock()

    class DataService:

        def GET(self):
            web.header("Content-Type", "text/json")
            StationServer.DATA_MUTEX.acquire()
            data = StationServer.DATA
            StationServer.DATA_MUTEX.release()
            return json.dumps(data, sort_keys=True,
                              indent=4, separators=(',', ': '))

    class UIService:

        def GET(self):
            try:
                web.header("Content-Type", "text/html")
                return open("StationServer.html", "rb").read()
            except:
                raise web.notfound()

    URLS = (
        "/Data",        DataService,
        "/index.htm",   UIService,
        "/index.html",  UIService,
        "/",            UIService,
    )

    def __init__(self):
        self._server = web.application(StationServer.URLS, locals())
        self._ds1624 = DS1624(address=0x48)
        self._max127 = MAX127(address=0x28)
        self._lm35_1 = LM35OnMAX127(adc=self._max127, channel=0)
        self._lm35_2 = LM35OnMAX127(adc=self._max127, channel=1)
        self._hih3610 = HIH3610OnMAX127(adc=self._max127, channel=2)
        self._ms5534 = MS5534(sclk=22, miso=27, mosi=17)
        self._led_1 = SimpleLED(pin=18)
        self._led_2 = SimpleLED(pin=23)
        self._led_3 = SimpleLED(pin=24)
        self._leds = [self._led_1, self._led_2, self._led_3]

    def start_devices(self):
        self._ds1624.start_conversions()
        self._ms5534.send_reset()

    def stop_devices(self):
        self._ds1624.stop_conversions()
        self._max127.power_down()

    def update_data(self):
        StationServer.DATA_MUTEX.acquire()
        StationServer.DATA = {
            "ds1624": self._ds1624.get_data(),
            "lm35_1": self._lm35_1.get_data(),
            "lm35_2": self._lm35_2.get_data(),
            "hih3610": self._hih3610.get_data(),
            "ms5534": self._ms5534.get_data(),
        }
        StationServer.DATA_MUTEX.release()

    def background_acquisition(self):
        print "Started sensor acquisition"
        start = time.time()
        while self._running:
            time.sleep(0.2)
            if time.time() > start + 2.0:
                self.update_data()
                start = time.time()
        print "Stopped sensor acquisition"

    def led_sequencer(self):
        print "Started LED sequencer"
        routine = 0
        iteration = 0
        index = 0
        while self._running:
            time.sleep(0.2)
            if routine == 0:
                if self._leds[index].get_state():
                    self._leds[index].off()
                    index += 1
                else:
                    self._leds[index].on()
                if index == len(self._leds):
                    index = 0
                    iteration += 1
                if iteration == 3:
                    routine = 1
                    iteration = 0
            elif routine == 1:
                if index == 0:
                    for led in self._leds:
                        led.on()
                    index += 1
                elif index == 1:
                    for led in self._leds:
                        led.off()
                    iteration += 1
                    index = 0
                if iteration == 3:
                    routine = 0
                    iteration = 0
        for led in self._leds:
            led.off()
        print "Stopped LED sequencer"

    def run_server(self):
        self._running = True
        self.start_devices()
        self._thread1 = threading.Thread(target=self.background_acquisition)
        self._thread1.start()
        self._thread2 = threading.Thread(target=self.led_sequencer)
        self._thread2.start()
        self._server.run()

    def stop_server(self):
        self._running = False
        self._thread1.join()
        self._thread2.join()
        self._server.stop()
        self.stop_devices()


def main():
    server = StationServer()
    result = 0
    try:
        server.run_server()
    except KeyboardInterrupt:
        result = 0
    except:
        result = 1
    finally:
        server.stop_server()
    return result


if __name__ == "__main__":
    sys.exit(main())
