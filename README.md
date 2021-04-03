# OctoLight
A simple plugin that adds a button to the navigation bar for toggling a GPIO pin on the Raspberry Pi.

![WebUI interface](img/screenshoot.png)

## Setup
Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

	https://github.com/gigibu5/OctoLight/archive/master.zip

## Configuration
![Settings panel](img/settings.png)

Currently, you can configure theses settings:
- `Light PIN`: The pin on the Raspberry Pi that the button controls. 
	- Default value: 19
	- The pin number is saved in the **BCM layout naming** scheme (orange labels on the pinout image below).
	- **!! IMPORTANT !!** The Raspberry Pi can only control th **GPIO** pins (orange labels on the pinout image below)
	![Raspberry Pi GPIO](img/rpi_gpio.png)

- `Inverted output`: If true, the output will be inverted
	- Usage: if you have a light, that is turned off when voltage is applied to the pin (wired in negative logic), you 
	should turn on this option, so the light isn't on when you reboot your Raspberry Pi.
- `Enable physical button`: If true, you will be able to turn on and off the light from a physical button wired to 
the Raspberry Pi GPIO
	- Default value: False
- `Button PIN`: The pin on the Raspberry Pi to read value from for the physical button. 
	- Default value: 2
- `Led Strip`: if checked, enable the support for a led strip on the `Light PIN`
	- Default value: False
    - Before using this option, you should follow the [guide bellow](#setup-spi)
    - Usage: theoretically it should work on a PWM, PCM or SPI pin but it has only been tested on the SPI pin.
-  `Number of leds`: Number of leds on the led strip.
   -  Default value: 20

## Setup SPI
**Only needed if you use the LED strip option**
1. Add the pi user to the gpio group.
	```shell
	sudo adduser pi gpio
	```
2. Enable SPI. The plugin uses SPI to drive the LEDs, which is disabled by default and needs to be turned on.
	- `Adds dtparam=spi=on to /boot/config.txt`
3. Increase SPI buffer size.  Whilst the plugin will work without this, it will only work well with a handful of LEDs.
	- `Adds spidev.bufsize=32768 to the end of /boot/cmdline.txt`
4. Set compatible clock frequency Raspberry Pi 3 or earlier only, not required for a Pi 4  The Pi 3's default internal 
clock frequency is not compatible with SPI, so it needs to be set to 250 to be compatible.
   - `Adds core_freq=250 to /boot/config.txt`
5. Set a minimum clock frequency Raspberry Pi 4 only  On a Raspberry Pi 4, the clock frequency is dynamic and can change
when the pi is 'idle' vs. 'working', which causes LEDs to flicker, change colour, or stop working completely. By setting
 a minimum the same as the max, we stop this dynamic clocking.
   -  `Adds core_freq_min=500 to /boot/config.txt`
6. reboot the pi
	```shell
	sudo reboot
	```

_[source](https://cp2004.gitbook.io/ws281x-led-status/guides/setup-guide-1/spi-setup)_

## TO DO
- [x] Update interface if Light is turned on or off
- [ ] Use wizard to setup the led strip library like on [OctoPrint-WS281x_LED_Status](https://github.com/cp2004/OctoPrint-WS281x_LED_Status) 

### Maybe in the distant future:
- [ ] Turn off on finish print

## Thanks

Thanks to [cp2004](https://github.com/cp2004) for its documentation to setup the SPI interface to be used by the
 [rpi_ws281x](https://github.com/jgarff/rpi_ws281x) library 