# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals


import octoprint.plugin
from octoprint.events import Events
import flask
import board
from rpi_ws281x import Color, PixelStrip, ws
import RPi.GPIO as GPIO


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# constants
BUTTON_PIN = "button_pin"
LIGHT_PIN = "light_pin"
INVERTED_OUTPUT = "inverted_output"
PREVIOUS_BUTTON_PIN = "previous_button_pin"
IS_LED_STRIP = "is_led_strip"
NB_LEDS = "nb_leds"

LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_CHANNEL = 0
LED_STRIP = ws.WS2812_STRIP
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)


class OctoLightPlugin(
		octoprint.plugin.AssetPlugin,
		octoprint.plugin.StartupPlugin,
		octoprint.plugin.ShutdownPlugin,
		octoprint.plugin.TemplatePlugin,
		octoprint.plugin.SimpleApiPlugin,
		octoprint.plugin.SettingsPlugin,
		octoprint.plugin.EventHandlerPlugin,
		octoprint.plugin.RestartNeedingPlugin
	):

	# variables
	light_state = False
	pixels = None

	def get_settings_defaults(self):
		return dict(
			light_pin=19,
			button_pin=2,
			previous_button_pin=2,
			inverted_output=False,
			is_led_strip=False,
			nb_leds=20,
		)

	def get_template_configs(self):
		return [
			dict(type="navbar", custom_bindings=True),
			dict(type="settings", custom_bindings=True)
		]

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/octolight.js"],
			css=["css/octolight.css"]
			#less=["less/octolight.less"]
		)

	def on_after_startup(self):
		self.light_state = False
		self._logger.info("--------------------------------------------")
		self._logger.info("OctoLight started, listening for GET request")
		self._logger.debug("GPIO Mode: {}".format(
			GPIO.getmode()
		))
		self._logger.info("Light pin: {}, inverted_input: {}, button pin: {}".format(
			self._settings.get([LIGHT_PIN]),
			self._settings.get([INVERTED_OUTPUT]),
			self._settings.get([BUTTON_PIN])
		))
		self._logger.info("--------------------------------------------")

		# Setting the default state of the light pin
		self.setup_pin()
		if not bool(self._settings.get([IS_LED_STRIP])):
			if bool(self._settings.get([INVERTED_OUTPUT])):
				GPIO.output(int(self._settings.get([LIGHT_PIN])), GPIO.HIGH)
			else:
				GPIO.output(int(self._settings.get([LIGHT_PIN])), GPIO.LOW)

		self._plugin_manager.send_plugin_message(self._identifier, dict(isLightOn=self.light_state))

		# Enabling watch to the default button pin
		self.enable_watch_button(self._settings.get([BUTTON_PIN]))

	def on_api_get(self, request):
		self._logger.info("Got request. Light state: {}".format(
			self.light_state
		))

		if self._settings.get([BUTTON_PIN]) != self._settings.get([PREVIOUS_BUTTON_PIN]):
			# stop watching on the previous pin
			GPIO.remove_event_detect(
				self._settings.get([PREVIOUS_BUTTON_PIN]))
			# enable watching on the new pin
			self.enable_watch_button(self._settings.get([BUTTON_PIN]))
			self._settings.set([PREVIOUS_BUTTON_PIN],
							   self._settings.get([BUTTON_PIN]))

		self.setup_pin()

		self.change_light_state(None)

		return flask.jsonify(status="ok")

	def on_event(self, event, payload):
		self._plugin_manager.send_plugin_message(self._identifier, dict(isLightOn=self.light_state))
		if event == Events.CLIENT_OPENED:
			return


	def enable_watch_button(self, button):
		self._logger.info("watching events on pin : {}".format(
			button
		))
		GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.add_event_detect(button, GPIO.FALLING,
							  callback=self.change_light_state, bouncetime=200)

	def change_light_state(self, channel):
		self.light_state = not self.light_state

		# Sets the light state depending on the inverted output setting (XOR)
		if bool(self._settings.get([IS_LED_STRIP])):
			if self.light_state:
				self._logger.debug(
					"Led strip mode is enabled, will turn on the led strip")
				self.colorWipe(self.pixels, Color(255, 255, 255))
			else:
				self._logger.debug(
					"Led strip mode is enabled, will turn off the led strip")
				self.colorWipe(self.pixels, Color(0, 0, 0))
		elif self.light_state ^ self._settings.get([INVERTED_OUTPUT]):
			GPIO.output(int(self._settings.get([LIGHT_PIN])), GPIO.HIGH)
		else:
			GPIO.output(int(self._settings.get([LIGHT_PIN])), GPIO.LOW)

		self._logger.debug("Light state switched to : {}".format(
			self.light_state
		))
		# message the ui to change the button color
		self._plugin_manager.send_plugin_message(self._identifier, dict(isLightOn=self.light_state))


	def get_update_information(self):
		return dict(
			octolight=dict(
				displayName="OctoLight",
				displayVersion=self._plugin_version,

				type="github_release",
				current=self._plugin_version,

				user="emouty",
				repo="OctoLight",
				pip="https://github.com/emouty/OctoLight/archive/{target}.zip"
			)
		)

	def on_shutdown(self):
		# release GPIO pin on shutdown
		GPIO.cleanup()

	# Define functions which animate LEDs in various ways.
	def colorWipe(self, strip, color):
		"""Wipe color across display a pixel at a time."""
		for i in range(strip.numPixels()):
			strip.setPixelColor(i, color)
			strip.show()

	def setup_pin(self):
		if bool(self._settings.get([IS_LED_STRIP])):

			# enabling led strip on selected pin
			self.pixels = PixelStrip(int(self._settings.get([NB_LEDS])), int(self._settings.get(
				[LIGHT_PIN])), LED_FREQ_HZ, LED_DMA, bool(self._settings.get([INVERTED_OUTPUT])), LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
			self.pixels.begin()
		else:
			# Sets the GPIO every time, if user changed it in the settings.
			GPIO.setup(int(self._settings.get([LIGHT_PIN])), GPIO.OUT)

__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = OctoLightPlugin()

__plugin_hooks__ = {
	"octoprint.plugin.softwareupdate.check_config":
		__plugin_implementation__.get_update_information
}
