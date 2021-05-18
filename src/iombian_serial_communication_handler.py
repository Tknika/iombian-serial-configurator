#!/usr/bin/env python3

import json
import logging
import serial
import threading

logger = logging.getLogger(__name__)


class IoMBianSerialConfiguratorHandler():

    SAVE_CONFIG_DELAY = 2

    def __init__(self, file_config_handler, port="/dev/ttyGS0", baudrate=115200, timeout=0.1):
        self.file_config_handler = file_config_handler
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_listener_thread = None
        self.listen = False

    def start(self):
        if self.file_config_handler.execute_command("is_configured"):
            logger.info("Device already configured, Serial Configurator Handler will not be started")
            self.stop()
            return
        logger.debug("Starting Serial Configurator Handler")
        self.listen = True
        self.serial_listener_thread = threading.Thread(target=self.__serial_listener)
        self.serial_listener_thread.start()

    def stop(self):
        logger.debug("Stopping Serial Configurator Handler")
        self.listen = False
        if self.serial_listener_thread:
            self.serial_listener_thread.join()
            self.serial_listener_thread = None

    def __serial_listener(self):
        number_of_curly_brackets = 0
        config_string = ""

        while self.listen:
            try:
                serial_conn = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
                logger.info(f"Connection established with serial port: '{self.port}'")
            except serial.serialutil.SerialException as error:
                logger.error(f"Serial port '{self.port}' cannot be found")
                break

            while(self.listen):
                try:
                    data = serial_conn.read()
                except serial.serialutil.SerialException as error:
                    logger.error("Serial exception reading serial connection!")
                    break

                if len(data) == 0:
                    continue

                try:
                    data_decoded = data.decode('utf-8')
                except:
                    logger.debug(f"Error decoding data as UTF-8: {data}")
                    continue

                if data_decoded == '{':
                    number_of_curly_brackets += 1
                elif data_decoded == '}':
                    number_of_curly_brackets -= 1

                config_string += data_decoded

                if number_of_curly_brackets == 0:
                    try:
                        config = json.loads(config_string)
                        logger.debug(config)
                        logger.info("New configuration received")
                        threading.Timer(self.SAVE_CONFIG_DELAY, self.file_config_handler.execute_command, ["save_config", config]).start()
                    except json.decoder.JSONDecodeError as error:
                        logger.debug("Non valid json string: {}".format(config_string))
                    config_string = ""

            serial_conn.close()
