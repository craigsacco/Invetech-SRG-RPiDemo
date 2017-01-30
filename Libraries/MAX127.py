import Adafruit_GPIO.I2C as I2C
import AdafruitOverrides

class MAX127(object):

    CTL_START = 0x80
    CTL_SELx_SHIFT = 4
    CTL_RANGE = 0x08
    CTL_BIPOLAR = 0x04
    CTL_OP_NORMAL = 0x00
    CTL_OP_POWERDOWN_STANDBY = 0x02
    CTL_OP_POWERDOWN_FULL = 0x03

    ADC_MAX_VALUE = 4095
    ADC_REFERENCE = 5.0

    def __init__(self, address=0x28, busnum=None, i2c=None, **kwargs):
        address = int(address)
        self.__name__ = \
            "MAX127" if address in range(0x28, 0x30) else \
            "Bad address for MAX127: 0x%02X not in range [0x28..0x2F]" % address
        if self.__name__[0] != 'M':
            raise ValueError(self.__name__)
        # Create I2C device.
        self._address = address
        self._i2c = i2c or I2C
        self._busnum = busnum or self._i2c.get_default_bus()
        self._device = self._i2c.get_i2c_device(self._address, self._busnum, **kwargs)
        AdafruitOverrides.add_i2c_device_overrides(self._device)
        AdafruitOverrides.add_smbus_overrides(self._device._bus)

    def send_control_byte(self, value):
        self._device.writeRaw8(MAX127.CTL_START | value)

    def stand_by(self):
        self.send_control_byte(MAX127.CTL_OP_POWERDOWN_STANDBY)

    def power_down(self):
        self.send_control_byte(MAX127.CTL_OP_POWERDOWN_FULL)

    def start_conversion(self, channel, range=False, bipolar=False):
        self.send_control_byte(MAX127.CTL_START |
                               (channel << MAX127.CTL_SELx_SHIFT) |
                               (MAX127.CTL_RANGE if range else 0) |
                               (MAX127.CTL_BIPOLAR if bipolar else 0) |
                               MAX127.CTL_OP_NORMAL)

    def get_adc_value(self):
        return (self._device.readRawU16BE() >> 4)

    def get_voltage(self, range=False, bipolar=False):
        value = self.get_adc_value()
        voltage = (value * MAX127.ADC_REFERENCE) / MAX127.ADC_MAX_VALUE
        if bipolar:
            voltage = (voltage * 2.0) - MAX127.ADC_REFERENCE
        if range:
            voltage = (voltage * 2.0)
        return voltage