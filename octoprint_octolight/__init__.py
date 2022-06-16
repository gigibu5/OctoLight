# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import octoprint.plugin
from octoprint.events import Events
import flask

import math
from octoprint.util import RepeatedTimer

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

class OctoLightPlugin(
		octoprint.plugin.AssetPlugin,
		octoprint.plugin.StartupPlugin,
		octoprint.plugin.TemplatePlugin,
		octoprint.plugin.SimpleApiPlugin,
		octoprint.plugin.SettingsPlugin,
		octoprint.plugin.EventHandlerPlugin,
		octoprint.plugin.RestartNeedingPlugin
	):

	light_state = False
	delayed_state = None

	def get_settings_defaults(self):
		return dict(
			light_pin = 13,
			inverted_output = False,
			delay_off = 5
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
			css=["css/octolight.css"],
			#less=["less/octolight.less"]
		)

	def on_after_startup(self):
		self.light_state = False
		self._logger.info("--------------------------------------------")
		self._logger.info("OctoLight started, listening for GET request")
		self._logger.info("Light pin: {}, inverted_input: {}, Delay Time: {}".format(
			self._settings.get(["light_pin"]),
			self._settings.get(["inverted_output"]),
			self._settings.get(["delay_off"])
		))
		self._logger.info("--------------------------------------------")

		# Setting the default state of pin
		GPIO.setup(int(self._settings.get(["light_pin"])), GPIO.OUT)
		if bool(self._settings.get(["inverted_output"])):
			GPIO.output(int(self._settings.get(["light_pin"])), GPIO.HIGH)
		else:
			GPIO.output(int(self._settings.get(["light_pin"])), GPIO.LOW)

		#Because light is set to ff on startup we don't need to retrieve the current state
		"""
		r = self.light_state = GPIO.input(int(self._settings.get(["light_pin"])))
        if r==1:
                self.light_state = False
        else:
                self.light_state = True

        self._logger.info("After Startup. Light state: {}".format(
                self.light_state
        ))
        """

		self._plugin_manager.send_plugin_message(self._identifier, dict(isLightOn=self.light_state))

	def light_toggle(self):
		# Sets the GPIO every time, if user changed it in the settings.
		GPIO.setup(int(self._settings.get(["light_pin"])), GPIO.OUT)

		self.light_state = not self.light_state
		self.stopTimer()

		# Sets the light state depending on the inverted output setting (XOR)
		if self.light_state ^ self._settings.get(["inverted_output"]):
			GPIO.output(int(self._settings.get(["light_pin"])), GPIO.HIGH)
		else:
			GPIO.output(int(self._settings.get(["light_pin"])), GPIO.LOW)

		self._logger.info("Got request. Light state: {}".format(
			self.light_state
		))

		self._plugin_manager.send_plugin_message(self._identifier, dict(isLightOn=self.light_state))

	def on_api_get(self, request):
		action = request.args.get('action', default="toggle", type=str)

		if action == "toggle":
			self.light_toggle()

			return flask.jsonify(state=self.light_state)

		elif action == "getState":
			return flask.jsonify(state=self.light_state)

		elif action == "turnOn":
			if not self.light_state:
				self.light_toggle()

			return flask.jsonify(state=self.light_state)

		elif action == "turnOff":
			if self.light_state:
				self.light_toggle()

			return flask.jsonify(state=self.light_state)

		elif action == "delayOff":
			self.delayed_off_setup()
			return flask.jsonify(state=self.light_state)

		elif action == "delayOffStop":
			self.delayed_off()
			return flask.jsonify(state=self.light_state)

		else:
			return flask.jsonify(error="action not recognized")

	#This stops the current timer, this does not control the light
	def stopTimer(self):
		if self.delayed_state is not None:
			self._logger.info("Stopping schedule")
			self.delayed_state.cancel()
			self.delayed_state = None

		return

	#This sets up the timer, this does not control the light
	#Check if the timer is already running, if so, stop it, then set it up with a new time
	def startTimer(self, mins):
		if math.isnan(int(mins)):
			self._logger.info("Error: Received value that is not an int: {}".format(
				mins
			))
			return
		
		self.stopTimer()

		self._logger.info("Setting up schedule")
		self.delayed_state = RepeatedTimer(int(mins) * 60, self.delayed_off)
		self.delayed_state.start()
		self._logger.info("Time till shutoff: {} seconds".format(
			int(mins) * 60
		))

		return

	#Setup the light to shutoff when called
	def delayed_off(self):
		if self.light_state:
			self.light_toggle()

		self.stopTimer()
		
		return

	#Setup the light to turn on then off after a set time
	def delayed_off_setup(self):
		if not self.light_state:
			self.light_toggle()
					#self._logger.info("int(self._settings.get(["delay_off"])) * 60")

		self.startTimer(self._settings.get(["delay_off"]))

		return

	def on_event(self, event, payload):
		if event == Events.CLIENT_OPENED:
			self._plugin_manager.send_plugin_message(self._identifier, dict(isLightOn=self.light_state))
			return
		if event == Events.PRINT_STARTED:
			self.delayed_off_setup()
			return

	def get_update_information(self):
		return dict(
			octolight=dict(
				displayName="OctoLight",
				displayVersion=self._plugin_version,

				type="github_release",
				current=self._plugin_version,

				user="gigibu5",
				repo="OctoLight",
				pip="https://github.com/gigibu5/OctoLight/archive/{target}.zip"
			)
		)

__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = OctoLightPlugin()

__plugin_hooks__ = {
	"octoprint.plugin.softwareupdate.check_config":
	__plugin_implementation__.get_update_information
}
