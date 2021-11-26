# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import octoprint.plugin
from octoprint.events import Events
import flask

import RPi.GPIO as GPIO


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
	gpio_board_mode = True

	def get_light_pin(self):
		board_pin = int(self._settings.get(["light_pin"]))
		if self.gpio_board_mode:
			return board_pin
		bcm_map = [-1, -1, 2, -1, 3, -1, 4, -1, -1, -1,
			   17, 18, 27, -1, 22, 23, -1, 24, 10, -1,
			   9, 25, 11, 8, -1, 7, -1, -1, 5, -1,
			   6, 12, 13, -1, 19, 16, 26, 20, -1, 21]
		if 1 <= board_pin <= 40:
			return bcm_map[board_pin - 1]
		return -1

	def get_settings_defaults(self):
		return dict(
			light_pin = 13,
			inverted_output = False
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
		# Set GPIO to board numbering, if possible
		current_mode = GPIO.getmode()
		if current_mode is None:
			GPIO.setmode(GPIO.BOARD)
			self.gpio_board_mode = True
		elif current_mode != GPIO.BOARD:
			GPIO.setmode(current_mode)
			self.gpio_board_mode = False
		GPIO.setwarnings(False)

		self.light_state = False
		self._logger.info("--------------------------------------------")
		self._logger.info("OctoLight started, listening for GET request")
		self._logger.info("Light pin: {}, inverted_input: {}".format(
			self._settings.get(["light_pin"]),
			self._settings.get(["inverted_output"])
		))
		self._logger.info("--------------------------------------------")

		# Setting the default state of pin
		pin = self.get_light_pin()
		GPIO.setup(pin, GPIO.OUT)
		if bool(self._settings.get(["inverted_output"])):
			GPIO.output(pin, GPIO.HIGH)
		else:
			GPIO.output(pin, GPIO.LOW)

		#Because light is set to ff on startup we don't need to retrieve the current state
		"""
		r = self.light_state = GPIO.input(pin)
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
		pin = self.get_light_pin()
		GPIO.setup(pin, GPIO.OUT)

		self.light_state = not self.light_state

		# Sets the light state depending on the inverted output setting (XOR)
		if self.light_state ^ self._settings.get(["inverted_output"]):
			GPIO.output(pin, GPIO.HIGH)
		else:
			GPIO.output(pin, GPIO.LOW)

		self._logger.info("Got request. Light state on channel {}: {}".format(
			pin,
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

		else:
			return flask.jsonify(error="action not recognized")

	def on_event(self, event, payload):
		if event == Events.CLIENT_OPENED:
			self._plugin_manager.send_plugin_message(self._identifier, dict(isLightOn=self.light_state))
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
