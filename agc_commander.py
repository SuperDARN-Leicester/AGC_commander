
# AGC commander for python
# by Cassie Lakin
# September  11th 2022
# This version is for use on site in Finland. It has no logging which is done by another script on site

from PyQt5.QtWidgets import QApplication, QPushButton, QMainWindow, QLabel, \
    QComboBox, QCheckBox, QLCDNumber
from PyQt5 import uic
from PyQt5.QtCore import QTimer
from datetime import datetime
import sys
import serial
import pandas as pd
import time

ser = serial.Serial('/dev/ttyS0')     # For use in field
ser.baudrate = 9600
ser.bytesize = 8
ser.parity = 'N'
ser.stopbits = 1
ser.timeout = 1

# Main Data String Array in bytes.
# 0 "STX" byte is always 55(hex).
# 1 "addr" is target microcontroller address in the range 1-254 decimal.
# 2 "Len" is the length of the data field. This is always 1 for command packets.
# 3 "cmd" is the command number 1-13.
# 4 "bcc" is the block checksum. This is the least significant 8 bits of the sum of bytes 1-3.

# This is the main packet. It will change depending on commands.
packet_to_send = bytearray([0x55, 0x01, 0x01, 0x01, 0x03])
radar_position = pd.read_csv("/home/radar/UOL_scripts/AGC_commander/antenna_positions.csv")


# Setting up the User interface
class AGCUI(QMainWindow):
    def __init__(self):
        super(AGCUI, self).__init__()
        # Import my ui
        uic.loadUi("agc_commander_ui.ui", self)
        # Define widgets
        self.response = self.findChild(QLabel, "response")
        self.code_sent = self.findChild(QLabel, "code_sent")
        self.code_received = self.findChild(QLabel, "code_received")
        self.porta = self.findChild(QLabel, "port_A")
        self.portb = self.findChild(QLabel, "port_B")
        self.portc = self.findChild(QLabel, "port_C")
        self.fifteen_value = self.findChild(QLabel, "fifteen_value")
        self.five_value = self.findChild(QLabel, "five_value")
        self.five_hundred_value = self.findChild(QLabel, "five_hundred_value")
        self.minus_fifteen_value = self.findChild(QLabel, "minus_fifteen_value")
        self.fifty_value = self.findChild(QLabel, "fifty_value")
        self.temp_value = self.findChild(QLabel, "temp_value")
        self.f_power = self.findChild(QLabel, "f_power_value")
        self.r_power = self.findChild(QLabel, "r_power_value")

        self.pos_select = self.findChild(QComboBox, "position_number")

        self.current_time = self.findChild(QLCDNumber, "current_time")

        self.auto_reset_enabled = self.findChild(QCheckBox, "auto_reset_enabled")
        self.check_5 = self.findChild(QCheckBox, "check_5")
        self.check_500 = self.findChild(QCheckBox, "check_500")
        self.check_50 = self.findChild(QCheckBox, "check_50")
        self.check_15 = self.findChild(QCheckBox, "check_15")
        self.check_m15 = self.findChild(QCheckBox, "check_m15")
        self.inhibit_on = self.findChild(QCheckBox, "inhibit_on")
        self.relay_closed = self.findChild(QCheckBox, "relay_closed")
        self.cap1_fitted = self.findChild(QCheckBox, "cap1_fitted")
        self.cap2_fitted = self.findChild(QCheckBox, "cap2_fitted")
        self.bad_duty = self.findChild(QCheckBox, "bad_duty")
        self.agc_loop_closed = self.findChild(QCheckBox, "agc_loop_closed")
        self.power_active = self.findChild(QCheckBox, "power_active")
        self.bad_SWR = self.findChild(QCheckBox, "bad_SWR")

        self.radar_position = self.findChild(QPushButton, "set_position")
        self.c1opush = self.findChild(QPushButton, "open_c1")
        self.c1cpush = self.findChild(QPushButton, "close_c1")
        self.c2opush = self.findChild(QPushButton, "open_c2")
        self.c2cpush = self.findChild(QPushButton, "close_c2")
        self.reltpush = self.findChild(QPushButton, "trip_relay")
        self.relrpush = self.findChild(QPushButton, "reset_relay")
        self.agcopush = self.findChild(QPushButton, "open_agc")
        self.agccpush = self.findChild(QPushButton, "close_agc")
        self.pingpush = self.findChild(QPushButton, "ping_tx")
        self.pstatus = self.findChild(QPushButton, "position_status")
        self.enable_reset = self.findChild(QPushButton, "enable_reset")
        self.disable_reset = self.findChild(QPushButton, "disable_reset")
        self.reset_microcontroller = self.findChild(QPushButton, "reset_micro")
        self.reset_all = self.findChild(QPushButton, "reset_all")

        # actions
        self.reltpush.clicked.connect(self.relay_tripped)
        self.relrpush.clicked.connect(self.relay_reset)
        self.pingpush.clicked.connect(self.position_pinged)
        self.agcopush.clicked.connect(self.agc_open)
        self.agccpush.clicked.connect(self.agc_closed)
        self.c1opush.clicked.connect(self.c1_open)
        self.c1cpush.clicked.connect(self.c1_closed)
        self.c2opush.clicked.connect(self.c2_open)
        self.c2cpush.clicked.connect(self.c2_closed)
        self.pstatus.clicked.connect(self.pos_status)
        self.enable_reset.clicked.connect(self.auto_enable)
        self.disable_reset.clicked.connect(self.auto_disable)
        self.reset_microcontroller.clicked.connect(self.reset_mic)
        self.reset_all.clicked.connect(self.reset_all_micros)
        # Clock timers
        self.timer = QTimer()
        self.timer.timeout.connect(self.clock_current)
        # Timer and update part
        self.timer.start(1000)
        # Call the function clock_current
        self.clock_current()
        # Show the app
        self.show()

    def clock_current(self):
        time_now = datetime.now()
        # Format to english style date
        formatted_time = time_now.strftime("%d-%m-%Y"   "  %T")
        self.current_time.setDigitCount(20)
        self.current_time.display(formatted_time)

    def position_pinged(self):
        radar = (int(self.pos_select.currentText())-1)
        true_radar_position = (radar_position.loc[radar].at['agc'])
        rad_value = int(true_radar_position, 16)
        packet_to_send[1] = rad_value
        packet_to_send[3] = 0x0b
        packet_to_send[4] = (sum(packet_to_send[1:4]))
        ser.write(packet_to_send)
        data_received = ser.readall()
        expected_response = packet_to_send[0:2]
        data_received_conv = (data_received).hex()
        tx_read = (packet_to_send).hex()
        rx = str(data_received_conv)
        tx = str(tx_read)
        readout_rx = [rx[i:i + 2] for i in range(0, len(rx), 2)]
        readout_tx = [tx[i:i + 2] for i in range(0, len(tx), 2)]
        self.code_sent.setText(str(readout_tx))
        self.code_received.setText(str(readout_rx))

        if data_received == expected_response:
            self.response.setText(f'Ping Good')
        else:
            self.response.setText(f" NO RESPONSE!")

    def relay_tripped(self):
        radar = (int(self.pos_select.currentText()) - 1)
        true_radar_position = (radar_position.loc[radar].at['agc'])
        rad_value = int(true_radar_position, 16)
        packet_to_send[1] = rad_value
        packet_to_send[3] = 0x03
        packet_to_send[4] = (sum(packet_to_send[1:4]))
        ser.write(packet_to_send)
        data_received = ser.readall()
        expected_response = packet_to_send[0:2]
        data_received_conv = (data_received).hex()
        tx_read = (packet_to_send).hex()
        rx = str(data_received_conv)
        tx = str(tx_read)
        readout_rx = [rx[i:i + 2] for i in range(0, len(rx), 2)]
        readout_tx = [tx[i:i + 2] for i in range(0, len(tx), 2)]
        self.code_sent.setText(str(readout_tx))
        self.code_received.setText(str(readout_rx))

        if data_received == expected_response:
            self.relay_closed.setChecked(False)
            self.response.setText(f"response good")
        else:
            self.response.setText(f" NO RESPONSE!")

    def relay_reset(self):
        radar = (int(self.pos_select.currentText()) - 1)
        true_radar_position = (radar_position.loc[radar].at['agc'])
        rad_value = int(true_radar_position, 16)
        packet_to_send[1] = rad_value
        packet_to_send[3] = 0x02
        packet_to_send[4] = (sum(packet_to_send[1:4]))
        ser.write(packet_to_send)
        data_received = ser.readall()
        expected_response = packet_to_send[0:2]
        data_received_conv = (data_received).hex()
        tx_read = (packet_to_send).hex()
        rx = str(data_received_conv)
        tx = str(tx_read)
        readout_rx = [rx[i:i + 2] for i in range(0, len(rx), 2)]
        readout_tx = [tx[i:i + 2] for i in range(0, len(tx), 2)]
        self.code_sent.setText(str(readout_tx))
        self.code_received.setText(str(readout_rx))

        if data_received == expected_response:
            self.relay_closed.setChecked(True)
            self.response.setText(f"response good")
        else:
            self.response.setText(f" NO RESPONSE!")

    def agc_open(self):
        radar = (int(self.pos_select.currentText()) - 1)
        true_radar_position = (radar_position.loc[radar].at['agc'])
        rad_value = int(true_radar_position, 16)
        packet_to_send[1] = rad_value
        packet_to_send[3] = 0x05
        packet_to_send[4] = (sum(packet_to_send[1:4]))
        ser.write(packet_to_send)
        data_received = ser.readall()
        expected_response = packet_to_send[0:2]
        data_received_conv = (data_received).hex()
        tx_read = (packet_to_send).hex()
        rx = str(data_received_conv)
        tx = str(tx_read)
        readout_rx = [rx[i:i + 2] for i in range(0, len(rx), 2)]
        readout_tx = [tx[i:i + 2] for i in range(0, len(tx), 2)]
        self.code_sent.setText(str(readout_tx))
        self.code_received.setText(str(readout_rx))

        if data_received == expected_response:
            self.agc_loop_closed.setChecked(False)
            self.response.setText(f"response good")
        else:
            self.response.setText(f" NO RESPONSE!")

    def agc_closed(self):
        radar = (int(self.pos_select.currentText()) - 1)
        true_radar_position = (radar_position.loc[radar].at['agc'])
        rad_value = int(true_radar_position, 16)
        packet_to_send[1] = rad_value
        packet_to_send[3] = 0x04
        packet_to_send[4] = (sum(packet_to_send[1:4]))
        ser.write(packet_to_send)
        data_received = ser.readall()
        expected_response = packet_to_send[0:2]
        data_received_conv = (data_received).hex()
        tx_read = (packet_to_send).hex()
        rx = str(data_received_conv)
        tx = str(tx_read)
        readout_rx = [rx[i:i + 2] for i in range(0, len(rx), 2)]
        readout_tx = [tx[i:i + 2] for i in range(0, len(tx), 2)]
        self.code_sent.setText(str(readout_tx))
        self.code_received.setText(str(readout_rx))

        if data_received == expected_response:
            self.agc_loop_closed.setChecked(True)
            self.response.setText(f"response good")
        else:
            self.response.setText(f" NO RESPONSE!")

    def c1_open(self):
        radar = (int(self.pos_select.currentText()) - 1)
        true_radar_position = (radar_position.loc[radar].at['agc'])
        rad_value = int(true_radar_position, 16)
        packet_to_send[1] = rad_value
        packet_to_send[3] = 0x07
        packet_to_send[4] = (sum(packet_to_send[1:4]))
        ser.write(packet_to_send)
        data_received = ser.readall()
        expected_response = packet_to_send[0:2]
        data_received_conv = (data_received).hex()
        tx_read = (packet_to_send).hex()
        rx = str(data_received_conv)
        tx = str(tx_read)
        readout_rx = [rx[i:i + 2] for i in range(0, len(rx), 2)]
        readout_tx = [tx[i:i + 2] for i in range(0, len(tx), 2)]
        self.code_sent.setText(str(readout_tx))
        self.code_received.setText(str(readout_rx))

        if data_received == expected_response:
            self.cap1_fitted.setChecked(False)
            self.response.setText(f"response good")
        else:
            self.response.setText(f" NO RESPONSE!")

    def c1_closed(self):
        radar = (int(self.pos_select.currentText()) - 1)
        true_radar_position = (radar_position.loc[radar].at['agc'])
        rad_value = int(true_radar_position, 16)
        packet_to_send[1] = rad_value
        packet_to_send[3] = 0x06
        packet_to_send[4] = (sum(packet_to_send[1:4]))
        ser.write(packet_to_send)
        data_received = ser.readall()
        expected_response = packet_to_send[0:2]
        data_received_conv = (data_received).hex()
        tx_read = (packet_to_send).hex()
        rx = str(data_received_conv)
        tx = str(tx_read)
        readout_rx = [rx[i:i + 2] for i in range(0, len(rx), 2)]
        readout_tx = [tx[i:i + 2] for i in range(0, len(tx), 2)]
        self.code_sent.setText(str(readout_tx))
        self.code_received.setText(str(readout_rx))

        if data_received == expected_response:
            self.cap1_fitted.setChecked(True)
            self.response.setText(f"response good")
        else:
            self.response.setText(f" NO RESPONSE!")

    def c2_open(self):
        radar = (int(self.pos_select.currentText()) - 1)
        true_radar_position = (radar_position.loc[radar].at['agc'])
        rad_value = int(true_radar_position, 16)
        packet_to_send[1] = rad_value
        packet_to_send[3] = 0x09
        packet_to_send[4] = (sum(packet_to_send[1:4]))
        ser.write(packet_to_send)
        data_received = ser.readall()
        expected_response = packet_to_send[0:2]
        data_received_conv = (data_received).hex()
        tx_read = (packet_to_send).hex()
        rx = str(data_received_conv)
        tx = str(tx_read)
        readout_rx = [rx[i:i + 2] for i in range(0, len(rx), 2)]
        readout_tx = [tx[i:i + 2] for i in range(0, len(tx), 2)]
        self.code_sent.setText(str(readout_tx))
        self.code_received.setText(str(readout_rx))

        if data_received == expected_response:
            self.cap2_fitted.setChecked(False)
            self.response.setText(f"response good")
        else:
            self.response.setText(f" NO RESPONSE!")

    def c2_closed(self):
        radar = (int(self.pos_select.currentText()) - 1)
        true_radar_position = (radar_position.loc[radar].at['agc'])
        rad_value = int(true_radar_position, 16)
        packet_to_send[1] = rad_value
        packet_to_send[3] = 0x08
        packet_to_send[4] = (sum(packet_to_send[1:4]))
        ser.write(packet_to_send)
        data_received = ser.readall()
        expected_response = packet_to_send[0:2]
        data_received_conv = (data_received).hex()
        tx_read = (packet_to_send).hex()
        rx = str(data_received_conv)
        tx = str(tx_read)
        readout_rx = [rx[i:i + 2] for i in range(0, len(rx), 2)]
        readout_tx = [tx[i:i + 2] for i in range(0, len(tx), 2)]
        self.code_sent.setText(str(readout_tx))
        self.code_received.setText(str(readout_rx))

        if data_received == expected_response:
            self.cap2_fitted.setChecked(True)
            self.response.setText(f"response good")
        else:
            self.response.setText(f" NO RESPONSE!")

    def pos_status(self):
        radar = (int(self.pos_select.currentText()) - 1)
        true_radar_position = (radar_position.loc[radar].at['agc'])
        rad_value = int(true_radar_position, 16)
        packet_to_send[1] = rad_value
        packet_to_send[3] = 0x01
        packet_to_send[4] = (sum(packet_to_send[1:4]))
        ser.write(packet_to_send)
        time.sleep(0.2)
        data_received = ser.readall()
        expected_response = packet_to_send[0:1]
        data_received_conv = (data_received).hex()
        tx_read = (packet_to_send).hex()
        rx = str(data_received_conv)
        tx = str(tx_read)
        readout_rx = [rx[i:i + 2] for i in range(0, len(rx), 2)]
        readout_tx = [tx[i:i + 2] for i in range(0, len(tx), 2)]

        self.code_sent.setText(str(readout_tx))
        self.code_received.setText(str(readout_rx))

        if data_received[0:1] == expected_response:
            self.response.setText("response as shown")
            five = (int(readout_rx[4], 16))
            five_hundred = (int(readout_rx[6], 16))
            fifteen = (int(readout_rx[5], 16))
            minus_fifteen = (int(readout_rx[7], 16))
            fifty = (int(readout_rx[8], 16))
            temp = readout_rx[9]
            forward = readout_rx[10]
            reflected = readout_rx[11]
            self.temp_value.setText(str(temp))
            self.f_power.setText(str(forward))
            self.r_power.setText(str(reflected))
            five_volts = (5 / 255)
            value5 = round(((five * five_volts) * 2), 2)
            self.five_value.setText(str(value5))

            fifteen_volts = (15 / 255)
            value15 = round(((fifteen * fifteen_volts) * 2), 2)
            self.fifteen_value.setText(str(value15))

            fifty_volts = (50 / 255)
            value50 = round(((fifty * fifty_volts) * 2), 2)
            self.fifty_value.setText(str(value50))

            minus_fifteen_volts = (-15 / 255)
            value15m = round(((minus_fifteen * minus_fifteen_volts) * 2), 2)
            self.minus_fifteen_value.setText(str(value15m))

            five_hundred_volts = (500 / 255)
            value500 = round(((five_hundred * five_hundred_volts) * 2), 2)
            self.five_hundred_value.setText(str(value500))

            port_a = (readout_rx[12])
            port_b = (readout_rx[13])
            port_c = (readout_rx[14])
            scale = 16
            num_of_bits = 8
            bin_porta = bin(int(port_a, scale))[2:].zfill(num_of_bits)
            bin_portb = bin(int(port_b, scale))[2:].zfill(num_of_bits)
            bin_portc = bin(int(port_c, scale))[2:].zfill(num_of_bits)
            self.porta.setText(str(bin_porta))
            self.portb.setText(str(bin_portb))
            self.portc.setText(str(bin_portc))
            print(bin_porta, bin_portb, bin_portc)

            if bin_porta[7] == "1":
                self.relay_closed.setChecked(True)
            else:
                self.relay_closed.setChecked(False)
            if bin_porta[6] == "1":
                self.inhibit_on.setChecked(True)
            else:
                self.inhibit_on.setChecked(False)
            if bin_porta[5] == "1":
                self.power_active.setChecked(True)
            else:
                self.power_active.setChecked(False)
            if bin_portb[5] == "1":
                self.cap1_fitted.setChecked(True)
            else:
                self.cap1_fitted.setChecked(False)
            if bin_portb[4] == "1":
                self.cap2_fitted.setChecked(True)
            else:
                self.cap2_fitted.setChecked(False)
            if bin_portb[3] == "1":
                self.agc_loop_closed.setChecked(True)
            else:
                self.agc_loop_closed.setChecked(False)
            if bin_portc[7] == "1":
                self.bad_duty.setChecked(False)
            else:
                self.bad_duty.setChecked(True)
            if bin_portc[6] == "1":
                self.bad_SWR.setChecked(False)
            else:
                self.bad_SWR.setChecked(True)
            if bin_portc[5] == "1":
                self.check_5.setChecked(True)
            else:
                self.check_5.setChecked(False)
            if bin_portc[4] == "1":
                self.check_15.setChecked(True)
            else:
                self.check_15.setChecked(False)
            if bin_portc[3] == "1":
                self.check_500.setChecked(True)
            else:
                self.check_500.setChecked(False)
            if bin_portc[2] == "1":
                self.check_m15.setChecked(True)
            else:
                self.check_m15.setChecked(False)
            if bin_portc[1] == "1":
                self.check_50.setChecked(True)
        else:
            self.response.setText("NO Response!!!")

    def reset_mic(self):
        radar = (int(self.pos_select.currentText()) - 1)
        true_radar_position = (radar_position.loc[radar].at['agc'])
        rad_value = int(true_radar_position, 16)
        packet_to_send[1] = rad_value
        packet_to_send[3] = 0x0a
        packet_to_send[4] = (sum(packet_to_send[1:4]))
        ser.write(packet_to_send)
        data_received = ser.readall()
        expected_response = packet_to_send[0:2]
        data_received_conv = (data_received).hex()
        tx_read = (packet_to_send).hex()
        rx = str(data_received_conv)
        tx = str(tx_read)
        readout_rx = [rx[i:i + 2] for i in range(0, len(rx), 2)]
        readout_tx = [tx[i:i + 2] for i in range(0, len(tx), 2)]
        self.code_sent.setText(str(readout_tx))
        self.code_received.setText(str(readout_rx))

        if data_received == expected_response:
            self.response.setText(f"Micro reset")
            self.relay_closed.setChecked(True)
            self.agc_loop_closed.setChecked(True)
            self.cap1_fitted.setChecked(True)
            self.cap2_fitted.setChecked(False)
            self.auto_reset_enabled.setChecked(False)
        else:
            self.response.setText(f"no response")
        self.pos_status()

    def reset_all_micros(self):
        self.response.setText(f"Please wait")
        for radar in range(16):
            true_radar_position = (radar_position.loc[radar].at['agc'])
            rad_value = int(true_radar_position, 16)
            packet_to_send[1] = (rad_value)
            packet_to_send[3] = 0x0a
            packet_to_send[4] = (sum(packet_to_send[1:4]))
            ser.write(packet_to_send)
        self.response.setText(f"ALL MICROCONTROLLERS RESET")

    def auto_enable(self):
        radar = (int(self.pos_select.currentText()) - 1)
        true_radar_position = (radar_position.loc[radar].at['agc'])
        rad_value = int(true_radar_position, 16)
        packet_to_send[1] = rad_value
        packet_to_send[3] = 0x0c
        packet_to_send[4] = (sum(packet_to_send[1:4]))
        ser.write(packet_to_send)
        data_received = ser.readall()
        expected_response = packet_to_send[0:2]
        data_received_conv = (data_received).hex()
        tx_read = (packet_to_send).hex()
        rx = str(data_received_conv)
        tx = str(tx_read)
        readout_rx = [rx[i:i + 2] for i in range(0, len(rx), 2)]
        readout_tx = [tx[i:i + 2] for i in range(0, len(tx), 2)]
        self.code_sent.setText(str(readout_tx))
        self.code_received.setText(str(readout_rx))
        if data_received == expected_response:
            self.auto_reset_enabled.setChecked(True)
        else:
            self.response.setText(f"no response")

    def auto_disable(self):
        radar = (int(self.pos_select.currentText()) - 1)
        true_radar_position = (radar_position.loc[radar].at['agc'])
        rad_value = int(true_radar_position, 16)
        packet_to_send[1] = rad_value
        packet_to_send[3] = 0x0d
        packet_to_send[4] = (sum(packet_to_send[1:4]))
        ser.write(packet_to_send)
        data_received = ser.readall()
        expected_response = packet_to_send[0:2]
        data_received_conv = (data_received).hex()
        tx_read = (packet_to_send).hex()
        rx = str(data_received_conv)
        tx = str(tx_read)
        readout_rx = [rx[i:i + 2] for i in range(0, len(rx), 2)]
        readout_tx = [tx[i:i + 2] for i in range(0, len(tx), 2)]
        self.code_sent.setText(str(readout_tx))
        self.code_received.setText(str(readout_rx))

        if data_received == expected_response:
            self.auto_reset_enabled.setChecked(False)
        else:
            self.response.setText(f"no response")


# Initialise
app = QApplication(sys.argv)
UIWindow = AGCUI()
app.exec_()
